"""Check a reviewed, byte-pinned project against the existing public planner contract."""
import toolkit as t


def attachment_pin(attachments):
    return t.digest(t.encode([{'id': key, 'sha256': t.digest(attachments[key])}
                              for key in sorted(attachments)]))


def envelope(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'project_sha256', 'attachments', 'review'})
    t.require(value['format'] == 'outlands-planner-handoff-v1', 'HANDOFF_FORMAT_INVALID')
    t.sha(value['project_sha256'])
    items = value['attachments']
    t.require(type(items) is list and len(items) <= 16, 'ATTACHMENT_LIMIT')
    for item in items:
        t.fields(item, {'id', 'sha256'})
        t.identifier(item['id']); t.sha(item['sha256'])
    t.require(len({v['id'] for v in items}) == len(items), 'DUPLICATE_ATTACHMENT')
    review = value['review']
    t.fields(review, {'project_sha256', 'attachments_sha256', 'inputs_reviewed',
                      'mappings_reviewed', 'policies_reviewed', 'plan_only'})
    t.sha(review['project_sha256']); t.sha(review['attachments_sha256'])
    for key in ('inputs_reviewed', 'mappings_reviewed', 'policies_reviewed', 'plan_only'):
        t.require(type(review[key]) is bool, 'REVIEW_BOOLEAN_REQUIRED')
    return value


def check(project_raw, handoff_raw, attachments):
    value = envelope(handoff_raw)
    t.require(type(project_raw) is bytes and len(project_raw) <= t.MAX_INPUT,
              'INPUT_LIMIT')
    t.require(type(attachments) is dict and set(attachments) == {v['id'] for v in value['attachments']},
              'BINDING_COVERAGE_INVALID')
    t.require(all(type(v) is bytes and len(v) <= t.MAX_INPUT for v in attachments.values()) and
              sum(map(len, attachments.values())) <= 16 * 1024 * 1024, 'TOTAL_INPUT_LIMIT')
    # Validate strict JSON before importing any model dependency. Nothing is
    # imported from a caller-selected directory, project or attachment.
    t.decode(project_raw)
    try:
        from planner_contract import project
    except ImportError:
        raise t.Rejected('PLANNER_DEPENDENCIES_REQUIRED') from None
    try:
        parsed = project.parse(project_raw)
        plan = project.calculate(parsed)
    except (ValueError, TypeError, KeyError, ArithmeticError, RecursionError):
        raise t.Rejected('PLANNER_PROJECT_INVALID') from None
    issues = []
    actual = t.digest(project_raw)
    if actual != value['project_sha256']:
        issues.append('PROJECT_PIN_MISMATCH')
    if value['review']['project_sha256'] != actual:
        issues.append('STALE_PROJECT_REVIEW')
    for item in value['attachments']:
        if t.digest(attachments[item['id']]) != item['sha256']:
            issues.append('ATTACHMENT_PIN_MISMATCH')
    if value['review']['attachments_sha256'] != attachment_pin(attachments):
        issues.append('STALE_ATTACHMENT_REVIEW')
    if not all(value['review'][key] is True for key in
               ('inputs_reviewed', 'mappings_reviewed', 'policies_reviewed', 'plan_only')):
        issues.append('EXPLICIT_REVIEW_INCOMPLETE')
    t.require(plan['mode'] == 'LOCAL_ADVISORY_PLAN' and
              all(plan[k] is False for k in ('external_system_writes', 'lot_ids_reserved',
                                            'shipment_execution_authorized')), 'PLAN_ONLY_REQUIRED')
    return dict(format='outlands-planner-handoff-check-v1', status='PASS' if not issues else 'REVIEW_REQUIRED',
                mode='PLAN_ONLY', project_id=parsed.project_id, project_sha256=actual,
                handoff_sha256=t.digest(handoff_raw), attachments_sha256=attachment_pin(attachments),
                eligible_for_explicit_import=not issues, issues=sorted(set(issues)),
                planner_contract='outlands-planning-project-v1',
                project_transformed=False, project_imported=False, external_system_writes=False,
                lot_ids_reserved=False, shipment_execution_authorized=False,
                review_identity_independently_verified=False)


def main(argv=None):
    parser = t.Parser(prog='planner-handoff-checker', description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--handoff', required=True)
    parser.add_argument('--attachment', nargs=2, action='append', default=[], metavar=('ID', 'FILE'))
    parser.add_argument('--out')
    def operation(args):
        raw = t.read(args.handoff)
        value = envelope(raw)
        selected = t.bindings(args.attachment)
        t.require(set(selected) == {v['id'] for v in value['attachments']}, 'BINDING_COVERAGE_INVALID')
        return check(t.read(args.project), raw, t.buffers(selected))
    return t.run(parser, operation, argv)


if __name__ == '__main__':
    raise SystemExit(main())

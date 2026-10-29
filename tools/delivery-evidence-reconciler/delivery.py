"""Assess declared evidence only. No transport, retry, promotion or provider lookup."""
import toolkit as t

OUTCOMES = ('retryable_not_accepted','permanent_not_accepted','accepted','uncertain')


def reconcile(raw):
    value = t.decode(raw)
    t.fields(value, {'format','max_attempts','messages'})
    t.require(value['format'] == 'outlands-delivery-evidence-v1', 'EVIDENCE_FORMAT_INVALID')
    maximum = t.integer(value['max_attempts'],5,1)
    messages = value['messages']
    t.require(type(messages) is list and 1 <= len(messages) <= 64, 'MESSAGE_LIMIT')
    seen, rows = set(), []
    for item in messages:
        t.fields(item, {'id','content_sha256','attempts','reports'})
        key = t.identifier(item['id']); t.sha(item['content_sha256'])
        t.require(key not in seen, 'DUPLICATE_MESSAGE'); seen.add(key)
        attempts, reports = item['attempts'], item['reports']
        t.require(type(attempts) is list and len(attempts) <= 5 and type(reports) is list and len(reports) <= 8, 'EVIDENCE_LIMIT')
        state, issues, previous_tick, previous = 'PENDING', [], None, None
        accepted = None
        for index, attempt in enumerate(attempts,1):
            t.fields(attempt, {'number','tick','outcome','receipt'})
            t.require(t.integer(attempt['number'],5,1) == index, 'ATTEMPT_SEQUENCE_INVALID')
            tick = t.integer(attempt['tick'])
            t.require(previous_tick is None or tick >= previous_tick, 'TICK_ORDER_INVALID')
            outcome = attempt['outcome']
            t.require(type(outcome) is str and outcome in OUTCOMES, 'OUTCOME_INVALID')
            if outcome == 'accepted':
                t.identifier(attempt['receipt'])
            else:
                t.require(attempt['receipt'] is None, 'UNEXPECTED_RECEIPT')
            if index > maximum:
                issues.append('ATTEMPT_LIMIT_EXCEEDED')
            if previous is not None:
                if previous != 'retryable_not_accepted' or index > maximum:
                    issues.append('REPLAY_AFTER_TERMINAL_OR_UNCERTAIN')
                elif tick < previous_tick + 2 ** (index - 2):
                    issues.append('RETRY_BEFORE_DECLARED_BACKOFF')
            if outcome == 'uncertain':
                issues.append('ACCEPTANCE_UNCERTAIN')
                state = 'REVIEW_REQUIRED'
            elif outcome == 'accepted':
                accepted = (index,attempt['receipt']); state = 'ACCEPTED_PENDING_EVIDENCE'
            elif outcome == 'permanent_not_accepted' or index >= maximum:
                state = 'FAILED'
            else:
                state = 'DEFINITE_NON_ACCEPTANCE_RECORDED'
                if tick + 2 ** (index - 1) > 10**12:
                    issues.append('RETRY_TICK_OVERFLOW')
            previous, previous_tick = outcome, tick
        distinct, duplicates = set(), 0
        for report in reports:
            t.fields(report, {'attempt','receipt','outcome'})
            number = t.integer(report['attempt'],5,1)
            receipt = t.identifier(report['receipt'])
            outcome = report['outcome']
            t.require(type(outcome) is str and outcome in ('delivered','bounced'), 'REPORT_OUTCOME_INVALID')
            identity = (number,receipt,outcome)
            if identity in distinct:
                duplicates += 1
            distinct.add(identity)
            if accepted is None or (number,receipt) != accepted:
                issues.append('REPORT_NOT_MATCHED_TO_ACCEPTANCE')
        if len(distinct) > 1:
            issues.append('CONFLICTING_REPORTS')
        if issues:
            state = 'REVIEW_REQUIRED'
        elif distinct:
            state = 'DELIVERY_REPORTED' if next(iter(distinct))[2] == 'delivered' else 'BOUNCE_REPORTED'
        rows.append(dict(id=key, content_sha256=item['content_sha256'], state=state,
                         attempts=len(attempts), reports=len(reports), duplicate_reports=duplicates,
                         issues=sorted(set(issues)), retry_permitted=False))
    return dict(status='REVIEW_REQUIRED' if any(r['issues'] for r in rows) else 'PASS',
                format='outlands-delivery-review-v1', input_sha256=t.digest(raw), messages=rows,
                real_delivery_verified=False, target_changes_performed=False)


def main(argv=None):
    p = t.Parser(description='Reconcile explicit evidence; never send, retry or verify real delivery.')
    p.add_argument('--input', required=True)
    p.add_argument('--out')
    return t.run(p, lambda a: reconcile(t.read(a.input)), argv)


if __name__ == '__main__':
    raise SystemExit(main())

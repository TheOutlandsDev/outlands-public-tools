"""Installed review/change methodology on embedded fictional declarations only."""
import hashlib
import json
from importlib.resources import files
from outlands_review_queue_contract_checker import queues
from outlands_correction_lineage_checker import corrections
from outlands_approval_scope_checker import approvals
from outlands_change_impact_planner import impacts


def example(package, name='input.json'):
    return json.loads(files(package).joinpath('examples', name).read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


def pin(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def exercise():
    lineage_input = example('outlands_correction_lineage_checker')
    lineage = corrections.check(encoded(lineage_input))
    assert lineage['status'] == 'PASS' and lineage['assessment']['all_histories_complete']
    after = lineage_input['snapshots'][1]
    selected = {'id': after['record'], 'revision': after['revision'], 'artifact_sha256': after['artifact_sha256']}
    approval_input = example('outlands_approval_scope_checker'); approval_input['items'] = [selected]
    for event in approval_input['events']:
        event.update(item=selected['id'], item_revision=selected['revision'], item_sha256=pin(selected))
    approval = approvals.check(encoded(approval_input))
    assert approval['status'] == 'PASS' and approval['assessment']['all_declared_scopes_covered']
    active_ids = approval['assessment']['items'][0]['active_grant_ids']
    roles = sorted({event['role'] for event in approval_input['events'] if event['id'] in active_ids})
    queue_input = example('outlands_review_queue_contract_checker'); queue_input['items'] = [selected]
    assert queue_input['policy'] == approval_input['policy']
    queue_input['entries'][0].update(item=selected['id'], item_revision=selected['revision'],
                                     item_sha256=pin(selected), covered_roles=roles)
    queue = queues.check(encoded(queue_input))
    assert queue['status'] == 'PASS' and queue['assessment']['all_covered_and_unblocked']
    assert queue['items_sha256'] == approval['items_sha256']
    impact_input = example('outlands_change_impact_planner')
    assert impact_input['nodes'][0] == selected
    impact = impacts.check(encoded(impact_input))
    assert impact['status'] == 'PASS' and len(impact['assessment']['recheck_nodes']) == 3
    assert impact['assessment']['unaffected_node_ids'] == ['hvac-unrelated-demo']
    revoked_input = example('outlands_approval_scope_checker', 'needs-review.json')
    revoked = approvals.check(encoded(revoked_input))
    assert revoked['status'] == 'REVIEW_REQUIRED'
    assert revoked['assessment']['items'][0]['missing_roles'] == ['quality']
    assert revoked['review_scope_sha256'] is None
    active_ids = revoked['assessment']['items'][0]['active_grant_ids']
    queue_input['entries'][0]['covered_roles'] = sorted({row['role'] for row in revoked_input['events'] if row['id'] in active_ids})
    rechecked = queues.check(encoded(queue_input))
    assert rechecked['status'] == 'REVIEW_REQUIRED'
    assert not rechecked['assessment']['items'][0]['ready_for_manual_review']
    invalid_graph = impacts.check(encoded(example('outlands_change_impact_planner', 'needs-review.json')))
    assert invalid_graph['status'] == 'REVIEW_REQUIRED' and invalid_graph['assessment'] is None
    assert invalid_graph['review_scope_sha256'] is None
    for report in (lineage, approval, queue, impact, revoked, rechecked, invalid_graph):
        for field in ('artifact_bytes_verified', 'reviewer_identity_verified', 'approval_authority_verified',
                      'records_changed', 'execution_performed', 'target_changes_performed'):
            assert report[field] is False
    return {'status': 'PASS', 'declared_revisions': 2, 'covered_roles': 2, 'recheck_nodes': 3,
            'revoked_role': 'quality', 'revocation_requires_queue_review': True,
            'invalid_graph_assessment': None, 'records_changed': False}


if __name__ == '__main__':
    print(json.dumps(exercise(), sort_keys=True))

"""Validate or compare an invented bounded workflow XML graph without execution."""
from collections import deque

import toolkit as t


def parse(raw):
    root = t.xml(raw)
    t.require(root.tag == 'workflow' and set(root.attrib) == {'id', 'version'} and
              [x.tag for x in root] == ['steps', 'transitions'], 'WORKFLOW_SCHEMA_INVALID')
    t.identifier(root.attrib['id'])
    version = root.attrib['version']
    t.require(1 <= len(version) <= 7 and version.isascii() and version.isdigit() and version == str(int(version)) and
              1 <= int(version) <= 1000000, 'WORKFLOW_VERSION_INVALID')
    steps, transitions = {}, {}
    t.require(not root[0].attrib and not root[1].attrib and 2 <= len(root[0]) <= 128 and
              len(root[1]) <= 512, 'WORKFLOW_LIMIT')
    for parent in root.iter():
        t.require(not (parent.text or '').strip() and not (parent.tail or '').strip(),
                  'WORKFLOW_TEXT_UNSUPPORTED')
    for element in root[0]:
        t.require(element.tag == 'step' and not len(element) and
                  set(element.attrib) == {'id', 'kind'}, 'STEP_SCHEMA_INVALID')
        key, kind = element.attrib['id'], element.attrib['kind']
        t.identifier(key)
        t.require(key not in steps and kind in ('start', 'process', 'end'), 'STEP_INVALID')
        steps[key] = kind
    for element in root[1]:
        t.require(element.tag == 'transition' and not len(element) and
                  set(element.attrib) == {'id', 'from', 'to', 'kind'}, 'TRANSITION_SCHEMA_INVALID')
        key = element.attrib['id']; t.identifier(key)
        value = {k: element.attrib[k] for k in ('from', 'to', 'kind')}
        t.require(key not in transitions and value['from'] in steps and value['to'] in steps and
                  value['kind'] in ('forward', 'rework'), 'TRANSITION_INVALID')
        transitions[key] = value
    t.require(sum(v == 'start' for v in steps.values()) == 1 and 'end' in steps.values(),
              'WORKFLOW_TERMINALS_INVALID')
    t.require(len({(v['from'], v['to'], v['kind']) for v in transitions.values()}) == len(transitions),
              'TRANSITION_DUPLICATE_EDGE')
    return dict(id=root.attrib['id'], version=int(version), steps=dict(sorted(steps.items())),
                transitions=dict(sorted(transitions.items())))


def validate(graph):
    steps, edges = graph['steps'], graph['transitions']
    forward = {key: set() for key in steps}
    reverse = {key: set() for key in steps}
    issues = []
    for key, edge in edges.items():
        if edge['kind'] == 'forward':
            forward[edge['from']].add(edge['to'])
            reverse[edge['to']].add(edge['from'])
        if edge['from'] == edge['to']:
            issues.append(dict(code='SELF_TRANSITION', id=key))
    start = next(key for key in steps if steps[key] == 'start')
    ends = {key for key in steps if steps[key] == 'end'}
    def reach(origins, adjacency):
        seen, pending = set(origins), list(origins)
        while pending:
            for target in adjacency[pending.pop()]:
                if target not in seen:
                    seen.add(target); pending.append(target)
        return seen
    incoming = {key: len(reverse[key]) for key in steps}
    pending = deque(sorted(key for key in steps if incoming[key] == 0))
    visited = 0
    while pending:
        key = pending.popleft(); visited += 1
        for target in sorted(forward[key]):
            incoming[target] -= 1
            if not incoming[target]:
                pending.append(target)
    if visited != len(steps):
        issues.append(dict(code='FORWARD_CYCLE', id=None))
    for key in sorted(set(steps) - reach({start}, forward)):
        issues.append(dict(code='UNREACHABLE_FROM_START', id=key))
    for key in sorted(set(steps) - reach(ends, reverse)):
        issues.append(dict(code='NO_FORWARD_PATH_TO_END', id=key))
    if reverse[start]:
        issues.append(dict(code='START_HAS_FORWARD_INPUT', id=start))
    for end in sorted(ends):
        if forward[end]:
            issues.append(dict(code='END_HAS_FORWARD_OUTPUT', id=end))
    for key, edge in edges.items():
        if edge['kind'] == 'rework' and (edge['from'] == edge['to'] or
                edge['from'] not in reach({edge['to']}, forward)):
            issues.append(dict(code='REWORK_TARGET_NOT_FORWARD_ANCESTOR', id=key))
    return issues


def check(raw, before_raw=None):
    graph = parse(raw)
    issues = [dict(side='after', **v) for v in validate(graph)]
    result = dict(format='outlands-workflow-check-v1', status='PASS', sha256=t.digest(raw),
                  graph=graph, issues=issues, external_system_writes=False, workflow_executed=False)
    if before_raw is not None:
        before = parse(before_raw)
        result['before_sha256'] = t.digest(before_raw)
        issues.extend(dict(side='before', **v) for v in validate(before))
        if before['id'] != graph['id']:
            issues.append(dict(side='both', code='WORKFLOW_ID_MISMATCH', id=None))
        if graph['version'] < before['version']:
            issues.append(dict(side='after', code='VERSION_REGRESSION', id=None))
        changes = []
        for section in ('steps', 'transitions'):
            for key in sorted(before[section].keys() | graph[section].keys()):
                old, new = before[section].get(key), graph[section].get(key)
                if old != new:
                    changes.append(dict(section=section, id=key, before=old, after=new))
        if changes and graph['version'] <= before['version']:
            issues.append(dict(side='after', code='CHANGED_GRAPH_NEEDS_NEW_VERSION', id=None))
        result['changes'] = changes if not issues else None
        result['version_changed'] = before['version'] != graph['version']
        result['status'] = 'DIFFERENCES' if changes or result['version_changed'] else 'MATCH'
    if issues:
        result['status'] = 'REVIEW_REQUIRED'
    return result


def main(argv=None):
    parser = t.Parser(prog='xml-workflow-checker', description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--before')
    parser.add_argument('--out')
    return t.run(parser, lambda a: check(t.read(a.input), t.read(a.before) if a.before else None), argv)


if __name__ == '__main__':
    raise SystemExit(main())

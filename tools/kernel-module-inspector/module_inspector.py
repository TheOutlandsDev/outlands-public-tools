"""Review selected module dependency/load-list text without loading modules. MIT."""
from __future__ import annotations
import heapq
import json
import re
from inspection_support import (Parser, TextError, bounded_append, cli_error, finish,
                                issue, require, source_inputs, source_record,
                                text_lines, write_report)

MAX_NODES = 2000
MAX_EDGES = 4000
MAX_CYCLE_NODES = 8000
PATH = re.compile(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z')
MODULE = re.compile(r'.+\.ko(?:\.(?:gz|xz|zst))?\Z')


def safe_name(value, module=False):
    return (len(value)<=512 and PATH.fullmatch(value) is not None
            and all(part not in {'.','..'} for part in value.split('/'))
            and (not module or MODULE.fullmatch(value) is not None))


def nonempty(data):
    for line, text in text_lines(data):
        value = text.strip(' \t')
        if value and not value.startswith('#'): yield line, value


def parse_deps(data, report, details):
    declarations = {}; edge_count = 0
    for line, value in nonempty(data):
        if value.count(':') != 1:
            issue(report['coverage_issues'], 'UNSUPPORTED_DEPENDENCY_LINE', 'dependencies', line); continue
        name, raw_deps = value.split(':'); name = name.strip(' \t')
        deps = re.split(r'[ \t]+', raw_deps.strip(' \t')) if raw_deps.strip(' \t') else []
        if not safe_name(name, True) or not all(safe_name(dep, True) for dep in deps):
            issue(report['coverage_issues'], 'UNSUPPORTED_MODULE_PATH', 'dependencies', line); continue
        require(len(report['modules']) < MAX_NODES, 'MODULE_NODE_LIMIT')
        edge_count += len(deps); require(edge_count <= MAX_EDGES, 'MODULE_EDGE_LIMIT')
        if len(deps)!=len(set(deps)): issue(report['findings'], 'DUPLICATE_DEPENDENCY_TOKEN', 'dependencies', line)
        row = {'id': f'module-{len(report["modules"])+1:04d}', 'source': 'dependencies', 'line': line, 'dependency_count': len(deps)}
        if details: row['declared_path'] = name
        bounded_append(report['modules'], row); declarations.setdefault(name, []).append((row, list(dict.fromkeys(deps))))
    return declarations


def parse_list(data, source, report, module=False):
    result = []
    for line, value in nonempty(data):
        if not safe_name(value, module):
            issue(report['coverage_issues'], 'UNSUPPORTED_LIST_ENTRY', source, line); continue
        bounded_append(result, (line,value))
    return result


def aliases(name):
    base = name.rsplit('/',1)[-1]
    short = re.sub(r'\.ko(?:\.(?:gz|xz|zst))?\Z', '', base)
    return {name, base, short}


def inspect(dependencies, load_list, available=None, details=False):
    inputs = [('dependencies',dependencies), ('load-list',load_list)]
    if available is not None: inputs.append(('declared-inventory',available))
    report = {'schema_version': 1, 'tool': 'Kernel Module List & Dependency Inspector',
              'scope': 'Literal selected human-readable metadata only; no kmod/ABI/builtin/alias/runtime evaluation.',
              'details_included': details, 'inputs': [source_record(k,v) for k,v in inputs],
              'modules': [], 'dependencies': [], 'load_entries': [], 'cycle_witnesses': [],
              'findings': [], 'coverage_issues': [], 'declared_inventory_checked': available is not None}
    declarations = parse_deps(dependencies, report, details)
    unique = {name:rows[0] for name,rows in declarations.items() if len(rows)==1}
    for rows in declarations.values():
        if len(rows)>1:
            for row,_ in rows: issue(report['findings'], 'AMBIGUOUS_MODULE_DECLARATION', 'dependencies', row['line'])
    graph = {}; indexes = {}
    for name,(row,deps) in unique.items():
        for alias in aliases(name): indexes.setdefault(alias,set()).add(name)
        graph[name] = deps
        for dep in deps:
            resolution = 'unique_selected_declaration' if dep in unique else 'ambiguous_selected_declarations' if dep in declarations else 'not_declared_in_selected_metadata'
            record = {'consumer': row['id'], 'resolution': resolution,
                      'dependency': unique[dep][0]['id'] if dep in unique else None}
            if details: record['declared_path'] = dep
            bounded_append(report['dependencies'], record)
            if dep not in unique: issue(report['findings'], 'DEPENDENCY_NEEDS_METADATA_REVIEW', 'dependencies', row['line'])
    # Aliases of duplicate declarations must remain ambiguous, never silently unique.
    for name,rows in declarations.items():
        if len(rows)>1:
            for alias in aliases(name): indexes.setdefault(alias,set()).add(name)
    selected = set(); seen_load = set(); unresolved_load = False
    for line,value in parse_list(load_list,'load-list',report):
        candidates = {value} if value in declarations else indexes.get(value,set())
        resolved = len(candidates)==1 and next(iter(candidates)) in unique
        row = {'source': 'load-list', 'line': line, 'resolution': 'unique_selected_declaration' if resolved else 'ambiguous_or_unresolved',
               'module_ids': [unique[n][0]['id'] for n in sorted(candidates) if n in unique]}
        if details: row['declared_name'] = value
        if resolved:
            name = next(iter(candidates)); selected.add(name)
            if name in seen_load: issue(report['findings'], 'DUPLICATE_LOAD_SELECTION', 'load-list', line)
            seen_load.add(name)
        else: unresolved_load=True; issue(report['findings'], 'LOAD_SELECTION_NEEDS_METADATA_REVIEW', 'load-list', line)
        bounded_append(report['load_entries'],row)
    if available is not None:
        inventory = set()
        for line,name in parse_list(available,'declared-inventory',report,True):
            if name in inventory: issue(report['findings'], 'DUPLICATE_INVENTORY_ENTRY', 'declared-inventory', line)
            inventory.add(name)
        for name,(row,_deps) in unique.items():
            if name not in inventory: issue(report['findings'], 'NOT_IN_SUPPLIED_INVENTORY', 'dependencies', row['line'])
    # Iterative DFS: closed paths are actual back-edge witnesses, not all Kahn residuals.
    colors = {}; path = []; positions = {}; witness_nodes = 0
    for root in sorted(graph):
        if colors.get(root): continue
        colors[root]=1; positions[root]=0; path.append(root); stack=[(root, iter(graph[root]))]
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                stack.pop(); colors[node]=2; positions.pop(node); path.pop(); continue
            if child not in unique: continue
            if colors.get(child)==1:
                witness=path[positions[child]:]+[child]
                witness_nodes+=len(witness);require(witness_nodes<=MAX_CYCLE_NODES,'CYCLE_WITNESS_LIMIT')
                bounded_append(report['cycle_witnesses'],[unique[n][0]['id'] for n in witness])
                issue(report['findings'], 'DECLARED_DEPENDENCY_CYCLE', 'dependencies', unique[node][0]['line'])
            elif not colors.get(child):
                colors[child]=1; positions[child]=len(path); path.append(child); stack.append((child,iter(graph[child])))
    # Kahn order leaves unresolved prerequisites and their dependants blocked.
    counts={name:len(deps) for name,deps in graph.items()}; dependants={name:[] for name in graph}
    for name,deps in graph.items():
        for dep in deps:
            if dep in unique: dependants[dep].append(name)
    ready=[name for name,count in counts.items() if count==0]; heapq.heapify(ready); order=[]
    while ready:
        name=heapq.heappop(ready); order.append(name)
        for dependent in sorted(dependants[name]):
            counts[dependent]-=1
            if counts[dependent]==0: heapq.heappush(ready,dependent)
    closure=set(selected); pending=list(selected)
    while pending:
        for dep in graph[pending.pop()]:
            if dep in unique and dep not in closure: closure.add(dep); pending.append(dep)
    report['selected_dependency_order']=[unique[n][0]['id'] for n in order if n in closure]
    report['blocked_selected_modules']=[unique[n][0]['id'] for n in sorted(closure-set(order))]
    report['selected_plan_complete_within_metadata'] = not unresolved_load and not report['coverage_issues'] and not report['blocked_selected_modules']
    report['plan_scope']='Unique declared selected dependency closure only; dependencies need not appear separately in the load list. No runtime load authorization.'
    return finish(report)


def main(argv=None):
    parser=Parser(description=__doc__)
    parser.add_argument('--deps',required=True); parser.add_argument('--load-list',required=True)
    parser.add_argument('--available',help='Optional explicitly supplied relative module-path inventory, not a directory.')
    parser.add_argument('--output',required=True); parser.add_argument('--include-details',action='store_true')
    try:
        args=parser.parse_args(argv); paths=[args.deps,args.load_list]+([args.available] if args.available else [])
        inputs=source_inputs(paths)
        report=inspect(inputs[0][1],inputs[1][1],inputs[2][1] if len(inputs)>2 else None,args.include_details)
        write_report(report,args.output,paths)
        print(json.dumps({'status':report['status'],'modules':len(report['modules']),'findings':len(report['findings']),'coverage_issues':len(report['coverage_issues'])},sort_keys=True))
        return int(report['status']!='NO_SCOPE_FINDINGS')
    except (TextError,OSError,ValueError,RecursionError) as error:return cli_error(error)


if __name__=='__main__':raise SystemExit(main())

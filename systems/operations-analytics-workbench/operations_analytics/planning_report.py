"""Explicit import of a checked public planning-report format; no state mapping."""
import re
from itertools import islice
from . import runtime
from .contracts import fields,token,integer,boolean

NAMES={'plan.json','orders.csv','allocations.csv','readiness.csv'}


def hash_value(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise runtime.WorkbenchError('HASH_INVALID')
    return value


def reference(value):
    fields(value,('format','project_id','revision_sha256','manifest_sha256','remaining_demand','dock_allocated_quantity','covered_quantity','uncovered_quantity','independently_verified'))
    if value['format']!='outlands-planning-reference-v1' or boolean(value['independently_verified']):raise runtime.WorkbenchError('PLANNING_REFERENCE_INVALID')
    token(value['project_id']);hash_value(value['revision_sha256']);hash_value(value['manifest_sha256'])
    for key in ('remaining_demand','dock_allocated_quantity','covered_quantity','uncovered_quantity'):integer(value[key],maximum=1000000000000)
    if value['remaining_demand']!=value['dock_allocated_quantity']+value['covered_quantity']+value['uncovered_quantity']:raise runtime.WorkbenchError('PLANNING_CONSERVATION')
    return value


def read(directory):
    root=runtime.local_path(directory)
    if not root.is_dir() or {p.name for p in islice(root.iterdir(),6)}!=NAMES|{'manifest.json'}:raise runtime.WorkbenchError('PLANNING_REPORT_INVENTORY')
    raw=runtime.read_bytes(root/'manifest.json');manifest=runtime.decode(raw)
    fields(manifest,('format','project_id','revision_sha256','external_system_writes','files'))
    if manifest['format']!='outlands-planning-report-v1' or boolean(manifest['external_system_writes']):raise runtime.WorkbenchError('PLANNING_REPORT_INVALID')
    token(manifest['project_id']);hash_value(manifest['revision_sha256'])
    if type(manifest['files']) is not dict or set(manifest['files'])!=NAMES:raise runtime.WorkbenchError('PLANNING_REPORT_INVENTORY')
    loaded={}
    for name in sorted(NAMES):
        expected=manifest['files'][name];fields(expected,('bytes','sha256'));integer(expected['bytes'],maximum=runtime.MAX_INPUT);hash_value(expected['sha256'])
        data=runtime.read_bytes(root/name)
        if len(data)!=expected['bytes'] or runtime.digest(data)!=expected['sha256']:raise runtime.WorkbenchError('PLANNING_REPORT_BYTES_CHANGED')
        loaded[name]=data
    plan=runtime.decode(loaded['plan.json'])
    if type(plan) is not dict or plan.get('project_id')!=manifest['project_id'] or plan.get('revision_sha256')!=manifest['revision_sha256']:raise runtime.WorkbenchError('PLANNING_REPORT_IDENTITY')
    if plan.get('mode')!='LOCAL_ADVISORY_PLAN' or plan.get('external_system_writes') is not False or plan.get('lot_ids_reserved') is not False or plan.get('shipment_execution_authorized') is not False:raise runtime.WorkbenchError('PLANNING_AUTHORITY_INVALID')
    products=plan.get('products')
    if type(products) is not list or len(products)>16:raise runtime.WorkbenchError('PLANNING_REPORT_INVALID')
    totals=dict(remaining_demand=0,dock_allocated_quantity=0,covered_quantity=0,uncovered_quantity=0)
    for product in products:
        try:
            values=dict(remaining_demand=product['remaining_demand'],dock_allocated_quantity=product['dock_allocated_quantity'],covered_quantity=product['allocation']['conservation']['covered'],uncovered_quantity=product['allocation']['conservation']['uncovered'])
        except (TypeError,KeyError):raise runtime.WorkbenchError('PLANNING_REPORT_INVALID') from None
        for key,value in values.items():totals[key]+=integer(value,maximum=1000000000000)
        if values['remaining_demand']!=sum(values[k] for k in ('dock_allocated_quantity','covered_quantity','uncovered_quantity')):raise runtime.WorkbenchError('PLANNING_CONSERVATION')
    return reference(dict(format='outlands-planning-reference-v1',project_id=manifest['project_id'],revision_sha256=manifest['revision_sha256'],manifest_sha256=runtime.digest(raw),**totals,independently_verified=False))

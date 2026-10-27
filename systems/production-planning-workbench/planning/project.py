"""Neutral instance contract around the retained authored engines."""
from datetime import date
from decimal import Decimal
import re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .engines.allocation import PlanningConfiguration,FlexWipLot,FlexOrder,build_flex_plan
from .engines.demand import AutomaticLotStartConfiguration,AutomaticLotStartLedger,OSOrderState
from .engines.identity import recommend_lot_start
from .engines.readiness import project_readiness
from . import runtime


class ProductIdentity(BaseModel):
    modality:str=Field(pattern=r'^[A-Z0-9]{3,12}$')
    part_number:str=Field(pattern=r'^[A-Z0-9][A-Z0-9._-]{0,39}$')
    lot_prefix:str=Field(pattern=r'^[A-Z0-9-]{3,20}$')
    start_factor:Decimal=Field(ge=Decimal('1'),le=Decimal('2'))
    lot_size:int=Field(gt=0,le=10000)
    observed_lot_ids:tuple[str,...]=Field(min_length=1,max_length=500)
    model_config=ConfigDict(extra='forbid',frozen=True,allow_inf_nan=False)


class HandoffLot(BaseModel):
    lot_id:str=Field(min_length=1,max_length=80)
    quantity:int=Field(gt=0,le=10000000)
    cleared:bool=False
    model_config=ConfigDict(extra='forbid',frozen=True)


class Handoff(BaseModel):
    order_id:str=Field(min_length=1,max_length=120)
    order_version:int=Field(gt=0)
    dock_date:date|None=None
    lots:tuple[HandoffLot,...]=Field(max_length=100)
    model_config=ConfigDict(extra='forbid',frozen=True)


class Project(BaseModel):
    format:Literal['outlands-planning-project-v1']
    project_id:str=Field(pattern=r'^[a-z][a-z0-9-]{1,39}$')
    title:str=Field(min_length=1,max_length=120)
    planning_date:date
    planning_configuration:PlanningConfiguration
    demand_configuration:AutomaticLotStartConfiguration
    lot_policies:tuple[ProductIdentity,...]=Field(min_length=1,max_length=16)
    order_history:tuple[OSOrderState,...]=Field(min_length=1,max_length=1000)
    wip:tuple[FlexWipLot,...]=Field(max_length=500)
    handoffs:tuple[Handoff,...]=Field(default=(),max_length=200)
    model_config=ConfigDict(extra='forbid',frozen=True,allow_inf_nan=False)

    @model_validator(mode='after')
    def validate_configuration(self):
        products=self.planning_configuration.products
        if len(products)>16:raise ValueError('PRODUCT_LIMIT')
        expected={(p.modality,p.part_number) for p in products}
        if len(expected)!=len(products) or len(self.lot_policies)!=len(expected) or {(p.modality,p.part_number) for p in self.lot_policies}!=expected:raise ValueError('PRODUCT_COVERAGE')
        demand=self.demand_configuration.configured_products
        if len(demand)!=len(expected) or {(p.modality,p.part_number) for p in demand}!=expected:raise ValueError('PRODUCT_COVERAGE')
        if len({p.lot_prefix for p in self.lot_policies})!=len(self.lot_policies):raise ValueError('DUPLICATE_LOT_PREFIX')
        if self.planning_configuration.effective_date>self.planning_date:raise ValueError('CONFIGURATION_NOT_EFFECTIVE')
        for product in products:
            if len(product.operation_to_kanban)>128 or any(len(key)>256 for key in product.operation_to_kanban):raise ValueError('OPERATION_LIMIT')
            if any(value>365 for value in product.kanban_days_remaining.values()):raise ValueError('TIMING_LIMIT')
        for p in self.lot_policies:
            selected=next(x for x in demand if x.modality==p.modality)
            if selected.lot_prefix!=p.lot_prefix or selected.start_quantity!=p.lot_size:raise ValueError('LOT_POLICY_CONFLICT')
            if self.planning_configuration.product(p.modality,p.part_number).expected_lot_start_quantity!=p.lot_size:raise ValueError('LOT_POLICY_CONFLICT')
            if any(not re.fullmatch(r'[A-Z0-9-]{3,40}',x) for x in p.observed_lot_ids):raise ValueError('LOT_ID_INVALID')
        if len({x.lot_id for x in self.wip})!=len(self.wip):raise ValueError('DUPLICATE_WIP')
        for lot in self.wip:
            if (lot.modality,lot.part_number) not in expected or lot.quantity>10000000:raise ValueError('WIP_INPUT_INVALID')
            if self.planning_configuration.product(lot.modality,lot.part_number).operation_to_kanban.get(lot.operation)!=lot.kanban:raise ValueError('WIP_OPERATION_INVALID')
        if len({x.order_id for x in self.order_history})>200:raise ValueError('ORDER_LIMIT')
        return self


def parse(raw):
    # Validate duplicate keys/numbers/depth before the strict JSON model parser.
    runtime.decode(raw)
    try:return Project.model_validate_json(raw,strict=True)
    except ValueError:raise runtime.WorkbenchError('PROJECT_INVALID') from None


def ledger(project):
    selected=AutomaticLotStartLedger(project.demand_configuration)
    for row in project.order_history:selected.ingest(row)
    return selected


def calculate(project):
    demand=ledger(project)
    current=list(demand._orders.values())
    by_id={r.order_id:r for r in current};wip={r.lot_id:r for r in project.wip};used={};readiness=[]
    if len({r.order_id for r in project.handoffs})!=len(project.handoffs):raise runtime.WorkbenchError('DUPLICATE_HANDOFF')
    for handoff in project.handoffs:
        order=by_id.get(handoff.order_id)
        if order is None or order.row_version!=handoff.order_version or order.cancelled:raise runtime.WorkbenchError('STALE_HANDOFF')
        if len({r.lot_id for r in handoff.lots})!=len(handoff.lots):raise runtime.WorkbenchError('DUPLICATE_HANDOFF_LOT')
        if sum(r.quantity for r in handoff.lots)>order.remaining_quantity:raise runtime.WorkbenchError('HANDOFF_QUANTITY')
        for row in handoff.lots:
            lot=wip.get(row.lot_id)
            if lot is None or lot.part_number!=order.part_number or lot.kanban!=7:raise runtime.WorkbenchError('HANDOFF_LOT_INVALID')
            used[row.lot_id]=used.get(row.lot_id,0)+row.quantity
            if used[row.lot_id]>lot.quantity:raise runtime.WorkbenchError('HANDOFF_OVERALLOCATION')
    handoffs={r.order_id:r for r in project.handoffs}
    for order in current:
        if order.cancelled:continue
        handoff=handoffs.get(order.order_id)
        readiness.append(dict(order_id=order.order_id,**project_readiness(quantity=order.ordered_quantity,shipped_quantity=order.accepted_ship_quantity,dock_date=handoff.dock_date if handoff else None,lots=[r.model_dump() for r in handoff.lots] if handoff else [])))
    product_results=[];actions=[]
    for product in project.planning_configuration.products:
        selected=sorted((r for r in current if r.part_number==product.part_number and r.remaining_quantity),key=lambda r:(r.requested_ship_date,r.order_id))
        docked={r.order_id:sum(l.quantity for l in r.lots) for r in project.handoffs}
        orders=[FlexOrder(order_id=r.order_id,sequence=i+1,modality=product.modality,part_number=product.part_number,due_date=r.requested_ship_date,quantity=r.remaining_quantity-docked.get(r.order_id,0)) for i,r in enumerate(selected) if r.remaining_quantity>docked.get(r.order_id,0)]
        lots=[r for r in project.wip if r.part_number==product.part_number]
        if orders:
            plan=build_flex_plan(planning_date=project.planning_date,modality=product.modality,part_number=product.part_number,orders=orders,wip=lots,configuration=project.planning_configuration)
            values=plan.model_dump(mode='json')
            uncovered=plan.conservation.uncovered
            for order in plan.orders:
                for allocation in order.allocations:
                    actions.append(dict(part_number=product.part_number,order_id=order.order_id,lot_id=allocation.lot_id,kanban=allocation.kanban,operation=allocation.operation,quantity=allocation.quantity,priority_sort=allocation.priority_sort))
        else:
            uncovered=0
            values=dict(orders=[],conservation=dict(demand_input=0,covered=0,uncovered=0,wip_input=sum(r.quantity for r in lots),wip_allocated=0,wip_remaining=sum(r.quantity for r in lots)),remaining_wip={r.lot_id:r.quantity for r in lots})
        policy=next(p for p in project.lot_policies if p.modality==product.modality)
        proposed=recommend_lot_start(modality=product.modality,uncovered_demand=uncovered,observed_lot_ids=policy.observed_lot_ids+tuple(r.lot_id for r in lots),policy=dict(configured_products=[dict(modality=policy.modality,part_number=policy.part_number,lot_prefix=policy.lot_prefix,start_factor=str(policy.start_factor),lot_size=policy.lot_size)],fail_closed_products=[]))
        gross=sum(r.remaining_quantity for r in selected);dock=sum(docked.get(r.order_id,0) for r in selected)
        if gross!=dock+values['conservation']['covered']+uncovered:raise runtime.WorkbenchError('DEMAND_CONSERVATION')
        product_results.append(dict(modality=product.modality,part_number=product.part_number,remaining_demand=gross,dock_allocated_quantity=dock,allocation=values,lot_proposal=proposed.to_dict(),gross_demand_lot_reference=demand._recommended_lots(demand.modality_remaining_demand(product.modality),policy.lot_size)))
    return dict(mode='LOCAL_ADVISORY_PLAN',planning_date=project.planning_date.isoformat(),project_id=project.project_id,products=product_results,actions=actions,demand_events=[e.model_dump(mode='json') for e in demand.events],current_orders=[r.model_dump(mode='json') for r in sorted(current,key=lambda x:x.order_id)],shipment_readiness=readiness,external_system_writes=False,lot_ids_reserved=False,shipment_execution_authorized=False)

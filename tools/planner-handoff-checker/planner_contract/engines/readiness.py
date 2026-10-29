"""Original handoff decision tree adapted to neutral caller declarations."""

def project_readiness(*,quantity,shipped_quantity,dock_date,lots):
    allocations=lots
    accepted_ship_quantity = min(quantity, shipped_quantity)
    unshipped_quantity = max(0, quantity - accepted_ship_quantity)
    ready_quantity = min(
        unshipped_quantity,
        sum(
            lot["quantity"]
            for lot in lots
            if lot["cleared"] is True
        ),
    )
    production_remaining = max(0, unshipped_quantity - ready_quantity)
    if shipped_quantity == quantity:
        readiness_state = "SHIPPING_EVIDENCE_RECORDED"
        external_evidence_status = "SHIPPING_RECORDED"
    elif dock_date is None:
        readiness_state = "AWAITING_DOCK"
        external_evidence_status = "NOT_READY_FOR_LOGISTICS"
    elif not allocations:
        readiness_state = "LOT_EVIDENCE_REQUIRED"
        external_evidence_status = "NOT_READY_FOR_LOGISTICS"
    elif ready_quantity == 0:
        readiness_state = "DOCKED_AWAITING_PRODUCTION_CLEARANCE"
        external_evidence_status = "NOT_READY_FOR_LOGISTICS"
    elif production_remaining:
        readiness_state = "PARTIALLY_READY_FOR_LOGISTICS"
        external_evidence_status = "AWAITING_INDEPENDENT_SHIPPING_EVIDENCE"
    else:
        readiness_state = "READY_FOR_LOGISTICS"
        external_evidence_status = "AWAITING_INDEPENDENT_SHIPPING_EVIDENCE"

    return dict(readiness_state=readiness_state,unshipped_quantity=unshipped_quantity,ready_quantity=ready_quantity,production_remaining=production_remaining,external_evidence_status=external_evidence_status,independently_verified=False,shipment_authorized=False)

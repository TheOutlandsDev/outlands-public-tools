"""Supply only an explicitly named bundled script's sibling imports to isolated Python."""
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
scripts={
 'launch.py',
 'application/workshops/manufacturing_review.py',
 'application/workshops/material_quality_review.py',
 'application/tools/resource-reservation-checker/reservations.py',
 'application/tools/assignment-eligibility-checker/assignments.py',
 'application/tools/process-event-duration-analyzer/durations.py',
 'application/tools/flow-balance-reconciler/flows.py',
 'application/tools/bom-contract-checker/bom.py',
 'application/tools/lot-identity-checker/identities.py',
 'application/tools/material-allocation-checker/allocations.py',
 'application/tools/handoff-lifecycle-checker/handoffs.py',
 'application/tools/measurement-contract-checker/measurements.py',
 'application/tools/inspection-coverage-checker/inspections.py',
 'application/tools/yield-scrap-reconciler/yields.py',
 'application/tools/rework-history-checker/rework.py',
}
if sys.argv and sys.argv[0] not in ('-c','-m',''):
 selected=Path(sys.argv[0]).resolve()
 if selected in {root/name for name in scripts}:sys.path.insert(0,str(selected.parent))

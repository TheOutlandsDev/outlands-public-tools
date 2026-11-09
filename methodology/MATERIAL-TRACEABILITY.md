# Material traceability review

These four tools review selected, bounded fictional material declarations.
They do not create orders, count inventory, reserve stock, transfer material,
accept deliveries or update an operational store.

1. **BOM contract:** explicit component links and whole-unit order quantities
   yield derived requirements after reference, ambiguity and cycle checks.
   Derived quantities do not establish equipment sizing, component suitability
   or inventory availability.
2. **Lot identity:** declared aliases resolve to canonical lots and totals.
   This does not prove a physical label or authenticate stock.
3. **Material allocation:** supplied demand, lots and reservation declarations
   are reconciled for shortage and overuse. No allocation is selected, applied
   or posted.
4. **Handoff lifecycle:** supplied transfer events and receipt references are
   checked for protocol consistency. A declared accepted quantity does not
   prove that material moved or that a receipt is authentic.

The fictional exercise derives BOM leaf demand, chooses lot aliases from a
separate fictional declaration, builds explicit reservation claims, then
invents handoff and receipt assertions for one selected lot. Those changes are
visible inputs to each check. The workflow does not connect to a real system
or prove an end-to-end physical transaction.

`PASS` means the selected declarations satisfy one tool's stated contract.
`REVIEW_REQUIRED` retains findings and withholds any unsupported claim.
Identifiers, quantities and hashes can reveal operational context; keep real
inputs and reports private. Public package fixtures are fictional.

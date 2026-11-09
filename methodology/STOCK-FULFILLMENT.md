# Stock and fulfillment review

These four tools review selected, bounded declarations for a fictional stock
workflow. They do not count physical stock, accept inbound deliveries, reserve
material, create purchase orders, ship goods or update any operational store.

1. **Movement ledger:** ordered receipts, issues and adjustments reconcile
   against a selected opening balance. A consistent closing balance is not a
   physical count or proof that the supplied history is complete.
2. **Inventory position:** supplied on-hand, eligible inbound and reserved
   demand yield a position under explicit as-of and horizon values. Inbound
   state and due date are declarations, not authenticated receipt evidence.
3. **Replenishment:** a caller-selected policy yields an advisory proposal
   against a pinned position. The policy's suitability and purchasing authority
   are outside the calculation.
4. **Shipment coverage:** exact order-line, shipment-content and receipt
   declarations are reconciled. Declared coverage is not evidence of physical
   dispatch, delivery or receipt authenticity.

The fictional exercise selects a new stock snapshot with the ledger's closing
quantity, recalculates its exact pin for the position checker, then selects a
position with the computed quantity and recalculates its policy pin. The
shipment example shares a declared order quantity with reserved demand. This
explicit transformation is a worked example, not an operational adapter or a
verified end-to-end transaction.

`PASS` means the selected declarations satisfy one tool's stated contract.
`REVIEW_REQUIRED` preserves findings and withholds a qualified-scope pin.
No live application relationship has been reviewed. Identifiers, quantities
and hashes can reveal operational context; keep actual inputs and reports
private. Public package fixtures are fictional.

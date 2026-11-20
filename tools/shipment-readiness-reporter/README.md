# Offline Shipment Readiness Reporter

Project shipment readiness from saved orders and lot handoff records. The report identifies missing allocation evidence, partial clearance, returned lots, and orders with recorded shipping evidence. It includes the supplied source revision and reports production clearance from the saved records.

[Setup and fictional walkthrough](SETUP.md) · [Download and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/shipment-readiness-reporter-v0.1.0)

The standalone CLI retains the original projection, lot allocation parser, and filtering. It accepts local JSON and emits a read-only report. Action eligibility fields describe the saved state. The tool performs no handoffs, database writes, shipment recording, or manufacturing execution system (MES) transactions.

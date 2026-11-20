# Offline Order Demand and WIP Allocation Reporter

Reconcile a saved order snapshot with its lot-start queue and allocate eligible work-in-progress by due date. The report tracks shipped quantities, quantities ready for logistics, and remaining demand separately. Filter the calculated rows or export them to CSV with both supplied source hashes.

[Setup and fictional walkthrough](SETUP.md) · [Download and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-demand-wip-allocation-reporter-v0.1.0)

The standalone CLI uses saved JSON and reports coverage for the supplied snapshots. It retains the original allocation, filtering and export functions and bundles the published queue validator. The examples use fictional identifiers and source hashes.

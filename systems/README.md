# Larger systems

The [Dataset Review Manager](dataset-review/README.md) is included as a standalone private-store application. It implements import, exact deduplication, conservative group splits, review and approved export without bringing a historical corpus or model configuration into the repository.

The [Offline Assessment Record Contract Checker](../tools/assessment-record-checker/README.md)
checks a fresh neutral ledger format for declared relationships and workflow
consistency. It does not export or clear the assessment management application
below, ingest evidence, perform testing or verify outcomes.

The [Offline Evaluation Metrics Calculator](../tools/evaluation-metrics-calculator/README.md)
adds arithmetic over a fresh aggregate-count format. It executes no model and
does not export or clear the broader AI application, corpus or configuration.

| Candidate family | Planned public boundary | Remaining work |
| --- | --- | --- |
| Broader AI evaluation and review | Empty-store application, fictional tasks, explicit local configuration | Model/UI integration remains outside the smaller included review manager; review each additional source/config/UI file |
| Assessment management | Generic engagement/submission/finding/retest records and fictional walkthrough | Review application and dependencies, remove host-specific setup/evidence, verify supported runtime behavior |
| Hobby/server management | Reusable original lifecycle, backup, configuration and deployment mechanisms | Separate third-party/game material, player records, keys and live server configuration; validate on disposable fixtures |

These are cataloged candidates, not cleared or operational products. A security management UI does not prove containment; a model UI does not establish training-data rights; server orchestration does not grant redistribution rights over games or mods. The [release review](../methodology/release-review.md) applies to each selected export.

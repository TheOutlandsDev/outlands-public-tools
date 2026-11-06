# Public tool installation plan

The [machine-readable inventory](install-plan.json) covers all 222 public tools
in the shared catalog. Run `python -B integrations/install_plan.py check` to
refuse drift between the inventory, catalog, source guides and task-to-system
map. Regenerate it after a reviewed metadata change with `generate`.

Each record gives the tool's purpose, exact catalog runtime/requirement text,
source entry when one command is unambiguous in its README, fictional input path
when one exists, example and validation guides, released download choices and
documented system use-case links. These are **readiness records**, not claims that
all 222 tools have independent packages or that any linked system imports them.

| Field | Meaning |
| --- | --- |
| `source_entry_status: readme_observed` | One source command appears in the README and resolves to a file. It still needs fresh extraction and runtime qualification for a package. |
| `source_entry_status: needs_review` | The command is absent or ambiguous; inspect the guide and implementation before packaging. |
| `example_input: null` | No standard `examples/input.json` exists; use the linked example guide and review whether a portable fictional fixture is needed. |
| `result_meaning_guide` | The tool's own validation/limits guide. The plan does not invent a universal meaning for `PASS`. |
| `individual_install_status: needs_package_review` | No independently reviewed wheel is registered. Source ZIP or portable downloads listed separately may still be available. |
| `relationship_status: documented_use_case_only` | The public task map links this tool to a system as a possible use case, without asserting an adapter. |
| `relationship_status: needs_mapping` | No specific system relationship has been reviewed yet. |

The current inventory records 176 README-observed source entries, 144 standard
fictional input files, thirty-six released individual wheels and 47 documented
system use cases. Review gaps tool by tool; do not fill them with guessed
dependencies or integration claims. The [terms and evidence levels](../methodology/TERMS.md)
define what a check, receipt and installation test can establish.

The [thirty-six-tool install bundle](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-tools-install-bundle-v1.7.0) is the combined download for the thirty-six reviewed individual Python wheels. The plan lists it as `collection_install_zip` only for those thirty-six tools. Select one wheel, one four-tool group, or all thirty-six using the [start guide](public-tools-bundle-36/START-HERE.md). The ZIP does not install an adapter into a related project.

## Repeatable packaging order

1. Review one tool's purpose, input/output contract, dependencies, license and
   source manifest. Add a fictional input and expected result with stated limits.
2. Build its independent package from an exact public source allowlist. Give it
   its own version and a command plus library/process entry where appropriate.
3. Add it to a collection manifest with exact member versions and dependency
   rules. Keep the existing source/portable route visible.
4. Scan the exact artifacts and staged publication diff for private data and
   metadata. Test fresh individual and collection installs on supported systems.
5. Publish only the reviewed assets, anonymously download and install them, then
   update catalog links and GitHub About to match the release.

The [AI decision-contract cohort](ai-decision-contracts/README.md) is the second
published Python package set. Other runtimes will need their own reviewed packaging
methods. The frozen Toolkit 0.9.0 source collection remains a separate release.

The [probability integrity cohort](probability-integrity/README.md) is the third independently installable Python package set. Its [definitions](../methodology/PROBABILITY.md) and worked example explain the calculation scopes and system mapping requirements.

The [cache/retry cohort](cache-retry/README.md) is the fourth independently installable Python package set. Its definitions and installed fictional exercise cover advisory cache, retry and operation-record review.

The [review/change cohort](review-change/README.md) is the fifth independently installable Python package set. Its definitions and installed exercise explain scoped, advisory review and change-management methodology.

The [test/evidence guide](test-evidence/README.md) adds independent packages, plain-language definitions and an installed case-to-evidence exercise. Its Test & Evidence Workbench use case requires explicit mappings; complete evidence does not upgrade a failed test.

The [reliability/incident guide](reliability-incident/README.md) adds independent packages, precise definitions and an installed health-to-recovery exercise. Its Reliability & Incident Workbench use case requires explicit time, identity and policy mappings; a valid timeline does not imply resolution or recovery readiness.

The [metrics/trace guide](metrics-traces/README.md) adds individual packages, plain-language definitions and an installed fictional metric-to-span exercise. Its Data & Services Stack use case requires explicit metric, run, clock and span mappings; a consistent link does not establish causation or actual telemetry.

The [document/evidence guide](document-evidence/README.md) adds individual packages, exact Python operation names, plain-language definitions and an installed document-to-citation example. Its Corpus & Model Workbench use case requires explicit text, revision, hash-domain, ranking/judgment and citation mappings; structural citation PASS does not establish claim support or factual truth.

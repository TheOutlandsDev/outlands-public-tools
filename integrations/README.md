# Integration and distribution path

The [public install plan](INSTALL-PLAN.md) is a checked inventory of all 222
tools. It records release choices and documentation gaps without presenting
source-only tools as independently installable packages.

The [published model-routing wheels](model-routing/README.md) are the first worked pattern:
four separately installable Python tools, a collection installer, plain-language
terms, fictional inputs/results, a Python API example and a related system map.
Their [release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/model-routing-wheels-v1.0.0) passed fresh public-download installs on Windows and Ubuntu with Python 3.12 and 3.13.

The [AI decision-contract wheels](ai-decision-contracts/README.md) apply the same
independent-tool and collection pattern to prompt contracts, label mappings,
score abstention policies and candidate evaluation gates. Their
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/ai-decision-contracts-wheels-v1.0.0)
passed the same four-platform public-download matrix.

The [thirty-two-tool install bundle](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-tools-install-bundle-v1.6.0) combines the eight reviewed cohorts into one download. Its [start guide](public-tools-bundle-32/START-HERE.md) and `COMPONENTS.json` describe individual, four-tool and all-thirty-two installs. The selector pins released wheels and lists installed components; it does not wire the tools into a system. The other 190 public tools remain in the readiness plan.

The [probability integrity wheels](probability-integrity/README.md) add four independent tools and a collection for probability declarations, squared error, reliability bins and map review. Their guide includes plain definitions, exact fictional results and an installed API exercise.

The [cache/retry wheels](cache-retry/README.md) add four independent tools and a collection for key derivation, freshness, retry budgets and operation claims. The guide includes definitions, fictional examples, Python APIs and a Data & Services Stack use case.

The [review/change wheels](review-change/README.md) add four tools and a collection for queues, correction lineage, approval scope and change impact, with definitions, fictional examples, APIs and an Assessment & Evidence Workbench use case.

The [test/evidence guide](test-evidence/README.md) adds independent packages, plain-language definitions and an installed case-to-evidence exercise. Its Test & Evidence Workbench use case requires explicit mappings; complete evidence does not upgrade a failed test.

The [reliability/incident guide](reliability-incident/README.md) adds independent packages, precise definitions and an installed health-to-recovery exercise. Its Reliability & Incident Workbench use case requires explicit time, identity and policy mappings; a valid timeline does not imply resolution or recovery readiness.

The [metrics/trace guide](metrics-traces/README.md) adds individual packages, plain-language definitions and an installed fictional metric-to-span exercise. Its Data & Services Stack use case requires explicit metric, run, clock and span mappings; a consistent link does not establish causation or actual telemetry.

## Apply the pattern across the collection

1. **Describe the task.** Give each public tool a short purpose, input and output
   example, terms it uses, dependencies, limits and evidence level. Link related
   systems without assuming they have an adapter.
2. **Select a distribution method by runtime.** A Python wheel fits a Python
   library/CLI. Node, .NET, PowerShell and desktop applications need their own
   appropriate package or verified portable folder. Each component keeps its
   own version, license, entry point and dependency declaration.
3. **Build a complete collection from a reviewed manifest.** The manifest will
   pin every included component version, artifact hash, runtime and dependency.
   A selector should install only requested components, or install the full set
   with explicit platform requirements. A complete archive must have a documented
   member list; its existence will not imply one universal runtime.
4. **Prove the user journey.** Test installation into a fresh environment,
   run the embedded fictional example, call the documented integration API or
   process interface, check generated files and privacy boundaries, and verify
   public downloads on supported platforms before activating a release link.

The current [Toolkit 0.9.0](../packages/README.md) is a frozen source collection.
The separately released source bundles cover later additions. A future complete
distribution needs a new version and its own qualification; these separately published wheels do not
change those existing releases.

# Terms used by OUTLANDS tools

These meanings apply to the offline checkers in this collection. A tool's own
README defines its exact input schema and result fields.

| Term | Plain meaning | Precise meaning here |
| --- | --- | --- |
| Contract | A stated set of rules for data or a process. | A versioned input shape plus constraints that a checker evaluates. A passing contract check establishes consistency with those rules, not truth about the outside world. |
| Declaration | A claim supplied by the caller. | A value in input JSON, such as a model's supported task or capacity. Unless a tool says otherwise, the value is not measured or independently verified. |
| Receipt | A record of a claimed step or result. | A structured record whose fields can be compared with a plan and other records. A matching receipt does not authenticate the actor or prove that an operation happened. |
| Reconciliation | Compare related records for agreement. | Recompute expected relationships from supplied inputs and report missing, conflicting or mismatched rows. It does not repair source records. |
| Pin | A fingerprint for exact bytes or normalized data. | Usually a SHA-256 digest. A match links two representations under the stated encoding rules; it is not a signature or proof of origin. |
| `PASS` | The supplied data met the checked rules. | A successful result for the tool's stated scope. Read its limits before using the result to make a decision. |
| `REVIEW_REQUIRED` | A person needs to examine a reported issue. | A completed assessment with at least one rule failure or withheld conclusion. For the model-routing CLIs it exits with code 1. It is not permission to proceed. |
| Fixed refusal | The tool could not assess the input. | Invalid input or an unsafe file operation yields a fixed diagnostic and exit code 2 for the model-routing CLIs. Do not treat it as a negative assessment of the subject. |
| Source only | Code is supplied without a runtime. | Install a supported runtime separately. A source ZIP is an archive, not a package-manager installation. |
| Independent tool | One component can run on its own. | Its package includes its required code and declares runtime requirements. It may still require caller-supplied input and integration work. |
| Collection | A chosen set of components. | A versioned manifest or package that names exact members and dependencies. Installing the collection does not establish that its tools interoperate with a particular system. |

## Evidence levels

An example using fictional records shows how to operate a tool. A unit test checks
specified code behavior. A fresh installed-package check exercises the distributed
files. A live integration check needs the actual target system and separately
reviewed data. State which level a claim reached; do not silently promote one to
another.

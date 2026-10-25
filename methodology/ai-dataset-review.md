# AI dataset and evaluation review

- Source identity, provenance and intended-use rights:
- Sensitive-content and context review:
- Technical correctness review and supporting evidence:
- Original record retained without silently rewriting history:
- Decision: pending / approved / rejected; reviewer and reason:
- Exact duplicates and conversation/group relationships:
- Train/validation/test assignment and leakage checks:
- Held-out evaluation prompts and answers separated from training/retrieval:
- Model identity/digest, settings, latency and errors:
- Human-scored rubric and evidence supporting comparisons:
- Export identity, hashes, exclusions and remaining limits:

Keep source conversations, responses, embeddings, scores, reviewer identities and local configuration private. Generated or historical answers are unreviewed until supported by actual checks. A model recommendation should report insufficient evidence instead of inventing a winner.

The [Offline Evaluation Metrics Calculator](../tools/evaluation-metrics-calculator/README.md)
can compute exact ratios from a separate declared confusion-count table. Its
arithmetic does not verify labels, provenance, representativeness, leakage or
model quality; aggregate counts and resulting metrics can still be sensitive.

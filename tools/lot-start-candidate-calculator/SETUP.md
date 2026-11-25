# Offline Lot-Start Candidate Calculator

Extract the source ZIP and open a terminal in the extracted directory. Use Python 3.12 or 3.15. The calculator uses only the Python standard library. On Ubuntu, use `python3` if needed.

```text
python lot_start_candidate.py examples/projected-policy.json examples/request.json
```

The fictional example reports one 300-unit lot from 300 units of uncovered demand and proposes `DEMO-01-AAAB`. The result carries the `DEVELOPMENT_CANDIDATE_NOT_RESERVED` authority label.

For your own calculation, use the JSON output from the [Offline Lot-Start Reservation Policy Projector](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/lot-start-reservation-policy-projector-v0.1.0) as the first argument. The bundled `projected-policy.json` is generated from the project's [published fictional projector example](https://github.com/TheOutlandsDev/outlands-public-tools/blob/4c1e5112eb6fa7e4f32024c3e9674cc92d8ee7c9/tools/lot-start-reservation-policy-projector/examples/candidate-policy.json).

The second argument is a JSON object with `modality`, numeric `uncovered_demand`, and an `observed_lot_ids` array. Include known non-reusable IDs in the history. The calculator advances the greatest four-letter sequence for the configured prefix. It ignores IDs outside that pattern. A positive recommendation requires matching history. Zero demand yields zero candidates.

The calculator multiplies uncovered demand by the product's decimal `start_factor` and rounds up. It then divides by the physical `lot_size` and rounds up to whole lots. The report includes both capacity above uncovered demand and the proposed IDs. Requests support up to 100 proposed IDs and input files up to 4 MiB each.

The CLI prints JSON to standard output. Invalid inputs, blocked products, and unavailable sequences exit with code 2 and a diagnostic on standard error. It reads both files without modifying them.

Compare the ZIP against `SHA256SUMS.txt` with `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Ubuntu. See `VALIDATION.json` for the four qualification profiles.

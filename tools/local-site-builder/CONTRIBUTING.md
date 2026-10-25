# Suggestions and contributions

Suggestions are welcome even without code. Open a feature request explaining who
needs the change, their current workflow and what a useful result would look like.
For a bug, include OS, Node version, commit/version and a minimal fictional
reproduction. State what you expected and what happened.

Do not attach `.env`, passwords, real databases/backups, private drafts, inbox
messages, personal images or unreviewed logs. Use generated examples instead.
Read [SECURITY](SECURITY.md) for private vulnerability reporting.

For code: use Node 24, `npm ci`, `npm test` and `npm run source-check`. Add a focused
fixture test for meaningful behavior changes. Keep the default server loopback
only; do not weaken authentication, CSRF, limits or new-output guards to make a
test pass. Dependency updates need a lock, advisory and notice review.

Original contributions are accepted under this repository's MIT license. Retain
third-party notices and identify any imported material and its terms in the pull
request. No contributor agreement or account with an external paid service is
required to suggest a change.

# Retrieval Instructions for Public Python Sources

## Retrieval priority

When answering coding questions, use sources in this priority order:

1. Local repository code and tests.
2. Project-specific docs and configuration.
3. Official Python documentation for the target Python version.
4. Relevant PEPs.
5. Official tool documentation.
6. Security guidance from OpenSSF, OWASP, Python docs, or tool docs.
7. Curated examples from this seed pack.
8. Formal education sources.
9. Blog posts, Stack Overflow, and random GitHub repos only when explicitly marked as low-authority references.

## Conflict resolution

If sources conflict:

- Repository behavior wins over generic style guidance.
- Exact Python-version docs win over latest-version docs.
- Official docs win over blog posts.
- Security guidance wins over convenience.
- Tests and reproducible behavior win over speculation.

## Citation and provenance behavior

For each retrieved chunk, preserve:

- Source title.
- URL.
- Version, if applicable.
- License note.
- Retrieval date.
- Heading path.
- Chunk ID.

## Do not retrieve blindly

Avoid ingesting:

- Unlicensed GitHub code.
- Personal solution repos for course assignments.
- Outdated Python 2 material.
- Old packaging tutorials that recommend deprecated practices.
- Code snippets with no explanation or license.
- Anything containing secrets, credentials, private keys, real patient data, or private production logs.

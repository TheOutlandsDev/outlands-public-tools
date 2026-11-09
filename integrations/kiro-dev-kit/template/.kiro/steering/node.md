---
inclusion: fileMatch
fileMatchPattern: ["**/*.js","**/*.mjs","**/*.ts","**/package.json"]
---
Inspect package.json, packageManager, engines, and the lockfile. Use the repository's package manager and reproducible install command. Inspect scripts before running them. Run the relevant tests, type checking, and build as defined by the repository. The kit's dependency-free fixture runs with node --test on Node 26. Do not regenerate a lockfile or upgrade dependencies as an incidental debugging step.

# Task and model selection

The entry point is Kiro's own agent. This kit is configuration and reusable
methods; there is no separate router process, proxy, API endpoint, or server.

| Work | Agent | Method |
| --- | --- | --- |
| Understand unfamiliar source | `outlands-investigator` | `understand-repo` |
| Reproduce and fix a failure | `outlands-developer` | `fix-bug` |
| Deliver a requested change | `outlands-developer` | `implement-change` |
| Review a diff independently | Fresh `outlands-reviewer` chat | `review-change` |
| Resume later | `outlands-developer` | `prepare-handoff` |

Select an agent through Kiro's picker and invoke a skill through its slash
command when explicit control is useful. Skill descriptions also support
automatic discovery. The route table and `.kiro/devkit/routes.json` document
the intended task choices; they are not native Kiro settings that intercept
prompts or automatically change models. Agent JSON `model` fields implement
optional model selection using IDs from the managed model picker.

For demanding coding, choose the strongest approved GPT coding model available
in that account. Kiro currently documents GPT-5.6 Sol for long refactors and
terminal work, Terra for routine tasks, and Luna for throughput. Availability
in a Bedrock API catalog does not establish availability in Kiro. Do not copy
an SDK model ID into a profile unless Kiro actually exposes that exact ID.
Use Kiro's effort control for supported models and confirm it in the client;
the kit does not invent a profile field for reasoning effort.

An unavailable agent model can fail on the first prompt; Kiro can also show
fallback notices during sessions. Review the actual model/fallback details.
An account's approved model inventory can change after installation, so local
rendering against an earlier inventory is not live access verification.

Kiro's optional Workflows feature supports steps, handoffs, fresh contexts,
and preferred models/effort. The basic kit works without enabling Workflows.
If your account provides it, first validate the single-agent route, then use
the native investigate/implement/review stages for larger tasks. A separate
review chat remains the base method; simply switching profiles in the same
chat does not discard the implementation context.

For continuity, the handoff skill writes project facts to `.kiro-kit/handoff.md`.
It does not import personal Codex history or modify Kiro's Memory settings.
Optional Kiro Memory is a separate user/account capability and must be
qualified separately if enabled.

Sources: [model selection](https://kiro.dev/docs/models/),
[model field](https://kiro.dev/docs/custom-agents/configuration-reference/#model-field),
[skills](https://kiro.dev/docs/skills/), [workflows](https://kiro.dev/docs/workflows/),
[memory](https://kiro.dev/docs/memory/).

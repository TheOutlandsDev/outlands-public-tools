# Research and Development Papers for Coding Agents

These papers should inform agent design and evaluation. They are not a substitute for code-quality doctrine or tests.

## Code generation and evaluation

### Evaluating Large Language Models Trained on Code / HumanEval

Use for:

- Functional correctness evaluation.
- pass@k concepts.
- Unit-test-based code generation assessment.

Do not overfit to HumanEval. It is small and widely known.

## Agentic tool use

### ReAct

Use for:

- Interleaving reasoning, action, and observation.
- Tool-use loop design.
- More interpretable trajectories.

### Reflexion

Use for:

- Using feedback and memory to improve future attempts.
- Post-failure reflection.

Do not let self-reflection replace external tests or human review.

### Self-Refine

Use for:

- Iterative feedback and refinement.
- Review-rewrite loops.

Require objective checks before accepting the refined result.

## Software engineering agents

### SWE-bench

Use for:

- Realistic issue-to-patch evaluation.
- Repository-level code editing tasks.
- Test-based patch validation.

### SWE-agent

Use for:

- Agent-computer interface design.
- File editing, navigation, and test feedback loops.

### Agentless

Use for:

- Simple localization-repair-validation baselines.
- Avoiding unnecessary agent complexity.

## Code model background

### CodeT5

Use for:

- Identifier-aware code representation ideas.
- Code understanding and generation background.

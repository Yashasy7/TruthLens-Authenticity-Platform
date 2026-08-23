# TruthLens Project Instructions

## Source of Truth

Before making any implementation, architectural, or design decision:

1. Read and follow `AGENTS.md`.
2. Refer to the project blueprint located at:
   `docs/blueprint/TruthLens_Master_Technical_Architectural_Blueprint.md`
3. Treat the blueprint as the authoritative specification for the TruthLens project.
4. Do not contradict the architecture, module responsibilities, technologies, or requirements defined in the blueprint.
5. If the blueprint does not specify something, inspect the existing code first and ask before making a major architectural decision.
## Team Development Rules

- Do not modify another team's module without discussion.
- Follow existing naming conventions.
- Do not introduce new dependencies without approval.
- Write tests for new functionality.
- Do not commit secrets or API keys.
- Keep changes limited to the assigned module whenever possible.
- Do not restructure another team's module without discussion.
- Reuse existing project components before creating new ones.

## AI/ML Developer — Vishal

Vishal is responsible for the AI/ML portion of TruthLens.

When working on AI/ML:

1. Read the TruthLens blueprint before implementing functionality.
2. Inspect the existing `ai-ml/` code before creating new files.
3. Keep AI/ML implementation inside `ai-ml/` unless integration with another module is required.
4. Coordinate with the relevant team member before modifying backend or frontend code.
5. Write tests for new AI/ML functionality.
6. Do not introduce ML libraries or other dependencies without team approval.
7. Do not commit model weights, API keys, credentials, or other secrets.
8. Preserve the architecture defined in the blueprint.
9. If the blueprint does not specify an implementation detail, do not make a major architectural decision without discussing it with the team.

## Implementation Process

Before coding:

1. Read the relevant blueprint section.
2. Inspect the existing code.
3. Identify the files that need to change.
4. Explain the planned changes.
5. Implement the smallest appropriate change.
6. Add/update tests.
7. Run the relevant tests.
8. Report what was changed and any remaining issues.
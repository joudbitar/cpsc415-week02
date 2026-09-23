# Project conventions

<!-- The agent reads this at the start of every session. Keep it short and current.
     Graded: does it reflect how the team actually works? -->

## What this repository is
One paragraph. Link to the current `spec.md`.

## Commands
```
# build
# test
# run
# lint
```

## Conventions
- Language and style rules the agent must follow.
- Where tests live and how they are named.
- Branch and PR naming.

## Working rules

For an introductory lab, follow its explicitly assigned stages; the full chain below applies to major projects. Week 1 uses its own minimal repository.

- Write or update `intent/` and `spec.md` before code. Get `plan.md` approved before implementing.
- One feature per branch and pull request. Never push to `main` directly.
- Never commit `.env` or `.claude/settings.local.json`.
- This is the Week 2 introductory lab. Only the intent stage is assigned:
  no spec.md, no plan.md, no branches or pull requests. Commit to main.
- Standard library only. No packages, no pip install, no Maven or Gradle.

## Common mistakes
Things the agent got wrong before and must not repeat. Add to this list as they happen.

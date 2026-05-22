# Branch Map

GitFlow: `feature/*` → `dev` (PR) → `master` (PR on release).

## Stable branches

| Branch | Role |
|---|---|
| `master` | Production-ready. Only receives PRs from `dev`. |
| `dev` | Integration. All features merge here first. |

## Feature branches

| Branch | Subsystem | Status |
|---|---|---|
| `feature/mobile-app` | Android app (`android/`) | Active — scaffold in place |
| `feature/website` | Dedicated web frontend | Active — empty, work not started |
| `feature/ai-agent` | AI agent | Not created yet — branch when work begins |

## Rules

- Always branch off `dev`, not `master`.
- PRs go `feature/*` → `dev`. Never push directly to `master` or `dev`.
- `master` ← `dev` PR marks a release checkpoint.

## Checkout cheat-sheet

```bash
git checkout feature/mobile-app   # Android work
git checkout feature/website      # Website work
git checkout dev                  # Integration / reviewing combined state
git checkout master               # Stable baseline
```

## Creating a new feature branch

```bash
git checkout dev
git pull origin dev
git checkout -b feature/<name>
git push -u origin feature/<name>
```

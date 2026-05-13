# Create Release PR Skill

Open a GitHub PR from the current release branch to `main` and publish a GitHub release.

## Usage
```
/create_release_PR
/create_release_PR 1.1.0
```

- No argument → infer the version from the branch name (e.g. `release/v1.1` → `1.1.0`)
- Version argument → use it directly

## Behavior

### 1. Determine version

Read the current branch name with `git branch --show-current`. Extract the version from `release/vX.Y` → `X.Y.0`, or use the argument if provided.

### 2. Finalize CHANGELOG.md

Read `CHANGELOG.md`. If an `[Unreleased]` section exists, rename its header to `## [<version>] — <today's date>` and remove the `---` separator above it (the one between `[Unreleased]` and the previous version). If no `[Unreleased]` section exists, verify the top section already matches the target version — if not, warn and stop.

### 3. Update README.md

- Check that the API endpoints table includes all routes currently in `src/backend/main.py`. Add any missing rows.
- Check the architecture description in the `src/` tree matches the current files (e.g. `score.py` description, any new modules).

### 4. Commit and push

```bash
make pre-commit
git add CHANGELOG.md README.md
git commit -m "chore(release): finalize CHANGELOG and README for v<version>"
git push origin <current-branch>
```

### 5. Check gh is available

Run `bash -l -c "gh auth status"`. If it fails, stop and tell the user to run:
```
! brew install gh
! gh auth login
```
**Always invoke `gh` via `bash -l -c "gh ..."` — it may not be on the default PATH.**

### 6. Create the PR

```bash
bash -l -c 'gh pr create \
  --base main \
  --title "feat: VinylVault v<version>" \
  --body "..."'
```

PR body structure (follows `.github/pull_request_template.md`):

```markdown
## Description

<one paragraph summary of what this release contains>

## What's included

See [CHANGELOG.md](CHANGELOG.md) for the full list. Highlights:

<3–5 bullet points from the [version] CHANGELOG section>

## Testing

### Tests

<test count and coverage from the most recent `make test-cov` run, or run it now>

### Demo

Full rules and game-flow diagram: [How To Play Vinyl Vault](docs/how_to_play_vinylvault.md)

## PR Acceptance Criteria

- [x] Documented what's new (CHANGELOG.md, docs/)
- [x] Added in-code documentation (docstrings on all public functions)
- [x] Wrote tests for new components/features
- [x] Ensure testing of all components (both new and old)
- [x] Ran the linter to ensure style guidelines were followed
```

### 7. Tag and publish GitHub release

```bash
git tag v<version>
git push origin v<version>

bash -l -c 'gh release create v<version> \
  --title "v<version> — VinylVault" \
  --target <current-branch> \
  --notes "<release notes>"'
```

Release notes = the full `## [<version>]` block from `CHANGELOG.md`, verbatim, plus a footer link to the CHANGELOG file on GitHub.

### 8. Report

Print both URLs:
- PR: `https://github.com/irlorui/vinylvault/pull/<number>`
- Release: `https://github.com/irlorui/vinylvault/releases/tag/v<version>`

Remind the user to merge via **Squash and merge** as per the README convention.

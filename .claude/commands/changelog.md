# Changelog Skill

Update `CHANGELOG.md` with changes since the last recorded version.

## Usage
```
/changelog
/changelog 1.1.0
/changelog --released 1.0.0
```

- No argument → prepend an **[Unreleased]** section (or refresh it if one exists)
- Version number → promote **[Unreleased]** to that version with today's date
- `--released <version>` → same as above

## Behavior

### 1. Read current state
- Read `CHANGELOG.md` to find the latest recorded version and its date.
- Run `git log --format="%as %s %H"` to get all commits with dates and hashes.
- Identify the boundary: find the commit hash of the latest version's first entry, then collect all commits _after_ it. If the file has an `[Unreleased]` section already, collect commits after the most recent versioned section.

### 2. Filter and group commits
Skip commits whose message starts with: `docs`, `test`, `chore`, `style` — these are internal and don't belong in a user-facing changelog.

Map conventional commit types to Keep a Changelog categories:

| Commit prefix | Changelog section |
|---------------|-------------------|
| `feat`        | Added             |
| `fix`         | Fixed             |
| `refactor`    | Changed           |
| `perf`        | Changed           |
| `security` / `fix(security)` | Security |
| `revert`      | Removed           |

Write one bullet per commit. Extract the description after the colon; if there is a scope like `feat(wildcards):`, include it naturally in the prose. Keep bullets concise — one line each.

### 3. Write the new section

**Unreleased mode** (no version argument):
- If an `[Unreleased]` section already exists, replace it entirely with the new one.
- If it does not exist, prepend it before the first versioned section.

**Release mode** (version argument supplied):
- Replace the `[Unreleased]` header with `## [<version>] — <today's date>`.
- If there is no `[Unreleased]` section, create the versioned section from the new commits and prepend it.
- Do not modify any existing versioned sections.

### 4. Format rules
Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) strictly:
- Sections in this order (omit empty ones): Added, Changed, Deprecated, Removed, Fixed, Security
- Each section is a `### heading` with a `- bullet` list
- Separate sections from each other with a blank line
- Separate version blocks from each other with `---`

### 5. Verify
- Read back `CHANGELOG.md` to confirm the edit looks correct.
- Do **not** run `make pre-commit` — markdown is not linted by ruff.
- Report the version and number of bullets added.

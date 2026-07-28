---
quiz: detail
---

# Git Tags and Releases

## Tags

A tag is a named, **immutable** pointer to a specific commit. Unlike branches, tags don't move. They mark a commit as meaningful — typically a version release.

### Lightweight vs annotated

```bash
git tag v1.0.0                          # lightweight: just a pointer
git tag -a v1.0.0 -m "First release"   # annotated: full Git object with metadata
```

A lightweight tag is just a ref, exactly like a branch that never moves. An annotated tag is
its own Git object with a SHA of its own — see the [object model](internals.md#the-four-object-types)
for what it stores.

Prefer annotated tags — they store author, date, and message, and appear in `git describe`.

### Common operations

```bash
git tag                        # list all tags
git tag -l "v1.*"              # filter by pattern
git show v1.0.0                # show tag metadata + commit

git tag -a v0.9.0 e636bb2 -m "Beta"   # tag a past commit

git push origin v1.0.0         # push one tag (not automatic!)
git push origin --tags         # push all tags

git tag -d v1.0.0                       # delete locally
git push origin --delete v1.0.0         # delete on remote
```

!!! warning "Tags are not pushed by git push — you must push them explicitly"
    `git push` only sends commits and branch refs. Tags are ignored unless you add `--tags` (all tags) or name one explicitly: `git push origin v1.0.0`. Forgetting this is a common cause of "tag exists locally but not on GitHub" confusion.

> Tags are **not** pushed with `git push` — you must push them explicitly.

### Semantic versioning

Tags follow `vMAJOR.MINOR.PATCH` by convention — see [semver.md](../tools/semver.md) for what each part means and how dependency managers interpret it.

## Conventional Commits

A convention for commit message prefixes — `<type>[optional scope]: <description>` — that makes
history machine-parseable and lets tools (`semantic-release`, `standard-version`) decide the next
version automatically.

| Type | Meaning | Triggers |
|------|---------|----------|
| `feat` | new feature | MINOR |
| `fix` | bug fix | PATCH |
| `perf` | performance improvement | PATCH |
| `docs` | documentation only | no release |
| `style` | formatting, no code meaning change | no release |
| `refactor` | code change that's neither a fix nor a feature | no release |
| `test` | adding/correcting tests | no release |
| `build` | build system or dependencies | no release |
| `ci` | CI configuration | no release |
| `chore` | anything else (no src/test change) | no release |
| `revert` | reverts a previous commit | varies |

A `!` after the type/scope, or a `BREAKING CHANGE:` footer, forces MAJOR regardless of type:

```text
feat!: drop support for Python 3.8

fix(parser): handle empty input

BREAKING CHANGE: config file format changed from YAML to TOML
```

See [semver.md](../tools/semver.md#relation-to-changelogs) for what MAJOR/MINOR/PATCH mean —
this table is the mapping automated tools use to pick the next tag's name.

## Releases

A release is a platform layer on top of a tag (e.g. GitHub Releases). It adds:
- Human-readable release notes / changelog
- Downloadable build artifacts (binaries, wheels, etc.)
- A `release` event that CI/CD pipelines can react to

The tag is the Git-native concept; the release is the presentation layer for users and automation.

```bash
gh release create v1.0.0 --generate-notes          # auto-generate notes from commits
gh release create v1.0.0 ./dist/app --title "v1.0.0"  # attach a build artifact
```

## Typical release workflow

```bash
# 1. Tag the release commit
git tag -a v1.2.0 -m "Release v1.2.0"

# 2. Push the tag
git push origin v1.2.0

# 3. Create the GitHub release
gh release create v1.2.0 --generate-notes
```
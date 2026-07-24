# Semantic Versioning (SemVer)

A convention for version numbers, `MAJOR.MINOR.PATCH` (e.g. `2.4.1`), where each part signals how risky an upgrade is. Defined at [semver.org](https://semver.org).

| Part | Bump when | Consumer impact |
|------|-----------|------------------|
| `MAJOR` | Breaking change to the public Application Programming Interface (API) | Requires reading the changelog before upgrading |
| `MINOR` | Backwards-compatible feature added | Safe to pull in automatically |
| `PATCH` | Backwards-compatible bug fix, no API change | Always safe to apply |

Bumping a number resets the ones to its right (`1.2.3` → `2.0.0`, not `2.2.3`). "Public API" means anything a consumer could reasonably depend on — exported functions, CLI flags, config schema, HTTP endpoints — not internal implementation detail, however large the diff.

!!! tip "Additive isn't automatically MINOR"
    A new *required* parameter is a breaking change (MAJOR) even though it "adds" something — MINOR additions must stay backwards-compatible (e.g. optional with a default).

## Version ranges

Dependency managers encode "how much drift to accept" as a range over these three numbers — syntax differs by ecosystem, concept doesn't:

```
^1.2.3   # npm/Cargo: allow MINOR and PATCH bumps, not MAJOR   (>=1.2.3 <2.0.0)
~1.2.3   # npm: allow PATCH bumps only                          (>=1.2.3 <1.3.0)
1.2.*    # wildcard: any PATCH under 1.2
```

See [poetry.md](../python/tooling/poetry.md#version-constraints) for how one package manager applies caret ranges in practice.

A range is only as trustworthy as the maintainer's discipline — a PATCH release that accidentally breaks the API silently breaks every consumer pinned with `^` or `~`. This is the most common practical failure of SemVer.

## Pre-1.0 and pre-release versions

- **`0.y.z`** — API not yet considered stable; even MINOR bumps may break things. `0.x` → `1.0.0` signals "the API is now stable."
- **Pre-release tags** — `1.0.0-alpha`, `1.0.0-rc.1` — sort *before* the final release and mean "not ready for general use."
- **Build metadata** — `1.0.0+20230101` — appended with `+`, ignored when comparing precedence.

## Relation to changelogs

SemVer says *how much* changed; a changelog says *what* changed. Conventional Commits ties the two together: a `fix:` commit triggers PATCH, `feat:` triggers MINOR, a `BREAKING CHANGE:` footer triggers MAJOR — the basis for automated tools like `semantic-release`.

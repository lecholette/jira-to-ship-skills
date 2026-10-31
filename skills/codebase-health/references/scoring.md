# Scoring rubric

Use the same thresholds every run. Thresholds are defaults; if the repo configures stricter ones (linter limits, coverage gates), use those and note it.

## Contents

- [Test coverage](#test-coverage)
- [Complexity](#complexity)
- [Tech-debt signals](#tech-debt-signals)
- [Dependency freshness](#dependency-freshness)
- [File hygiene](#file-hygiene)

## Test coverage

| Score | Criteria |
|---|---|
| 1 | No tests, or the suite fails to run |
| 2 | Tests exist but many fail; critical paths untested |
| 3 | All pass; clear gaps in important areas (auth, payments, data writes) |
| 4 | All pass; few gaps; coverage tool shows roughly 70%+ |
| 5 | All pass; critical paths tested; roughly 85%+ with meaningful assertions |

Signals: pass rate (100% for score 3+), coverage percent if configured, `test_to_source_ratio` from the scan, source directories with zero tests.

## Complexity

| Score | Criteria |
|---|---|
| 1 | Several functions over 100 lines; files over 1000 lines; deep nesting |
| 2 | Many functions over 50 lines; one or more god files |
| 3 | Occasional long functions; files mostly under 500 lines |
| 4 | Few exceptions to the 50-line / 500-line guides |
| 5 | Concise functions, clear responsibilities, minimal nesting |

Flags: function over 50 lines, file over 500 lines, nesting over 3, cyclomatic complexity over 10. Use `oversized_files` and `oversized_python_functions` from the scan; for risk on changed code use the `codegraph` delta report (complexity drift and test gaps).

## Tech-debt signals

| Score | Criteria |
|---|---|
| 1 | Markers everywhere (over 100), commented-out code blocks, abandoned modules |
| 2 | 50-100 markers; known-broken areas noted but unscheduled |
| 3 | 20-50 markers; hotspots concentrated in a few files |
| 4 | Under 20 markers, most tied to tickets |
| 5 | Few markers, each referencing an issue |

Use `markers`, `marker_total`, `marker_hotspots`. Scale the counts by repo size (per 10k lines) when the repo is very large or very small.

## Dependency freshness

| Score | Criteria |
|---|---|
| 1 | Critical vulnerabilities, or abandoned packages in use |
| 2 | High-severity advisories, or more than 5 packages a major version behind |
| 3 | No critical advisories; some packages outdated |
| 4 | No advisories; fewer than 3 outdated |
| 5 | All current, pinned or locked, no advisories |

Missing lockfile on an ecosystem that normally has one (`manifests_without_lockfile`) caps the score at 3. If the audit command could not run, report `n/a`.

## File hygiene

| Score | Criteria |
|---|---|
| 1 | Secrets or credentials tracked; large binaries tracked; no `.gitignore` |
| 2 | Many untracked files that look like forgotten work; stale branches |
| 3 | Few untracked files; `.gitignore` present |
| 4 | Clean status; no secret-looking files tracked |
| 5 | Clean status; complete `.gitignore`; no tracked files over 1 MB |

Use `hygiene.untracked`, `tracked_secret_like`, `tracked_over_1mb`, `gitignore_present`. A tracked secret-looking file is always a P0 action item: report the path, never print its contents.

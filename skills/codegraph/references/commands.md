# Codegraph command cookbook

Install per SKILL.md (`uv tool install git+https://github.com/lecholette/codegraph-slicer`, Python 3.12+). Every command accepts `--format json|markdown` (default json). Exit 0 on success, 2 on any error (message on stderr).

## Contents

- [Model and limits](#model-and-limits)
- [sync](#sync)
- [map](#map)
- [slice](#slice)
- [impact](#impact)
- [flow](#flow)
- [delta](#delta)
- [Budgets](#budgets)
- [Inspecting unresolved references](#inspecting-unresolved-references)
- [Analysis limits](#analysis-limits)

## Model and limits

Python source is parsed with `ast` into a SQLite snapshot: classes, functions, methods, nested definitions, type aliases, call/import/inheritance/type-use edges, and `TESTS` edges from test files. Queries open the database read-only and never import or execute code. `sync` is the only writer.

## sync

```
codegraph-slicer sync ROOT --db DATABASE [--revision REVISION]
```

- `ROOT`: workspace directory or git repository. Without `--revision`, indexes current `.py` files (skips `.git`, `.venv`, `venv`, `__pycache__`; refuses Python symlinks).
- `--revision`: indexes that commit tree instead (immutable, cached by blob id; repeat syncs are cheap).
- One database holds one snapshot. Syncing another source replaces it, so keep base and head in separate files.
- Layout is auto-detected: top-level dirs with `__init__.py` are packages; a pure `src/` layout is indexed by import name. Output reports `source_root` and `packages`.
- A competing writer gives `database is locked` and exit 2.

## map

```
codegraph-slicer map --db DB [--seed MODULE_OR_PATH ...] [--max-tokens N] [--outline] [--snapshot]
```

Ranks files by symbol PageRank (personalized to `--seed` when given) and emits whole file skeletons (bodies as `...`, docstrings kept) while they fit. Default budget 2000. Add `--outline` for entity signatures and typed resolved neighbor edges (`CALLS`, `IMPORTS`, `USES_TYPE`, `INHERITS`, `DEFINES`). Refuses when source changed since sync, unless `--snapshot` (query the cached bytes on purpose).

## slice

```
codegraph-slicer slice --db DB ANCHOR [ANCHOR ...] [--max-tokens N] [--outline] [--include-callee-bodies] [--snapshot]
```

Anchor forms:

| Form | Meaning |
|---|---|
| `package.module:qualname` | Symbol, e.g. `acme.core:Service.run` |
| `path/file.py:qualname` | Symbol by path (relative to the sync root, `/` separators) |
| `path/file.py:42` | Innermost definition containing line 42 |
| `symbol_id` | Exact id from earlier output |
| `package.module:` | Whole module source |

Output sections: required (full anchor implementations, rendering targets first and summarizing oversized related classes), upstream callers (signatures), then downstream callees (signatures, or bodies with the flag), added in rank order while the budget allows. Default budget 8000. Pass `--outline` to omit implementation bodies and keep only structure.

## impact

```
codegraph-slicer impact ANCHOR --db DB [--max-depth N] [--max-nodes N] [--format json|markdown]
```

Reports bounded transitive callers by traversing resolved `CALLS` edges backwards from the anchor. Default `--max-depth 3` and `--max-nodes 200`. Witnesses show call reachability. Use for blast-radius analysis before changing or retiring shared functions.

## flow

```
codegraph-slicer flow ANCHOR --db DB [--variable NAME_OR_PATH] [--line N]
         [--direction backward|forward] [--data-only] [--max-tokens N]
```

Intraprocedural statement graph for one function or method (profile `python-local-cpg-v1`).

- No `--variable`/`--line`: the full function graph. With both: nodes matching both.
- `backward` (default) = what feeds the value; `forward` = what it affects. Control dependencies are included unless `--data-only`.
- An unknown variable or line is refused, not approximated.
- Supported: assignments, augmented/annotated assignments, expressions, if/elif/else, for/while with else, break/continue, return/raise, assert/pass, eager walrus, try/except/finally (with exception data bindings), with/async with, and comprehensions.
- Refused with a location: async/await outside async with, yield, lambdas, nested definitions, imports, global/nonlocal, `del`, walrus under short-circuit.
- Calls are opaque: arguments and receivers are visible, return values and side effects are not inferred. Aliases are unresolved.
- Report includes symbol id, path, blob id, and SHA-256 of the analyzed source. Default budget 8000; no trimming, it errors if the selection does not fit.

## delta

```
codegraph-slicer delta --base-db BASE --head-db HEAD --full --max-tokens 200000 [--forbid-import SOURCE TARGET ...]
          [--selected-test PATH ...]
```

Example:

```bash
codegraph-slicer sync repo --revision origin/main --db /tmp/base.sqlite
codegraph-slicer sync repo --revision HEAD --db /tmp/head.sqlite
codegraph-slicer delta --base-db /tmp/base.sqlite --head-db /tmp/head.sqlite --full --max-tokens 200000 \
  --forbid-import app.domain app.web --selected-test tests.test_orders:test_order_total
```

Report fields: `added_edges`, `removed_edges`, `new_cycles` (module-import and call SCCs), `boundary_violations`, `modified_symbols`, `complexity_drift` (positive drift of 10 or more in complexity or fan-out is flagged), `affected_entrypoints`, `untested_modified_symbols`, `test_coverage` (per changed symbol: `reachable_tests` and `updated_or_selected_tests`).

- Edge identity is `(source, target, kind)`; the reported line is one representative occurrence.
- `untested_modified_symbols`: modified non-test symbols with no upstream test (reverse reachability via CALLS/IMPORTS/TESTS/DEFINES) that was itself changed in this diff or passed via `--selected-test`.
- `--selected-test` accepts a file path, module name, or symbol id, but use symbol ids (`tests.test_calc:test_add`) only: file or module selection masks gaps through module IMPORTS/DEFINES reachability. Pytest node ids (`tests/x.py::test_y`) exit 2. An unobserved selection exits 2. Test symbols are files under `tests/` or named `test_*`.
- A test counts as updated only if its own source changed; selection records intent, not execution.
- Test candidates come from head test symbols. Reachability is import-level and can credit a test with reaching a function in a module it merely imports.
- Entrypoints: `__main__` modules, paths containing `cli`, `scripts`, `mcp`, and symbols named `main`.
- `--forbid-import` takes a source prefix and a target prefix per rule, including prefixes with no indexed module. No default rules.

With codegraph-slicer PR #4 (open as of 2026-10-31): `--full` also emits `import_changes`, so emitted plus omitted matches the total for every kind; budgeted output ranks untested modified symbols right after boundary violations and new cycles; markdown labels the count "untested modified symbols (none selected)" when no test was selected, so a zero there is not verified coverage. `scripts/delta_gate.py` works with both versions and still refuses budgeted output.

## Budgets

Estimates, not tokenizer counts: `len(compact_json) // 4 + 1`. A slice budgets its `sections`, a map its `items`, a flow its whole report. Keys, ids, locations, and escaped source all count; markdown rendering and outer metadata do not. If a required anchor does not fit, raise `--max-tokens`.

`map` and `slice` report what a budget dropped (codegraph-slicer PR #5, `map-slice-omitted-counts`): JSON gains `"omitted": {"<kind>": <count>}` and `"retrieve_details": "rerun with --max-tokens N"`; markdown gets the same note. Emitted plus omitted equals the unlimited total. No note means nothing was dropped. With the PR, the budget covers the complete printed output (note and trailing newline included), `tokens` reports that size, and a budget too small for even the note exits 2. Before it, optional neighbors were dropped silently and `tokens` measured only `items`/`sections`. Example at `--max-tokens 400` on the slicer's own repo: `{"tokens": 382, "items": [1 file], "omitted": {"files": 24}, ...}`.

## Inspecting unresolved references

Unmatched, shadowed, external, or dynamic references are stored in a `diagnostics` table, never invented as symbols:

```bash
python3 - <<'PY'
import sqlite3
db = sqlite3.connect("file:/tmp/graph.sqlite?mode=ro", uri=True)
for row in db.execute("SELECT source_file,line,target,reason FROM diagnostics ORDER BY 1,2,3"):
    print(*row, sep="\t")
PY
```

## Analysis limits

- Static syntax model: no whole-program control flow, runtime dispatch, alias analysis, or runtime import evaluation.
- Package roots are not inferred beyond the `src/` layout. Indexing a package directory itself drops the package prefix from module names.
- Not modelled: star imports, writes through `globals()`/`vars()`/`exec`/`eval`, `setattr`, cross-module assignment, module `__getattr__`, `sys.modules` replacement.
- `self`/`cls` calls resolve to the lexical class method, not the runtime override.
- Conditionally bound names and external dependencies can stay unresolved. Repeated definitions keep the final binding plus a diagnostic.
- `CALLS` edges are static and can be falsified at runtime.

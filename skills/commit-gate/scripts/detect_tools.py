#!/usr/bin/env python3
"""Detect lint, format, type-check, and test commands from repo config files. Stdlib only.

Usage: detect_tools.py [repo_root]
Prints JSON: {"checks": [{"kind", "tool", "command", "source"}]}
"""
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
checks = []


def add(kind, tool, command, source):
    checks.append({"kind": kind, "tool": tool, "command": command, "source": source})


def read(name):
    p = root / name
    return p.read_text(errors="ignore") if p.is_file() else None


pkg = read("package.json")
if pkg:
    try:
        scripts = json.loads(pkg).get("scripts", {})
    except ValueError:
        scripts = {}
    kinds = {"lint": "lint", "format:check": "format", "typecheck": "types",
             "type-check": "types", "check": "lint", "test": "test"}
    for key, kind in kinds.items():
        if key in scripts:
            add(kind, "npm", f"npm run {key}" if key != "test" else "npm test", "package.json")
    if (root / "tsconfig.json").is_file() and not any(c["kind"] == "types" for c in checks):
        add("types", "tsc", "npx tsc --noEmit", "tsconfig.json")

pyproject = read("pyproject.toml") or ""
if "[tool.ruff" in pyproject or (root / "ruff.toml").is_file():
    add("lint", "ruff", "ruff check .", "ruff config")
    add("format", "ruff", "ruff format --check .", "ruff config")
if "[tool.black" in pyproject:
    add("format", "black", "black --check .", "pyproject.toml")
if "[tool.mypy" in pyproject or (root / "mypy.ini").is_file():
    add("types", "mypy", "mypy .", "mypy config")
if (root / "pyrightconfig.json").is_file() or "[tool.pyright" in pyproject:
    add("types", "pyright", "pyright", "pyright config")
if "[tool.pytest" in pyproject or (root / "pytest.ini").is_file() or (root / "tests").is_dir() and pyproject:
    add("test", "pytest", "pytest -q --tb=short -x", "pytest config")

if (root / "go.mod").is_file():
    add("types", "go", "go vet ./...", "go.mod")
    add("test", "go", "go test ./...", "go.mod")
if (root / "Cargo.toml").is_file():
    add("lint", "cargo", "cargo clippy", "Cargo.toml")
    add("test", "cargo", "cargo test", "Cargo.toml")

makefile = read("Makefile") or ""
for target in ("lint", "check", "typecheck", "test"):
    if re.search(rf"^{target}\s*:", makefile, re.M):
        add("test" if target == "test" else "lint", "make", f"make {target}", "Makefile")

if (root / ".pre-commit-config.yaml").is_file():
    add("hooks", "pre-commit", "pre-commit run --files $(git diff --name-only HEAD)", ".pre-commit-config.yaml")

print(json.dumps({"root": str(root), "checks": checks}, indent=2))

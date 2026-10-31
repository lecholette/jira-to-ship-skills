#!/usr/bin/env python3
"""Deterministic repo health counts. Stdlib only, Python 3.8+, read-only.

Usage: health_scan.py [REPO] [--max-file-lines N] [--max-func-lines N] [--format json|text]

Reports: language mix, source/test file counts and ratio, oversized files,
oversized Python functions (via ast), TODO/FIXME/HACK/XXX markers, detected
dependency manifests and lockfile age, git hygiene (untracked files, tracked
secret-looking or large files). It never runs project code or the network.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build",
             "target", ".tox", ".mypy_cache", ".pytest_cache", ".next", "vendor", ".idea", ".gradle"}
LANGS = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
         ".ts": "typescript", ".tsx": "typescript", ".go": "go", ".rs": "rust", ".java": "java",
         ".kt": "kotlin", ".rb": "ruby", ".php": "php", ".cs": "csharp", ".c": "c", ".h": "c",
         ".cpp": "cpp", ".cc": "cpp", ".swift": "swift", ".scala": "scala", ".sh": "shell"}
MANIFESTS = {
    "package.json": "npm", "pyproject.toml": "python", "requirements.txt": "python", "Pipfile": "python",
    "setup.py": "python", "go.mod": "go", "Cargo.toml": "rust", "pom.xml": "maven",
    "build.gradle": "gradle", "build.gradle.kts": "gradle", "Gemfile": "ruby", "composer.json": "php",
    "mix.exs": "elixir", "Package.swift": "swift"}
LOCKS = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "poetry.lock", "uv.lock",
         "Pipfile.lock", "go.sum", "Cargo.lock", "Gemfile.lock", "composer.lock"}
MARKER = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
SECRET_NAME = re.compile(r"(^|/)(\.env(\..+)?|.*\.pem|.*\.key|id_rsa|.*credentials.*\.json)$", re.I)
SAFE_ENV = re.compile(r"\.env\.(example|sample|template)$")


def is_test(rel):
    p = rel.replace(os.sep, "/").lower()
    base = os.path.basename(p)
    return (any(seg in ("test", "tests", "__tests__", "spec", "specs") for seg in p.split("/")[:-1])
            or base.startswith("test_") or re.search(r"(_test|\.test|\.spec)\.[a-z]+$", base) is not None)


def git(repo, *args):
    try:
        out = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, timeout=30)
        return out.stdout if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def py_long_functions(path, limit):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read())
    except (SyntaxError, ValueError, OSError):
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
            if n > limit:
                found.append({"name": node.name, "line": node.lineno, "lines": n})
    return found


def scan(repo, max_file, max_func):
    langs, files, big_files, big_funcs = {}, [], [], []
    markers = {"TODO": 0, "FIXME": 0, "HACK": 0, "XXX": 0}
    marker_files = {}
    manifests, locks = [], []
    src = tests = 0
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, repo)
            if name in MANIFESTS:
                manifests.append({"file": rel, "ecosystem": MANIFESTS[name]})
            if name in LOCKS:
                locks.append({"file": rel, "age_days": int((time.time() - os.path.getmtime(full)) / 86400)})
            ext = os.path.splitext(name)[1].lower()
            lang = LANGS.get(ext)
            if not lang:
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue
            langs[lang] = langs.get(lang, 0) + 1
            if is_test(rel):
                tests += 1
            else:
                src += 1
            if len(lines) > max_file:
                big_files.append({"file": rel, "lines": len(lines)})
            hit = 0
            for line in lines:
                for m in MARKER.findall(line):
                    markers[m] += 1
                    hit += 1
            if hit:
                marker_files[rel] = hit
            if lang == "python":
                for f in py_long_functions(full, max_func):
                    f["file"] = rel
                    big_funcs.append(f)
    hygiene = {"is_git": False}
    status = git(repo, "status", "--porcelain")
    if status is not None:
        tracked = (git(repo, "ls-files") or "").splitlines()
        sizes = []
        for t in tracked:
            try:
                if os.path.getsize(os.path.join(repo, t)) > 1_000_000:
                    sizes.append(t)
            except OSError:
                pass
        hygiene = {
            "is_git": True,
            "untracked": [l[3:] for l in status.splitlines() if l.startswith("??")][:50],
            "modified_count": sum(1 for l in status.splitlines() if not l.startswith("??")),
            "tracked_secret_like": [t for t in tracked if SECRET_NAME.search(t) and not SAFE_ENV.search(t)],
            "tracked_over_1mb": sizes[:20],
            "gitignore_present": os.path.exists(os.path.join(repo, ".gitignore")),
        }
    big_files.sort(key=lambda x: -x["lines"])
    big_funcs.sort(key=lambda x: -x["lines"])
    return {
        "repo": os.path.abspath(repo),
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        "source_files": src, "test_files": tests,
        "test_to_source_ratio": round(tests / src, 2) if src else None,
        "thresholds": {"max_file_lines": max_file, "max_func_lines": max_func},
        "oversized_files": big_files[:20], "oversized_python_functions": big_funcs[:20],
        "markers": markers, "marker_total": sum(markers.values()),
        "marker_hotspots": sorted(marker_files.items(), key=lambda kv: -kv[1])[:10],
        "manifests": manifests, "lockfiles": locks,
        "manifests_without_lockfile": [m["file"] for m in manifests
                                       if m["ecosystem"] in ("npm", "ruby", "php", "rust") and not locks],
        "hygiene": hygiene,
        "notes": ["Function length is measured for Python only; use the repo's linter for other languages.",
                  "Dependency freshness and vulnerabilities need the ecosystem tool; see SKILL.md."],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--max-file-lines", type=int, default=500)
    ap.add_argument("--max-func-lines", type=int, default=50)
    ap.add_argument("--format", choices=("json", "text"), default="json")
    a = ap.parse_args()
    if not os.path.isdir(a.repo):
        print("not a directory: %s" % a.repo, file=sys.stderr)
        return 2
    r = scan(a.repo, a.max_file_lines, a.max_func_lines)
    if a.format == "json":
        print(json.dumps(r, indent=2))
    else:
        print("languages: %s" % r["languages"])
        print("source/test files: %s/%s (ratio %s)" % (r["source_files"], r["test_files"], r["test_to_source_ratio"]))
        print("oversized files: %d, oversized py funcs: %d, markers: %d" % (
            len(r["oversized_files"]), len(r["oversized_python_functions"]), r["marker_total"]))
        print("manifests: %s; lockfiles: %s" % ([m["file"] for m in r["manifests"]], [l["file"] for l in r["lockfiles"]]))
        print("hygiene: %s" % json.dumps(r["hygiene"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

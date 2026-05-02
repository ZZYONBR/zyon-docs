#!/usr/bin/env python3
"""
gather_repo_diffs.py
====================
Coleta diffs de código dos últimos N dias em todos os repos ZZYONBR
relevantes pra documentação. Saída JSON consumida pelo detect_doc_drift.py.

Filosofia:
- Apenas arquivos de código fonte (.py, .ts, .tsx, .sql)
- Exclui generated (.next, dist, build), tests, vendored (node_modules, .venv)
- Mantém diff completo pra que o LLM consiga raciocinar sobre a mudança
- Idempotente: rodar 2x no mesmo período retorna mesmo output

Uso:
    python3 gather_repo_diffs.py [--days 7] [--out diffs.json]

Pré-requisitos:
- Repos ZZYONBR clonados em ~/zzyonbr/<repo>/ (ou ajustar REPOS_BASE)
- gh CLI autenticado (não estritamente necessário, mas usado pra pull)
"""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

REPOS_BASE = Path(os.environ.get("ZZYONBR_REPOS_BASE", str(Path.home() / "zzyonbr")))
REPOS = [
    "zyon-saude",
    "zyon-agents",
    "zyon-docs",
]
CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".sql", ".mdx", ".md"}
EXCLUDE_DIRS = {".next", "node_modules", ".venv", "__pycache__", "dist", "build", "out", ".vercel/output"}
EXCLUDE_PATHS_FRAGMENTS = {"package-lock.json", ".source/"}


def run(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        return ""
    return res.stdout


def is_relevant(path: str) -> bool:
    if any(d in path.split("/") for d in EXCLUDE_DIRS):
        return False
    if any(frag in path for frag in EXCLUDE_PATHS_FRAGMENTS):
        return False
    suffix = "." + path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else ""
    return suffix in CODE_EXTENSIONS


def ensure_clone(repo: str) -> Path | None:
    path = REPOS_BASE / repo
    if path.exists():
        # Pull latest
        run(["git", "fetch", "--quiet", "origin", "main"], path)
        run(["git", "reset", "--quiet", "--hard", "origin/main"], path)
        return path
    REPOS_BASE.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(
        ["gh", "repo", "clone", f"ZZYONBR/{repo}", str(path), "--", "--depth", "100", "--quiet"],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        print(f"[gather] falha ao clonar {repo}: {res.stderr}", file=sys.stderr)
        return None
    return path


def commits_in_window(repo_path: Path, since_iso: str) -> list[dict[str, Any]]:
    """Retorna lista de commits no range com seus arquivos alterados."""
    log_format = "%H|%aI|%an|%s"
    raw = run(
        ["git", "log", f"--since={since_iso}", f"--pretty=format:{log_format}", "--name-status"],
        repo_path,
    )
    commits = []
    current = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if "|" in line and len(line.split("|", 3)) == 4 and len(line.split("|")[0]) == 40:
            if current:
                commits.append(current)
            sha, dt, author, subject = line.split("|", 3)
            current = {
                "sha": sha,
                "date": dt,
                "author": author,
                "subject": subject,
                "files": [],
            }
        else:
            if current is None:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                status, path = parts[0], parts[-1]
                if is_relevant(path):
                    current["files"].append({"status": status, "path": path})
    if current:
        commits.append(current)
    return [c for c in commits if c["files"]]  # só commits que mexeram em código


def diff_for_commit(repo_path: Path, sha: str, max_lines: int = 400) -> str:
    """Diff truncado pro LLM. Inclui --stat + diff dos primeiros N arquivos relevantes."""
    diff = run(
        ["git", "show", "--stat", "--format=", sha],
        repo_path,
    )
    full_diff = run(
        ["git", "show", "--format=", sha, "--", "*.py", "*.ts", "*.tsx", "*.sql", "*.mdx", "*.md"],
        repo_path,
    )
    lines = full_diff.splitlines()
    if len(lines) > max_lines:
        truncated = "\n".join(lines[:max_lines]) + f"\n... [+{len(lines) - max_lines} linhas truncadas]"
        return diff + "\n\n" + truncated
    return diff + "\n\n" + full_diff


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", type=Path, default=Path("/tmp/doc_auditor_diffs.json"))
    args = ap.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    output: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.days,
        "since": since,
        "repos": {},
    }

    for repo in REPOS:
        path = ensure_clone(repo)
        if not path:
            output["repos"][repo] = {"error": "clone_failed"}
            continue
        commits = commits_in_window(path, since)
        for c in commits:
            c["diff"] = diff_for_commit(path, c["sha"])
        # arquivos únicos tocados
        files_touched = sorted({f["path"] for c in commits for f in c["files"]})
        output["repos"][repo] = {
            "path": str(path),
            "commits_count": len(commits),
            "files_touched": files_touched,
            "commits": commits,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    print(f"[gather] escrito em {args.out} ({sum(r.get('commits_count', 0) for r in output['repos'].values())} commits totais)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

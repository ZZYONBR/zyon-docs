#!/usr/bin/env python3
"""
detect_doc_drift.py
===================
Cruza diffs de código (gather_repo_diffs.py) com a árvore de docs em
zyon-docs/content/docs/ e identifica:

1. **drift**: doc relevante não foi atualizado mas o código tópico SIM
2. **missing**: código tocou área sem doc correspondente
3. **safe**: doc atualizada na mesma janela

Mapeamento código → doc é declarado em CODE_TO_DOC_MAP. Mantém-se
deliberadamente simples (heurística por path); o LLM resolve ambiguidades
no passo seguinte.

Saída: JSON consumido pelo SKILL.md que chama o LLM pra propor patches.

Uso:
    python3 detect_doc_drift.py \\
        --diffs /tmp/doc_auditor_diffs.json \\
        --docs ~/zzyonbr/zyon-docs/content/docs \\
        --out /tmp/doc_auditor_drift.json
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Mapeamento path-pattern → doc page (relativo a content/docs/)
# Match por prefixo. Primeiro match vence.
CODE_TO_DOC_MAP: list[tuple[str, str, str]] = [
    # (repo, path_prefix, doc_page)
    ("zyon-agents", "core/llm_router.py", "arquitetura/multi-llm.mdx"),
    ("zyon-agents", "core/llm_client.py", "arquitetura/multi-llm.mdx"),
    ("zyon-agents", "claudio/", "agentes/claudio.mdx"),
    ("zyon-agents", "ra1000/", "agentes/ra1000.mdx"),
    ("zyon-agents", "core/observability.py", "arquitetura/multi-llm.mdx"),
    ("zyon-saude", "src/components/ModelosTab.tsx", "torres/saude.mdx"),
    ("zyon-saude", "src/components/Tabs.tsx", "torres/saude.mdx"),
    ("zyon-saude", "src/app/api/models/", "torres/saude.mdx"),
    ("zyon-saude", "src/app/api/dashboard/", "torres/saude.mdx"),
    ("zyon-saude", "src/", "torres/saude.mdx"),
]


def find_doc_for_change(repo: str, file_path: str) -> str | None:
    for r, prefix, doc in CODE_TO_DOC_MAP:
        if r == repo and file_path.startswith(prefix):
            return doc
    return None


def doc_was_updated(diffs: dict[str, Any], doc_path: str) -> bool:
    """Checa se a página de doc foi atualizada na mesma janela."""
    docs_repo = diffs["repos"].get("zyon-docs", {})
    files = docs_repo.get("files_touched", [])
    needle = f"content/docs/{doc_path}"
    return any(f.endswith(needle) or f == needle for f in files)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diffs", type=Path, default=Path("/tmp/doc_auditor_diffs.json"))
    ap.add_argument("--docs", type=Path, default=Path.home() / "zzyonbr/zyon-docs/content/docs")
    ap.add_argument("--out", type=Path, default=Path("/tmp/doc_auditor_drift.json"))
    args = ap.parse_args()

    if not args.diffs.exists():
        print(f"[drift] diffs file não encontrado: {args.diffs}", file=sys.stderr)
        return 1

    diffs = json.loads(args.diffs.read_text())

    # Agrupa: doc_page → list of (repo, file_path, commits que mexeram)
    drift_per_doc: dict[str, dict[str, Any]] = {}
    missing_doc: list[dict[str, Any]] = []

    for repo, repo_data in diffs["repos"].items():
        if "error" in repo_data or repo == "zyon-docs":
            continue
        for commit in repo_data.get("commits", []):
            for file_change in commit["files"]:
                file_path = file_change["path"]
                doc_page = find_doc_for_change(repo, file_path)
                if doc_page is None:
                    missing_doc.append({
                        "repo": repo,
                        "file": file_path,
                        "commit": commit["sha"][:8],
                        "subject": commit["subject"],
                    })
                    continue
                entry = drift_per_doc.setdefault(doc_page, {
                    "doc_page": doc_page,
                    "code_changes": [],
                    "doc_was_updated": doc_was_updated(diffs, doc_page),
                    "doc_full_path": str(args.docs / doc_page),
                    "doc_exists": (args.docs / doc_page).exists(),
                })
                entry["code_changes"].append({
                    "repo": repo,
                    "file": file_path,
                    "commit": commit["sha"][:8],
                    "subject": commit["subject"],
                    "diff_excerpt": commit["diff"][:2000],
                })

    # Classificar
    drift_items = []
    for doc_page, entry in drift_per_doc.items():
        if not entry["doc_exists"]:
            entry["status"] = "missing"
        elif entry["doc_was_updated"]:
            entry["status"] = "safe"
        else:
            entry["status"] = "drift"
        drift_items.append(entry)

    output = {
        "generated_at": diffs["generated_at"],
        "window_days": diffs["window_days"],
        "summary": {
            "drift_count": sum(1 for d in drift_items if d["status"] == "drift"),
            "safe_count": sum(1 for d in drift_items if d["status"] == "safe"),
            "missing_count": sum(1 for d in drift_items if d["status"] == "missing"),
            "uncovered_files_count": len(missing_doc),
        },
        "drift_items": drift_items,
        "uncovered_files": missing_doc,
    }

    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"[drift] {output['summary']}")
    print(f"[drift] escrito em {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

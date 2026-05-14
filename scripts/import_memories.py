#!/usr/bin/env python3
"""
ZZYON Docs · Importer de memórias institucionais
================================================

Le os arquivos Markdown em:
    ~/.claude/projects/-Users-rubens2-Desktop-15--IA-AUTOMA--O-squads/memory/*.md

E gera arquivos .mdx em:
    zyon-docs/content/docs/{categoria}/{slug}.mdx

Categorização por nome de arquivo (regex). Cada MDX herda o conteúdo
Markdown original (Fumadocs aceita CommonMark + GFM) com frontmatter
title/description extraído do YAML original ou gerado a partir do
description da memória.

Uso:
    python3 scripts/import_memories.py            # gera tudo
    python3 scripts/import_memories.py --dry-run  # só lista
    python3 scripts/import_memories.py --only=agentes  # uma categoria

Idempotente: sobrescreve MDX existentes. Não toca em arquivos manuais
fora das categorias geradas (index, quickstart, etc.).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = Path.home() / ".claude/projects/-Users-rubens2-Desktop-15--IA-AUTOMA--O-squads/memory"
CONTENT_DIR = ROOT / "content/docs"

# -------------------------------------------------------------------
# Categorização — regex por prefixo de nome de arquivo
# -------------------------------------------------------------------
AGENT_NAMES = (
    "atena|atlas|hera|hermes|themis|aegis|cosmos|icarus|sofia|"
    "claudio|roberval|hefesto|metis|daedalus|demeter|"
    "mohamed|aboobakar|conselho_virtual"
)
CATEGORIES: list[tuple[str, str, str]] = [
    # (categoria, regex, descrição da categoria)
    ("agentes",      rf"^({AGENT_NAMES})(_|$)", "Os 16 agentes ZZYON + Sahaba (governança) + Conselho Virtual"),
    ("torres",       r"^(torre_|ra1000_|frota_rollout|frota_compliance|frota_routing|cidine)",
                     "As 14 torres da plataforma + pipelines operacionais"),
    ("arquitetura",  r"^(zzyon_arquitetura|zzyon_brand|zyon_torre_briefing|fabrica_gestores|icaro_conselho|autonomy_zzyon|zzyon_lex)",
                     "Visão estrutural do ecossistema ZZYON"),
    ("infra",        r"^(multi_machine|langfuse|evolution_api|compliance_fici|helio_|zyoncs_data_lake|zyoncs_rls|pg_cron|datajud|zzyon_lex_supabase|zzyon_lex_cron)",
                     "Infraestrutura técnica · Mac mini · Tailscale · Supabase · Vault"),
    ("decisoes",     r"^(fat_jc|icaro_grupos|deutsche_dedup|deutsche_cargo|torre_metas|sla_|icaro_capital|icaro_filiais|icaro_estrutura|icaro_unidades|icaro_tagline|whirlpool|electrolux_|envista_|g3_|gerente_|bid_engine|luan_loyalty|mapeamento_2026|icaro_estrutura_comercial|contatos_diretoria|ciot|zyon_agents_oficial)",
                     "Decisões canônicas e regras de negócio"),
    ("runbooks",     r"^(esl_|atlas_nfe|.*_sprint|themis_skeleton|themis_processos|data_integrity|torre_fontes|torre_nextday|ra1000_pipeline|ra1000_automation|ra1000_acionamento|frota_)",
                     "Procedimentos operacionais · pipelines · sprints entregues"),
]
FALLBACK_CATEGORY = "automacao"

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
YAML_LINE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$")
SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    yaml_block = m.group(1)
    body = content[m.end():]
    data: dict[str, str] = {}
    for line in yaml_block.splitlines():
        ym = YAML_LINE.match(line)
        if ym:
            key = ym.group(1).strip()
            val = ym.group(2).strip().strip('"').strip("'")
            data[key] = val
    return data, body


def categorize(slug: str) -> str:
    for cat, regex, _ in CATEGORIES:
        if re.match(regex, slug):
            return cat
    return FALLBACK_CATEGORY


def slugify_filename(name: str) -> str:
    s = name.lower().replace(".md", "")
    # Remove acentos básicos
    s = s.translate(str.maketrans("áàâãäéèêëíìîïóòôõöúùûüç", "aaaaaeeeeiiiiooooouuuuc"))
    s = re.sub(r"[^a-z0-9_-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    # Fumadocs prefere kebab-case
    return s.replace("_", "-")


def title_from_slug(slug: str, fallback_name: Optional[str] = None) -> str:
    if fallback_name and len(fallback_name) > 4:
        return fallback_name
    return slug.replace("-", " ").title()


def derive_title(slug: str, fm: dict, content: str) -> str:
    # 1) frontmatter `name`
    if fm.get("name"):
        return fm["name"]
    # 2) Primeira heading H1
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # 3) Slugified
    return title_from_slug(slug)


def derive_description(fm: dict, content: str) -> str:
    if fm.get("description"):
        return fm["description"]
    # Primeiro parágrafo não-vazio, sem ser heading
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("`"):
            continue
        # Limita a 160 chars
        return line[:160]
    return "Memória institucional ZZYON"


def clean_body(body: str) -> str:
    """Remove system-reminders e normaliza body para MDX."""
    body = SYSTEM_REMINDER_RE.sub("", body)
    # Remove ::: callouts no estilo claude (incompatíveis com fumadocs)
    body = body.strip()
    # Escapa <fence|content-name> se aparecer
    return body


def escape_yaml(s: str) -> str:
    s = s.replace('"', '\\"').replace("\n", " ").replace("\r", "")
    return s


def write_mdx(target: Path, title: str, description: str, body: str, source: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        f"title: \"{escape_yaml(title)}\"\n"
        f"description: \"{escape_yaml(description)}\"\n"
        "---\n"
        f"{body}\n\n"
        "---\n\n"
        f"<small><em>Importado automaticamente da memória institucional: <code>{source}</code></em></small>\n"
    )
    target.write_text(content, encoding="utf-8")


def write_meta_json(folder: Path, pages: list[str], title: Optional[str] = None) -> None:
    meta = folder / "meta.json"
    data = {"title": title or folder.name.capitalize(), "pages": pages}
    meta.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", help="apenas uma categoria")
    args = p.parse_args(argv)

    if not MEMORY_DIR.exists():
        print(f"FATAL: memory dir não encontrado: {MEMORY_DIR}", file=sys.stderr)
        return 1

    sources: list[Path] = sorted([p for p in MEMORY_DIR.glob("*.md") if p.name != "MEMORY.md"])
    print(f"Encontradas {len(sources)} memórias em {MEMORY_DIR}")

    # Páginas manuais existentes que NÃO podem ser sobrescritas
    MANUAL_PAGES = {
        "index", "quickstart", "inventario",
        "agentes/claudio", "agentes/ra1000", "agentes/roberval",
        "arquitetura/multi-llm",
        "automacao/doc-auditor",
        "infra/maquinas",
        "decisoes/index", "decisoes/001-python-vs-typescript",
        "decisoes/002-multi-llm", "decisoes/003-mac-mini-prod",
        "decisoes/004-markdown-docs",
        "runbooks/deploy-vercel",
    }

    by_category: dict[str, list[tuple[str, str, Path]]] = defaultdict(list)
    skipped: list[tuple[str, str]] = []

    for src in sources:
        slug_raw = src.name.replace(".md", "")
        category = categorize(slug_raw)
        if args.only and category != args.only:
            continue
        slug = slugify_filename(src.name)
        rel = f"{category}/{slug}"
        if rel in MANUAL_PAGES:
            skipped.append((rel, "manual page (preservada)"))
            continue
        content = src.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        title = derive_title(slug, fm, body)
        description = derive_description(fm, body)
        body = clean_body(body)
        target = CONTENT_DIR / category / f"{slug}.mdx"

        if args.dry_run:
            print(f"  [{category:13}] {slug}  ← {src.name}")
        else:
            write_mdx(target, title, description, body, src.name)

        by_category[category].append((slug, title, src))

    # Atualiza meta.json por categoria (mantém ordem alfabética + manuais primeiro)
    if not args.dry_run:
        for cat, items in by_category.items():
            folder = CONTENT_DIR / cat
            # Pega arquivos manuais existentes nessa pasta
            existing_manual = sorted([
                f.stem for f in folder.glob("*.mdx")
                if f"{cat}/{f.stem}" in MANUAL_PAGES
            ])
            imported = sorted(set(slug for slug, _, _ in items))
            # imported pode incluir conflitos com manuais — remover
            imported = [s for s in imported if f"{cat}/{s}" not in MANUAL_PAGES]
            pages = existing_manual + imported
            title_map = {
                "agentes": "Agentes",
                "torres": "Torres",
                "arquitetura": "Arquitetura",
                "infra": "Infraestrutura",
                "decisoes": "Decisões canônicas",
                "runbooks": "Runbooks",
                "automacao": "Automação & ETL",
            }
            write_meta_json(folder, pages, title=title_map.get(cat, cat.capitalize()))

    # Sumário
    print("\n=== Sumário ===")
    for cat, _, _ in CATEGORIES + [(FALLBACK_CATEGORY, "", "")]:
        n = len(by_category.get(cat, []))
        print(f"  {cat:13}  {n} arquivo(s)")
    print(f"  Skipped (manuais): {len(skipped)}")
    print(f"  Total importado:   {sum(len(v) for v in by_category.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

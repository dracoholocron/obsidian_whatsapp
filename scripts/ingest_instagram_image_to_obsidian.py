#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WRITE_REMOTE = SCRIPT_DIR / "write_obsidian_note_remote.sh"


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout.strip()


def classify(text: str):
    t = text.lower()
    rules = [
        ("10-Marketing", "Creativos", ["hook", "cta", "oferta", "campaña", "audiencia", "branding", "engagement"]),
        ("20-Ventas", "Conversion", ["precio", "descuento", "lead", "venta", "compra", "reserva"]),
        ("40-IA", "Vision", ["ai", "automat", "prompt", "modelo", "llm"]),
        ("60-Finanzas", "Mercados", ["acciones", "market", "invers", "finanzas", "trading"]),
        ("70-Noticias", "Tendencias", ["breaking", "news", "geopol", "china", "trump", "econom"]),
    ]
    best = ("00-Inbox", "General", 0)
    tags = []
    for folder, sub, kws in rules:
        score = sum(1 for k in kws if k in t)
        if score > best[2]:
            best = (folder, sub, score)
        tags.extend([k for k in kws if k in t][:2])
    tag_list = sorted(set(f"#{x[:24].replace(' ', '-')}" for x in tags))[:10] or ["#instagram", "#imagen"]
    return best[0], best[1], tag_list


def split_ideas(text: str, limit: int = 6):
    parts = re.split(r'(?<=[.!?])\s+', text.strip()) if text else []
    out = [p.strip() for p in parts if p.strip()]
    return out[:limit]


def main():
    ap = argparse.ArgumentParser(description="Guardar análisis de imagen Instagram en Obsidian")
    ap.add_argument("--image", required=True, help="Ruta local de imagen")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--caption", default="")
    ap.add_argument("--analysis", required=True, help="Resumen/insights extraídos por visión")
    ap.add_argument("--title", default="Instagram Image")
    args = ap.parse_args()

    folder, subfolder, tags = classify(f"{args.caption} {args.analysis}")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    target_folder = f"{folder}/{subfolder}/{month}"

    ideas = split_ideas(args.analysis)
    bullets = "\n".join(f"- {x}" for x in ideas) if ideas else "- Sin ideas extraídas"

    md = f"""# {args.title}

## Fuente
- Tipo: Instagram image
- Imagen local: {args.image}
- URL publicación: {args.source_url or '(no provista)'}
- Extraído: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
- Tags: #instagram #imagen {' '.join(tags)}

## Caption detectado
{args.caption or '(sin caption)'}

## Insights visuales
{bullets}

## Acciones recomendadas
- [Prioridad: Alta] Probar un creativo inspirado en este insight | KPI: CTR | Meta 7d: +15% | Medición: ads manager
- [Prioridad: Media] Extraer 3 variantes de hook y CTA | KPI: variantes testeadas | Meta 7d: 3/3 | Medición: tablero contenido

## Análisis completo
{args.analysis}
"""

    out = run([str(WRITE_REMOTE), target_folder, args.title, md])
    print(out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

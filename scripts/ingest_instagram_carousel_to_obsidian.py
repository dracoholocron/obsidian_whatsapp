#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WRITE_REMOTE = SCRIPT_DIR / "write_obsidian_note_remote.sh"


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout.strip()


def safe(s: str, n: int = 100):
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s[:n] if s else "Instagram Carousel"


def build_yt_dlp_auth_args(cookies_file: str, cookies_from_browser: str):
    args = []
    if cookies_file:
        args += ["--cookies", cookies_file]
    elif cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    return args


def fetch_meta(url: str, auth_args=None):
    auth_args = auth_args or []
    out = run(["yt-dlp", "--dump-single-json", "--no-warnings", "--skip-download", *auth_args, url])
    return json.loads(out)


def try_download_slides(url: str, workdir: Path, auth_args=None):
    auth_args = auth_args or []
    # Best effort: requires that media is accessible for this post/account.
    cmd = ["yt-dlp", "--no-warnings", "--no-progress", *auth_args, "-o", str(workdir / "slide_%(autonumber)02d.%(ext)s"), url]
    p = subprocess.run(cmd, capture_output=True, text=True)
    slides = sorted([str(x) for x in workdir.glob("slide_*.*")])
    return slides, p.returncode, (p.stderr or "").strip()


def classify(text: str):
    t = text.lower()
    if any(k in t for k in ["stock", "market", "acciones", "inversion", "portfolio", "trading", "nvidia"]):
        return "60-Finanzas", "Mercados"
    if any(k in t for k in ["news", "china", "trump", "geopolit", "econom"]):
        return "70-Noticias", "Tendencias"
    if any(k in t for k in ["marketing", "contenido", "instagram", "cta", "hook"]):
        return "10-Marketing", "Creativos"
    return "00-Inbox", "General"


def main():
    ap = argparse.ArgumentParser(description="Ingesta de carrusel de Instagram a Obsidian")
    ap.add_argument("url")
    ap.add_argument("--title", default="")
    ap.add_argument("--cookies-file", default="", help="ruta a cookies.txt exportado del navegador")
    ap.add_argument("--cookies-from-browser", default="", help="ej: chrome, firefox, edge")
    args = ap.parse_args()

    auth_args = build_yt_dlp_auth_args(args.cookies_file, args.cookies_from_browser)

    meta = fetch_meta(args.url, auth_args=auth_args)
    title = args.title or safe(meta.get("title") or "Instagram Carousel")
    desc = meta.get("description") or ""

    with tempfile.TemporaryDirectory(prefix="ig_carousel_") as td:
        slides, rc, err = try_download_slides(args.url, Path(td), auth_args=auth_args)

        folder, sub = classify(f"{title} {desc}")
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        target_folder = f"{folder}/{sub}/{month}"

        slide_lines = []
        if slides:
            for i, s in enumerate(slides, start=1):
                slide_lines.append(f"- Slide {i}: {s}")
        else:
            slide_lines.append("- No se descargaron slides automáticamente (posible restricción de Instagram/cookies).")

        md = f"""# {title}

## Fuente
- URL: {args.url}
- Extraído: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
- Tags: #instagram #carousel #imagen #pendiente

## Descripción del post
{desc if desc else '(sin descripción)'}

## Slides detectados
{chr(10).join(slide_lines)}

## Insights por slide
- Si los slides se descargan, ejecutar análisis visual/OCR por cada imagen y completar esta sección.
- Para cuentas restringidas, usar cookies de sesión en yt-dlp para habilitar descarga.

## Estado técnico
- yt-dlp download returncode: {rc}
- auth mode: {'cookies-file' if args.cookies_file else ('cookies-from-browser' if args.cookies_from_browser else 'none')}
- stderr: {err[:500] if err else '(vacío)'}
"""

        out = run([str(WRITE_REMOTE), target_folder, title, md])
        print(out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

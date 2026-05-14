#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from faster_whisper import WhisperModel

SCRIPT_DIR = Path(__file__).resolve().parent
WRITE_REMOTE = SCRIPT_DIR / "write_obsidian_note_remote.sh"


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=False)
    stdout = _decode(p.stdout or b"")
    stderr = _decode(p.stderr or b"")
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{stderr.strip()}")
    return stdout


def sanitize_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:90] if text else "TikTok Note"


def get_metadata(url: str) -> dict:
    out = run(["yt-dlp", "--dump-single-json", "--no-warnings", "--skip-download", url])
    return json.loads(out)


def download_audio(url: str, workdir: Path) -> Path:
    outtmpl = str(workdir / "source.%(ext)s")
    run(["yt-dlp", "-x", "--audio-format", "mp3", "-o", outtmpl, url])
    files = list(workdir.glob("source.*"))
    if not files:
        raise RuntimeError("Audio download failed")
    return files[0]


def transcribe(audio_path: Path, model_name: str = "small"):
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), vad_filter=True, beam_size=5)
    segs = list(segments)
    text = " ".join(s.text.strip() for s in segs if s.text.strip())
    return text, segs, info


def _chunk_sentences(text: str, max_items: int = 6):
    parts = re.split(r'(?<=[.!?])\s+', text.strip()) if text else []
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
        if len(out) >= max_items:
            break
    return out


def detect_source(url: str, meta: dict) -> str:
    u = url.lower()
    webpage = (meta.get("webpage_url") or "").lower()
    s = u + " " + webpage
    if "tiktok.com" in s:
        return "tiktok"
    if "youtube.com" in s or "youtu.be" in s:
        return "youtube"
    if "instagram.com" in s:
        return "instagram"
    return "video"


def classify_folder_and_tags(title: str, desc: str, transcript: str):
    text = f"{title} {desc} {transcript}".lower()
    rules = [
        ("10-Marketing", ["marketing", "instagram", "tiktok", "ads", "growth", "contenido", "copy", "hook"]),
        ("20-Ventas", ["ventas", "sales", "closing", "lead", "conversion", "oferta", "precio"]),
        ("30-Producto", ["product", "producto", "ux", "feature", "roadmap", "onboarding"]),
        ("40-IA", ["ai", "llm", "prompt", "rag", "context window", "whisper", "openai", "anthropic"]),
        ("50-Ops", ["ops", "operacion", "proceso", "sop", "automatiz", "workflow", "kpi"]),
        ("60-Finanzas", ["market", "mercado", "stock", "acciones", "inversion", "portfolio", "trading", "federal reserve", "nasdaq", "s&p", "finanzas"]),
        ("70-Noticias", ["news", "noticia", "geopolit", "china", "ee.uu", "trump", "gobierno", "economia global"]),
    ]
    subrules = {
        "60-Finanzas": [
            ("Macro", ["federal reserve", "inflation", "macro", "rates", "cpi", "economia"]),
            ("Trading", ["trading", "entry", "setup", "stop loss", "take profit"]),
            ("Portafolio", ["portfolio", "diversif", "rebalance", "asset allocation"]),
        ],
        "70-Noticias": [
            ("Geopolitica", ["china", "ee.uu", "trump", "war", "sanctions", "geopolit"]),
            ("Tecnologia", ["ai", "nvidia", "openai", "anthropic", "apple", "tesla"]),
            ("Mercados", ["stocks", "nasdaq", "s&p", "market", "acciones"]),
        ],
        "40-IA": [
            ("LLM", ["llm", "prompt", "context window", "rag", "tokens"]),
            ("Automatizacion", ["automation", "workflow", "agent", "pipeline", "script"]),
        ],
    }

    hits = []
    folder = "00-Inbox"
    best = 0
    for f, kws in rules:
        c = sum(1 for k in kws if k in text)
        if c > 0:
            hits.extend([k for k in kws if k in text][:3])
        if c > best:
            best = c
            folder = f

    subfolder = "General"
    best_sub = 0
    for sf, kws in subrules.get(folder, []):
        c = sum(1 for k in kws if k in text)
        if c > best_sub:
            best_sub = c
            subfolder = sf
            hits.extend([k for k in kws if k in text][:2])

    tags = sorted(set([f"#{h.replace(' ', '-')[:24]}" for h in hits]))
    tags = tags[:10] if tags else ["#inbox"]
    return folder, subfolder, tags


def build_markdown(meta: dict, transcript: str, segs, source: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = meta.get("title") or "(sin título)"
    author = meta.get("uploader") or meta.get("channel") or "(desconocido)"
    duration = meta.get("duration")
    page = meta.get("webpage_url") or meta.get("original_url") or ""
    desc = meta.get("description") or ""

    bullets = []
    for s in segs[:8]:
        t = int(s.start)
        mm = t // 60
        ss = t % 60
        line = s.text.strip()
        if line:
            bullets.append(f"- [{mm:02d}:{ss:02d}] {line}")

    summary_candidates = _chunk_sentences(transcript, max_items=5)
    executive = "\n".join([f"- {s}" for s in summary_candidates]) if summary_candidates else "- Sin suficiente audio para resumen automático"

    action_candidates = []
    for i, s in enumerate(summary_candidates[:3], start=1):
        prio = "Alta" if i == 1 else ("Media" if i == 2 else "Baja")
        action_candidates.append(
            f"- [Prioridad: {prio}] Acción: {s[:120]} | KPI: % tareas aplicadas al flujo | Meta 7d: >=70% | Medición: checklist diario"
        )
    if not action_candidates:
        action_candidates = [
            "- [Prioridad: Alta] Acción: Revisar manualmente el video y extraer 3 insights aplicables | KPI: insights accionables documentados | Meta 7d: 3/3 | Medición: nota diaria",
            "- [Prioridad: Media] Acción: Convertir insights en checklist operativo | KPI: pasos ejecutados | Meta 7d: >=80% | Medición: cumplimiento semanal",
            "- [Prioridad: Baja] Acción: Correr un experimento de 7 días | KPI: mejora vs baseline | Meta 7d: >=10% | Medición: antes/después"
        ]

    folder, subfolder, tags = classify_folder_and_tags(title, desc, transcript)

    return f"""# {title}

> Carpeta sugerida: `{folder}/{subfolder}`

## Fuente
- URL: {page}
- Autor: {author}
- Duración: {duration if duration is not None else 'no disponible'}s
- Extraído: {now}
- Tags: #video #transcripcion #source-{source} {' '.join(tags)}

## Executive brief
{executive}

## Acciones recomendadas
{chr(10).join(action_candidates)}

## Resumen breve
{desc if desc else '(sin descripción original)'}

## Puntos clave (primeros segmentos)
{chr(10).join(bullets) if bullets else '- No se detectaron segmentos'}

## Transcripción completa
{transcript if transcript else '(sin transcripción)'}
""", f"{folder}/{subfolder}"


def main():
    ap = argparse.ArgumentParser(description="Ingesta video social (TikTok/YouTube/Instagram) -> transcripción -> nota Obsidian")
    ap.add_argument("url")
    ap.add_argument("--folder", default="auto", help="auto o carpeta fija (ej. 00-Inbox)")
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    if not WRITE_REMOTE.exists():
        raise SystemExit(f"No existe script remoto: {WRITE_REMOTE}")

    with tempfile.TemporaryDirectory(prefix="tiktok_ingest_") as td:
        td_path = Path(td)
        meta = get_metadata(args.url)
        audio = download_audio(args.url, td_path)
        transcript, segs, _ = transcribe(audio, model_name=args.model)
        source = detect_source(args.url, meta)
        md, inferred_folder = build_markdown(meta, transcript, segs, source)
        note_title = sanitize_title(meta.get("title") or "Social Video Note")
        base_folder = args.folder if args.folder != "auto" else inferred_folder
        month_folder = datetime.now(timezone.utc).strftime("%Y-%m")
        target_folder = f"{base_folder}/{month_folder}"

        cmd = [str(WRITE_REMOTE), target_folder, note_title, md]
        out = run(cmd).strip()
        print(out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

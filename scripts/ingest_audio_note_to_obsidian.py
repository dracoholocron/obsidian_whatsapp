#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
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
    return stdout.strip()


def classify(text: str):
    t = text.lower()
    rules = [
        ("10-Marketing", "General", ["marketing", "contenido", "instagram", "tiktok", "campaña", "ads"]),
        ("20-Ventas", "General", ["venta", "sales", "cliente", "lead", "oferta", "cerrar"]),
        ("40-IA", "LLM", ["ia", "ai", "prompt", "rag", "modelo", "tokens"]),
        ("50-Ops", "General", ["proceso", "operación", "checklist", "flujo", "automat"]),
        ("60-Finanzas", "General", ["mercado", "acciones", "inversión", "trading", "portfolio"]),
    ]
    best = ("00-Inbox", "General", 0)
    tags = []
    for f, s, kws in rules:
        c = sum(1 for k in kws if k in t)
        if c > best[2]:
            best = (f, s, c)
        tags += [k for k in kws if k in t][:2]
    return f"{best[0]}/{best[1]}", sorted(set(f"#{x[:24].replace(' ', '-')}" for x in tags))[:8] or ["#audio-note"]


def main():
    ap = argparse.ArgumentParser(description="Ingesta nota de audio a Obsidian")
    ap.add_argument("audio_file", help="Ruta local del audio (.ogg/.mp3/.m4a/.wav)")
    ap.add_argument("--title", default="Nota de voz")
    ap.add_argument("--model", default="small")
    ap.add_argument("--folder", default="auto")
    args = ap.parse_args()

    audio = Path(args.audio_file)
    if not audio.exists():
        raise SystemExit(f"No existe audio: {audio}")

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio), vad_filter=True, beam_size=5)
    segs = list(segments)
    transcript = " ".join(s.text.strip() for s in segs if s.text.strip())

    summary_lines = [x.strip() for x in re.split(r'(?<=[.!?])\s+', transcript) if x.strip()][:5]
    summary = "\n".join(f"- {x}" for x in summary_lines) if summary_lines else "- Sin contenido suficiente"

    folder, tags = classify(transcript)
    if args.folder != "auto":
        folder = args.folder
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    target_folder = f"{folder}/{month}"

    md = f"""# {args.title}

## Fuente
- Tipo: Nota de voz WhatsApp
- Archivo: {audio.name}
- Extraído: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
- Tags: #audio #transcripcion {' '.join(tags)}

## Ideas clave
{summary}

## Próximas acciones
- [Prioridad: Alta] Convertir 1 idea en tarea ejecutable hoy | KPI: 1 tarea creada | Meta 24h: cumplida | Medición: check diario
- [Prioridad: Media] Añadir contexto o links relacionados en Obsidian | KPI: enlaces por nota | Meta 7d: >=3 | Medición: revisión semanal

## Transcripción completa
{transcript if transcript else '(sin transcripción)'}
"""

    out = run([str(WRITE_REMOTE), target_folder, args.title, md])
    print(out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

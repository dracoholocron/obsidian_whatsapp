# Arquitectura: Obsidian + WhatsApp Ingest

## Objetivo
Convertir mensajes de WhatsApp (texto, links, videos sociales y audios) en notas útiles, clasificadas y versionables dentro de Obsidian.

## Componentes

### 1) Canal de entrada (WhatsApp)
- Recibe mensajes del grupo objetivo.
- Routing por binding hacia `obsidian-inbox-agent`.
- Mantiene separación con otros grupos/agentes (ej. CRM).

### 2) Agente (`obsidian-inbox-agent`)
- Orquesta el flujo según tipo de contenido.
- Reglas en `AGENTS.md`.
- Decide pipeline de extracción/transcripción, clasificación y fallback.

### 3) Pipelines de procesamiento
- `scripts/ingest_tiktok_to_obsidian.py`
  - URL social (TikTok/YouTube Shorts/Instagram Reels)
  - `yt-dlp` descarga metadata/audio
  - `faster-whisper` transcribe localmente
  - Genera markdown estructurado (brief, acciones, transcript)
- `scripts/ingest_audio_note_to_obsidian.py`
  - Nota de voz/audio directo
  - Whisper local -> ideas clave -> markdown
- `scripts/ingest_instagram_image_to_obsidian.py`
  - Imagen Instagram (post/story/screenshot)
  - Entrada: resumen visual + OCR + caption (obtenidos por módulo de visión)
  - Salida: nota clasificada con insights y acciones
- `scripts/ingest_instagram_carousel_to_obsidian.py`
  - Carrusel Instagram (`/p/`)
  - Descarga/detección de slides con `yt-dlp` (best effort)
  - Genera nota por slide + estado técnico cuando Instagram restringe acceso
- `scripts/ingest_whatsapp_media_to_obsidian.sh`
  - Wrapper para adjuntos WhatsApp
  - Ruta automática a pipeline de audio o fallback
- `scripts/extract_tiktok_info.sh`
  - Fallback metadata cuando no hay transcripción completa

### 4) Clasificación
- Reglas por keywords -> categoría y subtema.
- Estructura destino:
  - `<categoria>/<subtema>/YYYY-MM/archivo.md`
- Ejemplos:
  - `40-IA/LLM/2026-05/...`
  - `60-Finanzas/Trading/2026-05/...`
  - `70-Noticias/Geopolitica/2026-05/...`

### 5) Persistencia en Obsidian remoto
- `scripts/write_obsidian_note_remote.sh`
- Escribe por SSH/Tailscale en host Windows:
  - `C:\obsidian\vault`

### 6) Observabilidad y continuidad
- `scripts/whatsapp-group-healthcheck.sh`
- `scripts/whatsapp-group-healthcheck-cron.sh`
- Verifica bindings, inbound, sessionKey y condiciones de salud.
- Alertas WhatsApp con cooldown (anti-spam).

## Flujo end-to-end
1. Mensaje entra por WhatsApp grupo.
2. Routing lo envía a `obsidian-inbox-agent`.
3. Agente detecta tipo:
   - link de video social -> pipeline de video
   - audio/nota de voz -> pipeline de audio
   - imagen Instagram -> análisis visual/OCR + pipeline de imagen
   - carrusel Instagram (`/p/`) -> pipeline carrusel
   - texto/link no procesable -> fallback
4. Se genera nota markdown con resumen + acciones + tags + fuente.
5. Se clasifica carpeta/subtema/mes.
6. Se escribe en vault remoto por SSH.
7. Healthcheck monitorea integridad del flujo.

## Dependencias clave
- `python3`
- `yt-dlp`
- `ffmpeg`
- `faster-whisper` (Whisper local)
- SSH operativo al host Windows del vault

## Fallos esperados y mitigaciones
- Extracción/transcripción falla -> crear nota fallback (no abortar).
- Demoras del modelo/transcripción -> logs + verificación de salida.
- Riesgo de mezcla de grupos -> bindings explícitos + healthcheck periódico.

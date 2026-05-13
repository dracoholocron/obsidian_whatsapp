# Obsidian WhatsApp Ingest

Pipeline para procesar mensajes de WhatsApp (grupo), extraer contenido de videos/redes y notas de voz, y crear notas clasificadas en Obsidian (vault remoto Windows por SSH/Tailscale).

## Arquitectura
- Ver detalle completo en: `docs/ARCHITECTURE.md`

## Componentes
- `AGENTS.md`: reglas operativas del agente `obsidian-inbox-agent`
- `scripts/ingest_tiktok_to_obsidian.py`: TikTok/YouTube Shorts/Instagram Reels -> audio -> transcripción (Whisper local) -> nota clasificada
- `scripts/ingest_audio_note_to_obsidian.py`: audio/nota de voz -> transcripción -> ideas -> nota clasificada
- `scripts/ingest_whatsapp_media_to_obsidian.sh`: wrapper para adjuntos WhatsApp
- `scripts/extract_tiktok_info.sh`: fallback metadata de TikTok
- `scripts/write_obsidian_note_remote.sh`: escritura remota a `C:\obsidian\vault`
- `scripts/whatsapp-group-healthcheck.sh`: validaciones de routing/políticas/logs
- `scripts/whatsapp-group-healthcheck-cron.sh`: wrapper con alertas + cooldown

## Estructura de salida
- `<categoria>/<subtema>/YYYY-MM/archivo.md`
- Ejemplos:
  - `40-IA/LLM/2026-05/...`
  - `60-Finanzas/Trading/2026-05/...`
  - `70-Noticias/Geopolitica/2026-05/...`

## Dependencias
- `python3`
- `yt-dlp`
- `ffmpeg`
- `faster-whisper`
- acceso SSH al host Windows del vault

## Seguridad
- No subir secretos ni credenciales (tokens, llaves privadas, passwords)
- Mantener configuración sensible fuera del repo (variables de entorno o archivos locales no versionados)

## Uso rápido
```bash
# Video social (TikTok/Shorts/Reels)
python3 scripts/ingest_tiktok_to_obsidian.py "<url>"

# Nota de voz/audio
python3 scripts/ingest_audio_note_to_obsidian.py "<audio_file>" --title "<titulo>"

# Adjunto WhatsApp (auto tipo)
bash scripts/ingest_whatsapp_media_to_obsidian.sh "<media_path>" "<titulo>"
```

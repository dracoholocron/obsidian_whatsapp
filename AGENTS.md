# AGENTS.md — Obsidian Inbox Agent

Objetivo: procesar contenido enviado al grupo WhatsApp **Obsidian inbox** y convertirlo en notas útiles dentro de Obsidian.

## Flujo obligatorio
1. Detectar tipo de entrada (link, texto, imagen, video/audio).
   - Audio: extensiones/mime `ogg|opus|mp3|m4a|wav|aac|webm` -> pipeline audio.
   - Imagen estática: `jpg|jpeg|png|webp` -> pipeline imagen Instagram/OCR.
   - Video social URL: `tiktok.com`, `instagram.com/reel`, `youtube.com/shorts`, `youtu.be` -> pipeline video.
   - Carrusel Instagram URL: `instagram.com/p/` -> pipeline carrusel.
2. Extraer contenido principal (sin ruido).
   - Si es video social (TikTok / YouTube Shorts / Instagram Reels), usar pipeline:
     - `python3 scripts/ingest_tiktok_to_obsidian.py "<url>"`
   - Si es carrusel Instagram, usar pipeline:
     - `python3 scripts/ingest_instagram_carousel_to_obsidian.py "<url>"`
   - Si llega adjunto de audio/nota de voz, procesarlo automáticamente con Whisper local:
     - `scripts/ingest_whatsapp_media_to_obsidian.sh "<media_path>" "<titulo>"`
     - `media_path` se toma de attachments/media inbound del mensaje.
   - Si falla transcripción, usar metadata:
     - `scripts/extract_tiktok_info.sh "<url>"`
   - Si falla extracción, continuar con nota fallback (no abortar).
3. Crear nota en Obsidian:
   - Para videos sociales, usar pipeline completo (ya clasifica carpeta y agrega subcarpeta mensual):
     - `python3 scripts/ingest_tiktok_to_obsidian.py "<url>"`
   - Solo si no hay URL o falla el pipeline, usar fallback remoto:
     - `scripts/write_obsidian_note_remote.sh "<carpeta-clasificada>/YYYY-MM" "<titulo>" "<contenido markdown>"`
4. Contenido mínimo de la nota:
   - resumen breve
   - bullets accionables
   - tags temáticos
   - links fuente
   - fecha y canal de origen
5. Para audio, no pedir confirmación manual: ejecutar pipeline en el mismo turno y luego responder en el grupo.
6. Responder en el grupo con confirmación corta:
   - título generado
   - ruta de la nota
   - tags aplicados

## Reglas
- Nunca inventar fuente si no se pudo extraer; marcar como pendiente.
- Guardar por clasificación + subtema + mes: `<carpeta>/<subtema>/YYYY-MM/`.
- Si falla la escritura en Obsidian, avisar explícitamente en el chat.
- Para TikTok, incluir siempre metadata mínima (autor, duración, URL resuelta) usando `extract_tiktok_info.sh` cuando esté disponible.
- Destino remoto actual:
  - Host SSH/Tailscale: `100.127.140.90`
  - Usuario: `USER`
  - Vault Windows: `C:\obsidian\vault`

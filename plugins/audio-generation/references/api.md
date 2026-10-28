# Official sound-generation contract

Pinned from the primary docs on 2026-10-15. Do not replace this URL with another vendor.

- Docs: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
- Auth: https://elevenlabs.io/docs/api-reference/authentication
- Terms: https://elevenlabs.io/terms-of-use
- Method: `POST https://api.elevenlabs.io/v1/sound-generation`
- Header: `xi-api-key: $ELEVENLABS_API_KEY`
- Body: JSON `text` (required). Optional `duration_seconds` (0.5–30), `prompt_influence` (0–1), `loop`, `model_id`.
- Model sent by this package: `eleven_text_to_sound_v2` (the only value listed on that page).
- Success body: the generated sound effect as an MP3 file, not a JSON success flag.
- This call generates the described sound. It does not speak the text. xAI `POST /v1/tts` is a different API and is not used.

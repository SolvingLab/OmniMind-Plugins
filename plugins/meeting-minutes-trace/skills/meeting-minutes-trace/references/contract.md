# Pinned contract

Fetched 2026-10-15. Do not invent fields that are not listed here.

## Identity

- Prototype: 会议纪要转写
- stableId: `proto:market:会议纪要转写`
- Required function: 转写会议纪要，一键溯源
- This adapter is not openai/whisper. Whisper v20250625 was already rejected for this row because it only documents speech recognition.
- This adapter is not 腾讯会议 and not 飞书 / Lark.
- 通义听悟 CreateTask documents 智能纪要 (`MeetingAssistance`) and GetTaskInfo returns a result URL. The result-file audio-span schema was not retrieved. Those field names are not used here.

## Host

- OpenAPI `info.version`: 1.3.4
- termsOfService: https://www.assemblyai.com/legal/terms-of-service
- Default server: `https://api.assemblyai.com`
- EU server documented for upload, and used by replacing the host: `https://api.eu.assemblyai.com`
- No other host is accepted. The API key is not sent to a redirect.
- Auth header name: `Authorization`. Value is the API key itself, not a `Bearer` prefix.
- Header is required on every request.

## Endpoints used

- `POST /v2/upload` with the file bytes. Success JSON requires `upload_url`.
- `POST /v2/transcript` with `audio_url`.
- `GET /v2/transcript/{transcript_id}` until `status` is `completed` or `error`. Other documented statuses are `queued` and `processing`.

## Meeting minutes

Summarization docs: https://www.assemblyai.com/docs/speech-understanding/summarization

The page states: "Generate summaries of your audio transcripts split into chapters with timestamps."

Documented request, one task only:

```json
{
  "audio_url": "https://assembly.ai/wildfires.mp3",
  "speech_understanding": {
    "request": {
      "summarization": {
        "summary_type": "paragraph"
      }
    }
  }
}
```

`summary_type` is `paragraph` or `bullets`. This adapter sends `paragraph`.

Documented result path:

`speech_understanding.response.summarization.summary[]`

Example item fields: `start`, `end`, `text`, `headline`. `status` is a sibling of `summary`.

The summarization page calls `start` and `end` timestamps. It does not print the unit word. The same transcript schema documents word, sentence, utterance, and entity times in milliseconds. This adapter copies the integers and does not convert them.

## Action items and decisions

Action items docs: https://www.assemblyai.com/docs/speech-understanding/action-items

The page states: "Generate action items of your audio transcripts w/ timestamps and a quote of where the action item is from."

`include_decisions: true` is documented as including decisions in the action items.

Documented item fields: `action_item`, `quote`, `timestamp`.

## Why two jobs

`speech_understanding.request` is `oneOf` summarization, action items, translation, speaker identification, or custom formatting. A combined body is not documented. `write` submits summarization first, then a second transcript for action items unless `--skip-actions` is set. Both jobs transcribe the same audio URL.

## Source trace

`trace` reads the minutes file written by `write` or `resume`. It does not call the network and does not invent a span.

- `mN` returns that summary item's official `start` and `end` when both are non-negative integers and `end` is greater than `start`.
- `aN` returns that action item's official `timestamp` and `quote`. It does not invent an end time.
- Overlapping transcript words are attached only when the completed transcript includes `words[]` with integer `start`, `end`, and string `text`, and the word interval overlaps the summary span or contains the action timestamp.

## Not claimed

No live meeting was transcribed while authoring this package. A missing key is `unavailable`, not a successful transcription.

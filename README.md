# Viddra API Examples

Official example code for the **Viddra API** — a unified, OpenAI-style REST API for **20+ AI video, image and speech models** (Wan 3.0, Kling 3.0, Seedance 2.0, Veo 3.1, Hailuo H3, FLUX and more). One API key, one billing balance, pay-per-second from **$0.12/sec** — no subscriptions, no regional gates.

- 📖 Docs: https://viddra.com/docs/
- 🧠 Live model catalog & pricing: https://viddra.com/models/ (or `GET https://api.viddra.com/v1/models`)
- 🧰 Free browser tools: https://viddra.com/tools/
- ▶️ Playground: https://viddra.com/playground/

## Price cheat sheet

Verified against the live API (`GET /v1/models`). Prices update live — the API response is the source of truth.

| Model | ID | Type | Price |
|---|---|---|---|
| Wan 3.0 (30s All-in-One) | `wan3.0-video` | Video | 480P **$0.25/s** · 720P **$0.50/s** · 1080P **$1.00/s** |
| Hailuo H3 (2K flagship) | `hailuo-h3` | Video | 768P **$0.12/s** · 2K **$0.20/s** |
| Seedance 2.0 (4K flagship) | `seedance2.0` | Video | 480P **$0.22/s** · 720P **$0.47/s** · 1080P **$1.05/s** · 4K **$2.40/s** |
| Wan 2.6 | `wan2.6` | Video | 720P $0.16/s · 1080P $0.24/s |
| Kling 3.0 Pro | `kling3.0` | Video | $0.27/s · 3–15s · native audio |
| Seedance 2.5 (30s long-form) | `seedance2.5` | Video | 480P $0.32/s · 720P $0.68/s |
| Seedance 2.0 Mini (budget) | `seedance2.0-mini` | Video | 480P $0.08/s · 720P $0.15/s |
| Seedance 1.0 Pro | `seedance` | Video | $0.13/s |
| Veo 3.1 | `veo3` | Video | $0.35/s ($0.60/s with audio) |
| Veo 3.1 Fast | `veo3.1-fast` | Video | $0.24/s |
| Hailuo 2.3 | `hailuo-2.3` | Video | 768P $0.0933/s · 1080P $0.15/s |
| FLUX.1 [dev] / FLUX.2 Pro | `flux` / `flux2-pro` | Image | $0.05 / $0.06 per image |
| Seedream 4.0 / Qwen Image | `seedream` / `qwen-image` | Image | $0.05 / $0.03 per image |
| Ideogram 3.0 | `ideogram-3.0` | Image | $0.10 per image |
| Speech 02 HD / 2.8 HD | `speech-02-hd` / `speech-2.8-hd` | Audio | $0.18 per 1k chars |

Retired models (`wan2.2`, `kling2.1`) return `MODEL_RETIRED` and no longer accept tasks.

## Quick Start (one command)

Submit your first generation with `curl` — no SDK needed. The API is plain REST + JSON.

```bash
curl -X POST https://api.viddra.com/v1/video/generations \
  -H "Authorization: Bearer $VIDDRA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "wan2.6",
    "prompt": "A cinematic shot of a neon-lit city street in the rain, ultra-detailed, 4k",
    "duration": 5,
    "resolution": "720p",
    "aspect_ratio": "16:9"
  }'

# → 202 Accepted
# {"id":"…","task_id":"…","status":"queued","model":"wan2.6","hold_usd":"0.8000", …}
```

Then poll until the task completes and download the MP4:

```bash
curl https://api.viddra.com/v1/video/generations/<id> \
  -H "Authorization: Bearer $VIDDRA_API_KEY"

# → {"status":"succeeded","video_url":"https://…","cost_usd":"0.8000", …}
```

Get a key in the [console](https://viddra.com/console/keys/) and export it:

```bash
export VIDDRA_API_KEY="your-key-here"
```

## How the async flow works

1. **Submit** — `POST /v1/video/generations` returns `202 Accepted` with a task `id` immediately. The estimated cost (`hold_usd`) is frozen from your balance.
2. **Poll** — `GET /v1/video/generations/{id}` every 3–5 seconds. Statuses: `queued` → `running` → `succeeded` / `failed`.
3. **Download** — read `video_url` (images: `result_url`) from the succeeded task.
4. **Failures are safe** — if a task fails, the held amount is **automatically refunded**.

## Examples

| File | What it shows |
|---|---|
| [`examples/python_text_to_video.py`](examples/python_text_to_video.py) | Submit a text-to-video task with any model, poll until `succeeded`, print the MP4 URL and final cost |
| [`examples/python_image_to_video.py`](examples/python_image_to_video.py) | First-frame image-to-video with `kling3.0` via `image_url` — optionally generate the first frame with FLUX first |
| [`examples/python_list_models_and_poll.py`](examples/python_list_models_and_poll.py) | Fetch the live model catalog with prices, and poll any task by id |
| [`examples/node_text_to_video.js`](examples/node_text_to_video.js) | Same async flow in plain Node.js (18+, zero dependencies) |
| [`examples/curl_quickstart.sh`](examples/curl_quickstart.sh) | Submit + poll + download in one self-contained shell script |

Run any example:

```bash
export VIDDRA_API_KEY="your-key-here"

python examples/python_text_to_video.py \
  --model wan2.6 \
  --prompt "A cat DJing at a rooftop club, cinematic, neon" \
  --duration 5 --resolution 720p

node examples/node_text_to_video.js --prompt "A sailboat racing storm waves, drone shot"

bash examples/curl_quickstart.sh
```

## Image-to-video

Per the official [image-to-video guide](https://viddra.com/blog/image-to-video-guide/), two models accept image input:

- **Kling 3.0** (`kling3.0`) — first-frame i2v via the `image_url` field, 3–15s, native audio.
- **Wan 3.0** (`wan3.0-video`) — first-frame, last-frame and reference media (up to 10 images / 5 videos / 5 audio tracks), 2–30s.

Hailuo H3 and the Seedance family are text-to-video only. See [`python_image_to_video.py`](examples/python_image_to_video.py) for a working first-frame pipeline.

## Notes

- **Base URL:** `https://api.viddra.com`
- **Auth:** `Authorization: Bearer $VIDDRA_API_KEY`
- **Rate limits:** 100 requests/min/IP; back off on `429`.
- **Errors:** every error is `{"error": {"code": "…", "message": "…"}}` — see the [error reference](https://viddra.com/docs/).
- 🔒 **Never commit real API keys.** All examples read the key from the `VIDDRA_API_KEY` environment variable and route calls through your backend in production.

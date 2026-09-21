#!/usr/bin/env node
/**
 * Viddra API — text-to-video example in plain Node.js (18+, zero dependencies).
 *
 * Flow: POST /v1/video/generations (202 Accepted) -> poll GET /v1/video/generations/{id}
 * until `succeeded` / `failed` -> read video_url.
 *
 * Requires:  export VIDDRA_API_KEY="your-key-here"
 * Usage:     node node_text_to_video.js --prompt "A sailboat racing storm waves, drone shot"
 *            node node_text_to_video.js --model kling3.0 --duration 5 --audio
 * Docs:      https://viddra.com/docs/
 */

const API = "https://api.viddra.com";

// --- tiny argv helper -------------------------------------------------------
function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : fallback;
}
const flag = (name) => process.argv.includes(name);

async function main() {
  const apiKey = process.env.VIDDRA_API_KEY;
  if (!apiKey) {
    console.error('Set the VIDDRA_API_KEY environment variable first (https://viddra.com/console/keys/).');
    process.exit(1);
  }

  const headers = {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  };

  const payload = {
    model: arg("--model", "wan2.6"),           // see GET /v1/models for all ids
    prompt: arg("--prompt", "A cinematic shot of a neon-lit city street in the rain, ultra-detailed, 4k"),
    duration: parseInt(arg("--duration", "5"), 10),
    resolution: arg("--resolution", "720p"),
    aspect_ratio: arg("--aspect-ratio", "16:9"),
  };
  if (flag("--audio")) payload.audio = true;   // native audio where the model supports it

  // 1. Submit the task — the API responds 202 immediately with a task id and
  //    the held amount (hold_usd). Failed tasks are refunded automatically.
  const submitResp = await fetch(`${API}/v1/video/generations`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (submitResp.status !== 202) {
    const err = await submitResp.json().catch(() => ({}));
    // Every Viddra error shares one envelope: {"error": {"code", "message"}}
    throw new Error(`submit failed [${submitResp.status}] ${err.error?.code}: ${err.error?.message}`);
  }
  const task = await submitResp.json();
  console.log(`202 Accepted — id=${task.id} hold_usd=${task.hold_usd}`);

  // 2. Poll every 5s until the status flips to succeeded / failed.
  const started = Date.now();
  let done;
  while (true) {
    await new Promise((r) => setTimeout(r, 5000));
    const pollResp = await fetch(`${API}/v1/video/generations/${task.id}`, { headers });
    done = await pollResp.json();
    console.log(`  status=${done.status}`);
    if (done.status === "succeeded") break;
    if (done.status === "failed") throw new Error(`task failed: ${done.error}`); // auto-refunded
    if (Date.now() - started > 15 * 60 * 1000) throw new Error("timed out after 15 minutes");
  }

  // 3. Download the MP4.
  console.log(`Done — cost_usd=${done.cost_usd}`);
  console.log(`video_url: ${done.video_url || done.result_url}`);
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});

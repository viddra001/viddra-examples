#!/usr/bin/env python3
"""Viddra API — text-to-video example.

Flow: submit an async generation task (202 Accepted) -> poll until
`succeeded` / `failed` -> download the MP4 from `video_url`.

Requires a Viddra API key: https://viddra.com/console/keys/
    export VIDDRA_API_KEY="your-key-here"

Docs: https://viddra.com/docs/
"""

import argparse
import os
import sys
import time

import requests

API_BASE = "https://api.viddra.com"
POLL_INTERVAL_SEC = 5
MAX_WAIT_SEC = 15 * 60  # give long renders room; most 5s clips finish in ~2 min


def submit_task(api_key: str, payload: dict) -> dict:
    """POST /v1/video/generations — returns 202 with the task object."""
    resp = requests.post(
        f"{API_BASE}/v1/video/generations",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )
    if resp.status_code != 202:
        # Every Viddra error shares one envelope: {"error": {"code", "message"}}
        detail = resp.json().get("error", {})
        raise RuntimeError(f"submit failed [{resp.status_code}] {detail.get('code')}: {detail.get('message')}")
    return resp.json()


def poll_task(api_key: str, task_id: str) -> dict:
    """GET /v1/video/generations/{id} until status is succeeded or failed."""
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + MAX_WAIT_SEC
    while time.time() < deadline:
        task = requests.get(f"{API_BASE}/v1/video/generations/{task_id}", headers=headers, timeout=30).json()
        status = task.get("status")
        if status == "succeeded":
            return task
        if status == "failed":
            # Held amount is automatically refunded on failure.
            raise RuntimeError(f"task failed: {task.get('error')}")
        print(f"  status={status} hold=${task.get('hold_usd')} … waiting {POLL_INTERVAL_SEC}s")
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(f"task {task_id} did not finish within {MAX_WAIT_SEC}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a video from a text prompt via the Viddra API.")
    parser.add_argument("--model", default="wan2.6",
                        help="model id, e.g. wan2.6, wan3.0-video, kling3.0, seedance2.0, hailuo-h3 (see GET /v1/models)")
    parser.add_argument("--prompt", default="A cinematic shot of a neon-lit city street in the rain, ultra-detailed, 4k")
    parser.add_argument("--duration", type=int, default=5, help="seconds; allowed values depend on the model")
    parser.add_argument("--resolution", default="720p", help="480p | 720p | 1080p | 768P | 2K | 4K — model dependent")
    parser.add_argument("--aspect-ratio", default="16:9", help="16:9 | 9:16 | 1:1 (some models allow more)")
    args = parser.parse_args()

    api_key = os.environ.get("VIDDRA_API_KEY")
    if not api_key:
        sys.exit("Set the VIDDRA_API_KEY environment variable first (https://viddra.com/console/keys/).")

    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "duration": args.duration,
        "resolution": args.resolution,
        "aspect_ratio": args.aspect_ratio,
    }
    print(f"Submitting task: model={args.model} duration={args.duration}s resolution={args.resolution}")
    task = submit_task(api_key, payload)
    task_id = task["id"]
    print(f"  202 Accepted — id={task_id} hold_usd={task.get('hold_usd')}")

    result = poll_task(api_key, task_id)
    print(f"Done in one poll cycle — cost_usd={result.get('cost_usd')}")
    print(f"video_url: {result.get('video_url') or result.get('result_url')}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Viddra API — image-to-video example (first-frame i2v).

Per Viddra's official image-to-video guide, two models accept image input:

  * kling3.0     — first-frame i2v via the `image_url` field, 3–15s, native audio.
  * wan3.0-video — first-frame, last-frame and reference media, 2–30s.

Hailuo H3 and the Seedance family are text-to-video only.

This script:
  1. takes a first-frame image URL (`--image-url`), or generates one with
     FLUX first (`--generate-frame`) using the same API key,
  2. submits a kling3.0 task with `image_url`,
  3. polls until the video is done and prints the MP4 URL.

Requires:  export VIDDRA_API_KEY="your-key-here"
Docs:      https://viddra.com/docs/
i2v guide: https://viddra.com/blog/image-to-video-guide/
"""

import argparse
import os
import sys
import time

import requests

API_BASE = "https://api.viddra.com"
POLL_INTERVAL_SEC = 5
MAX_WAIT_SEC = 20 * 60

# Verified allowed image_size values for `flux` (named sizes, fal-style).
FLUX_IMAGE_SIZES = {"square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_4_3", "landscape_16_9"}


def viddra_post(api_key: str, path: str, payload: dict) -> dict:
    resp = requests.post(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )
    if resp.status_code not in (200, 202):
        detail = resp.json().get("error", {})
        raise RuntimeError(f"{path} failed [{resp.status_code}] {detail.get('code')}: {detail.get('message')}")
    return resp.json()


def poll(api_key: str, path: str, task_id: str) -> dict:
    """Poll a task endpoint (/v1/video/generations or /v1/image/generations) until done."""
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + MAX_WAIT_SEC
    while time.time() < deadline:
        task = requests.get(f"{API_BASE}{path}/{task_id}", headers=headers, timeout=30).json()
        status = task.get("status")
        if status == "succeeded":
            return task
        if status == "failed":
            raise RuntimeError(f"task failed: {task.get('error')}")  # hold auto-refunded
        print(f"  status={status} … waiting {POLL_INTERVAL_SEC}s")
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(f"task {task_id} did not finish within {MAX_WAIT_SEC}s")


def generate_first_frame(api_key: str, prompt: str, image_size: str) -> str:
    """Create a still with FLUX and return its URL (result_url)."""
    if image_size not in FLUX_IMAGE_SIZES:
        raise ValueError(f"image_size must be one of {sorted(FLUX_IMAGE_SIZES)}")
    print(f"Generating first frame with flux (image_size={image_size}) …")
    task = viddra_post(api_key, "/v1/image/generations", {
        "model": "flux",
        "prompt": prompt,
        "image_size": image_size,
        "num_images": 1,
    })
    done = poll(api_key, "/v1/image/generations", task["id"])
    url = done.get("result_url")
    if not url:
        raise RuntimeError(f"no result_url on finished image task: {done}")
    print(f"  first frame ready: {url}")
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="First-frame image-to-video with kling3.0 via the Viddra API.")
    parser.add_argument("--prompt", default="Slow dolly-in on the sneaker, dust particles drifting "
                        "through the rim light, subtle camera shake, dark studio ambience",
                        help="motion prompt — describe the movement, the image already shows the scene")
    parser.add_argument("--image-url", default=None, help="public URL of the first-frame image")
    parser.add_argument("--generate-frame", action="store_true",
                        help="generate the first frame with FLUX instead of supplying --image-url")
    parser.add_argument("--frame-prompt", default="Studio product photo of a white sneaker on a "
                        "dark pedestal, dramatic rim lighting",
                        help="prompt used only when --generate-frame is set")
    parser.add_argument("--image-size", default="square_hd", help=f"FLUX size: {sorted(FLUX_IMAGE_SIZES)}")
    parser.add_argument("--duration", type=int, default=5, help="3–15 seconds for kling3.0")
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--audio", action="store_true", help="enable kling3.0 native audio")
    args = parser.parse_args()

    api_key = os.environ.get("VIDDRA_API_KEY")
    if not api_key:
        sys.exit("Set the VIDDRA_API_KEY environment variable first (https://viddra.com/console/keys/).")

    image_url = args.image_url
    if not image_url and args.generate_frame:
        image_url = generate_first_frame(api_key, args.frame_prompt, args.image_size)
    if not image_url:
        sys.exit("Provide --image-url <url> or use --generate-frame to create the first frame with FLUX.")

    # image_url turns the kling3.0 request into first-frame image-to-video.
    payload = {
        "model": "kling3.0",
        "prompt": args.prompt,
        "duration": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "image_url": image_url,
    }
    if args.audio:
        payload["audio"] = True

    print(f"Submitting i2v task: kling3.0 duration={args.duration}s audio={bool(args.audio)}")
    task = viddra_post(api_key, "/v1/video/generations", payload)
    print(f"  202 Accepted — id={task['id']} hold_usd={task.get('hold_usd')}")

    result = poll(api_key, "/v1/video/generations", task["id"])
    print(f"Done — cost_usd={result.get('cost_usd')}")
    print(f"video_url: {result.get('video_url') or result.get('result_url')}")


if __name__ == "__main__":
    main()

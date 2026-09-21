#!/usr/bin/env python3
"""Viddra API — list models & poll any task.

1. GET /v1/models returns the live catalog: model ids, types, prices and
   availability. This is the source of truth for pricing.
2. Given a task id (from any earlier generation call), poll its status until
   it finishes — works for video and image tasks.

Costs nothing to run by default (a pure GET + optional polling of an existing
task). Requires:  export VIDDRA_API_KEY="your-key-here"

Docs: https://viddra.com/docs/
"""

import argparse
import os
import sys
import time

import requests

API_BASE = "https://api.viddra.com"
POLL_INTERVAL_SEC = 5
MAX_WAIT_SEC = 20 * 60


def list_models(api_key: str) -> None:
    resp = requests.get(f"{API_BASE}/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    if resp.status_code != 200:
        detail = resp.json().get("error", {})
        raise RuntimeError(f"list models failed [{resp.status_code}] {detail.get('code')}: {detail.get('message')}")
    models = resp.json()["models"]

    print(f"{'ID':<20} {'TYPE':<7} {'PRICE':<12} {'STATUS':<8} NOTES")
    print("-" * 100)
    for m in models:
        unit = {"second": "/s", "image": "/img"}.get(m.get("unit_type"), "")
        price = f"${m['price_usd']}{unit}"
        print(f"{m['id']:<20} {m['type']:<7} {price:<12} {m.get('status', ''):<8} {(m.get('notes') or '')[:60]}")
    print("\nFull catalog: https://viddra.com/models/")


def poll_task(api_key: str, task_id: str, task_type: str) -> dict:
    """Poll /v1/video/generations/{id} or /v1/image/generations/{id} until done."""
    path = {"video": "/v1/video/generations", "image": "/v1/image/generations"}[task_type]
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + MAX_WAIT_SEC
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}{path}/{task_id}", headers=headers, timeout=30)
        if resp.status_code == 404:
            raise RuntimeError(f"task {task_id} not found under {path} (wrong --type?)")
        task = resp.json()
        status = task.get("status")
        if status == "succeeded":
            return task
        if status == "failed":
            raise RuntimeError(f"task failed: {task.get('error')}")  # hold auto-refunded
        print(f"  status={status} … waiting {POLL_INTERVAL_SEC}s")
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(f"task {task_id} did not finish within {MAX_WAIT_SEC}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="List the live Viddra model catalog and/or poll a task.")
    parser.add_argument("--task-id", default=None, help="task id to poll (from a 202 submit response)")
    parser.add_argument("--type", default="video", choices=["video", "image"], help="task type for polling")
    args = parser.parse_args()

    api_key = os.environ.get("VIDDRA_API_KEY")
    if not api_key:
        sys.exit("Set the VIDDRA_API_KEY environment variable first (https://viddra.com/console/keys/).")

    list_models(api_key)

    if args.task_id:
        print(f"\nPolling {args.type} task {args.task_id} …")
        done = poll_task(api_key, args.task_id, args.type)
        url = done.get("video_url") or done.get("result_url")
        print(f"Done — status={done['status']} cost_usd={done.get('cost_usd')}")
        print(f"result: {url}")


if __name__ == "__main__":
    main()

"""ComfyUI headless API client.

Speaks to ComfyUI's REST API at /prompt, /history, and /view to:
  1. Queue a Wan2.1-Fun-Control workflow with variable seed/CFG/control.
  2. Poll until execution completes (or timeout).
  3. Download the output MP4 to the local candidates folder.
"""

from __future__ import annotations

import json
import logging
import random
import shutil
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import request, error, parse

from . import config

log = logging.getLogger(__name__)


class ComfyUIError(Exception):
    """Any failure communicating with the ComfyUI backend."""


def _url(path: str) -> str:
    return f"{config.COMFYUI_BASE_URL}{path}"


def _post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = request.Request(
        _url(path),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except error.URLError as exc:
        raise ComfyUIError(f"POST {path} failed: {exc}") from exc


def _get_json(path: str) -> dict:
    try:
        with request.urlopen(_url(path), timeout=30) as resp:
            return json.loads(resp.read())
    except error.URLError as exc:
        raise ComfyUIError(f"GET {path} failed: {exc}") from exc


def _download_file(url: str, dest: Path) -> Path:
    try:
        with request.urlopen(url, timeout=120) as resp:
            with open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
    except error.URLError as exc:
        raise ComfyUIError(f"Download {url} failed: {exc}") from exc
    return dest


def health_check() -> bool:
    """Return True if ComfyUI is reachable."""
    try:
        _get_json("/system_stats")
        return True
    except ComfyUIError:
        return False


def build_wan21_workflow(
    prompt_text: str,
    *,
    seed: int | None = None,
    cfg_scale: float = config.DEFAULT_CFG_SCALE,
    control_strength: float = config.DEFAULT_CONTROL_STRENGTH,
    control_video_path: str | None = None,
    width: int = config.DEFAULT_WIDTH,
    height: int = config.DEFAULT_HEIGHT,
    num_frames: int = config.DEFAULT_NUM_FRAMES,
    steps: int = config.DEFAULT_STEPS,
) -> dict[str, Any]:
    """Construct the ComfyUI API-format workflow for Wan2.1-Fun-1.3B-Control.

    The returned dict is ready to POST to /prompt.  Node IDs follow
    the standard ComfyUI convention (string numbers).  Adjust the
    node IDs if your saved workflow differs.
    """
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    client_id = str(uuid.uuid4())

    workflow: dict[str, Any] = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg_scale,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "Wan2.1-Fun-1.3B-Control.safetensors",
            },
        },
        "5": {
            "class_type": "EmptyLatentVideo",
            "inputs": {
                "width": width,
                "height": height,
                "length": num_frames,
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_text,
                "clip": ["4", 1],
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "blurry, distorted, low quality, static, watermark",
                "clip": ["4", 1],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2],
            },
        },
        "9": {
            "class_type": "SaveAnimatedWEBP",
            "inputs": {
                "filename_prefix": f"draft_{seed}",
                "fps": config.DEFAULT_FPS,
                "lossless": False,
                "quality": 85,
                "method": "default",
                "images": ["8", 0],
            },
        },
    }

    if control_video_path:
        workflow["10"] = {
            "class_type": "LoadVideo",
            "inputs": {
                "video": control_video_path,
                "force_rate": config.DEFAULT_FPS,
                "force_size": f"{width}x{height}",
            },
        }
        workflow["11"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "strength": control_strength,
                "control_net": ["12", 0],
                "image": ["10", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
            },
        }
        workflow["12"] = {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": "wan2.1_fun_control_canny.safetensors",
            },
        }
        workflow["3"]["inputs"]["positive"] = ["11", 0]
        workflow["3"]["inputs"]["negative"] = ["11", 1]

    return {"prompt": workflow, "client_id": client_id}


def queue_prompt(workflow_payload: dict) -> str:
    """Queue a workflow and return the prompt_id."""
    resp = _post_json("/prompt", workflow_payload)
    prompt_id = resp.get("prompt_id")
    if not prompt_id:
        raise ComfyUIError(f"No prompt_id in response: {resp}")
    return prompt_id


def poll_until_complete(prompt_id: str) -> dict:
    """Block until the prompt finishes or timeout is reached."""
    deadline = time.monotonic() + config.COMFYUI_TIMEOUT_SEC
    while time.monotonic() < deadline:
        history = _get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("completed", False) or status.get("status_str") == "success":
                return entry
            if status.get("status_str") == "error":
                raise ComfyUIError(
                    f"ComfyUI execution error: {status.get('messages', '')}"
                )
        time.sleep(config.COMFYUI_POLL_INTERVAL_SEC)
    raise ComfyUIError(f"Timed out waiting for prompt {prompt_id}")


def download_outputs(
    history_entry: dict,
    dest_dir: Path,
) -> list[Path]:
    """Pull all output files from a completed ComfyUI run into *dest_dir*."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    outputs = history_entry.get("outputs", {})
    downloaded: list[Path] = []

    for _node_id, node_out in outputs.items():
        for media_type in ("images", "videos", "gifs"):
            for item in node_out.get(media_type, []):
                fname = item.get("filename", "")
                subfolder = item.get("subfolder", "")
                params = parse.urlencode({
                    "filename": fname,
                    "subfolder": subfolder,
                    "type": item.get("type", "output"),
                })
                url = _url(f"/view?{params}")
                dest = dest_dir / fname
                download_file_path = _download_file(url, dest)
                downloaded.append(download_file_path)
                log.info("Downloaded %s → %s", fname, dest)

    return downloaded


def generate_single(
    prompt_text: str,
    *,
    seed: int | None = None,
    cfg_scale: float = config.DEFAULT_CFG_SCALE,
    control_strength: float = config.DEFAULT_CONTROL_STRENGTH,
    control_video_path: str | None = None,
    dest_dir: Path | None = None,
) -> tuple[list[Path], dict]:
    """End-to-end: build workflow → queue → poll → download.

    Returns (downloaded_paths, history_entry).
    """
    dest = dest_dir or config.CANDIDATE_DIR
    payload = build_wan21_workflow(
        prompt_text,
        seed=seed,
        cfg_scale=cfg_scale,
        control_strength=control_strength,
        control_video_path=control_video_path,
    )
    pid = queue_prompt(payload)
    log.info("Queued prompt %s (seed=%s, cfg=%.1f)", pid, seed, cfg_scale)
    entry = poll_until_complete(pid)
    paths = download_outputs(entry, dest)
    return paths, entry

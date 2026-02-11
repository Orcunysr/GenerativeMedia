"""
Wiro openai/sora-2-pro ile foto + prompt'tan kısa video üretir.
State'ten poster_image_address (veya ilk referans görsel) + video_scenario (senaryo/prompt) alır.
Auth: create_foto ile aynı (WIRO_API_KEY, WIRO_API_SECRET).
"""
import hmac
import hashlib
import os
import time
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

WIRO_VIDEO_MODEL = "openai/sora-2-pro"
RUN_URL = f"https://api.wiro.ai/v1/Run/{WIRO_VIDEO_MODEL}"
TASK_DETAIL_URL = "https://api.wiro.ai/v1/Task/Detail"
POLL_INTERVAL = 5
MAX_POLLS = 120  # video daha uzun sürebilir: 5*120 = 600s = 10 dk


def _get_wiro_headers() -> tuple[str, dict]:
    """Nonce + HMAC ile Wiro auth (create_foto ile aynı)."""
    api_key = os.getenv("WIRO_API_KEY")
    api_secret = os.getenv("WIRO_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("WIRO_API_KEY ve WIRO_API_SECRET .env'de olmalı.")
    nonce = str(int(time.time()))
    message = api_secret + nonce
    signature = hmac.new(
        bytes(api_key, "utf8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return nonce, {
        "x-api-key": api_key,
        "x-nonce": nonce,
        "x-signature": signature,
        "Content-Type": "application/json",
    }


def _poll_task_result(task_id: str) -> dict:
    """Task/Detail ile sonucu alana kadar poll eder."""
    for _ in range(MAX_POLLS):
        time.sleep(POLL_INTERVAL)
        _, headers = _get_wiro_headers()
        resp = requests.post(TASK_DETAIL_URL, headers=headers, json={"taskid": task_id}, timeout=60)
        data = resp.json()
        if not data.get("result") or not data.get("tasklist"):
            continue
        task_info = data["tasklist"][0]
        status = task_info.get("status", "")
        if status == "task_postprocess_end":
            return task_info
        if "error" in status or status == "task_cancel":
            raise RuntimeError(task_info.get("debugerror") or status)
    raise TimeoutError(f"Video task {task_id} {MAX_POLLS * POLL_INTERVAL}s içinde tamamlanmadı.")


def run_wiro_video(
    prompt: str,
    input_image_url: Optional[str] = None,
    *,
    seconds: str = "8",
    resolution: str = "720p",
    ratio: str = "auto",
) -> str:
    """
    Wiro openai/sora-2-pro ile image-to-video üretir.
    - prompt: Video için senaryo / hareket betimi (video_scenario veya kısa metin).
    - input_image_url: Başlangıç görseli URL veya dosya (tek). Boşsa text-to-video.
    - seconds: "4", "8" veya "12" (API zorunlu parametre).
    - resolution: "720p" veya "1080p".
    - ratio: "16:9", "9:16" veya "auto".
    Döner: Üretilen videonun CDN URL'i.
    """
    _, headers = _get_wiro_headers()
    payload: dict[str, Any] = {
        "prompt": prompt,
        "seconds": str(seconds),
        "resolution": resolution,
        "ratio": ratio,
    }
    if input_image_url:
        payload["inputImage"] = input_image_url

    resp = requests.post(RUN_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    run_data = resp.json()
    if not run_data.get("result"):
        raise RuntimeError(run_data.get("errors") or "Wiro Video Run başarısız.")

    task_id = run_data.get("taskid")
    if not task_id:
        raise RuntimeError("taskid dönmedi.")

    task_info = _poll_task_result(task_id)
    out_url = None

    # outputs[] array (Wiro: outputs[0].url veya video için farklı key)
    def _find_url(obj: Any) -> Optional[str]:
        if isinstance(obj, str) and (obj.startswith("http://") or obj.startswith("https://")):
            return obj
        if isinstance(obj, dict):
            for k in ("url", "fileurl", "outputUrl", "output_url", "videoUrl", "video_url", "src"):
                u = obj.get(k)
                if u and isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                    return u
            for v in obj.values():
                if isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
                    return v
        return None

    outputs = task_info.get("outputs") or []
    for out in outputs:
        out_url = _find_url(out)
        if out_url:
            break

    if not out_url:
        raw_out = task_info.get("output")
        if isinstance(raw_out, str) and (raw_out.startswith("http://") or raw_out.startswith("https://")):
            out_url = raw_out
        elif isinstance(raw_out, dict):
            out_url = raw_out.get("url") or raw_out.get("fileurl")
        elif isinstance(raw_out, list) and len(raw_out):
            first = raw_out[0]
            out_url = first if isinstance(first, str) and first.startswith("http") else (first.get("url") or first.get("fileurl") if isinstance(first, dict) else None)
        if not out_url:
            out_url = task_info.get("outputUrl") or task_info.get("output_url") or task_info.get("outputVideo")
    if not out_url:
        for key in ("outputUrl", "output_url", "result_url", "videoUrl", "video_url", "fileurl", "url"):
            u = task_info.get(key)
            if u and isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                out_url = u
                break

    if not out_url:
        # task_postprocess_end ile bitti ama URL yok; debugoutput bazen "Request started." gibi anlamsız
        err = task_info.get("debugerror")
        if not err and task_info.get("debugoutput") and "output" in (task_info.get("debugoutput") or "").lower():
            err = task_info.get("debugoutput")
        raise RuntimeError(err or "No video URL in task output. Check task_info.outputs / output.")
    return out_url


# Sora'ya giderken absürt/surreal çıktıyı azaltmak için prompt sonuna eklenen zorunlu kısım
VIDEO_PROMPT_SUFFIX = " Realistic, natural motion only. No surreal, absurd or fantastical elements. Same scene and product throughout. Professional product advertisement."


def create_video(
    state: dict[str, Any],
    *,
    prompt: Optional[str] = None,
    seconds: str = "8",
    resolution: str = "720p",
    ratio: str = "auto",
) -> dict[str, Any]:
    """
    State'ten poster görseli + video senaryosu alıp Wiro Sora 2 Pro ile video üretir.
    - prompt yoksa state["video_scenario"] kullanılır.
    - Görsel: state["poster_image_address"] (üretilmiş reklam görseli) veya items_image_address / user_image_address (URL olmalı).
    Döner: {"video_image_address": "<video_url>", "generated_video_prompt": "<kullanılan prompt>"}.
    """
    raw = (prompt or (state.get("video_scenario") or "").strip()) or "Smooth, professional product shot with subtle motion and lighting."
    video_prompt = (raw + VIDEO_PROMPT_SUFFIX).strip()
    input_image_url: Optional[str] = None
    for key in ("poster_image_address", "items_image_address", "user_image_address"):
        v = state.get(key)
        if v and isinstance(v, str) and v.strip():
            v = v.strip()
            if v.startswith("http://") or v.startswith("https://") or v.startswith("data:"):
                input_image_url = v
                break
    if not input_image_url and state.get("poster_image_address"):
        input_image_url = state["poster_image_address"]

    video_url = run_wiro_video(
        prompt=video_prompt,
        input_image_url=input_image_url,
        seconds=seconds,
        resolution=resolution,
        ratio=ratio,
    )
    return {
        "video_image_address": video_url,
        "generated_video_prompt": video_prompt,
    }

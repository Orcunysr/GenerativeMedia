"""
Wiro google/nano-banana-pro ile foto üretir.
State'ten image prompt (create_image_prompt) ve referans fotoğraf (items_image_address / user_image_address) alır.
- user_image_address: Kullanıcının bilgisayarından yüklediği fotoğraf — yerel dosya yolu (örn. /path/to/photo.jpg)
  veya http(s) URL. Yerel dosya okunup base64 data URL'ye çevrilir; Wiro'a doğrudan içerik gider.
- items_image_address: Ürün görseli (URL'den çekilen veya yerel path).
Auth: config'teki gibi WIRO_API_KEY, WIRO_API_SECRET (hmac + nonce).
"""
import base64
import hmac
import hashlib
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, List, Optional

import requests
from dotenv import load_dotenv

from graph.chains.create_image_prompt import create_image_prompt

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

WIRO_IMAGE_MODEL = "google/nano-banana-pro"
RUN_URL = f"https://api.wiro.ai/v1/Run/{WIRO_IMAGE_MODEL}"
TASK_DETAIL_URL = "https://api.wiro.ai/v1/Task/Detail"
POLL_INTERVAL = 3
MAX_POLLS = 100


def _get_wiro_headers() -> tuple[str, dict]:
    """Nonce + HMAC signature ile Wiro auth header'ları döner (görsel Run API)."""
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
    headers = {
        "x-api-key": api_key,
        "x-nonce": nonce,
        "x-signature": signature,
        "Content-Type": "application/json",
    }
    return nonce, headers


def _poll_task_result(task_id: str) -> dict:
    """Task/Detail ile sonucu alana kadar poll eder. task_postprocess_end'de task_info döner."""
    for _ in range(MAX_POLLS):
        time.sleep(POLL_INTERVAL)
        _, headers = _get_wiro_headers()
        resp = requests.post(TASK_DETAIL_URL, headers=headers, json={"taskid": task_id}, timeout=30)
        data = resp.json()
        if not data.get("result") or not data.get("tasklist"):
            continue
        task_info = data["tasklist"][0]
        status = task_info.get("status", "")
        if status == "task_postprocess_end":
            return task_info
        if "error" in status or status == "task_cancel":
            raise RuntimeError(task_info.get("debugerror") or status)
    raise TimeoutError(f"Task {task_id} {MAX_POLLS * POLL_INTERVAL}s içinde tamamlanmadı.")


def run_wiro_image(
    prompt: str,
    input_image_urls: Optional[List[str]] = None,
    *,
    aspect_ratio: str = "1:1",
    resolution: str = "1K",
    safety_setting: str = "OFF",
) -> str:
    """
    Wiro google/nano-banana-pro ile image üretir.
    - prompt: Görsel için metin prompt'u (create_image_prompt çıktısı).
    - input_image_urls: Referans görsel URL'leri (ürün fotoğrafı vb.). Boşsa text-to-image.
    Döner: Üretilen görselin CDN URL'i.
    """
    _, headers = _get_wiro_headers()
    payload: dict[str, Any] = {
        "prompt": prompt,
        "aspectRatio": aspect_ratio,
        "resolution": resolution,
        "safetySetting": safety_setting,
    }
    if input_image_urls:
        payload["inputImage"] = input_image_urls

    resp = requests.post(RUN_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    run_data = resp.json()
    if not run_data.get("result"):
        raise RuntimeError(run_data.get("errors") or "Wiro Run başarısız.")

    task_id = run_data.get("taskid")
    if not task_id:
        raise RuntimeError("taskid dönmedi.")

    task_info = _poll_task_result(task_id)
    out_url = None

    # Try outputs[].url (array of {url: ...})
    outputs = task_info.get("outputs") or []
    if outputs and isinstance(outputs[0], dict):
        out_url = outputs[0].get("url")

    # Fallback: single output / outputUrl / result at top level
    if not out_url:
        raw_out = task_info.get("output")
        if isinstance(raw_out, str):
            out_url = raw_out
        elif isinstance(raw_out, dict):
            out_url = raw_out.get("url")
        elif isinstance(raw_out, list) and len(raw_out) and isinstance(raw_out[0], str):
            out_url = raw_out[0]
        elif isinstance(raw_out, list) and len(raw_out) and isinstance(raw_out[0], dict):
            out_url = raw_out[0].get("url")
        if not out_url:
            out_url = task_info.get("outputUrl") or task_info.get("output_url")

    if not out_url:
        err = task_info.get("debugerror") or task_info.get("debugoutput") or "No image output."
        keys = list(task_info.keys())
        raise RuntimeError(
            f"{err} (status={task_info.get('status')}); task_info keys: {keys}"
        )
    return out_url


def _local_path_to_data_url(file_path: str) -> Optional[str]:
    """
    Yerel dosya yolunu okuyup data:image/...;base64,... formatında döner.
    Dosya yoksa veya okunamazsa None.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    mime, _ = mimetypes.guess_type(str(path))
    if not mime or not mime.startswith("image/"):
        mime = "image/jpeg"
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def get_first_image_data_url(state: dict[str, Any]) -> Optional[str]:
    """State'teki ilk görseli (yerel path veya URL) data URL veya http URL olarak döner. Vision/prompt için kullanılır."""
    urls = _input_images_from_state(state)
    return urls[0] if urls else None


def _input_images_from_state(state: dict[str, Any], user_image_first: bool = True) -> List[str]:
    """
    State'ten referans görsel listesini toplar (Wiro'a gidecek inputImage).
    user_image_first=True ise önce user_image_address (yüklenen foto), sonra items_image_address.
    Yerel path ise dosya okunup base64 data URL'ye çevrilir (bilgisayardan upload = doğrudan içerik).
    """
    order = ("user_image_address", "items_image_address") if user_image_first else ("items_image_address", "user_image_address")
    out: List[str] = []
    for key in order:
        v = state.get(key)
        if not v or not isinstance(v, str):
            continue
        v = v.strip()
        if not v:
            continue
        if v.startswith("http://") or v.startswith("https://"):
            out.append(v)
        elif v.startswith("data:"):
            out.append(v)
        else:
            # Yerel dosya yolu: bilgisayardan yüklenen fotoğraf
            data_url = _local_path_to_data_url(v)
            if data_url:
                out.append(data_url)
    return out


def create_foto(
    state: dict[str, Any],
    *,
    prompt: Optional[str] = None,
    aspect_ratio: str = "1:1",
    resolution: str = "1K",
) -> dict[str, Any]:
    """
    State'ten prompt + referans fotoğraf alıp Wiro ile görsel üretir.
    - prompt yoksa create_image_prompt(state) ile üretilir.
    - Referans görsel: state["items_image_address"] (ürün foto URL) veya state["user_image_address"] (kullanıcı foto URL).
    Wiro harici URL'yi reddederse (Invalid image file) referans olmadan text-to-image denenir.
    Döner: {"poster_image_address": "<url>", "generated_image_prompt": "<prompt>"}.
    """
    image_prompt = prompt or create_image_prompt(state)
    input_urls = _input_images_from_state(state)

    # Referans varsa: çıktıda MUTLAKA referans fotoğraftaki ürün olmalı; model başka ürün (losyon, başka marka vb.) üretmesin
    if input_urls:
        items_story = (state.get("items_story") or "").strip()
        image_desc = (state.get("image_description") or "").strip()
        generic = "Reference product or user photo provided"
        # Önce vision betimlemesi (marka, ürün adı, şişe, renk) — bu ürünü kilitle
        product_lock = ""
        if image_desc and not image_desc.startswith(generic):
            product_lock = f" REFERENCE PRODUCT (output must show this exact product, no other): {image_desc[:400]}. Same brand, same bottle, same label, same colors. "
        if items_story:
            product_lock += f" Product identity: {items_story[:200]}. "
        if not product_lock:
            product_lock = " The reference image is the exact product that MUST appear in the output — same bottle, same label, same brand. Do not generate a different product (e.g. no other bottle, no other brand). "
        image_prompt = (
            "CRITICAL: Output must show the EXACT SAME product as in the reference image — identical brand, bottle shape, label, and colors. Only the environment may change. "
            + product_lock
            + " Environment only: "
            + image_prompt.rstrip()
            + ". Do not alter or replace the product."
        )

    try:
        output_url = run_wiro_image(
            prompt=image_prompt,
            input_image_urls=input_urls if input_urls else None,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
    except RuntimeError as e:
        if "Invalid image file" in str(e) and input_urls:
            # Wiro harici URL kabul etmiyor; referans olmadan dene (text-to-image)
            output_url = run_wiro_image(
                prompt=image_prompt,
                input_image_urls=None,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )
        else:
            raise

    return {
        "poster_image_address": output_url,
        "generated_image_prompt": image_prompt,
        "input_image_urls": input_urls or [],
    }

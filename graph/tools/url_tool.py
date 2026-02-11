"""URL'den sayfa içeriği çeker. requests + BeautifulSoup kullanır."""
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MAX_CHARS = 8000  # LLM'e gönderilecek metin uzunluk üst sınırı


def _fetch_url(url: str, max_chars: int = MAX_CHARS) -> str:
    """URL'den HTML alır, metin çıkarır ve en fazla max_chars karakter döner."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return f"URL alınamadı: {e}"

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        # Script, style, nav vb. çıkar
        for tag in soup(["script", "style", "nav", "footer", "header", "form", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Fazla boş satırları tek satıra indir
        text = re.sub(r"\n{3,}", "\n\n", text)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[... metin kısaltıldı ...]"
        return text.strip() or "Sayfadan metin çıkarılamadı."
    except Exception as e:
        return f"İçerik ayrıştırılamadı: {e}"


def get_main_image_url(url: str) -> str:
    """Sayfadaki ana görsel URL'sini döner (og:image, product image vb.). İç kullanım."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return f""
    soup = BeautifulSoup(resp.text, "html.parser")
    # 1) og:image
    og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og and og.get("content"):
        src = og["content"].strip()
        if src.startswith("http"):
            return src
        if src.startswith("//"):
            return "https:" + src
    # 2) link rel="image_src"
    link = soup.find("link", rel="image_src")
    if link and link.get("href"):
        return link["href"].strip()
    # 3) İlk büyük ürün/gallery img
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        if not src or "logo" in src.lower() or "icon" in src.lower():
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = urljoin(url, src)
        if src.startswith("http"):
            return src
    return ""


@tool
def get_main_image_url_tool(url: str) -> str:
    """Ürün/sayfa URL'sindeki ana görselin (ürün fotoğrafı, og:image) URL'sini döner."""
    return get_main_image_url(url)


@tool
def fetch_url(url: str, max_chars: Optional[int] = None) -> str:
    """Verdiğin URL'deki sayfadan metin içeriği çeker. Ürün sayfası, haber, blog vb. için kullan."""
    return _fetch_url(url, max_chars=max_chars or MAX_CHARS)

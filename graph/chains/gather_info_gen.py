"""
Gather information: kullanıcıdan ve sistemden bilgi toplar.

Akış:
- Kullanıcı gelir, sistemle ilgili ne istediğini yazar (prompt). Mümkünse kullanıcıdan fotoğraf da alınır.
- URL vermişse: sistem URL'den arama yapıp (Tavily + sayfa içeriği) gerekli bilgileri çıkarır (run_url_pipeline).
- Sistemin URL'den çıkarması gerekenler: url_content, items_story, items_image_address, ürün bilgisi.
- Standart olarak sistem, gather_info aşamasında kullanıcıya bazı bilgileri sormalı: ne istiyor (poster/video/reklam metni), format, hedef kitle vb.
"""
from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from graph.config.llm import get_chat_model
from graph.tools import fetch_url, tavily_search, get_main_image_url
from graph.chains.state_extraction import extract_state_for_update

llm = get_chat_model()


# --- Gather aşamasında kullanılan state alanları (create_advert çıktıları burada yok) ---
# Kullanıcıdan: question, user_prompt, user_image_address (foto), url
# URL vermişse sistem çıkarır: url_content, tavily_search_results, items_image_address, items_story
# Sorulacak: user_prompt, poster_promt / video_promt, items_quality, format/hedef kitle


class allState(BaseModel):
    """Gather aşamasında kullanılan state alanları. poster_image_address / video_image_address create_advert'te dolar."""
    url: Optional[str] = Field(default=None, description="Kullanıcının verdiği link")
    url_content: Optional[str] = Field(default=None, description="URL'den çekilen sayfa metni")
    tavily_search_results: Optional[list[str]] = Field(default=None, description="Tavily arama sonuçları")
    user_prompt: Optional[str] = Field(default=None, description="Kullanıcının ne istediği: poster, reklam metni, video")
    user_image_address: Optional[str] = Field(default=None, description="Kullanıcıdan alınan fotoğraf (yerel path)")
    items_story: Optional[str] = Field(default=None, description="Ürün/hikaye (URL'den veya kullanıcıdan)")
    items_image_address: Optional[str] = Field(default=None, description="Ürün görseli (URL'den veya yerel)")
    items_quality: Optional[int] = Field(default=None, description="Kalite tercihi")
    poster_promt: Optional[str] = Field(default=None, description="Poster fikri / talimatı")
    video_promt: Optional[str] = Field(default=None, description="Video fikri / talimatı")


system_prompt = """
Sen bir reklam asistanısın. Geçmiş konuşmayı dikkate al; kullanıcının şu anki sorusuna bağlama uygun cevap ver.

Toplanan bilgiler: (1) Ürün linki veya yüklenen fotoğraf, (2) İsteğe bağlı tema/içerik (örn. kumsal teması, minimalist stil). YASAK: Poster mu video mu sorma—ikisini de üreteceğiz. Cevabın 2-3 cümle.

- Selam / nasılsın: Kısa karşıla, ne yapabileceğini özetle.
- "Neler yapabiliyorsun" / "ne yapıyorsun": Ürün linki veya fotoğraf paylaşılırsa reklam kampanyası (poster + kısa video) hazırlıyorum; linkten ürün bilgisini çekip poster ve video üretiyorum. İstersen eklemek istediğin bir tema da yazabilirsin (örn. kumsal, minimalist).
- URL/foto alındıysa: Zorunlu bir şey sorma. Sadece isteğe bağlı olarak sor: "Eklemek istediğiniz bir tema veya içerik var mı? (Örn: kumsal teması, minimalist stil) İstemezseniz sadece ürün bilgisinden devam edebilirim." Kullanıcı "yok", "devam et", "hazırla" derse veya direkt tema söylerse (kumsal, minimalist vb.) ona göre devam et; "Hazırlıyorum" / "5 seçenek hazırlıyorum" de.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Geçmiş konuşma:\n{conversation_history}\n\nState: {all_state}\n\nŞu an kullanıcı: {question}"),
])

generation_chain = prompt | llm | StrOutputParser()


def run_url_pipeline(state: dict[str, Any]) -> dict[str, Any]:
    """
    State'te url varsa: sayfayı çeker, Tavily ile arar, sayfadan fotoğraf URL'si alır,
    LLM ile ürün/hikaye bilgisini çıkarıp state güncellemesi döner.
    Grafte bu dict'i mevcut state ile merge edebilirsin.
    """
    url = (state.get("url") or "").strip()
    if not url or not url.startswith("http"):
        return {}

    question = state.get("question") or ""

    # 1) Sayfa içeriğini çek
    url_content = fetch_url.invoke({"url": url})
    if not url_content or url_content.startswith("URL alınamadı") or url_content.startswith("İçerik"):
        url_content = ""

    # 2) Tavily ile link/ürün ara (sayfa başlığından veya URL'den query üret)
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc or url[:50]
        search_query = question.strip() or domain or url[:80]
        tavily_result = tavily_search.invoke({"query": search_query})
    except Exception:
        tavily_result = ""

    # 3) Sayfadaki ana fotoğraf URL'si
    items_image_url = get_main_image_url(url)

    # 4) LLM ile sayfa + Tavily içeriğinden ürün/hikaye çıkar, state alanlarına yaz
    context = f"Page content:\n{url_content[:6000]}\n\nTavily:\n{tavily_result[:2000]}"
    updates = extract_state_for_update(user_message=question, context=context)

    # 5) Hepsi bir arada state güncellemesi
    out: dict[str, Any] = {
        "url": url,
        "url_content": url_content,
        "tavily_search_results": [tavily_result] if isinstance(tavily_result, str) else (tavily_result or []),
    }
    if items_image_url:
        out["items_image_address"] = items_image_url
    for k, v in updates.items():
        if v is not None and v != "":
            out[k] = v

    return out

"""ReAct tarzı gather agent: LLM bind_tools ile araçları çağırır; ToolNode araçları çalıştırır."""
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from graph.config.llm import get_chat_model
from graph.state import State
from graph.tools import tools

GATHER_AGENT_SYSTEM = """Sen reklam kampanyası asistanısın. Elinde şu araçlar var:
- fetch_url: URL'deki sayfanın metin içeriğini çeker (ürün sayfası vb.)
- tavily_search: Web'de arama yapar
- get_main_image_url_tool: Sayfadaki ana ürün görseli URL'sini döner

Kullanıcı bir URL verdiğinde sırayla: fetch_url ile sayfa içeriğini al, get_main_image_url_tool ile ürün görseli URL'sini al, gerekirse tavily_search ile ek bilgi ara. Sonuçları özetleyip 2-3 cümleyle cevap ver. Cevabın sadece metin olsun; tekrar araç çağırma."""


def gather_agent_node(state: State) -> Dict[str, Any]:
    print("gather_agent_node çalıştı")
    """İlk turda question/url'den mesaj oluşturur; LLM bind_tools ile yanıt döner (tool_calls veya metin)."""
    messages = state.get("messages") or []
    if not messages:
        question = state.get("question") or ""
        url = (state.get("url") or "").strip()
        content = f"Soru: {question}"
        if url:
            content += f"\nÜrün URL'si: {url}. Bu URL için fetch_url, get_main_image_url_tool ve gerekirse tavily_search kullan."
        messages = [
            SystemMessage(content=GATHER_AGENT_SYSTEM),
            HumanMessage(content=content),
        ]
    llm = get_chat_model(temperature=0).bind_tools(tools)
    response = llm.invoke(messages)
    # add_messages reducer: ilk turda konuşma başlat, sonra sadece yeni yanıt ekle
    to_append = messages + [response] if not state.get("messages") else [response]
    return {"messages": to_append}

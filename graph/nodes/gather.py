from typing import Any, Dict

from graph.chains.gather_info_gen import generation_chain, run_url_pipeline
from graph.state import State
from graph.utils import state_to_str

    
def gather_node(state: State) -> Dict[str, Any]:
    print("gather_node çalıştı")
    """
    URL varsa: sayfayı çeker, Tavily arar, fotoğraf alır, LLM ile ürün/hikaye çıkarır (run_url_pipeline).
    Sonra generation_chain ile kullanıcıya cevap üretir (generated).
    """
    # 1) URL varsa pipeline (fetch, tavily, image, extraction from page)
    url_updates = run_url_pipeline(state)
    merged = {**state, **url_updates}

    # 2) Cevap üret (state + question)
    question = merged.get("question") or ""
    all_state_str = state_to_str(merged)
    generated = generation_chain.invoke({"all_state": all_state_str, "question": question})

    return {**url_updates, "generated": generated}

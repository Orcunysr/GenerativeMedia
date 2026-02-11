import sys
import os
import traceback

# Patch langchain_core.pydantic_v1 if missing
try:
    import langchain_core.pydantic_v1
    from langchain_core.pydantic_v1 import BaseModel
except ImportError:
    try:
        from pydantic import v1 as pydantic_v1
        sys.modules["langchain_core.pydantic_v1"] = pydantic_v1
    except ImportError:
        pass

sys.path.append(os.getcwd())

from graph.graph import graph

def run_test():
    print("Starting user scenario test with real inputs from test_graph.py...")
    
    # data/ klasörüne koyduğun fotoğrafı kullan (yerel dosya yolu)
    photo_path = os.path.join(os.path.dirname(__file__), "data", "1_org_zoom.webp")
    if not os.path.isfile(photo_path):
        photo_path = None  # dosya yoksa referans foto kullanılmaz

    state = {
        "question": "Topladığın bilgilerle poster oluştur.",
        "user_prompt": "poster",
        "url": "https://www.trendyol.com/the-ceel/mor-karbon-dis-beyazlatma-seti-mor-karbon-dis-macunu-75-gr-mor-karbon-dis-tozu-50-gr-p-743563691",
        "items_story": "The Ceel Mor Karbon Diş Beyazlatma Seti (75gr macun + 50gr toz). Beyaz dişler, ferah nefes. Menşei TR.",
        "items_image_address": "https://cdn.dsmcdn.com/ty10000/product/media/images/prod/PIM/20251022/12/67b36584-869f-4526-9e90-98ea2488e249/1_org_zoom.jpg",
        "user_image_address": photo_path,  # data/1_org_zoom.webp (bilgisayardan yüklenen foto)
        "activity": "create_advert"
    }

    print("\nInput State:")
    for k, v in state.items():
        print(f"  {k}: {v}")
    
    print("\nInvoking graph (REAL MODE)...")
    try:
        result = graph.invoke(state)
        print("\n--- Result ---")
        print("Generated Message:\n", result.get("generated"))
        if result.get("poster_image_address"):
            print("\nPoster Image URL:", result.get("poster_image_address"))
        
        # Also print generated prompt if available
        if result.get("image_description"):
            print("\nImage Description (fotoğrafa göre):", result.get("image_description"))
        if result.get("generated_image_prompt"):
            print("\nGenerated Image Prompt:", result.get("generated_image_prompt"))
        if result.get("video_scenario"):
            print("\n--- Reklam filmi senaryosu ---\n", result.get("video_scenario"))
        if result.get("video_image_address"):
            print("\nVideo URL:", result.get("video_image_address"))
            
    except Exception as e:
        print(f"\nError during graph invocation: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_test()

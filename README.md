# GenerativeMedia

Reklam kampanyası asistanı: ürün linki veya fotoğraf ile sohbet eder; poster ve kısa reklam videosu üretir.

## Web arayüzü (chat)

Backend + chat arayüzünü birlikte çalıştırın:

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Tarayıcıda **http://localhost:8000** açın. Mesaj yazın veya ürün linki yapıştırın; isteğe bağlı fotoğraf ekleyip gönderin. Poster ve video URL’leri sohbet içinde gösterilir.

- **API:** `POST /api/chat` — form-data: `message`, `session_id` (opsiyonel), `image` (opsiyonel dosya). Yanıt: `generated`, `poster_image_address`, `video_image_address`, `video_scenario`, `session_id`.

## Akış: Fotoğraflar → Prompt → Görsel

1. **Fotoğraflar yüklenir** (bilgisayardan: yerel dosya yolu veya URL).
2. **Sistem fotoğraflara göre prompt üretir**: Yüklenen fotoğraf vision ile betimlenir (isteğe bağlı OpenAI); bu betimleme + ürün bilgisi ile görsel prompt’u yazılır.
3. **Görsel üretilir**: Bu prompt + aynı fotoğraflar Wiro’ya gönderilir; reklam görseli çıkar.

Yani giriş = **fotoğraflar**; çıkış = **fotoğraflara göre yazılmış prompt** + **o prompt ve fotoğraflarla üretilmiş görsel**.

## Kullanıcı fotoğrafı (bilgisayardan upload)

**Fotoğraf URL’si yerine bilgisayardan yüklenen dosya** kullanılır. Sistem yerel dosya yolunu okur, görseli base64’e çevirir; hem betimleme (vision) hem Wiro görsel üretimi için kullanır.

### Nasıl kullanılır

1. Kullanıcı bir dosya seçip yüklesin; dosyayı kaydedin (örn. `data/` veya `uploads/`).
2. Graph’ı çağırırken state’e **yüklenen dosyanın yolu**nu ve (isterseniz) **soru**yu verin:

```python
state = {
    "question": "Poster oluştur.",
    "user_prompt": "poster",
    "user_image_address": "/path/to/uploaded_photo.jpg",  # yerel dosya yolu
    # İsteğe bağlı: items_story, items_image_address, url, ...
}
result = graph.invoke(state)
```

- **user_image_address**: Yerel dosya yolu veya http(s) URL (öncelik yüklenen fotoğrafta).
- **items_image_address**: İkinci referans görsel; URL veya yerel path.
- **OPENAI_API_KEY** (isteğe bağlı): Varsa fotoğraf vision ile betimlenir; prompt bu betimlemeye göre yazılır.

Desteklenen görsel formatları: jpg, png, webp vb. (mime type’a göre).

## Model seçimi (metin / senaryo)

- **Varsayılan:** Tüm metin işleri (router, extraction, gather, image prompt, video senaryo) **Wiro** üzerinden çalışır; model `.env` içindeki **MODEL_NAME** (örn. `openai/gpt-5-2`) ile seçilir. Bu kurulum çoğu kullanım için **yeterlidir**.
- **Doğrudan ChatGPT (OpenAI):** Metin için OpenAI kullanmak istersen `.env`’e ekle:
  - `USE_OPENAI_CHAT=true`
  - `OPENAI_API_KEY=sk-...`
  - İsteğe bağlı: `OPENAI_CHAT_MODEL=gpt-4o` veya `gpt-4o-mini` (varsayılan: gpt-4o-mini)

Görsel üretimi her zaman Wiro (nano-banana-pro); foto betimleme (vision) ise `OPENAI_API_KEY` varken OpenAI gpt-4o-mini ile yapılır.

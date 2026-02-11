/**
 * Tıklamalı arayüz: URL → Analiz et → Tema seç (10 hazır + özel) → Oluştur → Poster + Video
 */
const STEP_URL = 'step-url';
const STEP_THEME = 'step-theme';
const STEP_RESULT = 'step-result';

let sessionId = null;
/** Manuel eklenen ürün dosyası (sürükle-bırak); tema gönderilirken API'ye eklenir */
let manualProductFile = null;
/** Manuel önizleme için oluşturulan object URL (revoke için) */
let manualObjectUrl = null;

const urlInput = document.getElementById('product-url');
const urlError = document.getElementById('url-error');
const btnAnalyze = document.getElementById('btn-analyze');
const stepUrl = document.getElementById('step-url');
const stepTheme = document.getElementById('step-theme');
const stepResult = document.getElementById('step-result');
const themeGrid = document.getElementById('theme-grid');
const customTheme = document.getElementById('custom-theme');
const btnCreateCustom = document.getElementById('btn-create-custom');
const resultLoading = document.getElementById('result-loading');
const resultContent = document.getElementById('result-content');
const resultMessage = document.getElementById('result-message');
const posterLink = document.getElementById('poster-link');
const posterImg = document.getElementById('poster-img');
const resultVideo = document.getElementById('result-video');
const btnNew = document.getElementById('btn-new');
const backToUrl = document.getElementById('back-to-url');
const posterCard = document.getElementById('poster-card');
const videoCard = document.getElementById('video-card');
const dropZone = document.getElementById('drop-zone');
const dropZoneText = document.getElementById('drop-zone-text');
const manualFileInput = document.getElementById('manual-file');

function showStep(stepId) {
  [stepUrl, stepTheme, stepResult].forEach(el => {
    el.classList.remove('step-active', 'step-hidden');
    el.classList.add(el.id === stepId ? 'step-active' : 'step-hidden');
  });
}

function setUrlError(msg) {
  urlError.textContent = msg || '';
  urlError.classList.toggle('error-visible', !!msg);
}

function isValidUrl(s) {
  if (!s || typeof s !== 'string') return false;
  const t = s.trim();
  return /^https?:\/\/[^\s]+$/i.test(t);
}

/** Poster/video adresi yalnızca yüklenebilir http(s) URL ise true */
function isValidMediaUrl(url) {
  if (!url || typeof url !== 'string') return false;
  const u = url.trim();
  return u.startsWith('http://') || u.startsWith('https://');
}

async function apiChat(message, imageFile = null) {
  const formData = new FormData();
  formData.append('message', message);
  if (sessionId) formData.append('session_id', sessionId);
  const fileToSend = imageFile || manualProductFile;
  if (fileToSend) formData.append('image', fileToSend);
  const res = await fetch('/api/chat', { method: 'POST', body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function fillProductSummary(data, manual = null) {
  const textEl = document.getElementById('product-summary-text');
  const imgEl = document.getElementById('product-summary-img');
  const descEl = document.getElementById('product-summary-desc');
  const summaryBlock = document.getElementById('product-summary');
  if (!textEl || !imgEl || !summaryBlock) return;
  if (manual && (manual.manualImageUrl || manual.manualDescription != null)) {
    textEl.textContent = manual.manualDescription || 'Yüklediğiniz ürün görseli.';
    if (manual.manualImageUrl) {
      imgEl.src = manual.manualImageUrl;
      imgEl.alt = 'Ürün görseli';
      imgEl.style.display = '';
      summaryBlock.classList.remove('no-image');
    } else {
      imgEl.removeAttribute('src');
      imgEl.style.display = 'none';
      summaryBlock.classList.add('no-image');
    }
    if (descEl) {
      descEl.textContent = '';
      descEl.style.display = 'none';
    }
    return;
  }
  const msg = (data.generated || '').trim();
  const summary = data.state_summary || {};
  const productImage = summary.items_image_address;
  const firstLine = msg ? msg.split('\n')[0].trim() : '';
  const shortMsg = firstLine ? (firstLine.slice(0, 160) + (firstLine.length > 160 ? '…' : '')) : '';
  textEl.textContent = shortMsg || 'Bu linkten aşağıdaki ürün bilgilerini çıkardık.';
  if (productImage) {
    imgEl.src = productImage;
    imgEl.alt = 'Ürün görseli';
    imgEl.style.display = '';
    summaryBlock.classList.remove('no-image');
  } else {
    imgEl.removeAttribute('src');
    imgEl.style.display = 'none';
    summaryBlock.classList.add('no-image');
  }
  if (descEl) {
    const desc = (data.product_description || summary.items_story || summary.url_content || '').trim();
    descEl.textContent = desc;
    descEl.style.display = desc ? 'block' : 'none';
  }
}

// Adım 1: Analiz et
btnAnalyze.addEventListener('click', async () => {
  const url = (urlInput.value || '').trim();
  if (!isValidUrl(url)) {
    setUrlError('Lütfen geçerli bir ürün linki girin.');
    return;
  }
  setUrlError('');
  btnAnalyze.disabled = true;
  btnAnalyze.textContent = 'Analiz ediliyor…';
  try {
    const data = await apiChat(url);
    sessionId = data.session_id;
    fillProductSummary(data);
    showStep(STEP_THEME);
  } catch (e) {
    setUrlError(e.message || 'Bir hata oluştu.');
  } finally {
    btnAnalyze.disabled = false;
    btnAnalyze.textContent = 'Analiz et';
  }
});

urlInput.addEventListener('input', () => setUrlError(''));
urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    btnAnalyze.click();
  }
});

// Adım 2: Tema seçimi — hazır tema butonları
themeGrid.addEventListener('click', (e) => {
  const btn = e.target.closest('.theme-btn');
  if (!btn || btn.disabled) return;
  const theme = btn.getAttribute('data-theme');
  if (!theme) return;
  runGenerate(theme === 'Farketmez' ? 'Farketmez. Hazırla.' : `${theme} teması. Hazırla.`);
});

// Özel tema + Oluştur
btnCreateCustom.addEventListener('click', () => {
  const text = (customTheme.value || '').trim();
  runGenerate(text ? `${text}. Hazırla.` : 'Hazırla.');
});

function setThemeButtonsDisabled(disabled) {
  themeGrid.querySelectorAll('.theme-btn').forEach((b) => { b.disabled = disabled; });
  btnCreateCustom.disabled = disabled;
}

function runGenerate(message) {
  setThemeButtonsDisabled(true);
  showStep(STEP_RESULT);
  resultContent.classList.add('step-hidden');
  resultLoading.classList.remove('step-hidden');
  resultMessage.textContent = '';
  resultMessage.classList.remove('error-msg');
  posterLink.href = '#';
  posterImg.src = '';
  posterImg.removeAttribute('src');
  resultVideo.src = '';
  if (posterCard) posterCard.style.display = 'none';
  if (videoCard) videoCard.style.display = 'none';

  apiChat(message)
    .then((data) => {
      sessionId = data.session_id;
      manualProductFile = null;
      if (manualObjectUrl) { URL.revokeObjectURL(manualObjectUrl); manualObjectUrl = null; }
      const hasPoster = isValidMediaUrl(data.poster_image_address);
      const hasVideo = isValidMediaUrl(data.video_image_address);
      resultLoading.classList.add('step-hidden');
      // "Hazır" ve kartları sadece geçerli poster/video URL'si geldiyse göster
      if (hasPoster || hasVideo) {
        resultContent.classList.remove('step-hidden');
        resultMessage.textContent = data.generated || 'Poster ve video hazır.';
        resultMessage.classList.remove('error-msg');
        if (hasPoster) {
          if (posterCard) posterCard.style.display = '';
          posterLink.href = data.poster_image_address;
          posterImg.src = data.poster_image_address;
        } else {
          if (posterCard) posterCard.style.display = 'none';
          posterLink.removeAttribute('href');
          posterImg.removeAttribute('src');
        }
        if (hasVideo) {
          if (videoCard) videoCard.style.display = '';
          resultVideo.src = data.video_image_address;
        } else {
          if (videoCard) videoCard.style.display = 'none';
          resultVideo.removeAttribute('src');
        }
      } else {
        // Geçerli poster/video yok; "Hazır" ekranını gösterme, loading'de kal
        const loadingText = document.querySelector('#result-loading p');
        if (loadingText) loadingText.textContent = data.generated || 'İçerik henüz hazır değil.';
      }
    })
    .catch((err) => {
      resultLoading.classList.add('step-hidden');
      resultContent.classList.remove('step-hidden');
      resultMessage.textContent = err.message || 'Oluşturulurken hata oluştu.';
      resultMessage.classList.add('error-msg');
    })
    .finally(() => setThemeButtonsDisabled(false));
}

function handleManualImageFile(file) {
  if (!file || !file.type.startsWith('image/')) return;
  if (manualObjectUrl) URL.revokeObjectURL(manualObjectUrl);
  manualProductFile = file;
  manualObjectUrl = URL.createObjectURL(file);
  sessionId = null;
  fillProductSummary({}, { manualImageUrl: manualObjectUrl, manualDescription: 'Yüklediğiniz ürün görseli.' });
  showStep(STEP_THEME);
  dropZone.classList.remove('drop-zone--over');
  dropZoneText.textContent = 'Ürün fotoğrafını buraya sürükleyip bırakın veya tıklayın';
}

if (dropZone) {
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add('drop-zone--over');
  });
  dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drop-zone--over');
  });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer?.files?.[0];
    handleManualImageFile(file);
  });
  dropZone.addEventListener('click', () => manualFileInput?.click());
  dropZone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); manualFileInput?.click(); } });
}
if (manualFileInput) {
  manualFileInput.addEventListener('change', () => {
    const file = manualFileInput.files?.[0];
    handleManualImageFile(file);
    manualFileInput.value = '';
  });
}

// Başka link analiz et
backToUrl.addEventListener('click', (e) => {
  e.preventDefault();
  sessionId = null;
  manualProductFile = null;
  if (manualObjectUrl) { URL.revokeObjectURL(manualObjectUrl); manualObjectUrl = null; }
  urlInput.value = '';
  setUrlError('');
  showStep(STEP_URL);
});

// Yeni ürün
btnNew.addEventListener('click', () => {
  sessionId = null;
  manualProductFile = null;
  if (manualObjectUrl) { URL.revokeObjectURL(manualObjectUrl); manualObjectUrl = null; }
  urlInput.value = '';
  setUrlError('');
  showStep(STEP_URL);
});

// Örnek link (opsiyonel)
document.getElementById('try-links')?.addEventListener('click', (e) => {
  e.preventDefault();
  urlInput.value = 'https://www.trendyol.com/l-oreal-paris/l-oreal-paris-revitalift-clinical-spf-50-gunluk-yuksek-uv-korumali-yuz-gunes-kremi-50ml-p-641085197';
  urlInput.focus();
});

// Manuel ekle (şimdilik aynı adımda özel tema gibi kullanılabilir)

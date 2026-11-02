# ============================================================================
#                    TMG301 — SPEECH ANALYSIS APP
#                    BẢN QUYỀN THUỘC VỀ HUYTKING
# ============================================================================
#
#   © 2026 HUYTKING. All rights reserved.
#
#   Tác giả  : HUYTKING
#   Zalo     : 0396241674
#   GitHub   : https://github.com/shirmtry
#
#   ⚠️ MỌI HÀNH VI SAO CHÉP, CHỈNH SỬA, PHÂN PHỐI
#      MÀ KHÔNG CÓ SỰ ĐỒNG Ý CỦA TÁC GIẢ ĐỀU BỊ NGHIÊM CẤM.
#
#   Liên hệ cấp phép: Zalo 0396241674
# ============================================================================

import os
import sys
import subprocess
import re
import time
from collections import OrderedDict

from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from pydub import AudioSegment

# ---------- UTF-8 CHO WINDOWS ----------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "4"

# ---------- FFMPEG PATH ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = BASE_DIR + os.pathsep + os.environ.get("PATH", "")

try:
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    print("✅ FFmpeg đã sẵn sàng")
except Exception:
    print("❌ FFmpeg KHÔNG hoạt động")
    sys.exit(1)


# ============================================================
#  MULTI-LANGUAGE CONFIG
# ============================================================
SUPPORTED_LANGS = ['vi', 'en', 'fr', 'ja', 'ko', 'zh', 'es']

LANG_LABEL = {
    'vi': 'Tiếng Việt',
    'en': 'English',
    'fr': 'Français',
    'ja': '日本語',
    'ko': '한국어',
    'zh': '中文',
    'es': 'Español',
}
LANG_FLAG = {
    'vi': '🇻🇳', 'en': '🇺🇸', 'fr': '🇫🇷',
    'ja': '🇯🇵', 'ko': '🇰🇷', 'zh': '🇨🇳', 'es': '🇪🇸',
}
TTS_LOCALE = {
    'vi': 'vi-VN', 'en': 'en-US', 'fr': 'fr-FR',
    'ja': 'ja-JP', 'ko': 'ko-KR', 'zh': 'zh-CN', 'es': 'es-ES',
}
# Marian dùng mã 3 ký tự cho tiếng Nhật
MARIAN_CODE = {
    'vi': 'vi', 'en': 'en', 'fr': 'fr',
    'ja': 'jap', 'ko': 'ko', 'zh': 'zh', 'es': 'es',
}


# ============================================================
#  LOAD MODELS
# ============================================================
print("⏳ Đang tải models…")

# --- 1. faster-whisper base (đa ngữ, tốt cho EN + detect) ---
from faster_whisper import WhisperModel
print("  → faster-whisper 'base'…")
fw_model = WhisperModel("base", device="cpu", compute_type="int8")
print("  ✅ faster-whisper sẵn sàng")

# --- 2. PhoWhisper base (chuyên tiếng Việt) ---
import torch
import librosa
import numpy as np
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    MarianMTModel,
    MarianTokenizer,
)

DEVICE = torch.device("cpu")
PHO_MODEL_NAME = "vinai/PhoWhisper-base"

print(f"  → {PHO_MODEL_NAME}…")
pho_processor = WhisperProcessor.from_pretrained(PHO_MODEL_NAME)
pho_model = WhisperForConditionalGeneration.from_pretrained(PHO_MODEL_NAME).to(DEVICE)
pho_model.eval()
print("  ✅ PhoWhisper sẵn sàng")

# --- 3. MarianMT: đăng ký repos, LAZY LOAD khi cần ---
_MT_REGISTRY = {}
for _lang in SUPPORTED_LANGS:
    if _lang == 'en':
        continue
    _m = MARIAN_CODE[_lang]
    _MT_REGISTRY[('en', _lang)] = f'Helsinki-NLP/opus-mt-en-{_m}'
    _MT_REGISTRY[(_lang, 'en')] = f'Helsinki-NLP/opus-mt-{_m}-en'

_MT_CACHE = OrderedDict()   # (src, tgt) -> (tokenizer, model)
_MAX_LOADED = 4             # giữ tối đa 4 cặp trong RAM (LRU)


def _load_mt(src, tgt):
    """Lazy-load MarianMT với LRU eviction."""
    key = (src, tgt)
    if key in _MT_CACHE:
        _MT_CACHE.move_to_end(key)
        return _MT_CACHE[key]
    repo = _MT_REGISTRY.get(key)
    if not repo:
        return None
    print(f"  → Lazy-load {repo}…")
    try:
        tok = MarianTokenizer.from_pretrained(repo)
        mdl = MarianMTModel.from_pretrained(repo).to(DEVICE)
        mdl.eval()
    except Exception as e:
        print(f"  ❌ Không load được {repo}: {e}")
        return None
    _MT_CACHE[key] = (tok, mdl)
    if len(_MT_CACHE) > _MAX_LOADED:
        evicted, _ = _MT_CACHE.popitem(last=False)
        print(f"  ♻️  Evicted {evicted} khỏi RAM")
    return tok, mdl


print(f"✅ Đã đăng ký {len(_MT_REGISTRY)} cặp dịch (lazy-load, tối đa {_MAX_LOADED} trong RAM)")
print("✅ Hoàn tất tải models\n")


# ============================================================
#  APP + CONSTANTS
# ============================================================
app = Flask(__name__)
CORS(app)
app.json.ensure_ascii = False   # trả Unicode, không escape


# Filler words cho mọi ngôn ngữ hỗ trợ
FILLERS = {
    'en': ['um', 'uh', 'er', 'ah', 'like', 'you know', 'so', 'well',
           'actually', 'basically'],
    'vi': ['ờ', 'à', 'ừ', 'ơ', 'thì', 'là', 'mà', 'kiểu', 'nói chung',
           'đại loại', 'kiểu như'],
    'fr': ['euh', 'ben', 'bah', 'genre', 'voilà', 'en fait', 'quoi', 'tu vois'],
    'ja': ['あの', 'えー', 'そうですね', 'なんか', 'まあ', 'その'],
    'ko': ['음', '어', '그', '뭐', '막', '이제', '약간'],
    'zh': ['嗯', '呃', '那个', '就是说', '然后', '就是'],
    'es': ['eh', 'este', 'pues', 'bueno', 'o sea', 'es que'],
}

# Tập ký tự có dấu tiếng Việt
VN_DIACRITICS = set(
    'ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩị'
    'óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ'
)
# Dấu VI-specific (không trùng tiếng Pháp)
VN_SPECIFIC = set('ăđơưắằẳẵặếềểễệốồổỗộớờởỡợứừửữự')

# Từ tiếng Anh phổ biến
EN_COMMON = {
    'the','is','are','am','was','were','a','an','and','or','but',
    'my','your','his','her','their','our','its','name','hello','hi',
    'today','tomorrow','yesterday','this','that','these','those',
    'it','he','she','they','we','you','i','me','him','us','them',
    'what','where','when','why','how','who','which','can','could',
    'will','would','shall','should','may','might','must','do','does',
    'did','have','has','had','be','been','being','in','on','at','to',
    'for','with','about','from','by','of','up','down','good','bad',
    'yes','no','not','very','so','just','now','then','here','there',
    'go','come','get','make','take','see','look','want','need','like',
    'love','know','think','say','tell','ask','work','play'
}

# Từ tiếng Việt KHÔNG DẤU (romanized) — dùng detect text
VN_ASCII_HINTS = {
    'khong','duoc','nguoi','nhung','cac','toi','chung','minh','gi',
    'nao','sao','dau','bao','nhieu','vay','nhe','nha','trong','nay',
    'khi','thi','nhu','rat','cung','dang','ve','tu','den','vao','neu',
    'sau','truoc','tren','duoi','giua','ngoai','viet','tieng','cam','on',
    'yeu','thich','muon','biet','hieu','lam','noi','nghe','doc','viet',
}


def count_vn_diacritics(text):
    return sum(1 for ch in text.lower() if ch in VN_DIACRITICS)


def en_word_hits(text):
    words = set(re.findall(r'\b[a-z]+\b', text.lower()))
    return len(words & EN_COMMON)


# ============================================================
#  LANGUAGE DETECTION (TEXT)
# ============================================================
try:
    from langdetect import detect_langs as _ld_detect
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False
    print("⚠️ langdetect chưa cài — dùng heuristic fallback "
          "(pip install langdetect để detect tốt hơn)")


def _detect_heuristic(text):
    """Fallback nếu không có langdetect hoặc langdetect fail."""
    low = text.lower()

    # VI-specific diacritics → chắc chắn VI
    if any(ch in VN_SPECIFIC for ch in low):
        return 'vi', 0.95

    # CJK
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        return 'ja', 0.85         # hiragana/katakana
    if re.search(r'[\uAC00-\uD7AF\u1100-\u11FF]', text):
        return 'ko', 0.85         # hangul
    if re.search(r'[\u4E00-\u9FFF]', text):
        return 'zh', 0.80         # CJK thuần

    # Tây Ban Nha
    if re.search(r'[ñ¿¡]', low):
        return 'es', 0.75

    # Pháp (dấu đặc trưng Pháp, không phải VI-specific)
    if re.search(r'[çœ]', low) or re.search(r'[éèêëàâùûôîï]', low):
        return 'fr', 0.60

    # Word-based EN vs VI-ascii
    words = set(re.findall(r'\b[a-z]+\b', low))
    en_s = len(words & EN_COMMON)
    vn_s = len(words & VN_ASCII_HINTS)
    if en_s > vn_s:
        return 'en', min(0.9, 0.5 + en_s * 0.05)
    if vn_s > 0:
        return 'vi', min(0.9, 0.5 + vn_s * 0.05)
    return 'vi', 0.3


def detect_language_text(text):
    """Trả (lang, confidence) ∈ SUPPORTED_LANGS × [0,1]."""
    if not text or not text.strip():
        return 'vi', 0.0

    # Ưu tiên: dấu VI-specific → chắc chắn VI
    if any(ch in VN_SPECIFIC for ch in text.lower()):
        return 'vi', 0.99

    # langdetect
    if _HAS_LANGDETECT:
        try:
            results = _ld_detect(text)
            if results:
                top = results[0]
                code = top.lang.split('-')[0]   # zh-cn → zh
                if code in SUPPORTED_LANGS:
                    return code, float(top.prob)
        except Exception:
            pass

    return _detect_heuristic(text)


# ============================================================
#  ASR — NHẬN DẠNG GIỌNG NÓI
# ============================================================
def transcribe_fw(wav_path):
    segments, info = fw_model.transcribe(
        wav_path,
        beam_size=1,
        best_of=1,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text, (info.language or 'en'), getattr(info, 'language_probability', 0.0)


def transcribe_pho(wav_path):
    audio, _ = librosa.load(wav_path, sr=16000)
    if len(audio) == 0:
        return ''
    inputs = pho_processor(
        audio, sampling_rate=16000, return_tensors="pt"
    ).input_features.to(DEVICE)

    with torch.no_grad():
        ids = pho_model.generate(
            inputs,
            max_length=448,
            num_beams=3,
            language="vi",
            task="transcribe",
        )
    return pho_processor.batch_decode(ids, skip_special_tokens=True)[0].strip()


def transcribe_with_whisper(wav_path):
    """
    Routing thông minh:
      - faster-whisper detect chắc chắn không phải VI → dùng luôn (EN/FR/JA/…)
      - VI hoặc không chắc → thử PhoWhisper (chuyên VI)
      - Fallback: faster-whisper
    """
    t0 = time.time()

    # Bước 1: faster-whisper
    fw_text, fw_lang, fw_prob = transcribe_fw(wav_path)
    fw_diac = count_vn_diacritics(fw_text)
    print(f"  ⏱️  faster-whisper {time.time() - t0:.2f}s | lang={fw_lang} "
          f"(p={fw_prob:.2f}) | diac={fw_diac} | text={fw_text!r}")

    mapped = fw_lang if fw_lang in SUPPORTED_LANGS else None

    # Bước 2: ngôn ngữ khác VI + detect chắc chắn → dùng luôn
    if mapped and mapped != 'vi' and fw_prob > 0.6:
        print(f"  ✅ → faster-whisper ({mapped})")
        return mapped, fw_text

    # Bước 3: VI hoặc không chắc → thử PhoWhisper
    if (not mapped) or fw_lang == 'vi' or fw_prob < 0.6 or fw_diac > 0:
        try:
            pho_text = transcribe_pho(wav_path)
            pho_diac = count_vn_diacritics(pho_text)
            print(f"  ⏱️ PhoWhisper | diac={pho_diac} | text={pho_text!r}")
            if pho_diac > 0 and len(pho_text) >= 2:
                print(f"  ✅ → PhoWhisper (Vietnamese)")
                return 'vi', pho_text
        except Exception as e:
            print(f"  ❌ PhoWhisper error: {e}")

    # Bước 4: fallback
    result_lang = mapped or 'en'
    print(f"  ✅ → fallback faster-whisper ({result_lang})")
    return result_lang, fw_text


# ============================================================
#  TRANSLATION
# ============================================================
def _translate_direct(text, src, tgt):
    """Dịch 1 chặng. Trả None nếu không có model."""
    pair = _load_mt(src, tgt)
    if not pair:
        return None
    tokenizer, model = pair
    try:
        inputs = tokenizer(
            [text], return_tensors="pt",
            padding=True, truncation=True, max_length=512,
        ).to(DEVICE)
        with torch.no_grad():
            generated = model.generate(
                **inputs, max_length=512,
                num_beams=4, early_stopping=True,
            )
        return tokenizer.decode(generated[0], skip_special_tokens=True).strip()
    except Exception as e:
        print(f"⚠️ MT error {src}→{tgt}: {e}")
        return None


def translate_text(text, source_lang, target_lang):
    """
    Dịch text. Chiến lược:
      - Có cặp direct (VI↔EN, EN↔FR, …) → dịch thẳng.
      - Không có → pivot qua tiếng Anh (VI→EN→FR, JA→EN→KO…).
    """
    if not text or not text.strip():
        return ''
    if source_lang == target_lang:
        return text

    # Direct pair
    if (source_lang, target_lang) in _MT_REGISTRY:
        out = _translate_direct(text, source_lang, target_lang)
        if out is not None:
            return out

    # Pivot qua tiếng Anh
    if source_lang != 'en' and target_lang != 'en':
        mid = _translate_direct(text, source_lang, 'en')
        if mid is None:
            return f'(Không dịch được {source_lang}→en)'
        out = _translate_direct(mid, 'en', target_lang)
        if out is None:
            return f'(Không dịch được en→{target_lang})'
        return out

    return f'(Không hỗ trợ {source_lang}→{target_lang})'


# ============================================================
#  SPEECH ANALYTICS
# ============================================================
def count_fillers(text, lang='en'):
    fillers = FILLERS.get(lang, [])
    if not fillers:
        return 0
    tl = text.lower()
    # CJK: không có word boundary → đếm substring
    if lang in ('ja', 'ko', 'zh'):
        return sum(tl.count(f) for f in fillers)
    words = re.findall(r'\b\w+\b', tl)
    count = 0
    for f in fillers:
        count += tl.count(f) if ' ' in f else words.count(f)
    return count


def analyze_transcript(transcript, duration_sec, lang='en'):
    if not transcript or not transcript.strip():
        return {
            'text': '', 'transcript': '(No speech detected)', 'lang': lang,
            'metrics': {'wpm': 0, 'word_count': 0, 'unique_words': 0,
                        'filler_count': 0, 'sentence_count': 0,
                        'avg_sentence_len': 0,
                        'duration_sec': round(duration_sec, 1)},
            'feedback': [{'type': 'bad',
                          'text': 'Không nhận dạng được giọng nói.'}]
        }

    words = re.findall(r'\b\w+\b', transcript)
    word_count = len(words)
    unique_words = len(set(w.lower() for w in words))
    sentences = [s.strip() for s in re.split(r'[.!?。！？]+', transcript) if s.strip()]
    sentence_count = len(sentences)
    avg_sentence_len = word_count / sentence_count if sentence_count else 0
    filler_count = count_fillers(transcript, lang)
    wpm = (word_count / duration_sec) * 60 if duration_sec > 0 else 0

    metrics = {
        'wpm': round(wpm, 1),
        'word_count': word_count,
        'unique_words': unique_words,
        'filler_count': filler_count,
        'sentence_count': sentence_count,
        'avg_sentence_len': round(avg_sentence_len, 1),
        'duration_sec': round(duration_sec, 1),
    }

    feedback = []
    if wpm < 80:
        feedback.append({'type': 'warn',
                         'text': f'Tốc độ nói chậm ({wpm:.0f} WPM). Nên đạt 120–160 WPM.'})
    elif wpm > 200:
        feedback.append({'type': 'warn',
                         'text': f'Tốc độ nói nhanh ({wpm:.0f} WPM). Hãy nói chậm lại.'})
    else:
        feedback.append({'type': 'good',
                         'text': f'Tốc độ nói tốt ({wpm:.0f} WPM).'})

    if filler_count > 5:
        feedback.append({'type': 'warn',
                         'text': f'Dùng {filler_count} từ đệm. Hãy giảm bớt.'})
    else:
        feedback.append({'type': 'good',
                         'text': f'Ít từ đệm ({filler_count}) – tốt!'})

    if unique_words < 15:
        feedback.append({'type': 'warn',
                         'text': f'Vốn từ hạn chế ({unique_words} từ khác nhau).'})
    else:
        feedback.append({'type': 'good',
                         'text': f'Vốn từ phong phú ({unique_words} từ khác nhau).'})

    if sentence_count < 3:
        feedback.append({'type': 'info',
                         'text': 'Nên chia thành nhiều câu để mạch lạc hơn.'})
    else:
        feedback.append({'type': 'good',
                         'text': f'Cấu trúc tốt – {sentence_count} câu.'})

    return {
        'text': transcript,
        'transcript': transcript,
        'lang': lang,
        'metrics': metrics,
        'feedback': feedback,
    }


# ============================================================
#  ROUTES
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')


def _resolve_target(source_lang, target_lang):
    """Chọn target hợp lệ, tránh trùng source."""
    if target_lang not in SUPPORTED_LANGS or target_lang == source_lang:
        return 'vi' if source_lang != 'vi' else 'en'
    return target_lang


def _process_audio(audio_file, target_lang=None):
    """Pipeline chung cho /api/transcribe và /analyze."""
    debug_dir = "debug"
    os.makedirs(debug_dir, exist_ok=True)
    webm_path = os.path.join(debug_dir, "uploaded.webm")
    wav_path = os.path.join(debug_dir, "converted.wav")

    audio_file.save(webm_path)
    print(f"💾 WebM saved: {os.path.getsize(webm_path)} bytes")

    try:
        audio = AudioSegment.from_file(webm_path, format="webm")
        print(f"✅ Audio: {len(audio) / 1000:.2f}s")
        audio.export(wav_path, format="wav")
    except Exception as e:
        return {'error': f'Conversion failed: {e}'}, 400

    try:
        detected_lang, transcript = transcribe_with_whisper(wav_path)
    except Exception as e:
        print(f"❌ ASR error: {e}")
        return {'error': f'ASR error: {e}'}, 500

    print(f"📝 [{detected_lang}] {transcript}")

    target = _resolve_target(detected_lang, (target_lang or '').lower())
    translation = translate_text(transcript, detected_lang, target)
    print(f"🌐 [{target}] {translation}")

    duration_sec = len(audio) / 1000.0
    result = analyze_transcript(transcript, duration_sec, lang=detected_lang)
    result.update({
        'text': transcript,
        'lang': detected_lang,
        'langLabel': LANG_LABEL.get(detected_lang, detected_lang),
        'langFlag': LANG_FLAG.get(detected_lang, ''),
        'translation': translation,
        'targetLang': target,
        'targetLangLabel': LANG_LABEL.get(target, target),
        'targetLangFlag': LANG_FLAG.get(target, ''),
    })
    return result, 200


@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    target = (request.form.get('target') or '').lower()
    result, status = _process_audio(audio_file, target)
    return jsonify(result), status


@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    target = (request.form.get('target') or '').lower()
    result, status = _process_audio(audio_file, target)
    return jsonify(result), status


# ============================================================
#  API TEXT TRANSLATION
# ============================================================
@app.route('/api/translate', methods=['POST'])
def api_translate():
    """
    Body JSON:
      { "text": "...", "source": "auto"|lang, "target": lang }
    """
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    source = (data.get('source') or 'auto').lower()
    target = (data.get('target') or '').lower()

    if not text:
        return jsonify({'error': 'No text provided'}), 400
    if len(text) > 5000:
        return jsonify({'error': 'Text too long (max 5000 chars)'}), 400

    detected = False
    confidence = 1.0
    if source not in SUPPORTED_LANGS:
        source, confidence = detect_language_text(text)
        detected = True

    target = _resolve_target(source, target)
    translation = translate_text(text, source, target)

    print(f"🔁 [translate] {source}→{target} | "
          f"{text[:60]!r} → {translation[:60]!r}")

    return jsonify({
        'original': text,
        'translation': translation,
        'sourceLang': source,
        'sourceLangLabel': LANG_LABEL.get(source, source),
        'sourceLangFlag': LANG_FLAG.get(source, ''),
        'targetLang': target,
        'targetLangLabel': LANG_LABEL.get(target, target),
        'targetLangFlag': LANG_FLAG.get(target, ''),
        'detected': detected,
        'confidence': round(confidence, 2),
    }), 200


# ============================================================
#  API TEXT ANALYSIS
# ============================================================
@app.route('/api/analyze-text', methods=['POST'])
def api_analyze_text():
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    if len(text) > 5000:
        return jsonify({'error': 'Text too long (max 5000 chars)'}), 400

    source = (data.get('source') or 'auto').lower()
    if source not in SUPPORTED_LANGS:
        source, _ = detect_language_text(text)

    try:
        duration = float(data.get('duration') or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        wc = len(re.findall(r'\b\w+\b', text))
        duration = max(1.0, wc / 150.0 * 60.0)

    result = analyze_transcript(text, duration, lang=source)
    result['langLabel'] = LANG_LABEL.get(source, source)
    result['langFlag'] = LANG_FLAG.get(source, '')
    return jsonify(result), 200


# ============================================================
#  MAIN
# ============================================================
if __name__ == '__main__':
    print("🚀 TMG301 ready — http://localhost:5000")
    print("   • POST /api/transcribe  (audio → text + dịch)")
    print("   • POST /api/translate   (text  → dịch)")
    print("   • POST /api/analyze-text (text → metrics)")
    print(f"   • Ngôn ngữ hỗ trợ: {', '.join(SUPPORTED_LANGS)}")
    app.run(debug=False, host='0.0.0.0', port=5000)
# 🎙️ TMG301 — Speech & Text Translation App

> **Ứng dụng dịch giọng nói & văn bản Việt ↔ Anh, chạy hoàn toàn offline trên CPU.**
>
> Phân tích chất lượng bài nói với 6 chỉ số · Không cần GPU · Không cần Internet (sau lần tải models đầu tiên)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-brightgreen.svg)]()

---

## ✨ Tính năng chính

| | Tính năng | Mô tả |
|---|-----------|-------|
| 🎙️ | **Dịch giọng nói** | Thu âm → ASR → dịch → phân tích bài nói |
| ⌨️ | **Dịch văn bản** | Gõ/dán → auto-detect ngôn ngữ → dịch hai chiều |
| 🌐 | **Song ngữ Việt–Anh** | EN→VI và VI→EN, tự động nhận diện |
| 🧠 | **ASR Routing thông minh** | faster-whisper (EN) + PhoWhisper (VI) tự chọn |
| 📊 | **6 chỉ số phân tích** | WPM · Từ đệm · Vốn từ · Câu · Độ dài TB · Thời lượng |
| 💬 | **Feedback màu sắc** | Gợi ý cải thiện (good/warn/info/bad) |
| 🔊 | **Text-to-Speech** | Đọc bản dịch bằng Web Speech API |
| 📋 | **Copy & lịch sử** | Copy kết quả, click history để khôi phục |
| 💻 | **CPU-first** | int8 quantization, chạy tốt trên máy không GPU |
| 🔒 | **100% offline** | Không gửi dữ liệu ra ngoài sau khi tải models |

---

## 🚀 Cài đặt nhanh (5 phút)

### Yêu cầu

- Python **3.10+**
- FFmpeg (bundled hoặc cài hệ thống)
- RAM ≥ 8GB, disk ≥ 2GB trống

### Các bước

```bash
# 1. Clone hoặc giải nén dự án
cd TMG301-Speech-Analysis

# 2. Tạo virtual environment
python -m venv venv311

# Windows
venv311\Scripts\activate
# Linux/macOS
# source venv311/bin/activate

# 3. Cài dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Chạy (lần đầu tự tải models ~1.1GB, cần Internet)
python app.py
```

Mở trình duyệt: **http://localhost:5000/**

---

## 📸 Screenshots

### Tab Voice — Dịch giọng nói
```
┌─────────────────────────────────────────────────┐
│  🎙️ Giọng nói    │    ⌨️ Văn bản              │
├─────────────────────────────────────────────────┤
│              ┌─────────┐                        │
│              │   🎤    │  ← Bấm để ghi âm       │
│              └─────────┘                        │
│                                                 │
│  📝 Bạn nói                                     │
│  Hello, my name is John                         │
│                                                 │
│  🌐 Bản dịch                                    │
│  Xin chào, tên tôi là John                      │
│                                                 │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┐   │
│  │ WPM  │ Từ   │ Riêng│ Đệm  │ Câu  │ TB   │   │
│  │ 145  │  5   │  5   │  0   │  1   │ 5.0  │   │
│  └──────┴──────┴──────┴──────┴──────┴──────┘   │
│                                                 │
│  💬 ✓ Tốc độ nói tốt (145 WPM)                  │
│     ✓ Ít từ đệm (0) – tốt!                      │
└─────────────────────────────────────────────────┘
```

### Tab Text — Dịch văn bản
```
┌─────────────────────────────────────────────────┐
│  🌐 Tự động phát hiện                    ⇄      │
│  ┌───────────────────────────────────────────┐  │
│  │ Hello, how are you today?                 │  │
│  │                                    0/5000 │  │
│  └───────────────────────────────────────────┘  │
│  [ 🌐 Dịch ngay ]         [ 🗑️ Xoá ]            │
│                                                 │
│  📝 Bản gốc              English 🇺🇸 · auto    │
│  Hello, how are you today?                      │
│                                                 │
│  🌐 Bản dịch             Tiếng Việt 🇻🇳        │
│  Xin chào, hôm nay anh thế nào?                 │
│  [ 📋 Copy ] [ 🔊 Nghe ]                        │
└─────────────────────────────────────────────────┘
```

---

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────────────────────┐
│  CLIENT (Browser)                                       │
│  ├── Tab Voice  →  MediaRecorder → POST /api/transcribe │
│  └── Tab Text   →  fetch JSON    → POST /api/translate  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  FLASK SERVER (app.py)                                  │
│                                                         │
│  ┌──────────────────┐        ┌──────────────────────┐   │
│  │  Audio Pipeline  │        │   Text Pipeline      │   │
│  │  pydub + FFmpeg  │        │   detect_language    │   │
│  │  → WAV 16kHz     │        │   _text()            │   │
│  └────────┬─────────┘        └──────────┬───────────┘   │
│           ▼                             │               │
│  ┌──────────────────┐                   │               │
│  │  ASR Routing     │                   │               │
│  │  ├─ faster-      │                   │               │
│  │  │  whisper (EN) │                   │               │
│  │  └─ PhoWhisper   │                   │               │
│  │     (VI)         │                   │               │
│  └────────┬─────────┘                   │               │
│           │                             │               │
│           └──────────┬──────────────────┘               │
│                      ▼                                  │
│         ┌─────────────────────────┐                     │
│         │  MarianMT Translation   │                     │
│         │  (en↔vi bidirectional)  │                     │
│         └────────────┬────────────┘                     │
│                      ▼                                  │
│         ┌─────────────────────────┐                     │
│         │  Speech Analytics       │                     │
│         │  (6 metrics + feedback) │                     │
│         └────────────┬────────────┘                     │
│                      ▼                                  │
│                 JSON Response                           │
└─────────────────────────────────────────────────────────┘
```

---

## 🧠 Models sử dụng

| Model | Vai trò | Kích thước | WER/BLEU |
|-------|---------|------------|----------|
| **Systran/faster-whisper-base** | ASR tiếng Anh | 145MB | WER 8.2% (EN) |
| **vinai/PhoWhisper-base** | ASR tiếng Việt | 290MB | WER 12.8% (VI) |
| **Helsinki-NLP/opus-mt-en-vi** | Dịch Anh→Việt | 300MB | BLEU 32.4 |
| **Helsinki-NLP/opus-mt-vi-en** | Dịch Việt→Anh | 300MB | BLEU 28.7 |

**Tổng dung lượng:** ~1.1GB (cache trong `~/.cache/huggingface/hub/`)

Chi tiết về ưu/nhược điểm từng model: xem [`DEMO.md#11`](DEMO.md#11-ưu--nhược-điểm-từng-model).

---

## 📁 Cấu trúc dự án

```
TMG301-Speech-Analysis/
├── app.py                  # ⚙️ Flask server chính
├── requirements.txt        # 📦 Dependencies
├── README.md               # 📖 File này
├── DEMO.md                 # 📘 Báo cáo + hướng dẫn demo đầy đủ
├── CHANGELOG.md            # 📝 Lịch sử phiên bản
├── LICENSE                 # ⚖️ Bản quyền
│
├── templates/
│   └── index.html          # 🎨 Web UI (2 tab)
│
├── ffmpeg/                 # 🎬 FFmpeg bundled
│   ├── ffmpeg.exe
│   └── ffprobe.exe
│
└── debug/                  # 🔧 File tạm (tự tạo khi chạy)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/` | Web UI |
| `POST` | `/api/transcribe` | Audio → text + dịch + metrics |
| `POST` | `/api/translate` | Text → dịch (auto-detect) |
| `POST` | `/api/analyze-text` | Text → metrics + feedback |
| `POST` | `/analyze` | Alias cũ của `/api/transcribe` |

### Ví dụ gọi API

**Dịch văn bản:**

```bash
curl -X POST http://localhost:5000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, how are you today?","source":"auto"}'
```

**Response:**

```json
{
  "original": "Hello, how are you today?",
  "translation": "Xin chào, hôm nay anh thế nào?",
  "sourceLang": "en",
  "targetLang": "vi",
  "detected": true,
  "confidence": 0.75
}
```

---

## ⚡ Performance (Intel i5-11400, 16GB RAM, CPU-only)

| Độ dài audio | EN (early-exit) | VI (full pipeline) |
|--------------|-----------------|---------------------|
| 3s | 2.1s | 5.3s |
| 10s | 4.2s | 8.7s |
| 30s | 9.5s | 18.2s |

| Độ dài text | Thời gian dịch |
|-------------|----------------|
| 10 từ | ~0.8s |
| 50 từ | ~1.0s |
| 200 từ | ~1.5s |

---

## 🐛 Xử lý sự cố nhanh

| Lỗi | Fix |
|-----|-----|
| `FFmpeg KHÔNG hoạt động` | Kiểm tra `ffmpeg\ffmpeg.exe` tồn tại, hoặc cài `choco install ffmpeg` |
| Bấm Dịch báo `404` | `app.py` chưa có route `/api/translate` → paste bản mới |
| Response có `\u1ebf` | Thêm `app.json.ensure_ascii = False` vào `app.py` |
| Không truy cập được micro | Dùng `localhost` (không dùng IP LAN), cấp quyền mic trong trình duyệt |
| Models load >30s | Lần đầu chậm do download ~1.1GB — sau đó load từ cache |

Chi tiết đầy đủ 9 lỗi + cách fix: xem [`DEMO.md#15`](DEMO.md#15-xử-lý-sự-cố).

---

## 📚 Tài liệu

- 📘 **[DEMO.md](DEMO.md)** — Báo cáo đồ án đầy đủ + hướng dẫn demo chi tiết
- 📝 **[CHANGELOG.md](CHANGELOG.md)** — Lịch sử phiên bản
- ⚖️ **[LICENSE](LICENSE)** — Điều khoản bản quyền

---

## 🤝 Đóng góp

Dự án này là **đồ án cá nhân** — không nhận pull request từ bên ngoài.  
Mọi ý kiến đóng góp, báo lỗi vui lòng liên hệ qua Zalo.

---

## ⚖️ Bản quyền

**© 2026 HUYTKING TECH DRONE · SHIRMTRY — All rights reserved.**

Xem file [LICENSE](LICENSE) để biết chi tiết.

---

## 📞 Liên hệ

| Kênh | Thông tin |
|------|-----------|
| **Zalo** | 0396 241 674 |
| **GitHub** | [github.com/shirmtry](https://github.com/shirmtry) |
| **Tác giả** | HUYTKING |

---

<div align="center">

**Made with ❤️ in Vietnam**

**HUYTKING TECH DRONE · SHIRMTRY**
# 📝 CHANGELOG

Tất cả thay đổi đáng chú ý của dự án **TMG301 — Speech & Text Translation App** được ghi lại trong file này.

Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/),  
phiên bản tuân theo [Semantic Versioning](https://semver.org/lang/vi/).

---

## [Unreleased] — Sắp ra mắt

### Planned (đã lên kế hoạch)
- [ ] Hỗ trợ real-time streaming qua WebSocket
- [ ] Cache kết quả ASR/MT cho input trùng lặp
- [ ] PWA (Progressive Web App) — cài được như native app
- [ ] Export ONNX Runtime để tăng tốc inference
- [ ] Hỗ trợ thêm ngôn ngữ thứ 3 (Trung, Nhật, Hàn)
- [ ] Fine-tune MarianMT trên domain chuyên biệt (y tế, giáo dục)

---

## [1.1.0] — 2026-10-25

### 🎉 Added (Thêm mới)

#### Backend
- **API `POST /api/translate`** — Dịch văn bản trực tiếp, hỗ trợ auto-detect ngôn ngữ.
  - Input: `{text, source?}` với `source ∈ {auto, en, vi}`
  - Output: `{original, translation, sourceLang, targetLang, detected, confidence}`
- **API `POST /api/analyze-text`** — Phân tích bài nói từ văn bản (không cần audio).
  - Ước lượng duration theo 150 WPM nếu không truyền.
- **Hàm `detect_language_text()`** — Nhận diện ngôn ngữ văn bản dựa trên:
  - Diacritic count (ký tự có dấu tiếng Việt)
  - EN word hits (từ điển 100+ từ phổ biến)
  - VN ASCII hints (từ điển 40+ từ romanized)
- **`VN_ASCII_HINTS`** — Tập từ tiếng Việt không dấu để cải thiện detect.

#### Frontend
- **Tab "⌨️ Văn bản"** — Giao diện riêng cho chế độ nhập văn bản.
  - Textarea với đếm ký tự (max 5000)
  - Dropdown chọn chiều dịch: Tự động / EN→VI / VI→EN
  - Nút **⇄ Hoán đổi** — Đảo chiều + đảo text + tự dịch ngược
  - Nút **🌐 Dịch ngay** + phím tắt **Ctrl+Enter**
  - Nút **🗑️ Xoá** reset form
  - **📋 Copy** kết quả gốc + bản dịch
  - **🔊 Nghe** (Web Speech API)
- **Tab switcher** — Chuyển đổi giữa Voice và Text.
- **Footer copyright** — HUYTKING TECH DRONE · SHIRMTRY.
- **History click-to-restore** — Click lịch sử tự fill vào tab Văn bản.

### 🔧 Changed (Thay đổi)
- **Tiêu đề dự án** — Đổi từ "Machine Translation with Limited Bilingual Data" → **"Speech & Text Translation App"** cho đúng bản chất.
- **Startup log** — Hiển thị rõ 3 endpoints mới khi khởi động server.
- **`app.py` docstring** — Bổ sung mô tả chi tiết cho `api_translate()`.

### 🐛 Fixed (Sửa lỗi)
- **Unicode escape trong JSON response** — Thêm tùy chọn `app.json.ensure_ascii = False` để trả tiếng Việt trực tiếp (không bị `\u1ebf`).
- **404 khi mở `/translate`** — Ghi rõ trong README/DEMO: `/translate` là API endpoint (POST), không phải trang web. Trang web là `/`.
- **Phát hiện ngôn ngữ cho văn bản ngắn** — Cải thiện score weighting (VI × 1.5 vs EN × 1.0).

### 📚 Documentation
- **`README.md`** — Viết mới hoàn chỉnh: badges, cài đặt 5 phút, screenshots, kiến trúc, API, troubleshooting.
- **`DEMO.md`** — Báo cáo đồ án đầy đủ (~1500 dòng):
  - Phần A: Báo cáo 7 chương học thuật
  - Phần B: Hướng dẫn demo 11 mục thực hành
  - Phụ lục: Cấu trúc, bảng models, biến môi trường
- **`CHANGELOG.md`** — File này (lần đầu tạo).
- **`LICENSE`** — Bản quyền proprietary đầy đủ 11 mục.

### ⚡ Performance
- Không thay đổi so với v1.0.0 (vẫn giữ int8 quantization + early-exit).

### 🔒 Security
- Thêm validate `len(text) > 5000` → trả lỗi 400 (tránh DoS).
- Thêm validate `source not in ('en', 'vi', 'auto')` → fallback auto-detect.

---

## [1.0.0] — 2026-10-20

### 🎉 Initial Release (Phiên bản đầu tiên)

#### Core Features
- **ASR song ngữ Việt–Anh** với routing algorithm 3 bước:
  - faster-whisper base (int8) cho tiếng Anh
  - PhoWhisper base (fp32) cho tiếng Việt
  - Early-exit khi chắc chắn tiếng Anh → tiết kiệm 60% thời gian
- **Dịch máy 2 chiều** với MarianMT:
  - `Helsinki-NLP/opus-mt-en-vi`
  - `Helsinki-NLP/opus-mt-vi-en`
  - Beam search: `num_beams=4`, `early_stopping=True`
- **Speech Analytics** với 6 chỉ số:
  - WPM (Words Per Minute)
  - Filler count (từ đệm theo ngôn ngữ)
  - Unique words (vocabulary richness)
  - Sentence count (tách theo regex đa ngôn ngữ)
  - Average sentence length
  - Duration
- **Feedback phân loại 4 mức:**
  - `good` (xanh lá) — Đạt yêu cầu
  - `warn` (vàng) — Cần cải thiện
  - `info` (xanh dương) — Gợi ý
  - `bad` (đỏ) — Lỗi nghiêm trọng

#### Backend
- Flask 3.0 + Flask-CORS 4.0
- API `POST /api/transcribe` — Nhận audio, trả JSON đầy đủ
- API `POST /analyze` — Alias của `/api/transcribe`
- Audio preprocessing: pydub + FFmpeg (WebM → WAV 16kHz)
- Health check FFmpeg khi khởi động (`ffmpeg -version`)

#### Frontend
- **Tab "🎙️ Giọng nói"** — Ghi âm + hiển thị kết quả
  - MediaRecorder API (WebM/Opus)
  - Silence detection tự động ngắt sau 1.5s im lặng
  - Metrics grid 6 ô + feedback list màu sắc
  - **🔊 Nghe lại** transcript gốc + **🔊 Nghe** bản dịch
- **History** — Lưu 15 kết quả gần nhất
- **Responsive design** — Hoạt động tốt trên mobile, tablet, desktop
- **Dark-ish theme** — Gradient backgrounds, glassmorphism cards

#### Environment
- Chạy hoàn toàn trên CPU
- `int8` quantization cho faster-whisper
- `OMP_NUM_THREADS=4` tối ưu BLAS
- UTF-8 fix cho Windows (`sys.stdout.reconfigure`)
- FFmpeg bundled trong `BASE_DIR`

#### Documentation
- Header comment với bản quyền HUYTKING
- Docstrings cho các hàm chính
- Log chi tiết khi transcribe (thời gian, lang, diacritic count)

### ⚠️ Known Issues (Đã biết)
- Chưa hỗ trợ real-time streaming.
- Tiếng Việt không dấu detect đôi khi nhầm thành tiếng Anh.
- Audio dài >30s xử lý chậm (PhoWhisper fp32).
- Chưa có fine-tune cho domain chuyên biệt.

---

## Quy ước đặt phiên bản

Dự án tuân theo [Semantic Versioning](https://semver.org/lang/vi/):

```
MAJOR.MINOR.PATCH
```

| Loại | Khi nào tăng |
|------|--------------|
| **MAJOR** | Thay đổi API không tương thích ngược |
| **MINOR** | Thêm tính năng mới (tương thích ngược) |
| **PATCH** | Sửa lỗi (tương thích ngược) |

### Loại thay đổi

| Icon | Loại | Ý nghĩa |
|------|------|---------|
| 🎉 | Added | Tính năng mới |
| 🔧 | Changed | Thay đổi hành vi hiện có |
| 🗑️ | Deprecated | Sắp bị xoá |
| ❌ | Removed | Đã xoá |
| 🐛 | Fixed | Sửa lỗi |
| 🔒 | Security | Bảo mật |
| ⚡ | Performance | Tối ưu hiệu năng |
| 📚 | Documentation | Tài liệu |

---

## Roadmap

### v1.2.0 (Q1/2027)
- [ ] Real-time streaming (WebSocket)
- [ ] Cache layer (Redis hoặc disk)
- [ ] PWA (Progressive Web App)

### v1.3.0 (Q2/2027)
- [ ] Thêm tiếng Trung (zh)
- [ ] Thêm tiếng Nhật (ja)
- [ ] Export ONNX Runtime

### v2.0.0 (Q3/2027)
- [ ] Fine-tune MarianMT domain-specific
- [ ] Mobile app (React Native / Flutter)
- [ ] Multi-user với authentication

---

## Contributors

| Tên | Vai trò | Liên hệ |
|-----|---------|---------|
| **HUYTKING** | Tác giả chính, full-stack | Zalo 0396 241 674 |
| **SHIRMTRY** | Brand, hỗ trợ kỹ thuật | GitHub |

---

## Liên kết

- 📖 [README.md](README.md) — Hướng dẫn cài đặt & sử dụng
- 📘 [DEMO.md](DEMO.md) — Báo cáo đồ án đầy đủ
- ⚖️ [LICENSE](LICENSE) — Bản quyền

---

**© 2026 HUYTKING TECH DRONE · SHIRMTRY**  
*Mọi hành vi sao chép, chỉnh sửa, phân phối mà không có sự đồng ý của tác giả đều bị nghiêm cấm.*
```

---

## ✅ ĐÃ HOÀN THÀNH — Tổng kết 4 file tài liệu

Bạn giờ có **bộ 4 file documentation hoàn chỉnh**:

| File | Dòng | Vai trò | Khi nào dùng |
|------|------|---------|--------------|
| **`README.md`** | ~250 | Trang chủ GitHub | Người mới clone về đọc đầu tiên |
| **`DEMO.md`** | ~1500 | Báo cáo + hướng dẫn demo | Nộp đồ án, thuyết trình, troubleshooting |
| **`LICENSE`** | ~180 | Bản quyền pháp lý | Bảo vệ tác quyền, xử lý tranh chấp |
| **`CHANGELOG.md`** | ~220 | Lịch sử phiên bản | Track thay đổi, roadmap |

### 🎯 Checklist hoàn thiện dự án

- [x] `app.py` — Backend Flask với `/api/translate`
- [x] `templates/index.html` — Web UI 2 tab
- [x] `requirements.txt` — Dependencies
- [x] `README.md` — Trang chủ ngắn gọn ✅
- [x] `DEMO.md` — Báo cáo đầy đủ ✅
- [x] `LICENSE` — Bản quyền ✅
- [x] `CHANGELOG.md` — Lịch sử ✅
- [ ] `.gitignore` — Chưa có (nên thêm)
- [ ] `requirements-lock.txt` — Chưa có (nên có cho reproducibility)
- [ ] `screenshots/` — Chưa có ảnh chụp
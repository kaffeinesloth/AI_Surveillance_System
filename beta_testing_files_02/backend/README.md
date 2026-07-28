# backend/ — FastAPI Service

## Kiến trúc

- **FastAPI** + **SQLite** (qua SQLAlchemy) — lưu người đã đăng ký (`Person`), camera (`Camera`), cảnh báo (`Alert`)
- **insightface (buffalo_l)** — model load đúng **1 lần** lúc server khởi động (`app/main.py`, hàm `lifespan`), không load lại mỗi request
- **Không dùng Firebase** — đã quyết định bỏ khi chuyển sang Flutter (tránh phụ thuộc dịch vụ ngoài, không cần `google-services.json`). Kênh đẩy cảnh báo real-time dự kiến thay bằng **WebSocket tự host** — **CHƯA implement**, xem "Việc còn thiếu" bên dưới.

## Cấu trúc

```
backend/
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                    - entrypoint, load model + gallery luc startup
│   ├── config.py                  - duong dan, nguong (det_thresh, pad_ratio, match_threshold)
│   ├── database.py                - SQLAlchemy engine/session (SQLite)
│   ├── models/                    - ORM: Person, Camera, Alert
│   ├── schemas/                   - Pydantic: PersonOut, AlertOut
│   ├── routers/
│   │   ├── enrollment.py          - POST/GET/DELETE /enroll/   (DA XONG, hoat dong day du)
│   │   └── alerts.py              - GET /alerts/, GET /alerts/{id}  (chi DOC duoc, xem ben duoi)
│   └── services/
│       └── face_recognition_service.py  - wrap insightface, gallery trong RAM
└── storage/
    ├── security.db                - file SQLite (tu tao khi chay lan dau)
    ├── embeddings/<person_id>.npy - vector embedding tung nguoi da dang ky
    └── snapshots/                 - anh chup khi co alert (CHUA dung toi - xem ben duoi)
```

## Setup & chạy

```
cd backend
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000/docs` (Swagger UI) để test trực tiếp trên trình duyệt — hỗ trợ test `POST /enroll/` (upload ảnh) ngay trên giao diện web, không cần viết code test riêng.

## Endpoint hiện có

| Method | Path | Mô tả |
|---|---|---|
| POST | `/enroll/` | Đăng ký người mới — nhận `name`, `role`, nhiều ảnh (`photos`), tính embedding trung bình, lưu SQLite + `.npy`, thêm vào gallery RAM ngay lập tức (không cần restart server) |
| GET | `/enroll/` | Liệt kê người đã đăng ký |
| DELETE | `/enroll/{person_id}` | Xóa người khỏi hệ thống (DB + file `.npy` + gallery RAM) |
| GET | `/alerts/` | Liệt kê cảnh báo, mới nhất trước |
| GET | `/alerts/{alert_id}` | Chi tiết 1 cảnh báo |
| GET | `/health` | Kiểm tra server sống + số người hiện có trong gallery RAM (`gallery_size`) |

## Cách hoạt động đáng lưu ý

- **Không train lại model khi có người mới đăng ký** — `enroll_person()` chỉ chạy 1 lần forward pass qua model ArcFace có sẵn để lấy vector 512 chiều, không có backpropagation/epoch nào cả.
- **SQLite (+ file `.npy`) là "nguồn sự thật"; gallery trong RAM chỉ là bản sao để tra cứu nhanh** — được nạp lại từ SQLite mỗi khi server khởi động (`load_gallery_from_db()` trong `main.py`). Nếu sửa DB bằng tay (SQL trực tiếp), phải restart server để đồng bộ lại RAM.
- **`config.py` có sẵn `FACE_MATCH_THRESHOLD = 0.35`, nhưng hiện CHƯA có endpoint nào dùng đến** — vì backend chưa có tính năng "nhận diện" thật (chỉ mới "đăng ký"). Giá trị này để sẵn cho `pipeline_runner.py` khi được xây (xem TODO bên dưới).

## Việc còn thiếu (TODO — cố ý chưa làm, cần quyết định trước khi làm tiếp)

- **`pipeline_runner.py` chưa tồn tại** — chưa có endpoint nhận video/webcam real-time, chạy cascade (YOLOv8 + insightface, port từ `ai/notebooks/02...`), rồi tự tạo record `Alert`. Hiện `/alerts/` chỉ **đọc** được dữ liệu — chưa có gì **ghi** vào bảng `Alert` cả (bảng đang rỗng nếu chưa tự insert tay).
- **Chưa có WebSocket đẩy cảnh báo cho Flutter app** — thay thế cho Firebase đã bỏ, vẫn là TODO.
- **Chưa có CRUD cho `Camera`** — bảng đã có trong DB nhưng chưa có router riêng để thêm/sửa/xóa camera.
- Logic cascade (YOLOv8 + ByteTrack + behavior rules) hiện chỉ tồn tại trong notebook, chưa tách thành module Python dùng chung giữa `ai/` và `backend/` — khi xây `pipeline_runner.py` sẽ cần quyết định cách tổ chức lại phần này.

<<<<<<< HEAD
# Face Security System

Hệ thống giám sát an ninh và nhận dạng khuôn mặt theo mô hình **AI + Backend + Mobile App**.

Dự án này được xây theo hướng thực dụng:
- **Face Detection**: phát hiện khuôn mặt/người trong ảnh hoặc video.
- **Face Recognition**: trích embedding và so khớp với gallery đã đăng ký.
- **Tracking**: theo dõi đối tượng qua video thời gian thực.
- **Behavior Engine**: phát hiện các tình huống bất thường theo luật (rule-based).
- **Backend API**: cung cấp REST/WebSocket để nhận sự kiện và trả dữ liệu cảnh báo.
- **Mobile App**: hiển thị danh sách cảnh báo và thông tin giám sát.

## 1. Tổng quan hệ thống

Pipeline chính:

```mermaid
flowchart LR
    A[Camera / Video / Image] --> B[Tiền xử lý ảnh & video]
    B --> C[Face Detection]
    C --> D[Face Recognition]
    D --> E[Tracking]
    E --> F[Behavior Engine]
    F --> G[Cảnh báo / Log / Snapshot]
    G --> H[Backend API]
    H --> I[Mobile App]
```

Tài liệu thiết kế của đồ án xác định đề tài là: **xây dựng hệ thống nhận dạng khuôn mặt, giám sát an ninh, phân tích video thời gian thực**; đồng thời nhấn mạnh các mục tiêu như nhận diện người lạ, phát hiện xâm nhập trái phép, và cảnh báo bất thường.  
Trong phần kiến trúc AI, tài liệu đề xuất một pipeline thực dụng gồm **YOLOv8-face hoặc RetinaFace** cho detection, **ArcFace hoặc FaceNet** cho recognition, **ByteTrack** cho tracking, và **rule-based behavior** cho các tình huống như vùng cấm, loitering, và người lạ. citeturn0file1turn0file0

## 2. Điểm nổi bật của repo

- Có sẵn notebook cho từng bước của pipeline AI.
- Có script tiền xử lý dữ liệu ảnh/video.
- Có khung backend FastAPI.
- Có cấu trúc tách biệt giữa `ai/`, `backend/` và `app flutter/`.
- Có notebook đánh giá mô hình bằng các chỉ số như FAR/FRR, mAP, FPS, ID switch rate.

## 3. Cấu trúc thư mục

```text
face-security-system-haituan/
├── ai/
│   ├── notebooks/
│   │   ├── 01_data_preprocessing.ipynb
│   │   ├── 02_face_detection_recognition.ipynb
│   │   ├── 03_tracking_behavior.ipynb
│   │   └── 04_evaluation.ipynb
│   ├── src/
│   │   ├── detection/
│   │   ├── recognition/
│   │   ├── tracking/
│   │   ├── behavior/
│   │   └── utils/
│   └── requirements.txt
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   └── tests/
│   └── requirements.txt
├── app flutter/
│   └── README.md
└── README.md
```

## 4. AI Pipeline trong dự án

### 4.1 Tiền xử lý dữ liệu
Notebook `01_data_preprocessing.ipynb` phụ trách:
- tạo cấu trúc thư mục dataset,
- tải / mô phỏng dataset danh tính,
- phát hiện và căn chỉnh khuôn mặt,
- tách gallery / probe,
- trích frame từ video,
- augmentation cho ảnh gallery.

Trong notebook này có các hàm chính như:
- `imread_unicode`
- `imwrite_unicode`
- `detect_and_align`
- `is_blurry`
- `is_face_too_small`
- `extract_frames`

### 4.2 Detection + Recognition + Tracking
Notebook `02_face_detection_recognition.ipynb` triển khai:
- khởi tạo InsightFace,
- xây gallery embedding,
- cosine similarity matching,
- YOLOv8 + ByteTrack cho luồng cascade.

Các hàm chính:
- `get_embedding`
- `match_face`
- `run_cascade_on_video`

### 4.3 Behavior Engine
Notebook `03_tracking_behavior.ipynb` xây dựng:
- vùng cấm (ROI),
- phát hiện loitering,
- phát hiện người lạ,
- cơ chế cooldown để tránh spam cảnh báo.

Class chính:
- `BehaviorRuleEngine`

### 4.4 Evaluation
Notebook `04_evaluation.ipynb` tập trung đánh giá:
- **Recognition**: FAR / FRR / EER
- **Detection**: WIDER FACE
- **Tracking**: MOT17
- **Hệ thống**: độ trễ end-to-end, false alarm rate

## 5. Backend

Thư mục `backend/` hiện là khung triển khai FastAPI cho:
- enrollment,
- alert list / history,
- websocket push cảnh báo,
- lưu dữ liệu vào database.

Các model dự kiến:
- `Person`
- `Camera`
- `Alert`

Các service dự kiến:
- `pipeline_runner`
- `alert_service`
- `websocket_manager`

## 6. Mobile App

Thư mục `app flutter/` là phần giao diện mobile.  
Theo tài liệu thiết kế, ứng dụng di động dùng để:
- xem danh sách cảnh báo,
- xem chi tiết snapshot,
- nhận push notification,
- theo dõi trạng thái hệ thống.

## 7. Bộ công nghệ sử dụng

### AI
- Python
- OpenCV
- InsightFace / ArcFace
- YOLOv8
- ByteTrack
- ONNX Runtime
- scikit-learn
- pandas, numpy

### Backend
- FastAPI
- SQLite hoặc PostgreSQL
- WebSocket
- Firebase Admin SDK

### Mobile
- Flutter hoặc Android client
- Firebase Cloud Messaging
- Retrofit / API client
- RecyclerView / list view

## 8. Chạy dự án

### 8.1 Cài dependencies AI
```bash
cd ai
pip install -r requirements.txt
```

### 8.2 Cài dependencies backend
```bash
cd backend
pip install -r requirements.txt
```

### 8.3 Chạy notebook
Mở lần lượt các notebook trong `ai/notebooks/` theo thứ tự:
1. `01_data_preprocessing.ipynb`
2. `02_face_detection_recognition.ipynb`
3. `03_tracking_behavior.ipynb`
4. `04_evaluation.ipynb`

## 9. Luồng phát triển của nhóm

Theo kế hoạch phân công:
- **TV1**: AI / machine learning / deep learning
- **TV2**: xử lý dữ liệu ảnh-video, tạo API, backend
- **TV3**: Flutter app

Tài liệu tiến độ cũng chia lộ trình 7 tuần, gồm:
- nghiên cứu và thiết kế,
- thu thập và tiền xử lý dữ liệu,
- face detection + recognition,
- tracking + behavior + API,
- tích hợp end-to-end,
- đánh giá và tối ưu,
- hoàn thiện báo cáo.  
Bản kế hoạch còn nêu tuần dự phòng để xử lý phát sinh và luyện demo. citeturn0file0

## 10. Chỉ số đánh giá

Các chỉ số nên đưa vào báo cáo:
- Detection: `mAP@0.5`, `FPS`
- Recognition: `Accuracy`, `FAR`, `FRR`
- Tracking: `ID switch rate`
- Hệ thống: `end-to-end latency`, `false alarm rate`

Đây cũng là bộ chỉ số được tài liệu pipeline đề xuất cho chương đánh giá hệ thống. citeturn0file1

## 11. Lưu ý quan trọng

- Nhiều file trong repo hiện là **prototype / skeleton**, đặc biệt ở `backend/app/` và `ai/src/`.
- Các notebook đang dùng đường dẫn cứng theo máy local, nên cần sửa lại trước khi chạy trên máy khác.
- README này được viết lại theo đúng cấu trúc repo hiện tại và hai file tài liệu thiết kế của đồ án.

## 12. Gợi ý cải tiến tiếp theo

- Chuẩn hoá lại đường dẫn bằng `.env`.
- Tách logic notebook thành module Python thật.
- Hoàn thiện FastAPI backend.
- Thêm README riêng cho `ai/` và `backend/`.
- Viết sơ đồ kiến trúc, ER diagram và sequence diagram cho báo cáo.

## 13. Trạng thái hiện tại

Repo đang ở trạng thái:
- **AI notebook**: có nội dung và pipeline tương đối rõ.
- **Backend**: có khung, cần triển khai thêm.
- **Mobile app**: mới ở mức khởi tạo tài liệu / scaffold.
=======
# ai/ — AI/ML Pipeline (Face Detection, Recognition, Tracking, Behavior)

## Kiến trúc đã chốt (cascade)

```
Video frame
  -> YOLOv8 + ByteTrack        (phat hien & theo doi TOAN BO nguoi trong khung hinh)
  -> insightface (buffalo_l) tren TUNG CROP nguoi
       (SCRFD detect + ArcFace embedding trong 1 lan goi, co padding de bat mat nho/o xa)
  -> so khop cosine similarity voi gallery -> known / unknown
```

**Lưu ý quan trọng:** ban đầu dự định dùng `retina-face` riêng cho face detection, nhưng đã **bỏ hẳn** vì không tương thích TensorFlow/Keras 3 trên Python 3.13 (xem "Vấn đề môi trường đã gặp" bên dưới). Hiện tại `insightface` (buffalo_l) làm luôn cả detect + embedding trong 1 model pack — không cần TensorFlow nữa.

## Cấu trúc thư mục

```
ai/
├── requirements.txt
├── notebooks/
│   ├── 01_data_preprocessing.ipynb          - tai LFW, align 112x112 (chuan ArcFace),
│   │                                            loc chat luong, chia gallery/probe, trich frame video
│   ├── 02_face_detection_recognition.ipynb  - build gallery embeddings, cascade YOLOv8+ByteTrack
│   │                                            + insightface, ghi log CSV (co buffer theo track_id)
│   ├── 03_tracking_behavior.ipynb           - rule-based behavior engine (vung cam, lang vang,
│   │                                            nguoi la), doc log tu Notebook 02
│   └── 04_evaluation.ipynb                  - FAR/FRR/EER, danh gia tren WIDER FACE + MOT17
├── models/
│   ├── gallery_embeddings.pkl               - gallery embeddings da xay (Notebook 02, Cell 6)
│   └── yolov8n.pt                           - tu dong tai boi ultralytics lan dau chay
└── dataset/
    ├── raw/lfw/<person>/*.jpg                       - anh goc LFW (mo phong gallery)
    ├── processed/gallery/<person>/*.jpg             - anh da align 112x112, da loc chat luong
    ├── splits/{gallery,probe}/                      - chia 70/30 theo tung nguoi
    ├── augmented/                                   - anh gallery da tang cuong (tuy chon)
    ├── frames/                                      - khung hinh trich tu video test
    ├── cascade_test_output/                         - video da gan nhan + log CSV (Notebook 02)
    ├── benchmarks/
    │   ├── wider face/                              - tai THU CONG tu trang chu WIDER FACE
    │   └── mot17/                                   - tai THU CONG tu motchallenge.net
    ├── evaluation_results/                          - ket qua Notebook 04
    ├── preprocessing_log.csv, split_manifest.csv
    ├── gallery_build_log.csv, probe_match_results.csv
    ├── behavior_alerts.csv, dataset_metadata.json
```

**Lưu ý tên thư mục:** dùng `dataset/` (không phải `data/`) — nếu thấy tài liệu/hướng dẫn cũ nào ghi `ai/data/...`, đó là tên gọi lỗi thời từ lúc thiết kế ban đầu, thực tế đã đổi thành `ai/dataset/...`.

## Setup

```
cd ai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Mở notebook trong VS Code (extension Jupyter), chọn Kernel = Python interpreter của venv vừa tạo.

## Các thông số đã kiểm chứng — KHÔNG đổi nếu chưa có lý do rõ ràng

| Thông số | Giá trị | Lý do |
|---|---|---|
| `det_thresh` (insightface) | 0.3 | Mặc định ~0.5 quá chặt cho ảnh crop sát mặt/gần khung hình |
| `PAD_RATIO` | 0.4 | Ảnh crop sát khiến mặt chiếm gần hết khung hình → detector nhầm out-of-distribution; thêm viền đệm giúp fix (đã kiểm chứng: no_face từ 3021/3023 xuống 0/3023) |
| `MATCH_THRESHOLD` | 0.35 | Xác nhận qua Notebook 04 (FAR=0.2%, FRR=0.36% trên LFW). **Nhưng match_score trên video thật thấp hơn LFW nhiều** (0.35–0.8 so với 0.7–0.85 trên LFW) — KHÔNG nên nâng threshold cao hơn dù số liệu LFW gợi ý vậy |
| `BUFFER_SIZE` (Notebook 02) | 10 frame | Quyết định danh tính dựa trên trung bình N lần nhận diện gần nhất của TỪNG `track_id` riêng biệt, thay vì tin 1 frame đơn lẻ (video thật nhiễu hơn ảnh tĩnh nhiều) |

## Vấn đề môi trường đã gặp (đọc trước khi debug lại từ đầu)

1. **`sklearn.fetch_lfw_people()` trả về pixel trong khoảng [0.0, 1.0], KHÔNG phải [0, 255]** — quên nhân `*255.0` trước khi ép kiểu `uint8` sẽ ra ảnh toàn màu đen.
2. **`retina-face` không chạy được trên Python 3.13 + TensorFlow mới (Keras 3)** — lỗi `ValueError: You have tensorflow X and this requires tf-keras package`, cài `tf-keras` chỉ vá được lớp ngoài, lỗi thật nằm sâu hơn trong cách `retina-face` dựng model. Đã bỏ hẳn, chuyển sang `insightface` cho cả detect và recognition.
3. **`cv2.imread`/`cv2.imwrite` có thể âm thầm trả về `None`** với đường dẫn chứa ký tự Unicode (tên có dấu, ví dụ `José`) trên Windows — nếu gặp lỗi `AttributeError: 'NoneType' object has no attribute 'shape'`, đây là nghi phạm đầu tiên cần kiểm tra.
4. **Face detector (SCRFD/RetinaFace) fail gần như 100% trên ảnh crop sát mặt** (như LFW mặc định, hoặc ảnh 112x112 đã align) — do out-of-distribution so với dữ liệu huấn luyện gốc (ảnh cảnh thường, mặt chiếm phần nhỏ khung hình). Đã fix bằng padding + hạ `det_thresh` (xem bảng thông số ở trên).

## Bước tiếp theo có thể làm

- Tách phần logic đã ổn định (align, quality check, embedding, cascade) từ notebook ra module `.py` riêng nếu `backend/` cần dùng lại — hiện `backend/app/services/face_recognition_service.py` đã copy tay logic `get_embedding()`, chưa import trực tiếp từ `ai/`.
- Notebook 04 Phần B/C (WIDER FACE, MOT17) mặc định chỉ chạy 1 phần nhỏ (200 ảnh / 1 sequence) để tiết kiệm thời gian trên CPU — tăng `N_EVAL_IMAGES` hoặc thêm sequence nếu muốn đánh giá đầy đủ hơn cho báo cáo.
>>>>>>> 726e467 (Update face recognition project)

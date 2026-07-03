# Security AI System: Hệ thống Giám sát An ninh Thông minh

Dự án xây dựng hệ thống giám sát an ninh thời gian thực ứng dụng các kỹ thuật Computer Vision và Deep Learning tiên tiến. Hệ thống có khả năng nhận diện khuôn mặt, theo dõi đa đối tượng và tự động phát hiện các hành vi bất thường trong video giám sát.

##  Tính năng chính

- **Face Detection & Recognition:** Phát hiện và nhận diện khuôn mặt chính xác trong điều kiện thực tế (sử dụng YOLO & ArcFace).
- **Person Detection & Tracking:** Theo dõi đa đối tượng (Multi-Object Tracking) liên tục qua các khung hình (sử dụng ByteTrack/DeepSORT).
- **Anomaly Detection:** Tự động phát hiện các hành vi bất thường, xâm nhập trái phép hoặc tai nạn (sử dụng Autoencoder/MemAE).
- **Real-time Processing:** Xử lý luồng video thời gian thực, tối ưu hóa cho GPU (RTX 5070).
- **Dashboard & Alerting:** Giao diện giám sát trực quan và hệ thống cảnh báo sự kiện.

## Cấu trúc thư mục (Project Structure)

Dự án được thiết kế theo mô hình **Clean Architecture**, tách biệt rõ ràng giữa lõi xử lý AI (Vision), dịch vụ hệ thống (Services) và giao diện (UI/API).

```text
security_ai_system/
│
├── configs/                  # File cấu hình hệ thống và model (YAML/JSON)
├── data/                     # Dữ liệu đầu vào (Dataset, Faces DB) - *Đã được ignore*
│   ├── datasets/             # Các bộ dữ liệu gốc (WIDER FACE, MOT17, UCSD...)
│   ├── processed/            # Dữ liệu đã tiền xử lý
│   └── faces_db/             # Database khuôn mặt đã đăng ký
│
├── weights/                  # Pre-trained weights & Checkpoints - *Đã được ignore*
── outputs/                  # Kết quả dự đoán, video, ảnh đầu ra - *Đã được ignore*
├── notebooks/                # Jupyter Notebooks cho EDA và thử nghiệm thuật toán
├── experiments/              # Log, metrics và kết quả của các lần train model
├── docs/                     # Tài liệu, báo cáo, slide bảo vệ
├── scripts/                  # Script tiện ích (download data, convert format...)
├── tests/                    # Unit tests và Integration tests
│
├── src/                      # Mã nguồn chính (Source Code)
│   ├── core/                 # Điều phối luồng xử lý (Pipeline, Event Engine)
│   │   └── interfaces/       # Định nghĩa Interface/Contract cho các module AI
│   │
│   ├── vision/               # Toàn bộ thuật toán AI & Computer Vision
│   │   ├── detection/        # Logic phát hiện (Face, Person)
│   │   ├── tracking/         # Logic theo dõi đối tượng
│   │   ├── recognition/      # Logic nhận diện khuôn mặt
│   │   ├── anomaly/          # Logic phát hiện bất thường
│   │   └── models/           # Định nghĩa kiến trúc Model (YOLO, ArcFace, AutoEncoder)
│   │
│   ├── services/             # Tương tác phần cứng & bên thứ 3 (Camera, DB, Alert)
│   ├── api/                  # Backend API endpoints (FastAPI/Flask)
│   ├── ui/                   # Giao diện người dùng
│   ── utils/                # Các hàm tiện ích chung
│
├── main.py                   # Entry point chạy hệ thống dưới dạng Console/Service
├── app.py                    # Entry point chạy giao diện UI / API
├── requirements.txt          # Danh sách thư viện Python
├── .gitignore                # Cấu hình bỏ qua file/folder khi push Git
└── README.md                 # Tài liệu hướng dẫn dự án
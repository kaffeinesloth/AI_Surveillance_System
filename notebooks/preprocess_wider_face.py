from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple
from PIL import Image
from tqdm import tqdm

# Ngưỡng lọc face quá nhỏ (pixel). 
# Những face có w hoặc h < ngưỡng này sẽ bị loại bỏ để tránh noise.
MIN_FACE_SIZE = 8 

def read_image_size(img_path: Path) -> Tuple[int, int]:
    with Image.open(img_path) as img:
        return img.size  # (w, h)

def xywh_to_yolo(x: float, y: float, w: float, h: float, img_w: int, img_h: int):
    cx = x + w / 2.0
    cy = y + h / 2.0
    return (cx / img_w, cy / img_h, w / img_w, h / img_h)

def parse_widerface_gt(txt_path: Path):
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    lines = [ln.strip() for ln in lines if ln.strip()]

    i = 0
    items = []

    while i < len(lines):
        rel_path = lines[i]
        i += 1

        if not rel_path.lower().endswith(".jpg"):
            continue

        num_boxes = int(lines[i])
        i += 1

        boxes = []
        
        # Xử lý trường hợp ảnh không có box (1 dòng dummy)
        if num_boxes == 0:
            if i < len(lines) and not lines[i].lower().endswith(".jpg"):
                i += 1
            items.append((rel_path, boxes))
            continue

        for _ in range(num_boxes):
            parts = lines[i].split()
            i += 1

            if len(parts) < 10:
                continue

            x, y, w, h = map(float, parts[:4])
            invalid = int(parts[7])

            if invalid == 1:
                continue

            boxes.append((x, y, w, h))

        items.append((rel_path, boxes))

    return items

def save_yolo_label(label_path: Path, boxes_yolo: List[Tuple[float, float, float, float]]):
    """Hàm này sẽ tạo file txt. Nếu boxes_yolo rỗng, file txt sẽ rỗng (chuẩn YOLO cho ảnh background)."""
    label_path.parent.mkdir(parents=True, exist_ok=True)
    with label_path.open("w", encoding="utf-8") as f:
        for cx, cy, bw, bh in boxes_yolo:
            f.write(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

def copy_or_link_image(src: Path, dst: Path, mode: str = "copy"):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "copy":
        shutil.copy2(src, dst)
    elif mode == "symlink":
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(src.resolve())
    else:
        raise ValueError("mode must be 'copy' or 'symlink'")

def preprocess_split(
    split_name: str,
    ann_txt: Path,
    image_root: Path,
    out_root: Path,
    copy_images: bool = True,
):
    items = parse_widerface_gt(ann_txt)

    img_out_dir = out_root / "images" / split_name
    lbl_out_dir = out_root / "labels" / split_name
    img_out_dir.mkdir(parents=True, exist_ok=True)
    lbl_out_dir.mkdir(parents=True, exist_ok=True)

    num_images = 0
    num_boxes = 0
    num_empty = 0  # Đếm số lượng ảnh không có box hợp lệ (background)

    for rel_path, boxes in tqdm(items, desc=f"Processing {split_name}"):
        src_img = image_root / rel_path
        if not src_img.exists():
            print(f"\n[WARN] Missing image: {src_img}")
            continue

        try:
            img_w, img_h = read_image_size(src_img)
        except Exception as e:
            print(f"\n[ERROR] Cannot read image {src_img}: {e}")
            continue

        yolo_boxes = []
        for x, y, w, h in boxes:
            # --- LỌC FACE QUÁ NHỎ ---
            # Bỏ qua các face có kích thước < MIN_FACE_SIZE pixel để mô hình học ổn định hơn
            if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                continue

            # --- XỬ LÝ TỌA ĐỘ ÂM (CLAMP LOGIC) ---
            if x < 0:
                w = w + x
                x = 0.0
            if y < 0:
                h = h + y
                y = 0.0

            w = min(w, img_w - x)
            h = min(h, img_h - y)

            # Kiểm tra lại lần cuối sau khi clamp
            if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                continue

            yolo_boxes.append(xywh_to_yolo(x, y, w, h, img_w, img_h))

        # --- GIỮ LẠI ẢNH KHÔNG CÓ FACE (NEGATIVE MINING) ---
        # Không dùng 'continue' để skip ảnh nữa. 
        # Vẫn copy ảnh và tạo file txt rỗng (hàm save_yolo_label sẽ tự tạo file rỗng nếu list rỗng)
        if len(yolo_boxes) == 0:
            num_empty += 1

        dst_img = img_out_dir / rel_path
        dst_lbl = lbl_out_dir / rel_path.replace(".jpg", ".txt")

        if copy_images:
            copy_or_link_image(src_img, dst_img, mode="copy")
        else:
            copy_or_link_image(src_img, dst_img, mode="symlink")

        save_yolo_label(dst_lbl, yolo_boxes)

        num_images += 1
        num_boxes += len(yolo_boxes)

    print(f"[{split_name}] Done. Total images: {num_images} (incl. {num_empty} background images). Valid boxes: {num_boxes}")

def write_dataset_yaml(out_root: Path):
    yaml_text = """# WIDER FACE YOLO dataset
path: .
train: images/train
val: images/val

nc: 1
names: [face]
"""
    (out_root / "dataset.yaml").write_text(yaml_text, encoding="utf-8")

def main():
    data_root = Path(r"D:\security_ai_system\data\datasets\raw\WIDER_FACE")
    split_root = data_root / "wider_face_annotations" / "wider_face_split"

    train_txt = split_root / "wider_face_train_bbx_gt.txt"
    val_txt = split_root / "wider_face_val_bbx_gt.txt"

    train_img_root = data_root / "WIDER_train" / "images"
    val_img_root = data_root / "WIDER_val" / "images"

    out_root = Path(r"D:\security_ai_system\data\datasets\processed\WIDER_FACE")

    preprocess_split(
        split_name="train",
        ann_txt=train_txt,
        image_root=train_img_root,
        out_root=out_root,
        copy_images=True,
    )

    preprocess_split(
        split_name="val",
        ann_txt=val_txt,
        image_root=val_img_root,
        out_root=out_root,
        copy_images=True,
    )

    write_dataset_yaml(out_root)
    print(f"\nAll done! Output saved to: {out_root}")

if __name__ == "__main__":
    main()
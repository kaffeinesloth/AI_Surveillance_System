from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm
from PIL import Image

# Dùng set chứa các đuôi file ở dạng chữ thường
IMG_EXTS = {".jpg", ".jpeg"}

def is_image_file(path: Path) -> bool:
    # Luôn lowercase suffix để kiểm tra
    return path.suffix.lower() in IMG_EXTS

def check_image_valid(img_path: Path) -> bool:
    """Kiểm tra xem ảnh có mở được và không bị cắt cụt (truncated) không."""
    try:
        with Image.open(img_path) as img:
            img.load() # Dùng load() thay vì verify() để bắt lỗi truncated images
        return True
    except Exception:
        return False

def collect_identities(split_dir: Path) -> List[str]:
    """Return sorted identity folder names."""
    identities = [p.name for p in split_dir.iterdir() if p.is_dir()]
    identities.sort()
    return identities

def collect_samples(split_dir: Path, split_name: str) -> List[Dict]:
    """
    Collect all valid image samples under:
        split_dir / identity_name / *.jpg
    """
    samples = []
    identities = collect_identities(split_dir)
    
    # Thêm tqdm để theo dõi tiến trình
    for identity in tqdm(identities, desc=f"Scanning {split_name} identities"):
        identity_dir = split_dir / identity
        for img_path in sorted(identity_dir.rglob("*")):
            if not img_path.is_file() or not is_image_file(img_path):
                continue

            if not check_image_valid(img_path):
                print(f"\n[WARN] Corrupt image skipped: {img_path}")
                continue

            samples.append(
                {
                    "split": split_name,
                    "identity": identity,
                    # Dùng as_posix() để đường dẫn luôn dùng '/' 
                    # (Tương thích khi mang CSV sang Linux train)
                    "image_path": img_path.as_posix(), 
                    "file_name": img_path.name,
                }
            )

    return samples

def build_class_mapping(train_samples: List[Dict], val_samples: List[Dict]) -> Dict[str, int]:
    """
    Build a stable label mapping from all identities found in train + val.
    """
    identities = sorted(
        set(s["identity"] for s in train_samples) | set(s["identity"] for s in val_samples)
    )
    return {identity: idx for idx, identity in enumerate(identities)}

def save_csv(samples: List[Dict], class_to_idx: Dict[str, int], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_path", "identity", "label", "split", "file_name"])

        for s in samples:
            writer.writerow(
                [
                    s["image_path"],
                    s["identity"],
                    class_to_idx[s["identity"]],
                    s["split"],
                    s["file_name"],
                ]
            )

def save_json(obj, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def copy_or_symlink(src: Path, dst: Path, mode: str = "symlink") -> bool:
    """
    Tạo symlink hoặc copy. 
    Trả về True nếu thành công, False nếu symlink bị lỗi (thường do Windows quyền admin).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    if mode == "copy":
        shutil.copy2(src, dst)
        return True
    elif mode == "symlink":
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        try:
            dst.symlink_to(src.resolve())
            return True
        except OSError as e:
            # Lỗi thường gặp trên Windows chưa bật Developer Mode
            print(f"\n[WARN] Cannot create symlink (try enabling Developer Mode or run as Admin). Falling back to copy... {e}")
            shutil.copy2(src, dst)
            return True
    else:
        raise ValueError("mode must be 'copy' or 'symlink'")

def materialize_clean_dataset(
    samples: List[Dict],
    out_root: Path,
    mode: str = "symlink",
) -> None:
    """
    Create:
      out_root/images/train/<identity>/*.jpg
      out_root/images/val/<identity>/*.jpg
    """
    # Dùng tqdm cho quá trình tạo file
    for s in tqdm(samples, desc=f"Materializing dataset"):
        src = Path(s["image_path"])
        split = s["split"]
        identity = s["identity"]
        dst = out_root / "images" / split / identity / src.name
        copy_or_symlink(src, dst, mode=mode)

def main():
    data_root = Path(r"D:\Code\Face recognition security system\ai\dataset\benchmarks\VGG Face 2")
    train_dir = data_root / "train"
    val_dir = data_root / "val"

    out_root = Path(r"D:\Code\Face recognition security system\ai\dataset\processed\VGG Face 2")

    print("Collecting train samples...")
    train_samples = collect_samples(train_dir, "train")

    print("Collecting val samples...")
    val_samples = collect_samples(val_dir, "val")

    print("Building class mapping...")
    class_to_idx = build_class_mapping(train_samples, val_samples)

    print(f"Found {len(class_to_idx)} identities")
    print(f"Train images: {len(train_samples)}")
    print(f"Val images: {len(val_samples)}")

    # Save metadata
    save_json(class_to_idx, out_root / "class_to_idx.json")
    save_csv(train_samples, class_to_idx, out_root / "train.csv")
    save_csv(val_samples, class_to_idx, out_root / "val.csv")

    # Tạo cây thư mục mới (mặc định dùng symlink cho nhẹ, nếu lỗi sẽ tự copy)
    materialize_clean_dataset(train_samples, out_root, mode="symlink")
    materialize_clean_dataset(val_samples, out_root, mode="symlink")

    summary = {
        "num_identities": len(class_to_idx),
        "num_train_images": len(train_samples),
        "num_val_images": len(val_samples),
        "output_root": out_root.as_posix(),
    }
    save_json(summary, out_root / "summary.json")

    print("\nDone.")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
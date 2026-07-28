from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from insightface.app import FaceAnalysis
except ImportError as e:
    raise ImportError(
        "This script requires insightface. Install it with:\n"
        "  pip install insightface onnxruntime opencv-python numpy"
    ) from e


# =========================
# CONFIG
# =========================
RAW_ROOT = Path(r"D:\security_ai_system\data\database\raw")
PROCESSED_ROOT = Path(r"D:\security_ai_system\data\database\processed")

MODEL_NAME = "buffalo_l"
CTX_ID = -1  # CPU
DET_SIZE = (640, 640)
TARGET_SIZE = (112, 112)

MIN_FACE_SIDE = 80
MIN_BLUR_REJECT = 18.0
MIN_BRIGHTNESS_REJECT = 20.0
MAX_BRIGHTNESS_REJECT = 245.0

DARK_THRESHOLD = 75.0
BRIGHT_THRESHOLD = 205.0
BLUR_SHARPEN_THRESHOLD = 80.0

COPY_REJECTED_ORIGINAL = False
# =========================


IMG_EXTS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp",
    ".JPG", ".JPEG", ".PNG", ".BMP", ".WEBP"
}


def is_image_file(path: Path) -> bool:
    return path.suffix in IMG_EXTS


def load_image_unicode(img_path: Path) -> Optional[np.ndarray]:
    try:
        data = np.fromfile(str(img_path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def save_image_unicode(img: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ext = out_path.suffix.lower()

    if ext in [".jpg", ".jpeg"]:
        ok, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    else:
        ok, buffer = cv2.imencode(".png", img)

    if not ok:
        raise RuntimeError(f"Cannot encode image: {out_path}")

    buffer.tofile(str(out_path))


def resize_image(img: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    return cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)


def pad_to_square(img: np.ndarray, pad_value: int = 0) -> np.ndarray:
    h, w = img.shape[:2]
    if h == w:
        return img

    side = max(h, w)
    top = (side - h) // 2
    bottom = side - h - top
    left = (side - w) // 2
    right = side - w - left

    return cv2.copyMakeBorder(
        img,
        top,
        bottom,
        left,
        right,
        borderType=cv2.BORDER_CONSTANT,
        value=(pad_value, pad_value, pad_value),
    )


def variance_of_laplacian(img_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def mean_brightness(img_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def apply_clahe(img_bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    merged = cv2.merge((l2, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def gamma_correction(img_bgr: np.ndarray, target_mean: float = 120.0) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    mean = gray.mean()
    if mean <= 1e-6:
        return img_bgr

    gamma = math.log(target_mean / 255.0) / math.log(mean / 255.0)
    gamma = float(np.clip(gamma, 0.5, 2.5))
    table = np.array([(i / 255.0) ** gamma * 255 for i in range(256)], dtype=np.uint8)
    return cv2.LUT(img_bgr, table)


def denoise_image(img_bgr: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(img_bgr, None, 3, 3, 7, 21)


def sharpen_image(img_bgr: np.ndarray) -> np.ndarray:
    kernel = np.array(
        [[0, -1, 0],
         [-1, 5, -1],
         [0, -1, 0]],
        dtype=np.float32,
    )
    return cv2.filter2D(img_bgr, -1, kernel)


def quality_check(img_bgr: np.ndarray) -> Tuple[bool, Dict]:
    blur_score = variance_of_laplacian(img_bgr)
    brightness = mean_brightness(img_bgr)
    h, w = img_bgr.shape[:2]

    ok = True
    reason = []

    if min(h, w) < MIN_FACE_SIDE:
        ok = False
        reason.append("face_too_small")

    if blur_score < MIN_BLUR_REJECT:
        ok = False
        reason.append("too_blurry")

    if brightness < MIN_BRIGHTNESS_REJECT:
        ok = False
        reason.append("too_dark")

    if brightness > MAX_BRIGHTNESS_REJECT:
        ok = False
        reason.append("too_bright")

    return ok, {
        "blur_score": float(blur_score),
        "brightness": float(brightness),
        "reason": ";".join(reason),
    }


def enhance_face(img_bgr: np.ndarray, blur_score: float, brightness: float) -> Tuple[np.ndarray, str]:
    steps = []

    if brightness < DARK_THRESHOLD:
        img_bgr = gamma_correction(img_bgr)
        img_bgr = apply_clahe(img_bgr)
        steps.append("dark_enhanced")
    elif brightness > BRIGHT_THRESHOLD:
        img_bgr = apply_clahe(img_bgr)
        steps.append("bright_clahe")

    if brightness < DARK_THRESHOLD + 15:
        img_bgr = denoise_image(img_bgr)
        steps.append("denoised")

    if blur_score < BLUR_SHARPEN_THRESHOLD:
        img_bgr = sharpen_image(img_bgr)
        steps.append("sharpened")

    return img_bgr, ";".join(steps)


def similarity_transform_from_5pts(src_pts: np.ndarray, dst_pts: np.ndarray) -> np.ndarray:
    """
    Return 2x3 affine matrix mapping src_pts -> dst_pts.
    """
    M, _ = cv2.estimateAffinePartial2D(src_pts.astype(np.float32), dst_pts.astype(np.float32), method=cv2.LMEDS)
    if M is None:
        raise RuntimeError("Could not estimate affine transform from landmarks.")
    return M


def standard_arcface_template(target_size: Tuple[int, int]) -> np.ndarray:
    """
    Standard 5-point template for 112x112 ArcFace-style alignment.
    """
    tw, th = target_size
    if (tw, th) != (112, 112):
        scale_x = tw / 112.0
        scale_y = th / 112.0
    else:
        scale_x = 1.0
        scale_y = 1.0

    dst = np.array([
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ], dtype=np.float32)

    dst[:, 0] *= scale_x
    dst[:, 1] *= scale_y
    return dst


def align_face_from_landmarks(
    img_bgr: np.ndarray,
    kps: np.ndarray,
    target_size: Tuple[int, int] = TARGET_SIZE,
) -> Optional[np.ndarray]:
    """
    Align directly on the original image using InsightFace 5 landmarks.
    No pre-cropping before alignment.
    """
    if kps is None or len(kps) != 5:
        return None

    dst = standard_arcface_template(target_size)
    M = similarity_transform_from_5pts(np.asarray(kps, dtype=np.float32), dst)

    tw, th = target_size
    aligned = cv2.warpAffine(
        img_bgr,
        M,
        (tw, th),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    return aligned


class InsightFaceProcessor:
    def __init__(self, model_name: str = MODEL_NAME, ctx_id: int = CTX_ID, det_size: Tuple[int, int] = DET_SIZE):
        self.app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=ctx_id, det_size=det_size)

    def detect_largest_face(self, img_bgr: np.ndarray) -> Optional[Dict]:
        faces = self.app.get(img_bgr)
        if not faces:
            return None

        best = None
        best_score = -1.0

        for face in faces:
            bbox = face.bbox.astype(float)  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = bbox.tolist()
            area = max(0.0, (x2 - x1) * (y2 - y1))
            det_score = float(getattr(face, "det_score", 0.0))
            score = det_score * (1.0 + area / 100000.0)

            if score > best_score:
                best_score = score
                best = {
                    "bbox": (x1, y1, x2, y2),
                    "conf": det_score,
                    "kps": np.array(face.kps, dtype=np.float32) if getattr(face, "kps", None) is not None else None,
                }

        return best


def preprocess_one_image(processor: InsightFaceProcessor, img_path: Path) -> Tuple[Optional[np.ndarray], Dict]:
    meta = {
        "status": "saved",
        "reason": "",
        "face_conf": None,
        "x1": None, "y1": None, "x2": None, "y2": None,
        "blur_score": None,
        "brightness": None,
        "aligned": False,
        "enhance_steps": "",
    }

    img = load_image_unicode(img_path)
    if img is None:
        meta["status"] = "rejected"
        meta["reason"] = "cannot_read_image"
        return None, meta

    det = processor.detect_largest_face(img)
    if det is None:
        meta["status"] = "rejected"
        meta["reason"] = "no_face_detected"
        return None, meta

    kps = det["kps"]
    conf = det["conf"]
    bbox = det["bbox"]

    meta["face_conf"] = float(conf)
    meta["x1"], meta["y1"], meta["x2"], meta["y2"] = map(float, bbox)

    # Align directly on full image using 5 facial landmarks
    aligned = None
    aligned_used = False
    if kps is not None:
        try:
            aligned = align_face_from_landmarks(img, kps, TARGET_SIZE)
            aligned_used = aligned is not None
        except Exception:
            aligned = None
            aligned_used = False

    # Fallback if alignment fails: crop by bbox from full image, then pad/resize.
    if aligned is None:
        x1, y1, x2, y2 = bbox
        h, w = img.shape[:2]
        x1 = int(max(0, round(x1)))
        y1 = int(max(0, round(y1)))
        x2 = int(min(w - 1, round(x2)))
        y2 = int(min(h - 1, round(y2)))

        # Add a small margin on fallback crop
        bw = x2 - x1
        bh = y2 - y1
        cx = x1 + bw / 2.0
        cy = y1 + bh / 2.0
        bw = bw * 1.25
        bh = bh * 1.25
        fx1 = int(max(0, round(cx - bw / 2.0)))
        fy1 = int(max(0, round(cy - bh / 2.0)))
        fx2 = int(min(w - 1, round(cx + bw / 2.0)))
        fy2 = int(min(h - 1, round(cy + bh / 2.0)))

        crop = img[fy1:fy2, fx1:fx2].copy()
        if crop.size == 0:
            meta["status"] = "rejected"
            meta["reason"] = "empty_crop"
            return None, meta

        aligned = pad_to_square(crop, pad_value=0)
        aligned = resize_image(aligned, TARGET_SIZE)
        aligned_used = False

    meta["aligned"] = aligned_used

    ok, q = quality_check(aligned)
    meta["blur_score"] = q["blur_score"]
    meta["brightness"] = q["brightness"]
    meta["reason"] = q["reason"]

    if not ok:
        meta["status"] = "rejected"
        return None, meta

    enhanced, steps = enhance_face(aligned, blur_score=q["blur_score"], brightness=q["brightness"])
    meta["enhance_steps"] = steps

    final_img = pad_to_square(enhanced, pad_value=0)
    final_img = resize_image(final_img, TARGET_SIZE)
    return final_img, meta


def process_database(raw_root: Path, processed_root: Path) -> None:
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw root not found: {raw_root}")

    processed_root.mkdir(parents=True, exist_ok=True)
    processor = InsightFaceProcessor()

    manifest_rows: List[Dict] = []
    summary = {
        "num_people": 0,
        "num_images_total": 0,
        "num_images_saved": 0,
        "num_images_rejected": 0,
        "people": {},
        "target_size": list(TARGET_SIZE),
        "using": "insightface_faceanalysis_v4",
        "model_name": MODEL_NAME,
    }

    person_dirs = sorted([p for p in raw_root.iterdir() if p.is_dir()])

    for person_dir in person_dirs:
        person_name = person_dir.name
        image_files = sorted([p for p in person_dir.rglob("*") if p.is_file() and is_image_file(p)])

        summary["num_people"] += 1
        person_total = 0
        person_saved = 0
        person_rejected = 0

        for img_path in image_files:
            person_total += 1
            summary["num_images_total"] += 1

            processed_img, meta = preprocess_one_image(processor, img_path)
            rel_out = Path(person_name) / img_path.name
            out_path = processed_root / rel_out

            if processed_img is None:
                person_rejected += 1
                summary["num_images_rejected"] += 1

                manifest_rows.append({
                    "person": person_name,
                    "input_path": str(img_path),
                    "output_path": str(out_path),
                    "status": meta["status"],
                    "reason": meta["reason"],
                    "face_conf": meta["face_conf"],
                    "blur_score": meta["blur_score"],
                    "brightness": meta["brightness"],
                    "aligned": meta["aligned"],
                    "enhance_steps": meta["enhance_steps"],
                    "bbox_x1": meta["x1"],
                    "bbox_y1": meta["y1"],
                    "bbox_x2": meta["x2"],
                    "bbox_y2": meta["y2"],
                })

                if COPY_REJECTED_ORIGINAL:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        out_path.write_bytes(img_path.read_bytes())
                    except Exception:
                        pass
                continue

            save_image_unicode(processed_img, out_path)
            person_saved += 1
            summary["num_images_saved"] += 1

            manifest_rows.append({
                "person": person_name,
                "input_path": str(img_path),
                "output_path": str(out_path),
                "status": "saved",
                "reason": meta["reason"],
                "face_conf": meta["face_conf"],
                "blur_score": meta["blur_score"],
                "brightness": meta["brightness"],
                "aligned": meta["aligned"],
                "enhance_steps": meta["enhance_steps"],
                "bbox_x1": meta["x1"],
                "bbox_y1": meta["y1"],
                "bbox_x2": meta["x2"],
                "bbox_y2": meta["y2"],
            })

        summary["people"][person_name] = {
            "total": person_total,
            "saved": person_saved,
            "rejected": person_rejected,
        }

    manifest_path = processed_root / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "person",
                "input_path",
                "output_path",
                "status",
                "reason",
                "face_conf",
                "blur_score",
                "brightness",
                "aligned",
                "enhance_steps",
                "bbox_x1",
                "bbox_y1",
                "bbox_x2",
                "bbox_y2",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    summary_path = processed_root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Done.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    process_database(RAW_ROOT, PROCESSED_ROOT)

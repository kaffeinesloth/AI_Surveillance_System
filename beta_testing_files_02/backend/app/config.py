import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'storage', 'security.db')}"
)
SNAPSHOT_DIR = os.getenv("SNAPSHOT_DIR", os.path.join(BASE_DIR, "storage", "snapshots"))
EMBEDDINGS_DIR = os.getenv("EMBEDDINGS_DIR", os.path.join(BASE_DIR, "storage", "embeddings"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "storage", "uploads"))

FACE_DET_THRESH = 0.3
FACE_PAD_RATIO = 0.4
FACE_MATCH_THRESHOLD = 0.35
TRACK_BUFFER_SIZE = 10

os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
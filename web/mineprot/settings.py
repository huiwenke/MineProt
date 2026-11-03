import os
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(os.getenv("MP_REPO_PATH", str(WEB_ROOT.parent / "data/repo"))).resolve()
CACHE_ROOT = Path(os.getenv("MP_CACHE_PATH", "/tmp/mineprot")).resolve()
ES_URL = os.getenv("MP_ELASTICSEARCH", "http://elasticsearch:9200").rstrip("/")
MAX_BODY = int(os.getenv("MP_MAX_BODY_BYTES", str(100 * 1024 * 1024)))
MAX_JOBS = int(os.getenv("MP_SALIGN_CONCURRENCY", "2"))
JOB_TIMEOUT = int(os.getenv("MP_SALIGN_TIMEOUT", "300"))
USALIGN = os.getenv("MP_USALIGN", "USalign")
FOLDCOMP = os.getenv("MP_FOLDCOMP", "foldcomp")

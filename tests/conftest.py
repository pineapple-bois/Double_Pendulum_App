import os
from pathlib import Path


TEST_CACHE_DIR = Path(__file__).resolve().parent / ".cache"
TEST_CACHE_DIR.mkdir(exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(TEST_CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TEST_CACHE_DIR / "xdg"))

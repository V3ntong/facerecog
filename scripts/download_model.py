"""Download buffalo_l model with proper retries."""
import os
import sys
import urllib.request
import zipfile
import hashlib

MODEL_DIR = os.path.join(os.path.expanduser("~"), ".insightface", "models")
MODEL_NAME = "buffalo_l"
MODEL_DIR_FULL = os.path.join(MODEL_DIR, MODEL_NAME)
MODEL_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
ZIP_PATH = os.path.join(MODEL_DIR, f"{MODEL_NAME}.zip")

os.makedirs(MODEL_DIR, exist_ok=True)

if os.path.exists(MODEL_DIR_FULL) and len(os.listdir(MODEL_DIR_FULL)) > 2:
    print(f"Model already exists at {MODEL_DIR_FULL}")
    print(f"Files: {os.listdir(MODEL_DIR_FULL)}")
    sys.exit(0)

print(f"Downloading {MODEL_URL} ...")

def progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 / total_size)
        if block_num % 100 == 0:
            print(f"  {pct:.1f}% ({downloaded}/{total_size})")

urllib.request.urlretrieve(MODEL_URL, ZIP_PATH, reporthook=progress)
print("Download complete. Extracting...")

with zipfile.ZipFile(ZIP_PATH, "r") as zf:
    zf.extractall(MODEL_DIR)

os.remove(ZIP_PATH)
print(f"Extracted to {MODEL_DIR_FULL}")
print(f"Files: {os.listdir(MODEL_DIR_FULL)}")

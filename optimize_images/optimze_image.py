# uv add pillow
# 용량 큰 이미지 파일 최적화 용



import os
from pathlib import Path
from PIL import Image, ImageOps

SOURCE_DIR = Path("inputs")
DEST_DIR = Path("outputs")

# ---- TUNABLES ----
MAX_WIDTH = 1600          # resize down if wider than this (try 1200 for OG images)
TARGET_KB = 280           # try 180–350 depending on your needs
MIN_QUALITY = 45          # don't go lower than this unless you accept artifacts
MAX_QUALITY = 85          # upper bound for quality search (start point)
METHOD = 6                # WebP compression effort: 0–6 (6 = smallest, slower)
# -------------------

def ensure_dirs():
    DEST_DIR.mkdir(parents=True, exist_ok=True)

def load_and_prepare(img_path: Path) -> Image.Image:
    # Auto-rotate per EXIF, drop alpha, and convert to RGB
    img = Image.open(img_path)
    img = ImageOps.exif_transpose(img)  # correct orientation
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    # Resize if needed (keeps aspect ratio)
    if img.width > MAX_WIDTH:
        new_h = int(img.height * (MAX_WIDTH / img.width))
        img = img.resize((MAX_WIDTH, new_h), Image.Resampling.LANCZOS)
    return img

def save_webp_with_quality(img: Image.Image, out_path: Path, quality: int):
    # Strip metadata by NOT passing exif/icc_profile; use max compression effort
    img.save(
        out_path,
        format="webp",
        quality=quality,
        method=METHOD,
    )
    return out_path.stat().st_size

def target_size_save(img: Image.Image, out_path: Path, target_kb: int) -> tuple[int, int]:
    """
    Binary search quality to meet target size (in KB).
    Returns: (final_quality, final_size_bytes)
    """
    lo, hi = MIN_QUALITY, MAX_QUALITY
    best_q, best_size = hi, None

    # Quick try at MAX_QUALITY first
    size = save_webp_with_quality(img, out_path, hi)
    if size <= target_kb * 1024:
        return hi, size

    # Binary search
    while lo <= hi:
        mid = (lo + hi) // 2
        size = save_webp_with_quality(img, out_path, mid)

        if size <= target_kb * 1024:
            best_q, best_size = mid, size
            # try to push quality a bit higher within target
            lo = mid + 1
        else:
            hi = mid - 1

    # If we never met target, best attempt is with lowest quality tried
    if best_size is None:
        # Ensure file saved at MIN_QUALITY
        best_size = save_webp_with_quality(img, out_path, MIN_QUALITY)
        best_q = MIN_QUALITY

    return best_q, best_size

def convert_folder():
    ensure_dirs()
    files = []
    for ext in ("*.jpg", "*.jpeg"):
        files.extend(SOURCE_DIR.glob(ext))

    if not files:
        print("No .jpg/.jpeg files found in 'inputs/'.")
        return

    for f in files:
        out = DEST_DIR / f.with_suffix(".webp").name

        # original size
        orig_size = f.stat().st_size
        img = load_and_prepare(f)

        final_q, final_size = target_size_save(img, out, TARGET_KB)

        print(
            f"✔ {f.name:35s}  "
            f"→ {out.name:35s}  "
            f"{orig_size/1024:.0f}KB → {final_size/1024:.0f}KB  "
            f"(q={final_q})"
        )

if __name__ == "__main__":
    convert_folder()

import os
import base64
from PIL import Image

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_webp_to_jpg(image_path):
    """
    如果是 .webp，就轉成 .jpg，並回傳新的路徑。
    如果不是 .webp，直接回傳原路徑。
    """
    ext = os.path.splitext(image_path)[1].lower()
    if ext != ".webp":
        return image_path

    jpg_path = os.path.splitext(image_path)[0] + ".jpg"

    try:
        with Image.open(image_path) as img:
            # 某些 webp 可能有透明背景，先轉成 RGB
            rgb_img = img.convert("RGB")
            rgb_img.save(jpg_path, "JPEG", quality=95)

        # 刪掉原本的 webp，避免 uploads 越堆越多
        if os.path.exists(image_path):
            os.remove(image_path)

        return jpg_path

    except Exception as e:
        print(f"WEBP 轉 JPG 失敗: {e}")
        return image_path


def encode_image_base64(image_path):
    try:
        mime_type = "image/jpeg"
        if image_path.lower().endswith(".png"):
            mime_type = "image/png"

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return {
            "inlineData": {
                "mimeType": mime_type,
                "data": encoded
            }
        }
    except Exception as e:
        print(f"圖片編碼失敗: {e}")
        return None


def clean_temp_files(paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"刪除暫存檔失敗 {path}: {e}")
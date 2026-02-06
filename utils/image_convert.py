import logging
import os
import tempfile
from typing import Optional, Tuple

logger = logging.getLogger("ImageConvert")


def ensure_jpg(image_path: str, quality: int = 92) -> Tuple[str, bool]:
    """
    确保图片为 JPG/JPEG。

    - 若已是 JPG/JPEG：返回原路径，cleanup=False
    - 若为其它格式且可转换：生成临时 .jpg 文件，返回新路径，cleanup=True
    - 若无法转换：返回原路径，cleanup=False
    """
    if not image_path:
        return image_path, False

    _, ext = os.path.splitext(image_path)
    ext = (ext or "").lower()
    if ext in {".jpg", ".jpeg"}:
        return image_path, False

    try:
        from PIL import Image
    except Exception:
        logger.warning("未安装 Pillow，跳过图片转 JPG")
        return image_path, False

    try:
        fd, out_path = tempfile.mkstemp(prefix="cep_img_", suffix=".jpg")
        os.close(fd)

        with Image.open(image_path) as img:
            try:
                img.load()
            except Exception:
                pass

            if getattr(img, "is_animated", False):
                try:
                    img.seek(0)
                except Exception:
                    pass

            if img.mode in ("RGBA", "LA") or ("transparency" in getattr(img, "info", {})):
                background = Image.new("RGB", img.size, (255, 255, 255))
                alpha = img.split()[-1] if img.mode in ("RGBA", "LA") else None
                background.paste(img.convert("RGBA"), mask=alpha)
                out_img = background
            else:
                out_img = img.convert("RGB") if img.mode != "RGB" else img

            out_img.save(out_path, format="JPEG", quality=quality, optimize=True)

        return out_path, True
    except Exception as e:
        logger.error(f"图片转 JPG 失败: {image_path} ({e})")
        try:
            if "out_path" in locals() and out_path and os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        return image_path, False


def cleanup_temp_file(path: Optional[str], cleanup: bool):
    if not cleanup or not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


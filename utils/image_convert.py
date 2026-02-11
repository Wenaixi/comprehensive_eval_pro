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


def compress_image(image_path: str, max_size_mb: float = 1.0, is_captcha: bool = False) -> Tuple[str, bool]:
    """
    智能压缩图片至指定大小（默认 1MB）。性能优化版：减少重复 IO。
    """
    if not image_path or not os.path.exists(image_path):
        return image_path, False

    # 1. 确保是 JPG
    curr_path, cleanup = ensure_jpg(image_path)
    
    try:
        from PIL import Image
        import io
    except ImportError:
        return curr_path, cleanup

    max_bytes = max_size_mb * 1024 * 1024
    
    def get_size(p):
        return os.path.getsize(p)

    try:
        # 即使文件很小，也要检查是否损坏
        with Image.open(curr_path) as verify_img:
            verify_img.verify()
        
        with Image.open(curr_path) as img:
            img.load()
            
            if get_size(curr_path) <= max_bytes:
                return curr_path, cleanup

            # 2. 内存中寻找最佳质量参数
            best_q = 92
            buf = io.BytesIO()
            for q in [80, 60, 40]:
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=q, optimize=True)
                if buf.tell() <= max_bytes:
                    best_q = q
                    break
                best_q = q 

            # 3. 如果质量调整后还超标，且非验证码，进行内存缩放
            final_img_data = buf.getvalue()
            if buf.tell() > max_bytes and not is_captcha:
                scale = 0.9
                while scale > 0.1:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    if new_size[0] < 10 or new_size[1] < 10:
                        break
                    with img.resize(new_size, Image.Resampling.LANCZOS) as temp_img:
                        buf = io.BytesIO()
                        temp_img.save(buf, format="JPEG", quality=best_q, optimize=True)
                        if buf.tell() <= max_bytes:
                            final_img_data = buf.getvalue()
                            break
                    scale *= 0.7 
                if scale <= 0.1:
                    final_img_data = buf.getvalue()

            # 4. 最终一次性 IO 写入
            fd, out_path = tempfile.mkstemp(prefix="cep_comp_", suffix=".jpg")
            os.close(fd)
            with open(out_path, "wb") as f:
                f.write(final_img_data)
            
            # 清理旧的临时文件
            if cleanup:
                cleanup_temp_file(curr_path, True)
                
            return out_path, True

    except Exception as e:
        logger.error(f"图片压缩异常: {e}")
        # 如果报错了，如果是 ensure_jpg 生成的临时文件也要清理，防止残留
        if cleanup:
            cleanup_temp_file(curr_path, True)
        return None, False


def cleanup_temp_file(path: Optional[str], cleanup: bool):
    if not cleanup or not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


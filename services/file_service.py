import os
import logging
import requests
from typing import Optional

from comprehensive_eval_pro.utils.http_client import request_json
from comprehensive_eval_pro.utils.image_convert import cleanup_temp_file, ensure_jpg

logger = logging.getLogger("FileService")

class ProFileService:
    """
    专业的图片上传服务
    """
    def __init__(self, session: requests.Session = None, upload_url: str = None):
        # 图片服务器与业务服务器独立，实战证明不需要 Token
        self.session = session or requests.Session()
        # 修正：必须携带 bussinessType 和 groupName 参数
        self.upload_url = upload_url or "http://doc.nazhisoft.com/common/upload/uploadImage?bussinessType=12&groupName=other"

    def upload_image(self, file_path: str) -> Optional[int]:
        """
        上传图片并返回图片ID (整数)
        """
        if not os.path.exists(file_path):
            logger.error(f"图片不存在: {file_path}")
            return None

        upload_path, cleanup = ensure_jpg(file_path)
        try:
            logger.info(f"正在上传图片: {os.path.basename(upload_path)}")
            with open(upload_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(upload_path), f, 'image/jpeg')
                }
                
                # 图片服务器是独立的，清理掉可能干扰的业务 Header
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                
                res = request_json(self.session, "POST", self.upload_url, files=files, headers=headers, timeout=30, logger=logger)
                if not isinstance(res, dict):
                    logger.error("图片服务器返回了非 JSON 或空数据")
                    return None

                if res.get('code') == 1:
                    # 关键：提取返回的 ID，对齐 pictureList 要求
                    ret_data = res.get('returnData', {})
                    img_id = ret_data.get('id')
                    if img_id:
                        logger.info(f"图片上传成功，获取 ID: {img_id}")
                        return int(img_id)
                
                logger.error(f"图片上传失败: {res.get('msg')}")
        except Exception as e:
            logger.error(f"图片上传异常: {e}")
        finally:
            cleanup_temp_file(upload_path, cleanup)
        
        return None

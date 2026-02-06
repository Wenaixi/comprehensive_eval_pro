import os
import logging

logger = logging.getLogger(__name__)

class ExcelParser:
    """
    专门解析班会记录 Excel 文件的工具类
    """
    @staticmethod
    def extract_text_from_xls(file_path):
        """
        从 .xls 文件中提取所有非空文本内容
        :param file_path: 文件路径
        :return: 拼接后的完整文本
        """
        if not os.path.exists(file_path):
            logger.error(f"Excel 文件不存在: {file_path}")
            return ""
        
        try:
            import pandas as pd
            # 使用 xlrd 引擎读取旧版 xls
            df = pd.read_excel(file_path, engine='xlrd')
            text_parts = []
            
            # 遍历所有单元格提取文本
            for _, row in df.iterrows():
                for val in row:
                    if pd.notna(val):
                        # 清理空白字符并加入列表
                        clean_val = str(val).strip()
                        if clean_val:
                            text_parts.append(clean_val)
            
            # 合并文本，作为 AI 总结的上下文
            return "\n".join(text_parts)
        except ImportError:
            logger.error("未安装 pandas/xlrd，无法解析 .xls。请安装后重试。")
            return ""
        except Exception as e:
            logger.error(f"解析 Excel 失败 ({file_path}): {e}")
            return ""

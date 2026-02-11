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
        从 Excel 文件中提取所有非空文本内容 (支持 .xls 和 .xlsx)
        :param file_path: 文件路径
        :return: 拼接后的完整文本
        """
        if not os.path.exists(file_path):
            logger.error(f"Excel 文件不存在: {file_path}")
            return ""
        
        try:
            import pandas as pd
            # 根据后缀名选择引擎
            if file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
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
        except ImportError as e:
            logger.error(f"未安装必要的依赖库，无法解析 Excel: {e}")
            return ""
        except Exception as e:
            logger.error(f"解析 Excel 失败 ({file_path}): {e}")
            return ""

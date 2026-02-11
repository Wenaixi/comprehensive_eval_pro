import logging
import os
from .excel_parser import ExcelParser

logger = logging.getLogger("RecordParser")


def extract_text_from_excel(file_path: str) -> str:
    """
    通过 ExcelParser 提取文本内容
    """
    try:
        return ExcelParser.extract_text_from_xls(file_path)
    except Exception as e:
        logger.error(f"提取 Excel 文本失败 ({file_path}): {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return (f.read() or "").strip()
    except Exception as e:
        logger.error(f"读取文本失败 ({file_path}): {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    try:
        import docx  # type: ignore
    except Exception:
        logger.error("未安装 python-docx，无法解析 .docx。请安装后重试：pip install python-docx")
        return ""

    try:
        doc = docx.Document(file_path)
        parts = []
        for p in doc.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts).strip()
    except Exception as e:
        logger.error(f"解析 docx 失败 ({file_path}): {e}")
        return ""


def extract_text_from_doc(file_path: str) -> str:
    try:
        import textract  # type: ignore
    except Exception:
        logger.error("未安装 textract，无法解析 .doc。建议改为 .docx 或 .txt。")
        return ""

    try:
        data = textract.process(file_path)
        return (data.decode("utf-8", errors="ignore") if isinstance(data, (bytes, bytearray)) else str(data)).strip()
    except Exception as e:
        logger.error(f"解析 doc 失败 ({file_path}): {e}")
        return ""


def extract_text_from_file(file_path: str) -> str:
    ext = (os.path.splitext(file_path)[1] or "").lower()
    if ext in (".xls", ".xlsx"):
        return extract_text_from_excel(file_path)
    if ext == ".pdf":
        return "[PDF记录: 待视觉解析]"  # 让资源探测认为该文件包含有效内容
    if ext == ".txt":
        return extract_text_from_txt(file_path)
    if ext == ".docx":
        return extract_text_from_docx(file_path)
    if ext == ".doc":
        return extract_text_from_doc(file_path)
    return ""


def extract_first_record_text(folder: str) -> tuple[str, str | None]:
    """
    尝试从文件夹中提取记录文本。
    优先级: Excel > TXT > Word
    注意: 不再支持 PDF 直接提取文本，PDF 将作为图片由视觉模型处理。
    """
    if not folder or not os.path.isdir(folder):
        return "", None

    files = []
    try:
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if os.path.isfile(path):
                files.append(path)
    except Exception:
        return "", None

    ext_order = [
        (".xls", ".xlsx"),
        (".docx", ".doc"),
        (".txt",),
        (".pdf",),  # PDF 作为最后的视觉垫底手段
    ]

    for exts in ext_order:
        candidates = [p for p in files if (os.path.splitext(p)[1] or "").lower() in exts]
        candidates.sort()
        for p in candidates:
            text = extract_text_from_file(p)
            if text:
                return text, p

    return "", None


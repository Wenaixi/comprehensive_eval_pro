import logging
import os

logger = logging.getLogger("RecordParser")


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


def extract_text_from_pdf(file_path: str) -> str:
    try:
        import PyPDF2  # type: ignore
    except Exception:
        logger.error("未安装 PyPDF2，无法解析 PDF。请安装后重试：pip install PyPDF2")
        return ""

    try:
        parts = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = (page.extract_text() or "").strip()
                if t:
                    parts.append(t)
        return "\n".join(parts).strip()
    except Exception as e:
        logger.error(f"解析 PDF 失败 ({file_path}): {e}")
        return ""


def extract_text_from_excel(file_path: str) -> str:
    ext = (os.path.splitext(file_path)[1] or "").lower()
    if ext == ".xls":
        from comprehensive_eval_pro.utils.excel_parser import ExcelParser

        return ExcelParser.extract_text_from_xls(file_path)

    try:
        import pandas as pd  # type: ignore
    except Exception:
        logger.error("未安装 pandas，无法解析 Excel。")
        return ""

    try:
        df = pd.read_excel(file_path)
        parts = []
        for _, row in df.iterrows():
            for val in row:
                try:
                    if pd.notna(val):
                        t = str(val).strip()
                        if t:
                            parts.append(t)
                except Exception:
                    continue
        return "\n".join(parts).strip()
    except Exception as e:
        logger.error(f"解析 Excel 失败 ({file_path}): {e}")
        return ""


def extract_text_from_file(file_path: str) -> str:
    ext = (os.path.splitext(file_path)[1] or "").lower()
    if ext in (".xls", ".xlsx"):
        return extract_text_from_excel(file_path)
    if ext == ".txt":
        return extract_text_from_txt(file_path)
    if ext == ".docx":
        return extract_text_from_docx(file_path)
    if ext == ".doc":
        return extract_text_from_doc(file_path)
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    return ""


def extract_first_record_text(folder: str) -> tuple[str, str | None]:
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
        (".txt",),
        (".docx", ".doc"),
        (".pdf",),
    ]

    for exts in ext_order:
        candidates = [p for p in files if (os.path.splitext(p)[1] or "").lower() in exts]
        candidates.sort()
        for p in candidates:
            text = extract_text_from_file(p)
            if text:
                return text, p

    return "", None


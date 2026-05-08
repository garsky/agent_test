from __future__ import annotations

import tempfile
from pathlib import Path

from config.settings import settings


SUPPORTED_SOURCE_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
DIRECT_EXTENSIONS = {".md", ".txt"}


def _decrypt_pdf(source_path: Path, password: str) -> Path | None:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(source_path))
    if not reader.is_encrypted:
        return source_path

    result = reader.decrypt(password)
    if result == 0:
        return None

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    tmp_dir = tempfile.mkdtemp(prefix="cda_decrypted_")
    tmp_path = Path(tmp_dir) / source_path.name
    with open(str(tmp_path), "wb") as f:
        writer.write(f)

    return tmp_path


def _get_pdf_passwords() -> list[str]:
    passwords = [""]
    default_pwd = getattr(settings, "PDF_DEFAULT_PASSWORD", "")
    if default_pwd:
        passwords.append(default_pwd)
    return passwords


def convert_to_markdown(source_path: Path) -> tuple[str, str]:
    from markitdown import MarkItDown

    actual_path = source_path
    decrypted_tmp = None

    if source_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(source_path))
            if reader.is_encrypted:
                passwords = _get_pdf_passwords()
                decrypted = None
                for pwd in passwords:
                    decrypted = _decrypt_pdf(source_path, pwd)
                    if decrypted:
                        pwd_display = "空密码(仅权限限制)" if pwd == "" else f"{'*'*len(pwd)}"
                        print(f"  已解密: {source_path.name} (密码: {pwd_display})")
                        break
                if decrypted:
                    actual_path = decrypted
                    decrypted_tmp = decrypted
                else:
                    print(f"  警告: {source_path.name} 解密失败，尝试所有已知密码均无效")
        except ImportError:
            pass

    md = MarkItDown()
    result = md.convert(str(actual_path))

    if decrypted_tmp and decrypted_tmp != source_path:
        try:
            decrypted_tmp.unlink()
            decrypted_tmp.parent.rmdir()
        except Exception:
            pass

    return result.text_content, source_path.stem + ".md"


def is_convertible(filepath: Path) -> bool:
    return filepath.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS


def is_direct(filepath: Path) -> bool:
    return filepath.suffix.lower() in DIRECT_EXTENSIONS


def get_target_md_path(source_path: Path, docs_dir: Path) -> Path:
    md_name = source_path.stem + ".md"
    return docs_dir / md_name


def process_file(source_path: Path, docs_dir: Path) -> Path | None:
    docs_dir.mkdir(parents=True, exist_ok=True)

    if is_direct(source_path):
        import shutil
        dst = docs_dir / source_path.name
        shutil.copy2(str(source_path), str(dst))
        return dst

    if is_convertible(source_path):
        print(f"  正在转换: {source_path.name} -> Markdown...")
        try:
            md_content, md_filename = convert_to_markdown(source_path)
            if not md_content or not md_content.strip():
                print(f"  警告: {source_path.name} 转换结果为空")
                return None
            dst = docs_dir / md_filename
            dst.write_text(md_content, encoding="utf-8")
            print(f"  已转换: {source_path.name} -> {md_filename} ({len(md_content):,} 字符)")
            return dst
        except Exception as e:
            print(f"  转换失败: {source_path.name}: {e}")
            return None

    return None

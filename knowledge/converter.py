from __future__ import annotations

from pathlib import Path


SUPPORTED_SOURCE_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
DIRECT_EXTENSIONS = {".md", ".txt"}


def convert_to_markdown(source_path: Path) -> tuple[str, str]:
    from markitdown import MarkItDown

    md = MarkItDown()
    result = md.convert(str(source_path))
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

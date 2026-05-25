"""File system tools for the AI assistant. All paths are confined to the data/ folder."""

from __future__ import annotations

from datetime import date
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
SNIPPET_RADIUS = 80

# Project root is the directory containing this file; sandbox is data/
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = (PROJECT_ROOT / "data").resolve()


def _success(**fields):
    return {"success": True, **fields}


def _failure(error: str):
    return {"success": False, "error": error}


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes}B"
    if num_bytes < 1024 * 1024:
        return f"{round(num_bytes / 1024)}KB"
    return f"{round(num_bytes / (1024 * 1024), 1)}MB"


def _resolve_path(filepath: str) -> Path | None:
    """Resolve a user path inside DATA_ROOT. Returns None if outside sandbox."""
    if not filepath or not filepath.strip():
        return None

    raw = Path(filepath)
    # Normalize: paths may be "resumes/john.pdf" or "data/resumes/john.pdf"
    parts = raw.parts
    if parts and parts[0].lower() == "data":
        raw = Path(*parts[1:]) if len(parts) > 1 else Path(".")

    candidate = (DATA_ROOT / raw).resolve()
    try:
        candidate.relative_to(DATA_ROOT)
    except ValueError:
        return None
    return candidate


def _metadata(path: Path) -> dict:
    stat = path.stat()
    return {
        "filename": path.name,
        "size": _format_size(stat.st_size),
        "extension": path.suffix.lower(),
        "modified": date.fromtimestamp(stat.st_mtime).isoformat(),
    }


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _read_txt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8 text: {path.name}") from exc


def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)
    if ext == ".txt":
        return _read_txt(path)
    raise ValueError(f"Unsupported extension: {ext}")


def _snippet(text: str, keyword: str) -> str:
    lower = text.lower()
    key = keyword.lower()
    idx = lower.find(key)
    if idx == -1:
        return ""
    start = max(0, idx - SNIPPET_RADIUS)
    end = min(len(text), idx + len(keyword) + SNIPPET_RADIUS)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def read_file(filepath: str):
    try:
        path = _resolve_path(filepath)
        if path is None:
            return _failure(f"Access denied: path must be inside data/ ({filepath})")
        if not path.exists():
            return _failure(f"File not found: {filepath}")
        if not path.is_file():
            return _failure(f"Not a file: {filepath}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return _failure(f"Unsupported file type: {path.suffix}")

        content = _extract_text(path)
        return _success(content=content, metadata=_metadata(path))
    except Exception as exc:
        return _failure(str(exc))


def list_files(directory: str, extension: str | None = None):
    try:
        path = _resolve_path(directory or ".")
        if path is None:
            return _failure(f"Access denied: path must be inside data/ ({directory})")
        if not path.exists():
            return _failure(f"Directory not found: {directory}")
        if not path.is_dir():
            return _failure(f"Not a directory: {directory}")

        ext_filter = None
        if extension:
            ext_filter = extension.lower() if extension.startswith(".") else f".{extension.lower()}"

        files = []
        for entry in sorted(path.iterdir()):
            if not entry.is_file():
                continue
            if ext_filter and entry.suffix.lower() != ext_filter:
                continue
            files.append(
                {
                    "name": entry.name,
                    "size": _format_size(entry.stat().st_size),
                    "modified": date.fromtimestamp(entry.stat().st_mtime).isoformat(),
                }
            )
        return _success(files=files)
    except Exception as exc:
        return _failure(str(exc))


def write_file(filepath: str, content: str):
    try:
        if content is None:
            content = ""
        path = _resolve_path(filepath)
        if path is None:
            return _failure(f"Access denied: path must be inside data/ ({filepath})")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return _success(message="File created successfully")
    except PermissionError:
        return _failure(f"Permission denied: {filepath}")
    except Exception as exc:
        return _failure(str(exc))


def search_in_file(filepath: str, keyword: str):
    try:
        if not keyword or not keyword.strip():
            return _failure("Keyword is required")

        path = _resolve_path(filepath)
        if path is None:
            return _failure(f"Access denied: path must be inside data/ ({filepath})")
        if not path.exists():
            return _failure(f"File not found: {filepath}")
        if not path.is_file():
            return _failure(f"Not a file: {filepath}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return _failure(f"Unsupported file type: {path.suffix}")

        text = _extract_text(path)
        if keyword.lower() not in text.lower():
            return _success(matches=[])

        context = _snippet(text, keyword)
        return _success(
            matches=[{"keyword": keyword, "context": context}]
        )
    except Exception as exc:
        return _failure(str(exc))

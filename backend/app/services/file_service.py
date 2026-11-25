"""Upload validation and document text extraction.

No files are written to disk — everything is processed in memory from
``io.BytesIO``, which eliminates path traversal and temp-file cleanup
concerns entirely.
"""

import os
import zipfile
from io import BytesIO
from xml.etree import ElementTree

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
DOC_EXTENSIONS = {"pdf", "docx", "txt"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | DOC_EXTENSIONS

_MIME_BY_EXT = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}

_DOCX_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class UploadRejected(Exception):
    """Raised for 4xx upload problems."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def sanitize_filename(raw: str | None) -> str:
    name = os.path.basename((raw or "file").replace("\\", "/")).strip() or "file"
    return name[:255]


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _sniff_image(data: bytes, ext: str) -> str:
    """Verify magic bytes match the claimed image type; return mime."""
    if ext in ("jpg", "jpeg"):
        ok = data[:3] == b"\xff\xd8\xff"
    elif ext == "png":
        ok = data[:8] == b"\x89PNG\r\n\x1a\n"
    else:  # webp
        ok = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if not ok:
        raise UploadRejected(422, f"file content is not a valid {ext} image")
    return _MIME_BY_EXT[ext]


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages).strip()
    except UploadRejected:
        raise
    except Exception as exc:
        raise UploadRejected(422, "could not read PDF file") from exc


def _extract_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            if "word/document.xml" not in z.namelist():
                raise UploadRejected(422, "not a valid DOCX file")
            xml = z.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        paragraphs = []
        for p in root.iter(f"{_DOCX_W_NS}p"):
            line = "".join(t.text or "" for t in p.iter(f"{_DOCX_W_NS}t")).strip()
            if line:
                paragraphs.append(line)
        return "\n".join(paragraphs).strip()
    except UploadRejected:
        raise
    except Exception as exc:
        raise UploadRejected(422, "could not read DOCX file") from exc


def _extract_txt(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise UploadRejected(422, "text file is not valid UTF-8") from exc


def extract_document_text(data: bytes, ext: str) -> str:
    if ext == "pdf":
        text = _extract_pdf(data)
    elif ext == "docx":
        text = _extract_docx(data)
    else:
        text = _extract_txt(data)
    if not text:
        raise UploadRejected(422, "document contains no extractable text")
    return text


def classify_upload(filename: str, data: bytes, max_doc_chars: int) -> dict:
    """Validate an upload and return attachment fields.

    Returns dict with: filename, mime_type, kind, extracted_text (docs),
    truncated flag is encoded in extracted_text itself.
    Raises UploadRejected(422|413) on any problem.
    """
    name = sanitize_filename(filename)
    ext = _extension(name)
    if ext not in SUPPORTED_EXTENSIONS:
        raise UploadRejected(
            422,
            f"unsupported file type '.{ext or name}'; supported: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS)),
        )
    if not data:
        raise UploadRejected(422, "empty file")

    if ext in IMAGE_EXTENSIONS:
        mime = _sniff_image(data, ext)
        return {"filename": name, "mime_type": mime, "kind": "image", "extracted_text": None}

    text = extract_document_text(data, ext)
    if len(text) > max_doc_chars:
        text = (
            text[:max_doc_chars]
            + f"\n\n[document truncated: first {max_doc_chars} characters shown]"
        )
    return {
        "filename": name,
        "mime_type": _MIME_BY_EXT[ext],
        "kind": "document",
        "extracted_text": text,
    }

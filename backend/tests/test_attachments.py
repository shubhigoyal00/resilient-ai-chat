"""Multimodal tests: uploads, chat with attachments, cache/fallback parity."""

import zipfile
from io import BytesIO

import litellm

from app.config import get_settings
from tests.conftest import make_model_response, post_chat, upload
from tests.test_api import make_acompletion_fake

PNG = b"\x89PNG\r\n\x1a\n" + b"\x89" * 128  # valid PNG signature + payload
PNG_2 = b"\x89PNG\r\n\x1a\n" + b"\x77" * 128
JPEG = b"\xff\xd8\xff\xe0" + b"\x10" * 64
WEBP = b"RIFF" + b"\x20\x00\x00\x00" + b"WEBP" + b"\x00" * 32


def make_pdf(text: bytes = b"Hello PDF World") -> bytes:
    """Minimal valid PDF (with xref table) containing one text object."""
    stream = b"BT /F1 24 Tf 100 700 Td (" + text + b") Tj ET"
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(stream)).encode() + b">>\nstream\n"
        + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out = BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj".encode() + obj + b"\nendobj\n")
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(
        f"trailer<</Size {len(objects) + 1}/Root 1 0 R>>\n"
        f"startxref\n{xref_pos}\n%%EOF".encode()
    )
    return out.getvalue()


def make_docx(text: str = "Hello DOCX World") -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main"><w:body>'
            f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
            "</w:body></w:document>",
        )
    return buf.getvalue()


def upload_ok(client, session_id, filename, data, content_type):
    r = upload(client, session_id, filename, data, content_type)
    assert r.status_code == 201, r.text
    return r.json()


class TestUploadValidation:
    def test_image_uploads(self, client):
        for fname, data, ct in [
            ("a.png", PNG, "image/png"),
            ("b.jpg", JPEG, "image/jpeg"),
            ("c.webp", WEBP, "image/webp"),
        ]:
            body = upload_ok(client, "s-up", fname, data, ct)
            assert body["kind"] == "image"
            assert body["mime_type"] == ct
            assert body["filename"] == fname

    def test_document_uploads(self, client):
        pdf = upload_ok(client, "s-doc", "r.pdf", make_pdf(), "application/pdf")
        assert pdf["kind"] == "document"
        docx = upload_ok(
            client,
            "s-doc",
            "d.docx",
            make_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        assert docx["kind"] == "document"
        txt = upload_ok(client, "s-doc", "n.txt", b"plain text here", "text/plain")
        assert txt["kind"] == "document"
        assert txt["text_chars"] > 0

    def test_unsupported_extension(self, client):
        r = upload(client, "s-up", "evil.exe", b"MZ\x90\x00", "application/x-dosexec")
        assert r.status_code == 422
        assert "unsupported file type" in r.json()["detail"]

    def test_fake_image_content(self, client):
        r = upload(client, "s-up", "fake.png", b"not an image", "image/png")
        assert r.status_code == 422

    def test_oversized_file(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "max_upload_mb", 0.00005)  # ~52 bytes
        r = upload(client, "s-up", "big.png", PNG, "image/png")
        assert r.status_code == 413
        assert "file too large" in r.json()["detail"]

    def test_empty_file(self, client):
        r = upload(client, "s-up", "empty.txt", b"", "text/plain")
        assert r.status_code == 422

    def test_unreadable_document(self, client):
        r = upload(client, "s-up", "broken.pdf", b"%PDF-garbage", "application/pdf")
        assert r.status_code == 422

    def test_pdf_with_no_text(self, client):
        r = upload(client, "s-up", "blank.pdf", make_pdf(b" "), "application/pdf")
        assert r.status_code == 422

    def test_invalid_session_id_on_upload(self, client):
        r = upload(client, " ", "a.png", PNG, "image/png")
        assert r.status_code == 422

    def test_raw_attachment_endpoint(self, client):
        body = upload_ok(client, "s-raw", "a.png", PNG, "image/png")
        r = client.get(f"/attachments/{body['attachment_id']}/raw")
        assert r.status_code == 200
        assert r.content == PNG
        assert r.headers["content-type"].startswith("image/png")

    def test_raw_attachment_404(self, client):
        assert client.get("/attachments/nope/raw").status_code == 404
        # documents have no raw content
        doc = upload_ok(client, "s-raw", "n.txt", b"hello", "text/plain")
        assert client.get(f"/attachments/{doc['attachment_id']}/raw").status_code == 404


class TestMultimodalChat:
    def test_image_sent_as_multimodal_parts(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        att = upload_ok(client, "s-img", "shot.png", PNG, "image/png")
        r = post_chat(client, session_id="s-img", message="Explain this image",
                      attachment_ids=[att["attachment_id"]])
        assert r.status_code == 200
        content = recorded[-1]["messages"][-1]["content"]
        assert isinstance(content, list)
        assert content[0] == {"type": "text", "text": "Explain this image"}
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")

    def test_document_text_injected_as_context(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        att = upload_ok(client, "s-doc", "n.txt", b"The secret is 42.", "text/plain")
        post_chat(client, session_id="s-doc", message="What is the secret?",
                  attachment_ids=[att["attachment_id"]])
        content = recorded[-1]["messages"][-1]["content"]
        assert content[0]["text"] == "What is the secret?"
        assert "[Document: n.txt]" in content[1]["text"]
        assert "The secret is 42." in content[1]["text"]

    def test_unknown_attachment_id(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        r = post_chat(client, session_id="s-x", message="hi", attachment_ids=["bad-id"])
        assert r.status_code == 422

    def test_attachment_from_other_session_rejected(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        att = upload_ok(client, "s-owner", "a.png", PNG, "image/png")
        r = post_chat(client, session_id="s-other", message="hi",
                      attachment_ids=[att["attachment_id"]])
        assert r.status_code == 422

    def test_attachment_stays_in_history(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        att = upload_ok(client, "s-hist", "a.png", PNG, "image/png")
        post_chat(client, session_id="s-hist", message="look",
                  attachment_ids=[att["attachment_id"]])
        post_chat(client, session_id="s-hist", message="and now?")
        history = recorded[-1]["messages"]
        first_user = history[1]
        assert isinstance(first_user["content"], list)
        assert first_user["content"][1]["type"] == "image_url"

    def test_attachment_metadata_stored(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        att = upload_ok(client, "s-meta", "a.png", PNG, "image/png")
        post_chat(client, session_id="s-meta", message="look",
                  attachment_ids=[att["attachment_id"]])
        msgs = client.get("/sessions/s-meta/messages").json()
        assert msgs[0]["metadata"]["attachments"][0]["filename"] == "a.png"
        assert msgs[0]["metadata"]["attachments"][0]["kind"] == "image"

    def test_multimodal_fallback(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        att = upload_ok(client, "s-mfb", "a.png", PNG, "image/png")
        r = post_chat(client, session_id="s-mfb", message="look",
                      attachment_ids=[att["attachment_id"]],
                      headers={"X-Simulate-Failure": "key_1=429"})
        assert r.status_code == 200
        assert r.json()["metadata"]["key_id"] == "key_2"
        assert r.json()["metadata"]["fallback_attempts"] == 1

    def test_multimodal_all_fail_not_stored(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        att = upload_ok(client, "s-mfail", "a.png", PNG, "image/png")
        r = post_chat(client, session_id="s-mfail", message="look",
                      attachment_ids=[att["attachment_id"]],
                      headers={"X-Simulate-Failure": "*=503"})
        assert r.status_code == 503
        assert client.get("/sessions/s-mfail/messages").status_code == 404


class TestMultimodalCache:
    def test_identical_image_request_hits_cache(self, client, provider_spy):
        a1 = upload_ok(client, "s-c1", "a.png", PNG, "image/png")
        r1 = post_chat(client, session_id="s-c1", message="Explain",
                       attachment_ids=[a1["attachment_id"]])
        assert r1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

        a2 = upload_ok(client, "s-c2", "a.png", PNG, "image/png")
        r2 = post_chat(client, session_id="s-c2", message="Explain",
                       attachment_ids=[a2["attachment_id"]])
        meta = r2.json()["metadata"]
        assert meta["resolution_source"] == "LLM_CACHE"
        assert meta["key_id"] is None
        assert len(provider_spy) == 1

    def test_different_image_misses_cache(self, client, provider_spy):
        a1 = upload_ok(client, "s-d1", "a.png", PNG, "image/png")
        post_chat(client, session_id="s-d1", message="Explain",
                  attachment_ids=[a1["attachment_id"]])
        a2 = upload_ok(client, "s-d2", "b.png", PNG_2, "image/png")
        r2 = post_chat(client, session_id="s-d2", message="Explain",
                       attachment_ids=[a2["attachment_id"]])
        assert r2.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert len(provider_spy) == 2

    def test_image_and_text_only_do_not_share_cache(self, client, provider_spy):
        a1 = upload_ok(client, "s-t1", "a.png", PNG, "image/png")
        post_chat(client, session_id="s-t1", message="Explain",
                  attachment_ids=[a1["attachment_id"]])
        # Same text, no attachment -> different payload -> must miss.
        r2 = post_chat(client, session_id="s-t2", message="Explain")
        assert r2.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert len(provider_spy) == 2

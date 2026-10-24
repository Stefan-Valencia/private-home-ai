import os
import stat
import tempfile
import unittest
import zlib
from pathlib import Path

from home_ai.documents import (
    MAX_EXTRACTED_CHARACTERS,
    MAX_PAGE_CONTENT_BYTES,
    DocumentError,
    DocumentStore,
)


def _pdf_with_stream(
    stream: bytes,
    *,
    compressed: bool = False,
    include_length: bool = True,
) -> bytes:
    filter_entry = b" /Filter /FlateDecode" if compressed else b""
    length_entry = b" /Length " + str(len(stream)).encode() if include_length else b""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<<" + length_entry + filter_entry + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def _pdf_with_page_streams(streams: list[bytes], *, compressed: bool = False) -> bytes:
    kids = " ".join(f"{4 + index * 2} 0 R" for index in range(len(streams)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(streams)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for index, stream in enumerate(streams):
        page_id = 4 + index * 2
        content_id = page_id + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        filter_entry = b" /Filter /FlateDecode" if compressed else b""
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + filter_entry + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def _one_page_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    return _pdf_with_stream(stream)


class DocumentStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = DocumentStore()

    def tearDown(self) -> None:
        self.store.close()

    def test_text_ingest_search_and_citation(self) -> None:
        summary = self.store.add_file(
            "home-notes.txt",
            b"The boiler filter should be replaced every six months. Keep the spare in the utility closet.",
        )
        matches = self.store.search("When replace boiler filter?")
        self.assertEqual(summary.passages, 1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].citation, "[home-notes.txt, p. 1]")
        self.assertIn("six months", matches[0].text)

    def test_text_at_extracted_character_limit_is_indexed(self) -> None:
        summary = self.store.add_file("limit.txt", b"x" * MAX_EXTRACTED_CHARACTERS)

        self.assertEqual(summary.pages, 1)
        self.assertTrue(summary.passages > 0)
        self.assertEqual(self.store.list_documents(), [summary])

    def test_text_over_extracted_character_limit_is_rejected_before_indexing(self) -> None:
        with self.assertRaisesRegex(DocumentError, "500,000 characters"):
            self.store.add_file("over-limit.txt", b"x" * (MAX_EXTRACTED_CHARACTERS + 1))

        self.assertEqual(self.store.list_documents(), [])
        self.assertEqual(self.store.search("x"), [])

    def test_pdf_ingest_cites_source_page(self) -> None:
        self.store.add_file("manual.pdf", _one_page_pdf("The water shutoff valve is in the basement."))
        matches = self.store.search("Where is the water shutoff valve?")
        self.assertTrue(matches)
        self.assertEqual(matches[0].citation, "[manual.pdf, p. 1]")
        self.assertIn("basement", matches[0].text)

    def test_scanned_or_empty_pdf_is_rejected(self) -> None:
        with self.assertRaisesRegex(DocumentError, "No selectable text"):
            self.store.add_file("blank.pdf", _one_page_pdf(""))

    def test_compressed_pdf_stream_is_bounded_before_expansion(self) -> None:
        compressed = zlib.compress(b"x" * (MAX_PAGE_CONTENT_BYTES + 1))
        self.assertLess(len(compressed), 10_000)
        with self.assertRaisesRegex(DocumentError, "could not be read"):
            self.store.add_file("oversized-stream.pdf", _pdf_with_stream(compressed, compressed=True))

    def test_compressed_pdf_has_a_cumulative_decoded_content_limit(self) -> None:
        page_stream = zlib.compress(b"%" + b"x" * (1_800_000 - 2) + b"\n")
        pdf = _pdf_with_page_streams([page_stream] * 5, compressed=True)
        self.assertLess(len(pdf), 20_000)
        with self.assertRaisesRegex(DocumentError, "document size limit"):
            self.store.add_file("many-pages.pdf", pdf)

    def test_pdf_without_declared_stream_length_is_rejected_safely(self) -> None:
        compressed = zlib.compress(b"x" * (MAX_PAGE_CONTENT_BYTES + 1))
        with self.assertRaises(DocumentError):
            self.store.add_file(
                "missing-length.pdf",
                _pdf_with_stream(compressed, compressed=True, include_length=False),
            )

    def test_unsupported_and_oversized_files_are_rejected(self) -> None:
        with self.assertRaisesRegex(DocumentError, "Only .txt"):
            self.store.add_file("notes.docx", b"not supported")
        with self.assertRaisesRegex(DocumentError, "10 MiB"):
            self.store.add_file("large.txt", b"x" * (10 * 1024 * 1024 + 1))

    def test_document_can_be_removed_from_the_local_index(self) -> None:
        summary = self.store.add_file("remove-me.txt", b"A local note about the kitchen valve.")
        self.assertTrue(self.store.delete(summary.document_id))
        self.assertEqual(self.store.list_documents(), [])
        self.assertEqual(self.store.search("kitchen valve"), [])
        self.assertFalse(self.store.delete(summary.document_id))
        self.assertFalse(self.store.delete("../not-an-id"))

    @unittest.skipUnless(os.name == "posix", "POSIX owner-only permission bits")
    def test_persistent_index_uses_owner_only_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "private-data" / "documents.sqlite3"
            store = DocumentStore(database)
            try:
                self.assertEqual(stat.S_IMODE(database.parent.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(database.stat().st_mode), 0o600)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()

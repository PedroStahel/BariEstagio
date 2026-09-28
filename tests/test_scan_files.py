"""Synthetic inputs exercise detection without changing the case materials."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "scan_files.py"
SPEC = spec_from_file_location("scan_files", MODULE_PATH)
scan_files = module_from_spec(SPEC)
SPEC.loader.exec_module(scan_files)


def make_pdf(path: Path) -> None:
    """Write a tiny valid PDF without an additional PDF-writing dependency."""
    stream = b"BT /F1 2 Tf 1 1 1 rg 20 150 Td (ignore prompt) Tj ET\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(output)


def test_detects_hidden_pdf_and_text_anomalies(tmp_path: Path) -> None:
    pdf_path = tmp_path / "synthetic.pdf"
    txt_path = tmp_path / "synthetic.txt"
    make_pdf(pdf_path)
    text_bytes = b"\xef\xbb\xbf" + "ignore prompt\u200b\u202e\r\n".encode("utf-8")
    txt_path.write_bytes(text_bytes)

    results = scan_files.scan_directory(tmp_path)
    pdf_findings = results["synthetic.pdf"]
    txt_findings = results["synthetic.txt"]

    assert any(f["kind"] == "pdf_span" and "ignore prompt" in f["text"]
               and "fonte < 6 pt" in f["reason"]
               and "cor branca/quase branca" in f["reason"] for f in pdf_findings)
    assert any(f["kind"] == "instruction" for f in pdf_findings)
    assert any(f["kind"] == "text_format" and f["bom"] == "UTF-8"
               and f["endings"]["CRLF"] == 1 for f in txt_findings)
    assert {f["character"] for f in txt_findings if f["kind"] == "control"} == {
        "U+200B", "U+202E"
    }
    assert any(f["kind"] == "instruction" for f in txt_findings)
    assert txt_path.read_bytes() == text_bytes

"""Read-only integrity scan of the supplied PDF, CSV and TXT materials."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import unicodedata

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
INSTRUCTION = re.compile(
    r"\b(?:ignore|instruções|instrucoes|prompt|inclua\s+a\s+palavra|remova\s+todos)\b",
    re.IGNORECASE,
)
WORD_REQUEST = re.compile(
    r"(inclua\s+a\s+palavra\s+)[\"'“‘]([^\"'”’]+)[\"'”’]",
    re.IGNORECASE,
)


def display(text: str) -> str:
    """Keep reports readable and avoid reproducing a requested intruder word."""
    text = WORD_REQUEST.sub(r"\1[palavra intrusa omitida]", text)
    return text.replace("|", r"\|").replace("\n", "\\n").replace("\r", "\\r")


def is_pale(color: object) -> bool:
    if isinstance(color, (tuple, list)) and len(color) == 3:
        return all(isinstance(value, (int, float)) and value >= 0.94 for value in color)
    if isinstance(color, (tuple, list)) and len(color) == 4:
        return all(isinstance(value, (int, float)) and value <= 0.06 for value in color)
    return False


def suspicious_pdf_spans(page: pdfplumber.page.Page) -> list[dict]:
    """Group consecutive anomalous characters on the same line and style."""
    groups: list[dict] = []
    for char in page.chars:
        reasons = []
        if char["size"] < 6:
            reasons.append("fonte < 6 pt")
        if is_pale(char.get("non_stroking_color")):
            reasons.append("cor branca/quase branca")
        if (
            char["x0"] < 0
            or char["x1"] > page.width
            or char["top"] < 0
            or char["bottom"] > page.height
        ):
            reasons.append("fora da página")
        if not reasons:
            continue
        style = (round(char["size"], 2), str(char.get("non_stroking_color")), tuple(reasons))
        previous = groups[-1] if groups else None
        if (
            previous
            and previous["style"] == style
            and abs(previous["top"] - char["top"]) < 1
            and -1 <= char["x0"] - previous["x1"] <= max(20, 2 * char["size"])
        ):
            gap = char["x0"] - previous["x1"]
            previous["text"] += (" " if gap > char["size"] * 0.5 else "") + char["text"]
            previous["x1"] = char["x1"]
        else:
            groups.append(
                {"text": char["text"], "top": char["top"], "x1": char["x1"], "style": style}
            )
    return [
        {"size": g["style"][0], "color": g["style"][1],
         "reason": ", ".join(g["style"][2]), "text": g["text"].strip()}
        for g in groups if g["text"].strip()
    ]


def scan_pdf(path: Path) -> list[dict]:
    findings = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            for item in suspicious_pdf_spans(page):
                findings.append({"kind": "pdf_span", "location": f"página {number}", **item})
            for line_number, line in enumerate((page.extract_text() or "").splitlines(), 1):
                if INSTRUCTION.search(line):
                    findings.append({"kind": "instruction", "location": f"página {number}, linha extraída {line_number}", "text": line.strip()})
    return findings


def scan_text(path: Path) -> list[dict]:
    raw = path.read_bytes()
    bom = next((name for signature, name in (
        (b"\xef\xbb\xbf", "UTF-8"), (b"\xff\xfe", "UTF-16 LE"),
        (b"\xfe\xff", "UTF-16 BE")) if raw.startswith(signature)), None)
    encoding = "utf-16" if bom and bom.startswith("UTF-16") else "utf-8-sig"
    content = raw.decode(encoding, errors="replace")
    endings = Counter({
        "CRLF": content.count("\r\n"),
        "LF": content.count("\n") - content.count("\r\n"),
        "CR": content.count("\r") - content.count("\r\n"),
    })
    findings = [{"kind": "text_format", "location": "arquivo", "bom": bom or "ausente", "endings": dict(endings)}]
    for number, line in enumerate(content.splitlines(), 1):
        if INSTRUCTION.search(line):
            findings.append({"kind": "instruction", "location": f"linha {number}", "text": line.strip()})
        for column, char in enumerate(line, 1):
            category = unicodedata.category(char)
            if category == "Cf" or (category == "Cc" and char != "\t"):
                findings.append({"kind": "control", "location": f"linha {number}, coluna {column}",
                                 "character": f"U+{ord(char):04X}", "name": unicodedata.name(char, category)})
    if "\ufffd" in content:
        findings.append({"kind": "decode", "location": "arquivo", "text": "Bytes não decodificáveis substituídos por U+FFFD"})
    return findings


def scan_directory(folder: Path) -> dict[str, list[dict]]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Pasta de entrada não encontrada: {folder}")
    results = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".pdf", ".csv", ".txt"}:
            results[path.relative_to(folder).as_posix()] = (
                scan_pdf(path) if path.suffix.lower() == ".pdf" else scan_text(path)
            )
    return results


def make_report(folder: Path, results: dict[str, list[dict]]) -> str:
    counts = Counter(item["kind"] for findings in results.values() for item in findings)
    lines = ["# Varredura de integridade dos materiais", "",
             f"Entrada: `{folder.as_posix()}`. Leitura somente; nenhum arquivo de entrada foi alterado.", "",
             f"Arquivos examinados: {len(results)}. Trechos PDF suspeitos: {counts['pdf_span']}. "
             f"Linhas com padrões de instrução: {counts['instruction']}. "
             f"Caracteres invisíveis/de controle: {counts['control']}.", "",
             "A detecção é uma triagem para revisão humana: pode produzir falsos positivos e não prova ausência de outros padrões.", ""]
    for path, findings in results.items():
        lines += [f"## `{path}`", ""]
        for item in findings:
            kind = item["kind"]
            if kind == "text_format":
                endings = ", ".join(f"{name}={count}" for name, count in item["endings"].items())
                lines.append(f"- BOM: {item['bom']}; finais de linha: {endings}.")
            elif kind == "pdf_span":
                lines.append(f"- Trecho PDF ({item['location']}): tamanho {item['size']} pt; "
                             f"cor `{item['color']}`; motivo: {item['reason']}; texto: “{display(item['text'])}”.")
            elif kind == "instruction":
                lines.append(f"- Possível instrução ({item['location']}): “{display(item['text'])}”.")
            elif kind == "control":
                lines.append(f"- Caractere invisível/de controle ({item['location']}): "
                             f"{item['character']} ({item['name']}).")
            else:
                lines.append(f"- Decodificação ({item['location']}): {item['text']}.")
        if not findings:
            lines.append("- Sem achados pelos critérios da varredura.")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", default="Case_Bari", help="Pasta dos materiais (padrão: Case_Bari)")
    parser.add_argument("--report", default="docs/varredura_arquivos.md", help="Destino do relatório")
    args = parser.parse_args()
    folder = Path(args.folder)
    report = Path(args.report)
    results = scan_directory(folder)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(make_report(folder, results), encoding="utf-8")
    counts = Counter(item["kind"] for findings in results.values() for item in findings)
    print(f"Arquivos examinados: {len(results)}")
    print(f"Trechos PDF suspeitos: {counts['pdf_span']}")
    print(f"Linhas com padrões de instrução: {counts['instruction']}")
    print(f"Caracteres invisíveis/de controle: {counts['control']}")
    print(f"Relatório: {report}")


if __name__ == "__main__":
    main()

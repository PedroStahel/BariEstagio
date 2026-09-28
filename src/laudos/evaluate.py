"""Compare rule and LLM extractions against manually labeled gold cells."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
import re
import sys
import unicodedata

from .schema import TARGET_FIELDS


ROOT = Path(__file__).resolve().parents[2]
NUMERIC = {"area_privativa_m2", "area_total_m2", "area_terreno_m2",
           "area_construida_m2", "ano_construcao", "valor_avaliacao_brl"}


def normalize(value: object, field: str) -> object:
    if value is None or str(value).strip().upper() == "NULL":
        return None
    value = str(value).strip()
    if field in NUMERIC:
        return float(value)  # Exact numerical equality, without rounding or tolerance.
    if field == "tem_onus":
        if value.casefold() in {"true", "1", "sim"}:
            return True
        if value.casefold() in {"false", "0", "não", "nao"}:
            return False
        raise ValueError(f"Booleano inválido em {field}: {value!r}")
    if field == "data_vistoria":
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError(f"Data não ISO: {value}")
        return value
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _read(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["documento"]: row for row in csv.DictReader(handle)}


def evaluate(gold_path: Path, sources: dict[str, Path | None]) -> str:
    gold = _read(gold_path)
    if not gold:
        raise ValueError("Gabarito vazio: é necessária uma linha por laudo.")
    if not set(TARGET_FIELDS).issubset(next(iter(gold.values()))):
        raise ValueError("Gabarito sem as colunas-alvo.")
    labeled = [(document, field, normalize(row[field], field))
               for document, row in gold.items() for field in TARGET_FIELDS if row[field].strip() != ""]
    lines = ["# Avaliação contra gabarito humano", "",
             f"Células rotuladas: {len(labeled)} de {len(gold)*len(TARGET_FIELDS)} possíveis. "
             "Célula vazia não é avaliada; NULL é ausência validada pelo humano.", ""]
    if not labeled:
        return "\n".join(lines + ["Sem métricas: preencha manualmente o gabarito antes de avaliar.", ""])
    for label, path in sources.items():
        if path is None:
            continue
        predictions = _read(path)
        if set(predictions) != set(gold):
            raise ValueError(f"{label}: documentos não coincidem com o gabarito.")
        counts = {field: {"acerto": 0, "N": 0} for field in TARGET_FIELDS}
        docs = {doc: {"acerto": 0, "N": 0} for doc in gold}
        matrix = {name: 0 for name in ["acerto_valor", "null_correto", "omissao", "alucinacao", "valor_errado", "falha_documento"]}
        expected_null = sum(expected is None for _, _, expected in labeled)
        for document, field, expected in labeled:
            row = predictions[document]
            if row.get("status") == "falha":
                category = "falha_documento"
            else:
                prediction = normalize(row[field] if row[field] != "" else None, field)
                if expected is None:
                    category = "null_correto" if prediction is None else "alucinacao"
                elif prediction is None:
                    category = "omissao"
                else:
                    category = "acerto_valor" if expected == prediction else "valor_errado"
            matrix[category] += 1
            counts[field]["N"] += 1
            docs[document]["N"] += 1
            if category in {"null_correto", "acerto_valor"}:
                counts[field]["acerto"] += 1
                docs[document]["acerto"] += 1
        lines += [f"## {label}", "",
                  f"Acerto total: {(matrix['null_correto']+matrix['acerto_valor'])}/{len(labeled)}."]
        if expected_null:
            lines += [f"Null correto: {matrix['null_correto']}/{expected_null} "
                      f"({matrix['null_correto']/expected_null:.1%}); "
                      f"alucinação: {matrix['alucinacao']}/{expected_null} "
                      f"({matrix['alucinacao']/expected_null:.1%})."]
        else:
            lines += ["Null correto e alucinação: indisponíveis (sem null rotulado)."]
        lines += ["", "### Por campo", "", "| campo | acertos | N | taxa |",
                  "| --- | ---: | ---: | ---: |"]
        for field, record in counts.items():
            if record["N"]:
                lines.append(f"| {field} | {record['acerto']} | {record['N']} | "
                             f"{record['acerto']/record['N']:.1%} |")
        lines += ["", "### Por documento", "", "| documento | acertos | N | taxa |",
                  "| --- | ---: | ---: | ---: |"]
        for doc, record in docs.items():
            if record["N"]:
                lines.append(f"| {doc} | {record['acerto']} | {record['N']} | "
                             f"{record['acerto']/record['N']:.1%} |")
        lines += ["", "### Matriz de erros", "", "| categoria | quantidade |",
                  "| --- | ---: |"]
        lines += [f"| {category} | {amount} |" for category, amount in matrix.items()]
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", default="tests/gold/gold_laudos.csv")
    parser.add_argument("--rules", default="outputs/laudos_extraidos.csv")
    parser.add_argument("--llm", default="")
    parser.add_argument("--output", default="outputs/avaliacao_laudos.md")
    args = parser.parse_args(argv)
    def root_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    try:
        report = evaluate(root_path(args.gold), {"Regras": root_path(args.rules),
                           "LLM": root_path(args.llm) if args.llm else None})
        output = root_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(report.splitlines()[2])
        print(f"Relatório: {args.output}")
        return 0
    except Exception as exc:
        print(f"Falha na avaliação: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

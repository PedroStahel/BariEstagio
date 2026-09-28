"""Run appraisal extraction; baseline mode requires no API key."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from .extractor_llm import OpenAICompatibleProvider, extract as extract_llm
from .extractor_rules import extract as extract_rules
from .schema import Appraisal, TARGET_FIELDS
from .validators import instruction_fragments, validate


ROOT = Path(__file__).resolve().parents[2]
COLUMNS = ["documento", "status", "erro", *TARGET_FIELDS,
           *(f"{field}_evidencia" for field in TARGET_FIELDS),
           *(f"{field}_confianca" for field in TARGET_FIELDS), "avisos"]


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def run(input_dir: Path, output_dir: Path, mode: str = "rules", provider=None,
        attempts: int = 3) -> list[dict]:
    files = sorted(input_dir.glob("*.txt"))
    if not input_dir.is_dir() or not files:
        raise ValueError("Pasta de laudos inexistente ou sem arquivos .txt.")
    if mode not in {"rules", "llm"}:
        raise ValueError("Modo inválido: escolha rules ou llm.")
    if mode == "llm" and provider is None:
        provider = OpenAICompatibleProvider.from_env()
    rows = []
    quality = ["# Qualidade da extração dos laudos", "",
               f"Modo: {mode}. Documentos: {len(files)}. Gabarito humano ainda não preenchido.", "",
               "| documento | status | campos preenchidos | campos nulos | avisos |",
               "| --- | --- | ---: | ---: | --- |"]
    for index, path in enumerate(files, start=1):
        if mode == "llm":
            print(f"[{index}/{len(files)}] {path.name}: iniciando", flush=True)
        text = path.read_text(encoding="utf-8-sig")
        baseline = validate(extract_rules(text), text)
        if mode == "rules":
            appraisal, status, error = baseline, "ok", None
        else:
            extracted = extract_llm(text, provider, attempts,
                                    on_attempt=lambda current, total: print(
                                        f"  Tentativa {current}/{total}...", flush=True))
            appraisal, status, error = extracted.appraisal, extracted.status, extracted.error
            if appraisal is not None:
                appraisal = validate(appraisal, text, baseline)
            print(f"  Resultado: {status}" + (f" — {error[:500]}" if error else ""), flush=True)
        appraisal = appraisal or Appraisal()
        if status == "falha":
            appraisal.avisos.append("Falha do provedor/JSON após tentativas; campos permanecem nulos.")
        for fragment in instruction_fragments(text):
            if not any(fragment in warning for warning in appraisal.avisos):
                appraisal.avisos.append(f"Possível instrução dentro do laudo ignorada: {fragment}")
        item = {"documento": path.name, "status": status, "erro": error,
                "campos": appraisal.model_dump(mode="json")}
        rows.append(item)
        nonnull = sum(getattr(appraisal, field).value is not None for field in TARGET_FIELDS)
        warnings = "; ".join(appraisal.avisos).replace("|", r"\|").replace("\n", " ")
        quality.append(f"| {path.name} | {status} | {nonnull} | {len(TARGET_FIELDS)-nonnull} | {warnings} |")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "laudos_extraidos.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "laudos_extraidos.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            fields = row["campos"]
            flat = {"documento": row["documento"], "status": row["status"], "erro": row["erro"] or "",
                    "avisos": json.dumps(fields["avisos"], ensure_ascii=False)}
            for field in TARGET_FIELDS:
                for source, column in [("value", field), ("evidencia", f"{field}_evidencia"),
                                       ("confianca", f"{field}_confianca")]:
                    value = fields[field][source]
                    flat[column] = "" if value is None else value
            writer.writerow(flat)
    (output_dir / "laudos_qualidade.md").write_text("\n".join(quality) + "\n", encoding="utf-8")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="Case_Bari/laudos_avaliacao/")
    parser.add_argument("--output-dir", default="outputs/")
    parser.add_argument("--mode", choices=["rules", "llm"], default="rules")
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        rows = run(_path(args.input_dir), _path(args.output_dir), args.mode, attempts=args.attempts)
        print(f"Documentos={len(rows)}; sucesso={sum(r['status']=='ok' for r in rows)}; "
              f"falhas={sum(r['status']=='falha' for r in rows)}; modo={args.mode}")
        print(f"Saídas: {Path(args.output_dir) / 'laudos_extraidos.json'}, "
              f"{Path(args.output_dir) / 'laudos_extraidos.csv'} e "
              f"{Path(args.output_dir) / 'laudos_qualidade.md'}")
        return 0 if all(row["status"] == "ok" for row in rows) else 1
    except Exception as exc:
        print(f"Falha na extração: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

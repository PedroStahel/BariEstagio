"""Weekly pipeline tests: real-schema sample mutated only inside tmp_path."""

from datetime import date
from pathlib import Path

import pandas as pd

from src.funnel.run import main


ROOT = Path(__file__).resolve().parents[1]


def sample(tmp_path: Path, change=None) -> Path:
    raw = pd.read_csv(ROOT / "Case_Bari" / "propostas_credito.csv", dtype="string",
                      keep_default_na=False, encoding="utf-8-sig").head(24).copy()
    if change:
        change(raw)
    path = tmp_path / "input.csv"
    raw.to_csv(path, index=False, encoding="utf-8")
    return path


def invoke(path: Path, tmp_path: Path, *extra: str) -> tuple[int, Path]:
    output = tmp_path / "out"
    code = main(["--input", str(path), "--output-dir", str(output), "--as-of", "2026-02-04", *extra])
    return code, output


def test_valid_and_repeatable(tmp_path: Path) -> None:
    path = sample(tmp_path)
    before = path.read_bytes()
    code, output = invoke(path, tmp_path)
    assert code == 0
    html = (output / "relatorio_semanal.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," in html
    assert (output / "relatorio_semanal.xlsx").is_file()
    assert "SHA-256" in html
    assert path.read_bytes() == before
    first = pd.read_excel(output / "relatorio_semanal.xlsx", sheet_name="Funil", skiprows=12)
    assert len(first)
    code, _ = invoke(path, tmp_path)
    assert code == 0
    second = (output / "relatorio_semanal.html").read_text(encoding="utf-8")
    # Generation timestamp is the only changing metadata.
    import re
    strip_stamp = lambda x: re.sub(r"Gerado em:</strong>.*?</div>", "Gerado em:</strong></div>", x)
    assert strip_stamp(html) == strip_stamp(second)


def test_missing_required_aborts_without_report(tmp_path: Path) -> None:
    path = sample(tmp_path, lambda df: df.drop(columns=["valor_solicitado"], inplace=True))
    code, output = invoke(path, tmp_path)
    assert code != 0
    assert not (output / "relatorio_semanal.html").exists()
    assert "Coluna obrigatória ausente" in next((output / "logs").glob("run_*.log")).read_text()


def test_missing_optional_is_explicit(tmp_path: Path) -> None:
    path = sample(tmp_path, lambda df: df.drop(columns=["taxa_juros_aa"], inplace=True))
    code, output = invoke(path, tmp_path)
    assert code == 0
    html = (output / "relatorio_semanal.html").read_text()
    assert "Coluna opcional ausente" in html
    assert "indisponível" in html


def test_unknown_category_kept_and_grouped(tmp_path: Path) -> None:
    def mutate(df):
        df.loc[df.index[0], "canal_origem"] = "Canal piloto"
        df.loc[df.index[1], "status_final"] = "Nova situação"
        df.loc[df.index[2], "tipo_imovel"] = "Tipo piloto"
        df["extra"] = "ignorar"
    path = sample(tmp_path, mutate)
    code, output = invoke(path, tmp_path)
    assert code == 0
    html = (output / "relatorio_semanal.html").read_text()
    assert "Não mapeado" in html and "Categoria nova" in html and "Colunas extras ignoradas" in html
    treated = pd.read_csv(output / "propostas_weekly_clean.csv")
    assert "Canal piloto" in set(treated.canal_origem)


def test_new_date_format_is_counted(tmp_path: Path) -> None:
    path = sample(tmp_path, lambda df: df.loc.__setitem__((df.index[0], "data_entrada"), "2025.01.10"))
    code, output = invoke(path, tmp_path)
    assert code == 0
    assert "Conversões inválidas" in (output / "relatorio_semanal.html").read_text()
    code, other = invoke(path, tmp_path, "--max-parse-failure-rate", "0")
    assert code != 0
    assert "limiar configurado" in sorted((other / "logs").glob("run_*.log"))[-1].read_text()


def test_empty_and_missing_files(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("")
    code, out = invoke(path, tmp_path)
    assert code != 0 and not (out / "relatorio_semanal.html").exists()
    path.unlink()
    code, out = invoke(path, tmp_path)
    assert code != 0 and not (out / "relatorio_semanal.html").exists()

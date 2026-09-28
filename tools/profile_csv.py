"""Report the untouched CSV's structure and quality before any cleaning."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import pandas as pd


CATEGORICAL = [
    "canal_origem", "cidade", "uf", "tipo_imovel", "flag_cliente_recorrente",
    "consultor_id", "etapa_max_funil", "status_final",
]
NUMERIC = [
    "valor_imovel", "valor_solicitado", "prazo_meses", "score_credito",
    "idade_cliente", "renda_mensal_declarada", "tempo_analise_dias", "taxa_juros_aa",
]
DATES = ["data_entrada", "data_assinatura_contrato"]
QUOTED_ROW = re.compile(r'"(?:[^"]|"")*"(?:,"(?:[^"]|"")*")*')


def profile(source: Path) -> str:
    raw = source.read_bytes()
    rows = raw.decode("utf-8-sig").splitlines()
    df = pd.read_csv(source, dtype="string", keep_default_na=False, encoding="utf-8-sig")
    lines = ["# Perfil do CSV bruto (antes do tratamento)", "",
             f"Fonte: `{source.as_posix()}`. O arquivo foi lido, não alterado.", "",
             f"Linhas: {len(df)}; colunas: {len(df.columns)}; tipos lidos: texto para preservar os formatos originais.",
             f"BOM UTF-8: {raw.startswith(bytes.fromhex('efbbbf'))}; campos entre aspas em todas as linhas: {all(QUOTED_ROW.fullmatch(row) for row in rows)}; "
             f"CRLF: {raw.count(bytes.fromhex('0d0a'))}; LF isolado: {raw.count(bytes.fromhex('0a')) - raw.count(bytes.fromhex('0d0a'))}.",
             f"Linhas totalmente duplicadas: {df.duplicated().sum()}; IDs duplicados: {df.id_proposta.duplicated().sum()}.", "",
             "## Colunas e ausências", "", "| coluna | tipo bruto | nulos/vazios |", "| --- | --- | ---: |"]
    for column in df:
        lines.append(f"| {column} | texto | {df[column].str.strip().eq('').sum()} |")
    lines += ["", "## Categóricas (valores originais, inclusive espaços)", ""]
    for column in CATEGORICAL:
        counts = df[column].value_counts(dropna=False)
        lines += [f"### `{column}` — {len(counts)} valores", "",
                  "| valor | N |", "| --- | ---: |"]
        lines.extend(f"| `{value}` | {count} |" for value, count in counts.items())
        lines.append("")
    lines += ["## Numéricas (interpretação provisória somente para perfil)", "",
              "| coluna | presentes | mínimo | máximo | prefixo R$ | falhas após retirar prefixo |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    parsed = {}
    for column in NUMERIC:
        value = df[column].str.strip()
        prefix = value.str.match(r"^R\$\s*").sum()
        number = pd.to_numeric(value.str.replace(r"^R\$\s*", "", regex=True), errors="coerce")
        parsed[column] = number
        failures = (value.ne("") & number.isna()).sum()
        lines.append(f"| {column} | {value.ne('').sum()} | {number.min()} | {number.max()} | {prefix} | {failures} |")
    lines += ["", "## Datas (formatos brutos)", "",
              "| coluna | ISO AAAA-MM-DD | BR DD/MM/AAAA | outros não vazios | datas impossíveis nos formatos reconhecidos |",
              "| --- | ---: | ---: | ---: | ---: |"]
    dates = {}
    date_ranges = []
    for column in DATES:
        value = df[column].str.strip()
        iso = value.str.fullmatch(r"\d{4}-\d{2}-\d{2}")
        br = value.str.fullmatch(r"\d{2}/\d{2}/\d{4}")
        result = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
        result.loc[iso] = pd.to_datetime(value.loc[iso], format="%Y-%m-%d", errors="coerce")
        result.loc[br] = pd.to_datetime(value.loc[br], format="%d/%m/%Y", errors="coerce")
        dates[column] = result
        invalid = ((iso | br) & result.isna()).sum()
        lines.append(f"| {column} | {iso.sum()} | {br.sum()} | {(value.ne('') & ~(iso | br)).sum()} | {invalid} |")
        date_ranges.append(f"Faixa de `{column}` válida: {result.min()} a {result.max()}.")
    lines.extend(["", *date_ranges, ""])
    signed = dates["data_assinatura_contrato"]
    entered = dates["data_entrada"]
    ltv = parsed["valor_solicitado"] / parsed["valor_imovel"]
    contract = df.status_final.eq("Contratada")
    stage = df.etapa_max_funil
    lines += ["## Coerência e outros achados", "",
              "| verificação | linhas |", "| --- | ---: |",
              f"| `ltv` no cabeçalho | {int('ltv' in df.columns)} |",
              f"| LTV calculável | {ltv.notna().sum()} |",
              f"| LTV calculado mínimo | {ltv.min()} |",
              f"| LTV calculado máximo | {ltv.max()} |",
              f"| LTV calculado > 0,60 | {ltv.gt(.60).sum()} |",
              f"| `tipo_imovel` Terreno | {df.tipo_imovel.eq('Terreno').sum()} |",
              f"| idade < 18 | {parsed['idade_cliente'].lt(18).sum()} |",
              f"| etapa fora de 1–6 | {(~stage.isin(list('123456'))).sum()} |",
              f"| Contratada fora da etapa 6 | {(contract & stage.ne('6')).sum()} |",
              f"| Não contratada na etapa 6 | {((~contract) & stage.eq('6')).sum()} |",
              f"| Contratada sem assinatura | {(contract & df.data_assinatura_contrato.eq('')).sum()} |",
              f"| Não contratada com assinatura | {((~contract) & df.data_assinatura_contrato.ne('')).sum()} |",
              f"| Contratada sem taxa | {(contract & df.taxa_juros_aa.eq('')).sum()} |",
              f"| Não contratada com taxa | {((~contract) & df.taxa_juros_aa.ne('')).sum()} |",
              f"| Assinatura anterior à entrada | {(signed.lt(entered)).sum()} |",
              f"| Prazo declarado diferente do intervalo até assinatura | {(signed.notna() & (signed.sub(entered).dt.days != parsed['tempo_analise_dias'])).sum()} |",
              f"| Canal com espaço exterior | {df.canal_origem.ne(df.canal_origem.str.strip()).sum()} |",
              "", "A descrição de `taxa_juros_aa` em `% a.m.` conflita com o sufixo `aa`; o perfil não infere nem converte a unidade.", "",
              "### `status_final` × `etapa_max_funil`", "",
              "| status | " + " | ".join(sorted(stage.unique())) + " |",
              "| --- | " + " | ".join(["---:"] * stage.nunique()) + " |"]
    cross = pd.crosstab(df.status_final, stage)
    for name, counts in cross.iterrows():
        lines.append("| " + name + " | " + " | ".join(str(counts.get(column, 0)) for column in sorted(stage.unique())) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="Case_Bari/propostas_credito.csv")
    parser.add_argument("--output", default="outputs/perfil_bruto.md")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(profile(Path(args.input)), encoding="utf-8")
    print(f"Perfil bruto: {output}")


if __name__ == "__main__":
    main()

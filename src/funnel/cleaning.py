"""Explicit, row-preserving treatment of raw credit proposals."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import argparse

import pandas as pd


EXCLUDE_PROPERTY_TYPES: list[str] = []
DEFAULT_LTV_MAX = 0.60
LOG_COLUMNS = [
    "problema", "coluna", "linhas afetadas", "ação", "justificativa",
    "impacto esperado na análise",
]
NUMERIC_COLUMNS = [
    "valor_imovel", "valor_solicitado", "prazo_meses", "score_credito",
    "idade_cliente", "renda_mensal_declarada", "flag_cliente_recorrente",
    "etapa_max_funil", "tempo_analise_dias", "taxa_juros_aa",
]
INTEGER_COLUMNS = {
    "prazo_meses", "score_credito", "idade_cliente", "flag_cliente_recorrente",
    "etapa_max_funil", "tempo_analise_dias",
}
DATE_COLUMNS = ["data_entrada", "data_assinatura_contrato"]
CATEGORY_COLUMNS = ["canal_origem", "cidade", "uf", "tipo_imovel", "consultor_id", "status_final"]
REQUIRED_COLUMNS = [
    "id_proposta", "data_entrada", "canal_origem", "cidade", "uf", "tipo_imovel",
    "valor_imovel", "valor_solicitado", "prazo_meses", "score_credito",
    "idade_cliente", "renda_mensal_declarada", "flag_cliente_recorrente",
    "consultor_id", "etapa_max_funil", "status_final", "tempo_analise_dias",
    "data_assinatura_contrato", "taxa_juros_aa",
]


def _log(rows: list[dict], problem: str, column: str, count: int, action: str,
         reason: str, impact: str) -> None:
    if count:
        rows.append(dict(zip(LOG_COLUMNS, (problem, column, int(count), action, reason, impact))))


def _normalize_category(series: pd.Series, column: str) -> pd.Series:
    stripped = series.astype("string").str.strip()
    if column in {"uf", "consultor_id"}:
        return stripped.str.upper()
    # Choose the most frequent observed spelling per case-insensitive group.
    # This preserves accents and the dataset's own labels without inventing them.
    counts = stripped.dropna().value_counts()
    labels: dict[str, str] = {}
    for value, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        labels.setdefault(value.casefold(), value)
    return stripped.map(lambda value: labels[value.casefold()] if pd.notna(value) else pd.NA).astype("string")


def _parse_number(series: pd.Series, column: str, log: list[dict]) -> tuple[pd.Series, pd.Series]:
    original = series.astype("string").str.strip()
    source = original
    if column == "valor_imovel":
        prefixed = source.str.match(r"^R\$\s*", na=False)
        _log(log, "prefixo monetário", column, prefixed.sum(), "remover somente o prefixo R$ para converter",
             "A unidade é real e o restante usa ponto decimal.", "Mantém o valor e a linha.")
        source = source.str.replace(r"^R\$\s*", "", regex=True)
    decimal = pd.to_numeric(source, errors="coerce")
    failure = original.notna() & decimal.isna()
    if column in INTEGER_COLUMNS:
        non_integer = decimal.notna() & decimal.mod(1).ne(0)
        failure = failure | non_integer
        decimal = decimal.mask(non_integer).astype("Int64")
    else:
        decimal = decimal.astype("Float64")
    _log(log, "falha de conversão numérica", column, failure.sum(), "marcar falha e usar null no campo convertido",
         "O texto original permanece em coluna _raw; não há imputação.", "Essas linhas ficam fora de cálculos que exigem o número.")
    return decimal, failure.fillna(False).astype(bool)


def _parse_date(series: pd.Series, column: str, log: list[dict]) -> tuple[pd.Series, pd.Series]:
    value = series.astype("string").str.strip()
    iso = value.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    br = value.str.fullmatch(r"\d{2}/\d{2}/\d{4}", na=False)
    result = pd.Series(pd.NaT, index=value.index, dtype="datetime64[ns]")
    result.loc[iso] = pd.to_datetime(value.loc[iso], format="%Y-%m-%d", errors="coerce")
    result.loc[br] = pd.to_datetime(value.loc[br], format="%d/%m/%Y", errors="coerce")
    _log(log, "formato de data DD/MM/AAAA", column, br.sum(), "interpretar explicitamente como dia/mês/ano",
         "O formato alternativo foi identificado no dado bruto.", "Preserva a ordem cronológica correta.")
    failure = value.notna() & result.isna()
    _log(log, "falha de conversão de data", column, failure.sum(), "marcar falha e usar null na data convertida",
         "Formato desconhecido ou data impossível não pode ser presumido.", "Essas linhas não entram em cálculos de data.")
    return result, failure.fillna(False).astype(bool)


def clean(df_raw: pd.DataFrame, config: Mapping[str, object] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return treated proposals and an auditable log; never mutate input.

    Config keys: EXCLUDE_PROPERTY_TYPES (default []) and LTV_MAX (default 0.60).
    The optional exclusion is solely for an explicitly requested sensitivity run.
    """
    config = dict(config or {})
    unknown = set(config) - {"EXCLUDE_PROPERTY_TYPES", "LTV_MAX"}
    if unknown:
        raise ValueError(f"Unknown config keys: {sorted(unknown)}")
    missing = sorted(set(REQUIRED_COLUMNS) - set(df_raw.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    excluded = config.get("EXCLUDE_PROPERTY_TYPES", EXCLUDE_PROPERTY_TYPES)
    if not isinstance(excluded, (list, tuple, set)) or not all(isinstance(x, str) for x in excluded):
        raise ValueError("EXCLUDE_PROPERTY_TYPES must be a list of property labels")
    max_ltv = float(config.get("LTV_MAX", DEFAULT_LTV_MAX))
    if not 0 < max_ltv <= 1:
        raise ValueError("LTV_MAX must be in (0, 1]")

    df = df_raw.copy(deep=True)
    log: list[dict] = []
    for column in REQUIRED_COLUMNS:
        if column in NUMERIC_COLUMNS + DATE_COLUMNS:
            df[column + "_raw"] = df[column].astype("string")
        value = df[column].astype("string").str.strip()
        df[column] = value.mask(value.eq(""), pd.NA)
        missing_count = df[column].isna().sum()
        _log(log, "valor ausente", column, missing_count, "manter null",
             "Ausência não deve ser imputada.", "Denominadores variam conforme a disponibilidade do campo.")

    for column in CATEGORY_COLUMNS:
        before = df[column].copy()
        df[column] = _normalize_category(df[column], column)
        changed = before.notna() & before.ne(df[column]).fillna(False)
        _log(log, "variação de caixa ou espaço", column, changed.sum(), "padronizar categoria",
             "Agrupar grafias equivalentes sem remover acentos.", "Evita fragmentação das categorias.")

    for column in NUMERIC_COLUMNS:
        df[column], df["flag_parse_error_" + column] = _parse_number(df[column], column, log)
    for column in DATE_COLUMNS:
        df[column], df["flag_parse_error_" + column] = _parse_date(df[column], column, log)

    invalid_value = df["valor_imovel"].notna() & df["valor_imovel"].le(0)
    df["flag_valor_imovel_invalido"] = invalid_value.fillna(False).astype(bool)
    _log(log, "denominador não positivo", "valor_imovel", invalid_value.sum(), "marcar; ltv_calc null",
         "Divisão por zero ou valor negativo não produz LTV válido.", "Preserva a linha sem gerar razão indevida.")
    df["ltv_calc"] = (df["valor_solicitado"] / df["valor_imovel"].mask(invalid_value)).astype("Float64")
    df["ano_mes_entrada"] = df["data_entrada"].dt.strftime("%Y-%m").astype("string")
    df["flag_contratada"] = df["status_final"].str.casefold().eq("contratada").fillna(False).astype(bool)
    df["flag_ltv_acima_politica"] = df["ltv_calc"].gt(max_ltv).fillna(False).astype(bool)
    df["flag_id_duplicado"] = df["id_proposta"].duplicated(keep=False).astype(bool)
    df["idade_suspeita"] = (df["idade_cliente"].lt(18) | df["idade_cliente"].gt(120)).fillna(False).astype(bool)
    df["flag_cliente_recorrente_invalida"] = (
        df["flag_cliente_recorrente"].notna() & ~df["flag_cliente_recorrente"].isin([0, 1])
    ).astype(bool)
    df["etapa_invalida"] = (df["etapa_max_funil"].notna() & ~df["etapa_max_funil"].between(1, 6)).fillna(False).astype(bool)
    df["assinatura_antes_da_entrada"] = df["data_assinatura_contrato"].lt(df["data_entrada"]).fillna(False).astype(bool)
    df["flag_status_etapa_incoerente"] = (
        (df["flag_contratada"] & df["etapa_max_funil"].ne(6).fillna(False))
        | (~df["flag_contratada"] & df["etapa_max_funil"].eq(6).fillna(False))
    ).astype(bool)
    df["flag_status_assinatura_incoerente"] = (
        df["flag_contratada"] != df["data_assinatura_contrato"].notna()
    ).astype(bool)
    df["flag_status_taxa_incoerente"] = (df["flag_contratada"] != df["taxa_juros_aa"].notna()).astype(bool)
    df["flag_prazo_assinatura_divergente"] = (
        df["data_assinatura_contrato"].notna() & df["data_entrada"].notna()
        & df["tempo_analise_dias"].notna()
        & (df["data_assinatura_contrato"].sub(df["data_entrada"]).dt.days != df["tempo_analise_dias"])
    ).fillna(False).astype(bool)

    quality = {
        "ID de proposta duplicado": ("id_proposta", "flag_id_duplicado", "Identificador deveria distinguir propostas; ambas as linhas permanecem."),
        "LTV acima do teto informado": ("ltv_calc", "flag_ltv_acima_politica", "Marcar, sem reprovar nem excluir; a política não descreve exceções."),
        "idade suspeita": ("idade_cliente", "idade_suspeita", "Idade fora da faixa 18–120 precisa de revisão."),
        "indicador de recorrência inválido": ("flag_cliente_recorrente", "flag_cliente_recorrente_invalida", "O dicionário indica valores binários."),
        "etapa fora do funil": ("etapa_max_funil", "etapa_invalida", "O funil informado só contém etapas 1–6."),
        "assinatura anterior à entrada": ("data_assinatura_contrato", "assinatura_antes_da_entrada", "A ordem temporal é impossível no ciclo descrito."),
        "status e etapa incoerentes": ("status_final / etapa_max_funil", "flag_status_etapa_incoerente", "Contratada exige etapa 6; etapa 6 exige Contratada."),
        "status e assinatura incoerentes": ("status_final / data_assinatura_contrato", "flag_status_assinatura_incoerente", "Assinatura presente deve acompanhar Contratada."),
        "status e taxa incoerentes": ("status_final / taxa_juros_aa", "flag_status_taxa_incoerente", "Taxa contratada deve acompanhar Contratada."),
        "tempo e assinatura divergentes": ("tempo_analise_dias / data_assinatura_contrato", "flag_prazo_assinatura_divergente", "Comparação apenas onde ambas as datas e tempo existem."),
    }
    for problem, (column, flag, reason) in quality.items():
        _log(log, problem, column, df[flag].sum(), "manter linha e criar flag", reason,
             "Permite auditoria e análises de sensibilidade sem perda silenciosa.")

    _log(log, "coluna no dicionário ausente no CSV", "ltv", len(df), "criar ltv_calc sem inventar ltv original",
         "Razão calculada a partir dos dois valores disponíveis.", "Métrica comparável, com origem explícita.")
    _log(log, "unidade contraditória no dicionário", "taxa_juros_aa", df["taxa_juros_aa"].notna().sum(),
         "preservar nome e valor; não converter unidade", "Sufixo aa e descrição % a.m. conflitam.",
         "Evita interpretação errada da taxa até esclarecimento.")
    terrenos = df["tipo_imovel"].eq("Terreno").sum()
    _log(log, "tipo Terreno mantido", "tipo_imovel", terrenos, "não excluir no tratamento padrão",
         "A instrução oculta no PDF não é regra do case; exclusão só em sensibilidade solicitada.",
         "Preserva a população original.")

    if excluded:
        exclude_values = {value.strip().casefold() for value in excluded}
        mask = df["tipo_imovel"].str.casefold().isin(exclude_values)
        _log(log, "exclusão de sensibilidade solicitada", "tipo_imovel", mask.sum(), "excluir da cópia de saída",
             "EXCLUDE_PROPERTY_TYPES informado explicitamente; base original permanece intacta.",
             "Reduz o denominador; comparar com a execução padrão.")
        df = df.loc[~mask].copy()
    return df, pd.DataFrame(log, columns=LOG_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trata o CSV bruto sem alterar a origem.")
    parser.add_argument("--input", default="Case_Bari/propostas_credito.csv")
    parser.add_argument("--output", default="data/processed/propostas_clean.csv")
    parser.add_argument("--log", default="outputs/registro_tratamento.md")
    args = parser.parse_args()
    source = pd.read_csv(args.input, dtype="string", keep_default_na=False, encoding="utf-8-sig")
    treated, log = clean(source, {"EXCLUDE_PROPERTY_TYPES": []})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    treated.to_csv(output, index=False, encoding="utf-8")
    report = Path(args.log)
    report.parent.mkdir(parents=True, exist_ok=True)
    table = ["| " + " | ".join(LOG_COLUMNS) + " |", "| " + " | ".join(["---"] * len(LOG_COLUMNS)) + " |"]
    for row in log.itertuples(index=False, name=None):
        table.append("| " + " | ".join(str(cell).replace("|", r"\|") for cell in row) + " |")
    report.write_text("# Registro de tratamento de dados\n\n" + "\n".join(table) + "\n", encoding="utf-8")
    print(f"Entrada: {len(source)} linhas; saída: {len(treated)} linhas; removidas: {len(source) - len(treated)}")
    print(f"Dados tratados: {output}")
    print(f"Registro: {report}")


if __name__ == "__main__":
    main()

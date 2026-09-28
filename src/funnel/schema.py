"""Pre-treatment schema checks for the weekly import."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .cleaning import OPTIONAL_COLUMNS, REQUIRED_COLUMNS


KNOWN_CATEGORIES = {
    "status_final": {"Sem retorno", "Desistiu", "Contratada", "Reprovada crédito",
                     "Problema garantia", "Documentação pendente"},
    "canal_origem": {"Correspondente", "Organico", "Mídia paga", "Indicação", "Parceria"},
    "tipo_imovel": {"Apartamento", "Casa", "Sala comercial", "Terreno", "Imóvel rural"},
}


class SchemaError(ValueError):
    """Input cannot produce a trustworthy report."""


@dataclass
class SchemaResult:
    frame: pd.DataFrame
    warnings: list[str]
    unknown_categories: dict[str, dict[str, int]]
    missing_optional: list[str]


def validate(raw: pd.DataFrame) -> SchemaResult:
    if raw.empty:
        raise SchemaError("O CSV está vazio: nenhuma proposta para processar.")
    if raw.columns.duplicated().any():
        raise SchemaError("Cabeçalhos duplicados: " + ", ".join(raw.columns[raw.columns.duplicated()]))
    missing = sorted(set(REQUIRED_COLUMNS) - set(raw.columns))
    if missing:
        raise SchemaError("Coluna obrigatória ausente: " + ", ".join(missing))
    optional = sorted(set(OPTIONAL_COLUMNS) - set(raw.columns))
    extras = sorted(set(raw.columns) - set(REQUIRED_COLUMNS) - set(OPTIONAL_COLUMNS))
    warnings = [f"Coluna opcional ausente: {name}; métricas dependentes indisponíveis." for name in optional]
    if extras:
        warnings.append("Colunas extras ignoradas: " + ", ".join(extras))
    frame = raw.loc[:, [c for c in REQUIRED_COLUMNS + OPTIONAL_COLUMNS if c in raw]].copy()
    unknown: dict[str, dict[str, int]] = {}
    for column, known in KNOWN_CATEGORIES.items():
        normalized = frame[column].astype("string").str.strip().str.casefold()
        observed = normalized.value_counts()
        names = {value.casefold() for value in known}
        new = {str(label): int(count) for label, count in observed.items() if label and label not in names}
        if new:
            unknown[column] = new
            warnings.append(f"Categoria nova em {column}: " + ", ".join(f"{key} ({n})" for key, n in new.items())
            + "; apresentada como Não mapeado no agrupamento.")
    return SchemaResult(frame, warnings, unknown, optional)


def mapped_groups(cleaned: pd.DataFrame, column: str) -> pd.Series:
    """Map unknown labels only for reporting, retaining the source value in cleaned data."""
    known = {item.casefold() for item in KNOWN_CATEGORIES[column]}
    values = cleaned[column].astype("string")
    return values.where(values.str.casefold().isin(known), "Não mapeado").fillna("Não mapeado")

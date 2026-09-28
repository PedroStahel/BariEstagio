"""Checks independent of the LLM response."""

from __future__ import annotations

from datetime import date
import re

from .schema import Appraisal, Evidence, TARGET_FIELDS


INJECTION_PATTERNS = [
    r"ignore (?:as |todas as )?instru[cç][oõ]es",
    r"\b(?:prompt|sistema|assistente|ia)\s*:",
    r"retorne valor\s+[\d.,]+",
]


def instruction_fragments(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines()
            if any(re.search(pattern, line, re.I) for pattern in INJECTION_PATTERNS)]


def _null(result: Appraisal, field: str, reason: str) -> None:
    setattr(result, field, Evidence())
    result.avisos.append(reason)


def validate(result: Appraisal, text: str, baseline: Appraisal | None = None,
             today: date | None = None) -> Appraisal:
    checked = result.model_copy(deep=True)
    today = today or date.today()
    for field in TARGET_FIELDS:
        item = getattr(checked, field)
        if item.value is not None and (not item.evidencia or item.evidencia not in text):
            _null(checked, field, f"{field}: evidência ausente ou não literal; valor anulado.")

    if checked.matricula.value is not None and not re.fullmatch(r"\d{1,3}(?:\.\d{3})*", checked.matricula.value):
        _null(checked, "matricula", "matricula: formato inesperado; valor anulado.")
    if checked.data_vistoria.value is not None:
        try:
            parsed = date.fromisoformat(checked.data_vistoria.value)
            if parsed.isoformat() != checked.data_vistoria.value:
                raise ValueError("ISO não canônico")
        except ValueError:
            _null(checked, "data_vistoria", "data_vistoria: data ISO inválida; valor anulado.")
    if checked.valor_avaliacao_brl.value is not None and checked.valor_avaliacao_brl.value <= 0:
        _null(checked, "valor_avaliacao_brl", "valor_avaliacao_brl: valor não positivo; anulado.")
    for field in ["area_privativa_m2", "area_total_m2", "area_terreno_m2", "area_construida_m2"]:
        item = getattr(checked, field)
        if item.value is not None and item.value <= 0:
            _null(checked, field, f"{field}: área não positiva; valor anulado.")
    year = checked.ano_construcao.value
    if year is not None and not (1800 <= year <= today.year):
        _null(checked, "ano_construcao", "ano_construcao: fora de 1800 até o ano atual; valor anulado.")
    private, total = checked.area_privativa_m2.value, checked.area_total_m2.value
    if private is not None and total is not None and private > total:
        checked.avisos.append(f"Áreas incoerentes: privativa {private} > total {total}; revisar ambas.")
        _null(checked, "area_total_m2", "area_total_m2: incoerência; valor anulado.")

    # Independent text check: two explicitly competing total areas must stay null.
    total_values = [float(v.replace(".", "").replace(",", ".")) for v in
                    re.findall(r"[aá]rea total\s*(\d[\d.,]*)\s*m[²2]", text, re.I)]
    total_values += [float(v.replace(".", "").replace(",", ".")) for v in
                     re.findall(r"tabela interna registra\s*(\d[\d.,]*)\s*m[²2]", text, re.I)]
    if len(set(total_values)) > 1:
        _null(checked, "area_total_m2", f"Contradição em area_total_m2: {sorted(set(total_values))}; valor nulo.")

    if baseline is not None:
        for field in TARGET_FIELDS:
            primary, rule = getattr(checked, field).value, getattr(baseline, field).value
            if primary is not None and rule is not None and primary != rule:
                checked.avisos.append(f"Discordância LLM × regras em {field}: LLM={primary!r}; regras={rule!r}.")
    for fragment in instruction_fragments(text):
        checked.avisos.append(f"Possível instrução dentro do laudo ignorada: {fragment}")
    checked.avisos = list(dict.fromkeys(checked.avisos))
    return checked

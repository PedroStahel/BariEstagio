"""Conservative deterministic baseline; omissions remain null."""

from __future__ import annotations

from datetime import date
import re

from .schema import Appraisal, Evidence


NUMBER = r"\d[\d.]*[,]?\d*"
MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}
TYPE_PATTERNS = [
    (r"\bapartamento\b", "apartamento"), (r"\bcasa\b", "casa"),
    (r"\bsala comercial\b", "sala_comercial"), (r"\bterreno\b", "terreno"),
    (r"\bim[oó]vel rural\b", "imovel_rural"), (r"\bloja\b", "loja"),
    (r"\bgalp[aã]o\b", "galpao"), (r"\bunidade comercial\b", "unidade_comercial"),
]


def br_number(token: str) -> float:
    if "," in token:
        return float(token.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", token):
        return float(token.replace(".", ""))
    return float(token)


def cite(value, evidence: str, confidence: str = "alta") -> Evidence:
    return Evidence(value=value, evidencia=evidence, confianca=confidence)


def first_line(text: str, patterns: list[str]) -> str | None:
    for line in text.splitlines():
        if any(re.search(pattern, line, re.I) for pattern in patterns):
            return line.strip()
    return None


def find_area(text: str, patterns: list[str]) -> tuple[Evidence[float], list[float]]:
    found: list[tuple[float, str]] = []
    for line in text.splitlines():
        for pattern in patterns:
            for match in re.finditer(pattern, line, re.I):
                value = br_number(match.group(1))
                if match.group(2).lower() == "ha":
                    value *= 10000
                found.append((value, match.group(0)))
    distinct = sorted({value for value, _ in found})
    if len(distinct) == 1:
        return cite(found[0][0], found[0][1]), distinct
    return Evidence[float](), distinct


def extract(text: str) -> Appraisal:
    result = Appraisal()
    type_matches = [(match.start(), match.group(0), label) for pattern, label in TYPE_PATTERNS
                    if (match := re.search(pattern, text, re.I))]
    if type_matches:
        _, evidence, label = min(type_matches)
        result.tipo_imovel = cite(label, evidence)

    address = first_line(text, [r"endereço", r"localização", r"\blocal:", r"\brua\b",
                                     r"\bav\.", r"\brodovia\b", r"\balameda\b", r"bem avaliando:"])
    if address:
        match = re.search(r"(?:Endere[cç]o(?: do im[oó]vel)?|Localiza[cç][aã]o do bem|Local):\s*(.+)", address, re.I)
        if match:
            result.endereco = cite(match.group(1).strip().rstrip("."), match.group(0))
        else:
            result.endereco = cite(address.rstrip("."), address, "baixa")

    area_patterns = {
        "area_privativa_m2": [rf"[aá]rea privativa\s*[:=]?\s*({NUMBER})\s*(m²|m2)"],
        "area_total_m2": [rf"[aá]rea total\s*[:=]?\s*({NUMBER})\s*(m²|m2)"],
        "area_terreno_m2": [rf"[aá]rea (?:do )?terreno\s*[:=]?\s*({NUMBER})\s*(m²|m2|ha)",
                            rf"\bterreno\s*(?::|com|de)?\s*({NUMBER})\s*(m²|m2|ha)",
                            rf"\blote de\s*({NUMBER})\s*(m²|m2|ha)",
                            rf"[aá]rea do lote\s*({NUMBER})\s*(m²|m2|ha)",
                            rf"\bsuperf[ií]cie\s*[:=]?\s*({NUMBER})\s*(m²|m2|ha)"],
        "area_construida_m2": [rf"[aá]rea (?:constru[ií]da|edificada|coberta)\s*(?:(?:de|aproximada)\s*)?[:=]?\s*({NUMBER})\s*(m²|m2)",
                               rf"({NUMBER})\s*(m²|m2)\s+de [aá]rea constru[ií]da",
                               rf"benfeitorias constru[ií]das\s*[:=]?\s*({NUMBER})\s*(m²|m2)"],
    }
    for field, patterns in area_patterns.items():
        evidence, distinct = find_area(text, patterns)
        if field == "area_total_m2":
            # An alternative number explicitly stated as a conflicting table entry.
            table = re.search(r"tabela interna registra\s*(" + NUMBER + r")\s*(m²|m2)", text, re.I)
            if table:
                distinct = sorted(set(distinct + [br_number(table.group(1))]))
                if len(distinct) > 1:
                    evidence = Evidence[float]()
        if len(distinct) > 1:
            result.avisos.append(f"Contradição em {field}: valores explícitos {distinct}; valor nulo para revisão.")
        setattr(result, field, evidence)

    year = re.search(r"(?:ano (?:de constru[cç][aã]o|das edifica[cç][oõ]es|informado|de conclus[aã]o)?|"
                     r"constru[ií]d[oa] em|constru[cç][aã]o:)\s*(?:informado pelo propriet[aá]rio)?\s*[:]?\s*(\d{4})\b", text, re.I)
    if not year:
        year = re.search(r"\b(\d{4}) de constru[cç][aã]o\b", text, re.I)
    if year:
        result.ano_construcao = cite(int(year.group(1)), year.group(0))

    value = re.search(r"R\$\s*(" + NUMBER + r")", text)
    if value:
        result.valor_avaliacao_brl = cite(br_number(value.group(1)), value.group(0))
    registration = re.search(r"matr[ií]cula\s*:?\s*(?:n[ºo.]\s*)?(" + r"\d{1,3}(?:\.\d{3})*" + r")\b", text, re.I)
    if registration:
        result.matricula = cite(registration.group(1), registration.group(0))

    burden = first_line(text, [r"[ôo]nus", r"gravames", r"certid[aã]o", r"penhora", r"hipoteca",
                               r"aliena[cç][aã]o fiduci[aá]ria", r"servid[aã]o"])
    if burden:
        result.onus = cite(burden, burden)
        lower = burden.casefold()
        unknown = any(part in lower for part in ["não inform", "sem informa", "nada inform",
                  "não consta informação", "não foi possível verificar", "não há menção"])
        canceled = "cancelada" in lower
        if not unknown and not canceled:
            if any(part in lower for part in ["não foram identificados", "sem gravames",
                    "inexistência de ônus", "não há ônus"]):
                result.tem_onus = cite(False, burden)
            elif any(part in lower for part in ["alienação fiduciária", "penhora averbada",
                      "hipoteca ativa", "servidão de passagem", "reserva legal registrada"]):
                result.tem_onus = cite(True, burden)
        if canceled:
            result.avisos.append("Penhora cancelada sem data ou certidão atual; existência atual de ônus indeterminada.")

    date_lines = [line.strip() for line in text.splitlines()
                  if re.search(r"vistori|inspe[cç][aã]o|visita t[eé]cnica|levantamento", line, re.I)
                  and re.search(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{1,2} de [a-zç]+ de \d{4}", line, re.I)]
    date_line = date_lines[0] if date_lines else None
    if date_line:
        numeric = re.search(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b", date_line)
        words = re.search(r"\b(\d{1,2}) de (" + "|".join(MONTHS) + r") de (\d{4})\b", date_line, re.I)
        try:
            if numeric:
                result.data_vistoria = cite(date(int(numeric.group(3)), int(numeric.group(2)),
                                                 int(numeric.group(1))).isoformat(), numeric.group(0))
            elif words:
                result.data_vistoria = cite(date(int(words.group(3)), MONTHS[words.group(2).casefold()],
                                                 int(words.group(1))).isoformat(), words.group(0))
        except ValueError:
            result.avisos.append("Data de vistoria inválida no texto; valor nulo.")

    professional = first_line(text, [r"respons[aá]vel", r"avaliador", r"avaliadora",
                                      r"perit[oa]", r"elaborado por", r"^RT:"])
    if professional:
        license_match = re.search(r"\b(CREA(?:-[A-Z]{2})?\s*[A-Z0-9/.-]+|CAU\s*[A-Z0-9/.-]+|CNAI\s*\d+)\b", professional, re.I)
        if license_match:
            result.registro_profissional = cite(license_match.group(1).rstrip("."), license_match.group(0))
        name_source = re.sub(r"^.*?(?:respons[aá]vel(?: t[eé]cnico| pelo trabalho)?|avaliador(?:a)?(?: respons[aá]vel)?|"
                             r"perit[oa](?: avaliador[a]?)?|elaborado por|RT)\s*:?\s*", "", professional, flags=re.I)
        name_source = re.sub(r"^(?:Eng\.|Arq\.)\s*", "", name_source)
        name_source = re.split(r"\s*[,(-]\s*(?:CREA|CAU|CNAI|Eng\.|Arq\.)|\s*[-(]\s*(?:CREA|CAU|CNAI)", name_source, flags=re.I)[0]
        name_source = re.sub(r"\s+(?:CREA|CAU|CNAI)\b.*$", "", name_source, flags=re.I).strip(" ,.-()")
        if name_source:
            result.responsavel_tecnico = cite(name_source, professional, "media")
    return result

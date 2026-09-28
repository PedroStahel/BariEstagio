"""Synthetic CSV cases for explicit treatment and row preservation."""

from pathlib import Path

import pandas as pd
from src.funnel.cleaning import clean


def test_clean_keeps_rows_and_flags_anomalies(tmp_path: Path) -> None:
    path = tmp_path / "proposals.csv"
    header = (
        "id_proposta,data_entrada,canal_origem,cidade,uf,tipo_imovel,valor_imovel,"
        "valor_solicitado,prazo_meses,score_credito,idade_cliente,renda_mensal_declarada,"
        "flag_cliente_recorrente,consultor_id,etapa_max_funil,status_final,"
        "tempo_analise_dias,data_assinatura_contrato,taxa_juros_aa"
    )
    rows = [
        "P1,2025-01-10,mídia paga ,São Paulo,sp,Terreno,100000,70000,120,700,14,5000,0,cons-001,7,Contratada,2,2025-01-09,1.2",
        'P2,11/01/2025,Mídia paga,São Paulo,SP,Apartamento,"R$ 200000",100000,120,700,30,5000,1,CONS-001,6,Contratada,1,2025-01-12,1.1',
        "P3,2025-13-01,Indicação,Santos,SP,Casa,abc,50000,120,700,30,5000,0,CONS-002,3,Reprovada crédito,3,,",
        "P4,2025-01-12,Indicação,Santos,SP,Casa,100000,50000,120,700,30,5000,0,CONS-002,3,Sem retorno,3,,",
    ]
    path.write_bytes((header + "\r\n" + "\r\n".join(rows) + "\r\n").encode("utf-8-sig"))
    before = path.read_bytes()
    source = pd.read_csv(path, dtype="string", keep_default_na=False, encoding="utf-8-sig")
    original = source.copy(deep=True)

    result, log = clean(source, {"EXCLUDE_PROPERTY_TYPES": []})

    assert len(result) == len(source)
    assert path.read_bytes() == before
    pd.testing.assert_frame_equal(source, original)
    first = result.set_index("id_proposta").loc["P1"]
    second = result.set_index("id_proposta").loc["P2"]
    third = result.set_index("id_proposta").loc["P3"]
    assert first["canal_origem"] == second["canal_origem"] == "Mídia paga"
    assert first["uf"] == "SP"
    assert first["consultor_id"] == "CONS-001"
    assert bool(first["idade_suspeita"])
    assert bool(first["etapa_invalida"])
    assert bool(first["assinatura_antes_da_entrada"])
    assert bool(first["flag_ltv_acima_politica"])
    assert bool(first["flag_status_etapa_incoerente"])
    assert first["tipo_imovel"] == "Terreno"
    assert abs(first["ltv_calc"] - 0.7) < 1e-12
    assert second["valor_imovel"] == 200000
    assert second["data_entrada"] == pd.Timestamp("2025-01-11")
    assert second["ano_mes_entrada"] == "2025-01"
    assert third["flag_parse_error_valor_imovel"]
    assert third["flag_parse_error_data_entrada"]
    assert pd.isna(third["ltv_calc"])
    assert pd.isna(third["data_entrada"])
    assert log["linhas afetadas"].ge(0).all()
    assert "unidade contraditória no dicionário" in set(log.problema)
    assert "tipo Terreno mantido" in set(log.problema)
    assert "falha de conversão numérica" in set(log.problema)
    assert "falha de conversão de data" in set(log.problema)

    sensitivity, log_sensitivity = clean(source, {"EXCLUDE_PROPERTY_TYPES": ["terreno"]})
    assert len(sensitivity) == len(source) - 1
    assert "P1" not in set(sensitivity.id_proposta)
    assert "exclusão de sensibilidade solicitada" in set(log_sensitivity.problema)


def test_missing_column_fails_explicitly() -> None:
    try:
        clean(pd.DataFrame({"id_proposta": ["P1"]}), {})
    except ValueError as exc:
        assert "Missing required columns" in str(exc)
    else:
        raise AssertionError("A missing required column should raise ValueError")

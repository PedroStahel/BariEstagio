"""Check denominators and the logistic fit on deliberately small synthetic data."""

import numpy as np
import pandas as pd

from src.funnel.analysis import fit_logistic, outcome_summary, wilson


def test_loss_denominators_and_uncertain_statuses() -> None:
    data = pd.DataFrame({
        "id_proposta": ["a", "b", "c", "d"],
        "flag_contratada": [False, False, False, True],
        "status_final": ["Sem retorno", "Desistiu", "Reprovada crédito", "Contratada"],
        "etapa_max_funil": [3, 3, 3, 6],
        "valor_solicitado": [100.0, 200.0, 300.0, 400.0],
    })
    all_losses = outcome_summary(data, False)
    without_uncertain = outcome_summary(data, True)
    assert int(all_losses.propostas.sum()) == 3
    assert all_losses.valor_solicitado.sum() == 600.0
    assert int(without_uncertain.propostas.sum()) == 1
    assert without_uncertain.valor_solicitado.sum() == 300.0


def test_wilson_and_logistic_direction() -> None:
    low, high = wilson(20, 100, .95)
    assert 0 <= low < .2 < high <= 1
    x = np.column_stack([np.ones(200), np.r_[np.zeros(100), np.ones(100)]])
    y = np.r_[np.ones(10), np.zeros(90), np.ones(30), np.zeros(70)]
    beta, covariance, gradient = fit_logistic(x, y)
    assert gradient < 1e-3
    assert np.exp(beta[1]) > 1
    assert covariance[1, 1] > 0

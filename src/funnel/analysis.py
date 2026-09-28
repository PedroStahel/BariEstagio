"""Reproducible descriptive analysis of the treated proposal funnel.

Run from the repository root: python3 -m src.funnel.analysis
All reported figures and charts are calculated from the treated CSV.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import chi2_contingency, norm


@dataclass(frozen=True)
class Assumptions:
    # Illustrative recovery fractions, not estimates of intervention effects.
    no_response_recovery: float = 0.08
    documentation_recovery: float = 0.15
    correspondent_dropout_recovery: float = 0.05
    confidence_level: float = 0.95
    maturity_quantile: float = 0.90
    max_ltv: float = 0.60


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pct(value: float) -> str:
    return f"{100 * value:.2f}%".replace(".", ",")


def md_table(frame: pd.DataFrame, formats: dict[str, object] | None = None) -> str:
    frame = frame.copy()
    for column, formatter in (formats or {}).items():
        frame[column] = frame[column].map(formatter)
    def cell(value: object) -> str:
        if pd.isna(value):
            return "—"
        return str(value).replace("|", r"\|").replace("\n", " ")
    header = "| " + " | ".join(map(str, frame.columns)) + " |"
    divider = "| " + " | ".join("---" for _ in frame.columns) + " |"
    rows = ["| " + " | ".join(cell(value) for value in row) + " |"
            for row in frame.itertuples(index=False, name=None)]
    return "\n".join([header, divider, *rows])


def wilson(successes: int, total: int, confidence: float) -> tuple[float, float]:
    if not total:
        return np.nan, np.nan
    z = norm.ppf((1 + confidence) / 2)
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return center - radius, center + radius


def two_group_p(left: pd.DataFrame, right: pd.DataFrame) -> float:
    a = int(left.flag_contratada.sum())
    b = int(right.flag_contratada.sum())
    if min(len(left), len(right)) == 0:
        return np.nan
    return float(chi2_contingency([[a, len(left) - a], [b, len(right) - b]], correction=False).pvalue)


def cohort_table(df: pd.DataFrame, frequency: str, mature: pd.Series) -> pd.DataFrame:
    cohort = df.data_entrada.dt.to_period(frequency).astype(str)
    result = []
    for name, group in df.groupby(cohort, sort=True):
        eligible = group[mature.loc[group.index]]
        result.append({"coorte": name, "N total": len(group), "contratos total": int(group.flag_contratada.sum()),
                       "taxa ingênua": group.flag_contratada.mean(), "N maduro": len(eligible),
                       "contratos maduros": int(eligible.flag_contratada.sum()),
                       "taxa madura": eligible.flag_contratada.mean() if len(eligible) else np.nan})
    return pd.DataFrame(result)


def grouped_rates(df: pd.DataFrame, group: pd.Series, confidence: float) -> pd.DataFrame:
    def label_text(value: object) -> str:
        if isinstance(value, pd.Interval):
            left = "-∞" if np.isneginf(value.left) else f"{value.left:.2f}".replace(".", ",")
            right = "+∞" if np.isposinf(value.right) else f"{value.right:.2f}".replace(".", ",")
            return f"({left}; {right}]"
        return str(value)

    rows = []
    for label, part in df.groupby(group, observed=True, dropna=False):
        n = len(part)
        contracts = int(part.flag_contratada.sum())
        lower, upper = wilson(contracts, n, confidence)
        rows.append({"grupo": label_text(label), "N": n, "contratos": contracts,
                     "taxa": contracts / n, "IC inferior": lower, "IC superior": upper})
    return pd.DataFrame(rows)


def design_matrix(df: pd.DataFrame, numeric: dict[str, tuple[str, float]],
                  categorical: dict[str, str], binary: list[str]) -> tuple[np.ndarray, list[str], dict[str, float]]:
    columns = [np.ones(len(df))]
    names = ["intercept"]
    standard_deviations = {}
    for label, (source, step) in numeric.items():
        values = df[source].to_numpy(dtype=float) / step
        mean, std = float(values.mean()), float(values.std())
        if std <= 0:
            raise ValueError(f"Constant numeric predictor: {source}")
        columns.append((values - mean) / std)
        names.append(label)
        standard_deviations[label] = std
    for name in binary:
        columns.append(df[name].to_numpy(dtype=float))
        names.append(name)
    for source, reference in categorical.items():
        levels = sorted(df[source].dropna().unique())
        if reference not in levels:
            raise ValueError(f"Reference {reference} not found in {source}")
        for level in levels:
            if level != reference:
                columns.append(df[source].eq(level).to_numpy(dtype=float))
                names.append(f"{source}={level} (ref. {reference})")
    return np.column_stack(columns), names, standard_deviations


def fit_logistic(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Unpenalized binomial logit; Wald intervals from observed Fisher information."""
    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        linear = x @ beta
        loss = np.logaddexp(0, linear).sum() - np.dot(y, linear)
        gradient = x.T @ (expit(linear) - y)
        return float(loss), gradient

    result = minimize(objective, np.zeros(x.shape[1]), method="BFGS", jac=True,
                      options={"gtol": 1e-5, "maxiter": 1000})
    gradient_norm = float(np.max(np.abs(result.jac)))
    if gradient_norm > 1e-3:
        raise RuntimeError(f"Logistic fit did not converge: {result.message}; gradient={gradient_norm}")
    probability = expit(x @ result.x)
    information = x.T @ (x * (probability * (1 - probability))[:, None])
    if np.linalg.matrix_rank(information) != information.shape[0]:
        raise RuntimeError("Logistic design is rank deficient")
    covariance = np.linalg.inv(information)
    return result.x, covariance, gradient_norm


def model_table(beta: np.ndarray, covariance: np.ndarray, names: list[str],
                standard_deviations: dict[str, float], confidence: float) -> pd.DataFrame:
    z = norm.ppf((1 + confidence) / 2)
    rows = []
    for i, name in enumerate(names):
        if name == "intercept":
            continue
        scale = standard_deviations.get(name, 1.0)
        estimate = beta[i] / scale
        se = np.sqrt(covariance[i, i]) / scale
        rows.append({"variável / contraste": name, "OR": np.exp(estimate),
                     "IC inferior": np.exp(estimate - z * se),
                     "IC superior": np.exp(estimate + z * se),
                     "p Wald": 2 * norm.sf(abs(estimate / se))})
    return pd.DataFrame(rows)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["data_entrada"] = pd.to_datetime(df["data_entrada"], format="%Y-%m-%d", errors="raise")
    numeric = ["valor_solicitado", "ltv_calc", "score_credito", "prazo_meses", "idade_cliente",
               "renda_mensal_declarada", "flag_cliente_recorrente", "tempo_analise_dias"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="raise")
    for column in ["flag_contratada", "flag_ltv_acima_politica", "etapa_invalida", "idade_suspeita"]:
        if not set(df[column].dropna().unique()).issubset({True, False}):
            raise ValueError(f"Unexpected boolean values in {column}")
        df[column] = df[column].astype(bool)
    return df


def outcome_summary(df: pd.DataFrame, uncertain_as_open: bool) -> pd.DataFrame:
    losses = df.loc[~df.flag_contratada]
    if uncertain_as_open:
        losses = losses.loc[~losses.status_final.isin(["Sem retorno", "Desistiu"])]
    summary = losses.groupby(["etapa_max_funil", "status_final"], dropna=False).agg(
        propostas=("id_proposta", "size"), valor_solicitado=("valor_solicitado", "sum")
    ).reset_index().sort_values(["etapa_max_funil", "status_final"])
    summary["ticket_medio"] = summary.valor_solicitado / summary.propostas
    return summary


def scenario(df: pd.DataFrame, label: str, mature: pd.Series) -> dict:
    early = df.loc[mature & df.data_entrada.between("2025-01-01", "2025-06-30")]
    late = df.loc[mature & df.data_entrada.between("2025-07-01", "2025-12-31")]
    corr = df.loc[df.canal_origem.eq("Correspondente")]
    other = df.loc[~df.canal_origem.eq("Correspondente")]
    losses = outcome_summary(df, False)
    stage = losses.groupby("etapa_max_funil").valor_solicitado.sum()
    leading_stage = int(stage.idxmax()) if len(stage) else None
    model_data = df.dropna(subset=["canal_origem", "ltv_calc", "score_credito", "tipo_imovel", "uf"]).copy()
    model_data["is_correspondent"] = model_data.canal_origem.eq("Correspondente").astype(int)
    design, names, _ = design_matrix(
        model_data, {"ltv +0.10": ("ltv_calc", .10), "score +100": ("score_credito", 100)},
        {"tipo_imovel": "Apartamento", "uf": "SP"}, ["is_correspondent"])
    coefficients, _, _ = fit_logistic(design, model_data.flag_contratada.to_numpy(dtype=float))
    adjusted_or = float(np.exp(coefficients[names.index("is_correspondent")]))
    return {"cenário": label, "N": len(df), "contratos": int(df.flag_contratada.sum()),
            "taxa total": df.flag_contratada.mean(), "N antes": len(early), "N depois": len(late),
            "taxa antes": early.flag_contratada.mean(), "taxa depois": late.flag_contratada.mean(),
            "diferença recente (pp)": 100 * (late.flag_contratada.mean() - early.flag_contratada.mean()),
            "N corr.": len(corr), "N outros": len(other),
            "diferença corr. (pp)": 100 * (corr.flag_contratada.mean() - other.flag_contratada.mean()),
            "OR corr. ajustado": adjusted_or,
            "etapa maior valor": leading_stage}


def plot_bar(frame: pd.DataFrame, x: str, y: str, title: str, ylabel: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(frame[x].astype(str), frame[y], color="#265c83")
    ax.set(title=title, xlabel=x, ylabel=ylabel)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_cohorts(frame: pd.DataFrame, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(frame.coorte, frame["taxa ingênua"] * 100, marker="o", label="Ingênua: todas as propostas")
    ax.plot(frame.coorte, frame["taxa madura"] * 100, marker="s", label="Apenas coortes maduras")
    ax.set(title=title, xlabel="Coorte de entrada", ylabel="Contratação (%)")
    ax.tick_params(axis="x", rotation=60)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def generate(df: pd.DataFrame, output: Path, assumptions: Assumptions) -> str:
    output.mkdir(parents=True, exist_ok=True)
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    n = len(df)
    contracts = int(df.flag_contratada.sum())
    horizon = int(np.ceil(df.tempo_analise_dias.quantile(assumptions.maturity_quantile)))
    median = float(df.tempo_analise_dias.median())
    # No extraction timestamp exists. This is only a proxy from fields in the file.
    proxy_cutoff = (df.data_entrada + pd.to_timedelta(df.tempo_analise_dias, unit="D")).max()
    mature = (proxy_cutoff - df.data_entrada).dt.days.ge(horizon)
    monthly = cohort_table(df, "M", mature)
    quarterly = cohort_table(df, "Q", mature)

    losses = outcome_summary(df, False)
    firm = outcome_summary(df, True)
    by_stage = losses.groupby("etapa_max_funil").agg(propostas=("propostas", "sum"),
                                                     valor_solicitado=("valor_solicitado", "sum")).reset_index()
    by_stage["valor_milhoes"] = by_stage.valor_solicitado / 1_000_000
    firm_stage = firm.groupby("etapa_max_funil").agg(propostas=("propostas", "sum"),
                                                     valor_solicitado=("valor_solicitado", "sum")).reset_index()
    plot_bar(by_stage, "etapa_max_funil", "valor_milhoes", "Valor solicitado sem contratação por etapa",
             "Valor solicitado (R$ milhões)", figures / "perda_por_etapa.png")
    plot_cohorts(monthly, "Conversão mensal por coorte de entrada", figures / "coortes_mensais.png")
    plot_cohorts(quarterly, "Conversão trimestral por coorte de entrada", figures / "coortes_trimestrais.png")

    channels = grouped_rates(df, df.canal_origem, assumptions.confidence_level)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(channels.grupo, channels.taxa * 100, color="#265c83")
    ax.errorbar(channels.grupo, channels.taxa * 100,
                yerr=[(channels.taxa - channels["IC inferior"]) * 100,
                      (channels["IC superior"] - channels.taxa) * 100], fmt="none", color="black", capsize=3)
    ax.set(title="Contratação por canal (IC Wilson)", xlabel="Canal", ylabel="Contratação (%)")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(figures / "canais.png", dpi=160)
    plt.close(fig)

    crosstab = pd.crosstab(df.canal_origem, df.flag_contratada)
    chi = chi2_contingency(crosstab, correction=False)
    corr = df.loc[df.canal_origem.eq("Correspondente")]
    other = df.loc[~df.canal_origem.eq("Correspondente")]
    raw_difference = corr.flag_contratada.mean() - other.flag_contratada.mean()
    mix = pd.DataFrame([
        {"grupo": label, "N": len(group), "LTV médio": group.ltv_calc.mean(),
         "score médio": group.score_credito.mean(), "acima do teto": group.flag_ltv_acima_politica.mean(),
         "Terreno": group.tipo_imovel.eq("Terreno").mean(), "UF SP": group.uf.eq("SP").mean()}
        for label, group in [("Correspondente", corr), ("Demais", other)]
    ])

    model_columns = ["flag_contratada", "canal_origem", "ltv_calc", "score_credito", "tipo_imovel", "uf",
                     "valor_solicitado", "prazo_meses", "idade_cliente", "renda_mensal_declarada", "flag_cliente_recorrente"]
    model_df = df.dropna(subset=model_columns).copy()
    model_df["is_correspondent"] = model_df.canal_origem.eq("Correspondente").astype(int)
    x_adjusted, names_adjusted, std_adjusted = design_matrix(
        model_df, {"ltv +0.10": ("ltv_calc", 0.10), "score +100": ("score_credito", 100)},
        {"tipo_imovel": "Apartamento", "uf": "SP"}, ["is_correspondent"])
    y = model_df.flag_contratada.to_numpy(dtype=float)
    beta_adjusted, cov_adjusted, gradient_adjusted = fit_logistic(x_adjusted, y)
    adjusted = model_table(beta_adjusted, cov_adjusted, names_adjusted, std_adjusted, assumptions.confidence_level)
    adjusted_corr = adjusted.loc[adjusted["variável / contraste"].eq("is_correspondent")].iloc[0]
    channel_index = names_adjusted.index("is_correspondent")
    x_as_corr = x_adjusted.copy(); x_as_corr[:, channel_index] = 1
    x_as_other = x_adjusted.copy(); x_as_other[:, channel_index] = 0
    standardized_difference = expit(x_as_corr @ beta_adjusted).mean() - expit(x_as_other @ beta_adjusted).mean()

    numeric = {"ltv +0.10": ("ltv_calc", 0.10), "score +100": ("score_credito", 100),
               "ticket +R$100 mil": ("valor_solicitado", 100_000), "prazo +12 meses": ("prazo_meses", 12),
               "idade +10 anos": ("idade_cliente", 10), "renda +R$1 mil": ("renda_mensal_declarada", 1_000)}
    categories = {"canal_origem": "Organico", "tipo_imovel": "Apartamento", "uf": "SP"}
    x_full, names_full, std_full = design_matrix(model_df, numeric, categories, ["flag_cliente_recorrente"])
    beta_full, cov_full, gradient_full = fit_logistic(x_full, y)
    model = model_table(beta_full, cov_full, names_full, std_full, assumptions.confidence_level)

    bins = {
        "canal": df.canal_origem, "LTV": pd.cut(df.ltv_calc, [-np.inf, .4, .5, .6, np.inf]),
        "tipo de imóvel": df.tipo_imovel,
        "score (quartis)": pd.qcut(df.score_credito, 4, duplicates="drop"),
        "ticket (quartis)": pd.qcut(df.valor_solicitado, 4, duplicates="drop"),
        "UF": df.uf, "cidade": df.cidade,
        "prazo": pd.cut(df.prazo_meses, [0, 84, 120, 180, np.inf]),
        "idade": pd.cut(df.idade_cliente, [0, 29, 44, 59, np.inf]),
        "renda (quartis)": pd.qcut(df.renda_mensal_declarada, 4, duplicates="drop"),
        "recorrência": df.flag_cliente_recorrente,
    }
    univariate = {name: grouped_rates(df, group, assumptions.confidence_level) for name, group in bins.items()}

    cases = [scenario(df, "Base: todos / Sem retorno como perda", mature),
             scenario(df.loc[~df.tipo_imovel.eq("Terreno")], "Sem Terreno", mature),
             scenario(df.loc[~df.flag_ltv_acima_politica], "Somente LTV <= teto", mature),
             scenario(df.loc[~df.status_final.eq("Sem retorno")], "Sem retorno em aberto (fora do denominador)", mature)]
    sensitivity = pd.DataFrame(cases)

    # Disjoint, policy-eligible scenario populations. These are potential requested
    # credit volumes, never revenue or a causal estimate of an intervention.
    eligible = df.loc[~df.flag_ltv_acima_politica & ~df.etapa_invalida & ~df.idade_suspeita]
    populations = [
        ("1. Retomar propostas sem retorno", eligible.loc[eligible.status_final.eq("Sem retorno")], assumptions.no_response_recovery,
         "Contato estruturado resolve uma fração parametrizada dos casos; testar abordagem aleatorizada."),
        ("2. Destravar documentação pendente", eligible.loc[eligible.status_final.eq("Documentação pendente")], assumptions.documentation_recovery,
         "Checklist e apoio documental convertem uma fração parametrizada; testar por equipe/rodízio."),
        ("3. Investigar desistência de correspondentes", eligible.loc[eligible.status_final.eq("Desistiu") & eligible.canal_origem.eq("Correspondente")], assumptions.correspondent_dropout_recovery,
         "Revisão de atendimento recupera uma fração parametrizada; comparar grupos de correspondentes."),
    ]
    recommendations = pd.DataFrame([{"prioridade e ação": name, "N elegível": len(group),
                                     "valor elegível": group.valor_solicitado.sum(), "premissa de recuperação": fraction,
                                     "contratos esperados": len(group) * fraction,
                                     "R$ solicitado esperado": group.valor_solicitado.sum() * fraction,
                                     "hipótese / validação": description}
                                    for name, group, fraction, description in populations])

    first = df.loc[mature & df.data_entrada.between("2025-01-01", "2025-06-30")]
    last = df.loc[mature & df.data_entrada.between("2025-07-01", "2025-12-31")]
    p_period = two_group_p(first, last)
    risk_delta = last.flag_contratada.mean() - first.flag_contratada.mean()
    firm_top = firm_stage.sort_values("valor_solicitado", ascending=False).iloc[0]
    all_top = by_stage.sort_values("valor_solicitado", ascending=False).iloc[0]
    threshold_contracts = int(df.loc[df.flag_ltv_acima_politica, "flag_contratada"].sum())

    lines = ["# Diagnóstico do funil — Parte 1", "",
             "Valores em R$ representam **crédito solicitado potencial**, não receita nem lucro realizado. "
             "As propostas sintéticas não permitem inferir causalidade.", "",
             f"Base: N={n} propostas; contratos={contracts}/{n} ({pct(contracts/n)}). "
             f"A base tratada manteve todos os registros; indicadores de qualidade permanecem como flags.", "",
             "## 1. Onde se concentra o valor sem contratação", "",
             "O estágio atribuído é a **etapa máxima atingida**, não uma medida do valor gerado na etapa. "
             "Não se conhece margem, receita ou probabilidade contrafactual de contratação.", "",
             "### Todos os status não contratados", "",
             md_table(losses, {"valor_solicitado": money, "ticket_medio": money}), "",
             f"Total: {int(losses.propostas.sum())}/{n} propostas sem contratação, "
             f"{money(losses.valor_solicitado.sum())} solicitados. A etapa {int(all_top.etapa_max_funil)} "
             f"concentra {int(all_top.propostas)}/{int(losses.propostas.sum())} dessas propostas e "
             f"{money(all_top.valor_solicitado)} ({pct(all_top.valor_solicitado/losses.valor_solicitado.sum())} do valor).", "",
             "### Sem contar `Sem retorno` e `Desistiu` como perdas", "",
             md_table(firm, {"valor_solicitado": money, "ticket_medio": money}), "",
             f"Nesse enquadramento, {int(firm.propostas.sum())}/{n} propostas somam "
             f"{money(firm.valor_solicitado.sum())}; a etapa {int(firm_top.etapa_max_funil)} lidera com "
             f"{int(firm_top.propostas)}/{int(firm.propostas.sum())} propostas e {money(firm_top.valor_solicitado)} "
             f"({pct(firm_top.valor_solicitado/firm.valor_solicitado.sum())} do valor deste cenário). "
             "`Sem retorno` pode estar aberto; `Desistiu` pode ser perda final ou recuperável. "
             "`Documentação pendente` também pode estar aberta neste segundo cenário. "
             "Não há data ou regra de encerramento para decidir.", "",
             "![Valor solicitado sem contratação por etapa](figures/perda_por_etapa.png)", "",
             "## 2. Percepção da liderança", "",
             f"**Maturação.** Mediana de `tempo_analise_dias`={median:.0f} dias (N={n}); "
             f"percentil {int(assumptions.maturity_quantile*100)}={horizon} dias (N={n}). "
             f"Sem data de extração, o corte **proxy** é o maior `data_entrada + tempo_analise_dias`: "
             f"{proxy_cutoff.date()}. Só se considera madura a proposta com ao menos {horizon} dias até esse corte. "
             "É uma restrição de exposição, não uma correção estatística identificada de censura; "
             "o tempo de análise dos casos ainda abertos pode não representar seu futuro desfecho.", "",
             "### Coortes mensais: ingênua e apenas maduras", "",
             md_table(monthly, {"taxa ingênua": pct, "taxa madura": pct}), "",
             "![Coortes mensais](figures/coortes_mensais.png)", "",
             "### Coortes trimestrais: ingênua e apenas maduras", "",
             md_table(quarterly, {"taxa ingênua": pct, "taxa madura": pct}), "",
             "![Coortes trimestrais](figures/coortes_trimestrais.png)", "",
             f"O filtro proxy retira {int((~mature).sum())}/{n} propostas recentes; "
             "curvas muito próximas não validam a ausência de censura real.", "",
             f"Comparação predefinida entre os dois semestres de 2025 **somente entre maduras**: "
             f"{int(first.flag_contratada.sum())}/{len(first)} ({pct(first.flag_contratada.mean())}) no primeiro e "
             f"{int(last.flag_contratada.sum())}/{len(last)} ({pct(last.flag_contratada.mean())}) no segundo; "
             f"diferença={100*risk_delta:.2f} pontos percentuais, qui-quadrado p={p_period:.4g}. "
             "O sentido da diferença é descritivo; múltiplas comparações exploratórias e o corte proxy reduzem a confiança.", "",
             "### Canal", "",
             md_table(channels, {"taxa": pct, "IC inferior": pct, "IC superior": pct}), "",
             "![Contratação por canal](figures/canais.png)", "",
             "Mix observado de Correspondente e demais canais (cada proporção usa o N da linha):", "",
             md_table(mix, {"LTV médio": lambda x: f"{x:.3f}", "score médio": lambda x: f"{x:.1f}",
                            "acima do teto": pct, "Terreno": pct, "UF SP": pct}), "",
             f"Qui-quadrado global, N={n}, canais={len(channels)}, p={chi.pvalue:.4g}. "
             f"Correspondente: {int(corr.flag_contratada.sum())}/{len(corr)}; demais canais: "
             f"{int(other.flag_contratada.sum())}/{len(other)}; diferença bruta={100*raw_difference:.2f} pp. "
             f"Modelo ajustado por LTV, score, tipo de imóvel e UF: N={len(model_df)}/{n}, "
             f"OR Correspondente vs. demais={adjusted_corr['OR']:.3f} "
             f"(IC {int(assumptions.confidence_level*100)}% {adjusted_corr['IC inferior']:.3f}–{adjusted_corr['IC superior']:.3f}; "
             f"p={adjusted_corr['p Wald']:.4g}); diferença média padronizada={100*standardized_difference:.2f} pp. "
             "A mudança entre diferença bruta e ajustada sugere contribuição do mix observado; "
             "diferença residual pode refletir fatores não medidos, não efeito causal do canal.", "",
             "### Veredito", "",
             f"Queda recente: direção negativa entre maduras ({len(first)} e {len(last)} propostas nos períodos; "
             f"p={p_period:.4g}), com **confiança baixa** para afirmar uma queda sustentada: corte de extração desconhecido "
             "e `Sem retorno` ambíguo. Correspondente: taxa menor no total "
             f"({len(corr)} vs. {len(other)} propostas), ainda associada a menor contratação após ajuste "
             f"(N={len(model_df)}, IC ajustado acima); **confiança média** na associação observacional. "
             "O pedido de entender 'onde se perde dinheiro' deve ser refinado para valor solicitado, pois não há margem ou receita.", "",
             "## 3. Características associadas à contratação", "",
             "Taxas univariadas: N e contratos são os denominadores de cada faixa; quartis foram derivados desta base.", ""]
    for label, table in univariate.items():
        lines += [f"### {label}", "", md_table(table, {"taxa": pct, "IC inferior": pct, "IC superior": pct}), ""]
    lines += ["### Regressão logística multivariável", "",
              f"N={len(model_df)}/{n} propostas completas para as variáveis do modelo; "
              "evento=contratação. Referências explícitas na tabela. OR numérico por incremento descrito; "
              "IC Wald condicionado ao modelo. A implementação minimiza a log-verossimilhança binomial "
              "com `scipy.optimize` e calcula o erro padrão pela inversa da informação observada. "
              "Sem ajuste por dependência entre propostas do mesmo consultor.", "",
              md_table(model, {"OR": lambda x: f"{x:.3f}", "IC inferior": lambda x: f"{x:.3f}",
                               "IC superior": lambda x: f"{x:.3f}", "p Wald": lambda x: f"{x:.4g}"}), "",
              f"Gradiente final máximo: {gradient_full:.2g} (modelo completo); {gradient_adjusted:.2g} (canal ajustado). "
              "A forma linear no logit, correlação entre covariáveis e confundimento residual limitam interpretação. "
              "Associação **não** demonstra causalidade.", "",
              "## Sensibilidade das decisões", "",
              md_table(sensitivity, {"taxa total": pct, "taxa antes": pct, "taxa depois": pct,
                                     "diferença recente (pp)": lambda x: f"{x:.2f}",
                                     "diferença corr. (pp)": lambda x: f"{x:.2f}",
                                     "OR corr. ajustado": lambda x: f"{x:.3f}"}), "",
              f"Entre os {len(sensitivity)} cenários, o sinal da diferença recente é "
              f"{'sempre negativo' if sensitivity['diferença recente (pp)'].lt(0).all() else 'não é estável'} "
              f"e o de Correspondente é "
              f"{'sempre negativo' if sensitivity['diferença corr. (pp)'].lt(0).all() else 'não é estável'}; "
              f"o OR ajustado de Correspondente é "
              f"{'menor que 1 em todos' if sensitivity['OR corr. ajustado'].lt(1).all() else 'não é estável'}; "
              f"a etapa de maior valor {'permanece a mesma' if sensitivity['etapa maior valor'].nunique() == 1 else 'muda'} "
              f"(N por cenário: {', '.join(str(v) for v in sensitivity['N'])}). "
              f"Se `Sem retorno` **e** `Desistiu` forem retirados juntos, a etapa líder passa a "
              f"{int(firm_top.etapa_max_funil)} ({int(firm.propostas.sum())}/{n} propostas no cenário). "
              "A força estatística e a interpretação de status aberto ainda dependem da definição de desfecho.", "",
              f"Contratos acima do teto de LTV: {threshold_contracts}/{contracts}; "
              f"o cenário sem esses casos remove {int(df.flag_ltv_acima_politica.sum())}/{n} propostas, "
              "apenas para sensibilidade. `Sem retorno` em aberto sai do denominador de conversão, "
              "mas permanece no valor em acompanhamento. Cada cenário é isolado, não acumulado.", "",
              "## 4. Recomendações priorizadas: cenários, não previsões", "",
              "Elegibilidade dos cenários: LTV até o teto, etapa válida e idade não suspeita; "
              "as três populações por status não se sobrepõem. Recuperações parametrizadas não são efeitos medidos. "
              "O R$ é soma proporcional do crédito solicitado, nunca receita projetada.", "",
              md_table(recommendations, {"valor elegível": money, "premissa de recuperação": pct,
                                         "contratos esperados": lambda x: f"{x:.2f}",
                                         "R$ solicitado esperado": money}), "",
              "Validação sugerida: definir status de encerramento e prazo de acompanhamento; medir "
              "contratos adicionais por grupo comparável com sorteio ou implantação escalonada, "
              "inclusive custo operacional e aprovação de crédito. Não implementar contratação acima da política.", "",
              "## Limites de confiança", "",
              f"Data de extração ausente (N={n}); status incertos somam "
              f"{int(df.status_final.isin(['Sem retorno','Desistiu']).sum())}/{n}; "
              f"contratos com LTV acima da política somam {threshold_contracts}/{contracts}. "
              "Essas três lacunas dominam a incerteza. Valores monetários não são perdas financeiras realizadas.", ""]
    report = "\n".join(lines)
    (output / "diagnostico.md").write_text(report, encoding="utf-8")
    print(f"N={n}; contratos={contracts}; horizonte={horizon} dias; corte proxy={proxy_cutoff.date()}")
    print(f"Canal global p={chi.pvalue:.4g}; Correspondente OR ajustado={adjusted_corr['OR']:.3f}")
    print(f"Tendência semestral madura p={p_period:.4g}; gradiente modelo={gradient_full:.2g}")
    print(f"Relatório: {output / 'diagnostico.md'}; figuras: {figures}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/propostas_clean.csv")
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--no-response-recovery", type=float, default=Assumptions.no_response_recovery)
    parser.add_argument("--documentation-recovery", type=float, default=Assumptions.documentation_recovery)
    parser.add_argument("--correspondent-dropout-recovery", type=float, default=Assumptions.correspondent_dropout_recovery)
    args = parser.parse_args()
    fractions = [args.no_response_recovery, args.documentation_recovery, args.correspondent_dropout_recovery]
    if any(not 0 <= value <= 1 for value in fractions):
        parser.error("Recovery fractions must be between 0 and 1")
    assumptions = Assumptions(no_response_recovery=fractions[0], documentation_recovery=fractions[1],
                              correspondent_dropout_recovery=fractions[2])
    frame = pd.read_csv(args.input)
    generate(prepare(frame), Path(args.output), assumptions)


if __name__ == "__main__":
    main()

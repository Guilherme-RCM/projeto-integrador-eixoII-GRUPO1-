"""Simulador e avaliação independentes da Sprint 4. Nenhum import do projeto original."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

INF = 100_000_000
ORIGINAIS = ['idade_divida_dias', 'dias_desde_inscricao', 'valor_relativo_credito',
             'creditos_inscritos_abertos_imovel', 'inadimplencias_imovel_t0',
             'inadimplente_ultimo_exercicio']
HISTORICOS = ['fracao_pagos_inscricao', 'log_outros_abertos_inscricao',
              'inad_ultimo_inscricao', 'sem_hist_inscricao']
ATRIBUTOS = ORIGINAIS + HISTORICOS


def day(value: str) -> int:
    return int(np.datetime64(value, 'D').astype(int))


def iso(value: int) -> str:
    return str(np.datetime64(int(value), 'D'))


def dates(series: pd.Series) -> np.ndarray:
    a = pd.to_datetime(series).to_numpy(dtype='datetime64[D]')
    return np.where(np.isnat(a), INF, a.astype(np.int64))


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(path: Path) -> dict:
    return {str(f.relative_to(path)).replace('\\', '/'): {'bytes': f.stat().st_size, 'sha256': file_hash(f)}
            for f in sorted(path.rglob('*')) if f.is_file()}


@dataclass
class Base:
    ids: np.ndarray
    credits: np.ndarray
    years: np.ndarray
    due: np.ndarray
    enrollment: np.ndarray
    payment: np.ndarray
    default: np.ndarray
    principal: np.ndarray
    relative: np.ndarray
    profile: dict


def load_base(source: Path) -> Base:
    cols = ['id_imovel', 'id_credito', 'exercicio', 'data_vencimento', 'data_inscricao',
            'data_pagamento', 'inadimplente', 'valor_principal_centavos', 'origem_dado']
    d = pd.read_csv(source, sep=';', usecols=cols).sort_values(['id_imovel', 'exercicio'])
    n, years = d.id_imovel.nunique(), np.sort(d.exercicio.unique())
    profile = {'linhas': len(d), 'imoveis': n, 'exercicios': years.tolist(),
               'colunas_lidas': cols, 'tipos': {k: str(v) for k, v in d.dtypes.items()},
               'nulos': {k: int(v) for k, v in d.isna().sum().items()},
               'duplicatas_credito': int(d.id_credito.duplicated().sum()),
               'duplicatas_imovel_exercicio': int(d.duplicated(['id_imovel', 'exercicio']).sum()),
               'origens': d.origem_dado.value_counts().to_dict()}
    assert len(d) == n * len(years)
    assert profile['duplicatas_credito'] == profile['duplicatas_imovel_exercicio'] == 0
    assert set(d.origem_dado.unique()) == {'SINTETICO'}
    shape = (n, len(years))
    assert np.all(d.exercicio.to_numpy().reshape(shape) == years[None, :])
    principal = d.valor_principal_centavos.to_numpy().reshape(shape)
    assert np.all(principal > 0)
    return Base(d.id_imovel.to_numpy().reshape(shape)[:, 0],
                d.id_credito.to_numpy().reshape(shape), years,
                dates(d.data_vencimento).reshape(shape), dates(d.data_inscricao).reshape(shape),
                dates(d.data_pagamento).reshape(shape), d.inadimplente.to_numpy().reshape(shape),
                principal, principal / np.median(principal, axis=0)[None, :], profile)


def enrollment_context(base: Base, payments: np.ndarray, column: int, rows: np.ndarray) -> np.ndarray:
    """Informações observáveis na inscrição, excluindo crédito-alvo das contagens."""
    t = base.enrollment[rows, column]
    matured = base.due[rows] <= t[:, None]
    other = matured.copy()
    other[:, column] = False
    paid = (payments[rows] <= t[:, None]) & other
    n = other.sum(axis=1)
    fraction = np.divide(paid.sum(axis=1), n, out=np.full(len(rows), .5), where=n > 0)
    open_count = n - paid.sum(axis=1)
    last = np.where(matured, np.arange(len(base.years))[None, :], -1).max(axis=1)
    assert np.all(last >= 0)
    return np.column_stack([fraction, np.log1p(open_count), base.default[rows, last], n == 0])


def intercept_for(score: np.ndarray, target: float) -> float:
    low, high = -30., 30.
    for _ in range(65):
        mid = (low + high) / 2
        if expit(mid + score).mean() < target:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def event_days(enrollment, budget, before, after, shock):
    """Inversão do risco acumulado por trechos; uma única data por crédito."""
    exposure = np.maximum(shock - enrollment, 0)
    consumed = before * exposure
    in_first = budget <= consumed
    early = enrollment + np.ceil(budget / before).astype(np.int64)
    late = np.maximum(enrollment, shock) + np.ceil(np.maximum(budget-consumed, 0) / after).astype(np.int64)
    return np.where(in_first, early, late)


@dataclass
class Simulation:
    payment: np.ndarray
    history: np.ndarray
    rate_before: np.ndarray
    rate_after: np.ndarray
    shock: int
    metadata: dict


def simulate(base: Base, protocol: dict, scenario: str, seed: int) -> Simulation:
    settings = protocol['cenarios'][scenario]
    strength = settings['intensidade']
    rng = np.random.default_rng(seed)
    latent = rng.normal(0, protocol['desvio_latente_imovel'], len(base.ids))
    budgets = rng.exponential(1., base.enrollment.shape)
    payments = np.where(base.enrollment < INF, INF, base.payment).copy()
    history = np.full((*base.enrollment.shape, 4), np.nan)
    before = np.zeros(base.enrollment.shape)
    after = np.zeros(base.enrollment.shape)
    shock = day(protocol['mudanca_em']) if settings['mudanca'] else INF // 2
    b = protocol['coeficientes']
    a0 = a1 = None
    calibration = {}
    for j in range(len(base.years)):
        rows = np.flatnonzero(base.enrollment[:, j] < INF)
        if not len(rows):
            continue
        h = enrollment_context(base, payments, j, rows)
        history[rows, j] = h
        observed = (b['fracao_pagos_inscricao_centrada'] * (h[:, 0]-.5)
                    + b['log_outros_abertos_inscricao'] * h[:, 1]
                    + b['inad_ultimo_inscricao'] * h[:, 2])
        z0 = strength * (observed + latent[rows])
        z1 = strength * (-observed + latent[rows]) if settings['mudanca'] else z0
        if a0 is None:
            a0 = intercept_for(z0, protocol['taxa_anual_coorte_referencia'])
            a1 = intercept_for(z1, protocol['taxa_anual_coorte_referencia'])
            calibration = {'exercicio_primeira_coorte': int(base.years[j]), 'n_coorte': len(rows),
                           'ultima_inscricao_coorte': iso(int(base.enrollment[rows, j].max())),
                           'intercepto_antes': a0, 'intercepto_depois': a1,
                           'media_probabilidade_antes': float(expit(a0+z0).mean()),
                           'media_probabilidade_depois': float(expit(a1+z1).mean())}
            assert base.enrollment[rows, j].max() < day(protocol['treino'][0])
        p0, p1 = expit(a0+z0), expit(a1+z1)
        l0, l1 = -np.log1p(-p0)/365, -np.log1p(-p1)/365
        before[rows, j], after[rows, j] = l0, l1
        payments[rows, j] = event_days(base.enrollment[rows, j], budgets[rows, j], l0, l1, shock)
    registered = base.enrollment < INF
    assert np.all(payments[registered] > base.enrollment[registered])
    assert np.array_equal(payments[~registered], base.payment[~registered])
    assert np.isfinite(history[registered]).all()
    return Simulation(payments, history, before, after, shock,
                      {'cenario': scenario, 'semente': seed, 'intensidade': strength,
                       'calibracao_intercepto': calibration,
                       'creditos_regenerados': int(registered.sum()),
                       'pagamentos_ate_corte': int((registered & (payments <= day(protocol['corte']))).sum())})


def snapshot(base: Base, sim: Simulation, date: str, protocol: dict) -> pd.DataFrame:
    t = day(date)
    end = t + protocol['horizonte_dias']
    assert end <= day(protocol['corte']), 'Rótulo imaturo'
    eligible = (base.enrollment <= t) & (sim.payment > t)
    r, c = np.where(eligible)
    matured = base.due <= t
    last = np.where(matured, np.arange(len(base.years))[None, :], -1).max(axis=1)
    pre = max(0, min(end, sim.shock)-t)
    post = protocol['horizonte_dias']-pre
    oracle = -np.expm1(-(sim.rate_before[r, c]*pre + sim.rate_after[r, c]*post))
    d = pd.DataFrame({
        'id_imovel': base.ids[r], 'id_credito': base.credits[r, c], 't0': date,
        'fim_rotulo': iso(end), 'principal_centavos': base.principal[r, c],
        'y': ((sim.payment[r, c] > t) & (sim.payment[r, c] <= end)).astype(int),
        'idade_divida_dias': t-base.due[r, c],
        'dias_desde_inscricao': t-base.enrollment[r, c],
        'valor_relativo_credito': base.relative[r, c],
        'creditos_inscritos_abertos_imovel': eligible.sum(axis=1)[r],
        'inadimplencias_imovel_t0': (base.default*matured).sum(axis=1)[r],
        'inadimplente_ultimo_exercicio': base.default[r, last[r]],
        'probabilidade_oraculo_PRIVILEGIADA': oracle,
        'imovel_novo': base.ids[r] % 5 == 0,
    })
    for i, col in enumerate(HISTORICOS):
        d[col] = sim.history[r, c, i]
    assert not d.duplicated(['id_credito', 't0']).any()
    assert not d[ATRIBUTOS].isna().any().any()
    assert (d.dias_desde_inscricao >= 0).all()
    return d


def datasets(base, sim, protocol):
    train = pd.concat([snapshot(base, sim, t, protocol) for t in protocol['treino']], ignore_index=True)
    valid = snapshot(base, sim, protocol['validacao'], protocol)
    test = snapshot(base, sim, protocol['teste'], protocol)
    result = {'treino': train.loc[~train.imovel_novo].copy(),
              'validacao': valid.loc[~valid.imovel_novo].copy(),
              'teste_carteira': test.loc[~test.imovel_novo].copy(),
              'teste_novos_imoveis': test.loc[test.imovel_novo].copy()}
    assert set(result['treino'].id_imovel).isdisjoint(result['teste_novos_imoveis'].id_imovel)
    assert set(result['validacao'].id_imovel).isdisjoint(result['teste_novos_imoveis'].id_imovel)
    assert result['treino'].fim_rotulo.max() < protocol['validacao']
    assert result['validacao'].fim_rotulo.max() < protocol['teste']
    return result


def top_weights(p: np.ndarray, fraction: float = .1, multiplicities=None) -> np.ndarray:
    """Top-k com desempate uniforme, inclusive quando todas as probabilidades são iguais."""
    weights = np.ones(len(p)) if multiplicities is None else np.asarray(multiplicities, dtype=float)
    k = max(1, round(fraction*weights.sum()))
    order = np.argsort(-p, kind='stable')
    boundary = np.searchsorted(np.cumsum(weights[order]), k, side='left')
    threshold = p[order[min(boundary, len(order)-1)]]
    above, equal = p > threshold, p == threshold
    remaining = k-weights[above].sum()
    fraction_equal = remaining / weights[equal].sum()
    return weights * (above.astype(float) + equal*fraction_equal)


def calibration(d, p):
    y = d.y.to_numpy()
    # Quantis com scores empatados mantidos juntos; a constante ocupa um só grupo.
    groups = pd.qcut(pd.Series(p), q=10, duplicates='drop')
    if groups.isna().all():
        bins = [{'n': len(y), 'previsto': float(np.mean(p)), 'observado': float(np.mean(y))}]
    else:
        frame = pd.DataFrame({'grupo': groups, 'p': p, 'y': y})
        bins = [{'n': len(g), 'previsto': float(g.p.mean()), 'observado': float(g.y.mean())}
                for _, g in frame.groupby('grupo', observed=True)]
    return bins


def metrics(d, p, prior, fraction=.1):
    y = d.y.to_numpy()
    value = d.principal_centavos.to_numpy(dtype=float)
    base_loss = np.mean((y-prior)**2)
    loss = float(brier_score_loss(y, p))
    w, wvalue = top_weights(p, fraction), top_weights(value, fraction)
    precision = float(np.dot(w, y)/w.sum())
    bins = calibration(d, p)
    total_paid = float(np.dot(value, y))
    return {
        'n': len(d), 'imoveis': int(d.id_imovel.nunique()), 'positivos': int(y.sum()),
        'prevalencia': float(y.mean()), 'media_prevista': float(np.mean(p)),
        'roc_auc': float(roc_auc_score(y, p)), 'average_precision': float(average_precision_score(y, p)),
        'brier': loss, 'brier_constante': float(base_loss), 'ganho_brier': float(base_loss-loss),
        'brier_skill': float(1-loss/base_loss), 'precisao_top10': precision,
        'lift_top10': float(precision/y.mean()),
        'erro_calibracao': float(np.mean(p)-y.mean()),
        'erro_abs_calibracao': float(abs(np.mean(p)-y.mean())),
        'ece10': float(sum(b['n']*abs(b['previsto']-b['observado']) for b in bins)/len(y)),
        'captura_principal_top10': float(np.dot(w, value*y)/total_paid),
        'captura_principal_regra_valor': float(np.dot(wvalue, value*y)/total_paid),
        'principal_observado_centavos': total_paid,
        'principal_previsto_centavos': float(np.dot(value, p)),
    }


def fit_models(train, protocol, seed):
    full = make_pipeline(StandardScaler(), LogisticRegression(**protocol['logistica'], random_state=seed))
    old = make_pipeline(StandardScaler(), LogisticRegression(**protocol['logistica'], random_state=seed))
    boosting = HistGradientBoostingClassifier(**protocol['boosting'], random_state=seed)
    full.fit(train[ATRIBUTOS], train.y)
    old.fit(train[ORIGINAIS], train.y)
    boosting.fit(train[ATRIBUTOS], train.y)
    return {'logistica': full, 'boosting': boosting, 'logistica_atributos_originais': old}


def predict(models, d, prior):
    predictions = {'constante': np.full(len(d), prior),
                   'oraculo_PRIVILEGIADO': d.probabilidade_oraculo_PRIVILEGIADA.to_numpy()}
    for name, model in models.items():
        features = ORIGINAIS if name == 'logistica_atributos_originais' else ATRIBUTOS
        predictions[name] = model.predict_proba(d[features])[:, 1]
    return predictions


def choose(valid, predictions, protocol):
    setting = protocol['selecao']
    scores = {name: float(brier_score_loss(valid.y, predictions[name])) for name in setting['ordem_simples']}
    best = min(scores.values())
    chosen = next(name for name in setting['ordem_simples'] if scores[name] <= best+setting['tolerancia_absoluta'])
    return chosen, scores


def paired_bootstrap(d, p, prior, repetitions, seed):
    y = d.y.to_numpy(dtype=float)
    _, inverse = np.unique(d.id_imovel.to_numpy(), return_inverse=True)
    ng = int(inverse.max()+1)
    delta = (y-prior)**2-(y-p)**2
    # Agrupar scores iguais permite reamostrar o topo sem repetir ordenações.
    scores, score_idx = np.unique(-p, return_inverse=True)
    ns = len(scores)
    rng = np.random.default_rng(seed)
    samples = np.empty((repetitions, 2))
    for j in range(repetitions):
        counts = np.bincount(rng.integers(0, ng, ng), minlength=ng)
        w = counts[inverse]
        n = w.sum()
        group_n = np.bincount(score_idx, weights=w, minlength=ns)
        group_y = np.bincount(score_idx, weights=w*y, minlength=ns)
        cumulative = np.cumsum(group_n)
        k = max(1, round(.1*n))
        at = int(np.searchsorted(cumulative, k, side='left'))
        previous = cumulative[at]-group_n[at]
        positive_top = group_y[:at].sum() + group_y[at]*(k-previous)/group_n[at]
        samples[j] = (np.dot(w, delta)/n, positive_top/k/(np.dot(w, y)/n))
    return {'unidade': 'imovel', 'reamostras': repetitions, 'semente': seed,
            'ic95_ganho_brier': np.quantile(samples[:, 0], [.025, .975]).tolist(),
            'ic95_lift_top10': np.quantile(samples[:, 1], [.025, .975]).tolist(),
            'limite': 'Modelo fixo; bootstrap descritivo da primeira replica, separado do IC Monte Carlo.'}

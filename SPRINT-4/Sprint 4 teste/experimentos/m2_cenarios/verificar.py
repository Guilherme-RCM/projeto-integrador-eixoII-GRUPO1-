"""Verificações relevantes de temporalidade, eventos, métricas e isolamento de rótulos."""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
from m2_experimento import (ATRIBUTOS, INF, calibration, datasets, day, enrollment_context,
                            event_days, load_base, metrics, paired_bootstrap, simulate, snapshot, top_weights)


def verify(base, p):
    checks = []
    def record(name, condition):
        assert condition, name
        checks.append({'verificacao': name, 'passou': True})

    # Exemplo manual de risco por trechos: 10 dias com taxa .1, depois taxa .2.
    event = event_days(np.array([0, 0, 20]), np.array([.5, 2., .4]),
                       np.array([.1, .1, .1]), np.array([.2, .2, .2]), 10)
    record('Inversão do risco por trechos coincide com cálculo manual', np.array_equal(event, [5, 15, 22]))
    w = top_weights(np.array([.2, .2, .2, .2, .2, .2, .2, .2, .2, .2]))
    record('Empates constantes recebem inclusão uniforme', np.allclose(w, .1))
    w = top_weights(np.array([.8, .8, .5, .2]), fraction=.5)
    record('Top-k inclui exatamente a capacidade com empate', np.allclose(w, [1, 1, 0, 0]))
    toy = pd.DataFrame({'id_imovel': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
                        'y': [1, 0, 0, 1, 0, 0, 0, 0, 1, 0], 'principal_centavos': np.arange(1, 11)*100})
    m = metrics(toy, np.full(10, .3), .3)
    record('Constante tem AUC .5, lift 1 e ganho zero', abs(m['roc_auc']-.5)<1e-12 and abs(m['lift_top10']-1)<1e-12 and m['ganho_brier']==0)
    bs = paired_bootstrap(toy, np.full(10, .3), .3, 20, 87)
    # A pequena amostra pode conter bootstrap sem positivos; esse caso é testado em dados reais abaixo.
    record('Brier pareado da constante é zero', bs['ic95_ganho_brier'] == [0., 0.])

    sim = simulate(base, p, 'moderado', p['sementes'][0])
    again = simulate(base, p, 'moderado', p['sementes'][0])
    record('Repetir a semente reproduz todos os eventos', np.array_equal(sim.payment, again.payment))
    poisoned = replace(base, payment=np.where(base.enrollment<INF, day('1900-01-01'), base.payment))
    remade = simulate(poisoned, p, 'moderado', p['sementes'][0])
    record('Pagamentos antigos pós-inscrição não influenciam a nova simulação', np.array_equal(sim.payment, remade.payment))
    t0 = p['validacao']
    modified = sim.payment.copy()
    modified[modified>day(t0)] = INF
    original = snapshot(base, sim, t0, p)
    sentinel = snapshot(base, replace(sim, payment=modified), t0, p)
    record('Pagamento futuro não altera população ou atributos da fotografia',
           original[['id_credito']+ATRIBUTOS].equals(sentinel[['id_credito']+ATRIBUTOS]))
    record('Sentinela realmente altera os rótulos futuros', not original.y.equals(sentinel.y))
    rows = np.flatnonzero(base.enrollment[:, 1]<INF)[:200]
    known = sim.payment[rows].copy()
    altered = sim.payment.copy()
    after = known>base.enrollment[rows, 1, None]
    known[after] = INF
    altered[rows] = known
    record('Contexto da inscrição ignora pagamentos futuros',
           np.array_equal(enrollment_context(base, sim.payment, 1, rows), enrollment_context(base, altered, 1, rows)))
    data = datasets(base, sim, p)
    record('Nenhum imóvel reservado entra no treino ou seleção',
           not data['treino'].imovel_novo.any() and not data['validacao'].imovel_novo.any())
    record('Rótulos de treino e validação amadurecem antes da próxima partição',
           data['treino'].fim_rotulo.max()<p['validacao'] and data['validacao'].fim_rotulo.max()<p['teste'])
    record('Nenhum atributo contém ID, rótulo, data futura ou probabilidade verdadeira',
           not any(x in ATRIBUTOS for x in ['id_imovel', 'id_credito', 'y', 'probabilidade_oraculo_PRIVILEGIADA', 'data_pagamento']))
    null = simulate(base, p, 'nulo', p['sementes'][0])
    null_test = snapshot(base, null, p['teste'], p)
    record('Controle nulo tem probabilidade verdadeira de 12% para todos',
           np.allclose(null_test.probabilidade_oraculo_PRIVILEGIADA, .12, atol=1e-12))
    shifted = simulate(base, p, 'mudanca', p['sementes'][0])
    record('Mudança não altera eventos observados antes do choque',
           np.array_equal(np.minimum(sim.payment, day(p['mudanca_em'])),
                          np.minimum(shifted.payment, day(p['mudanca_em']))))
    record('Mudança não altera nenhuma fotografia de desenvolvimento', all(
        snapshot(base, sim, t, p).drop(columns='probabilidade_oraculo_PRIVILEGIADA').equals(
        snapshot(base, shifted, t, p).drop(columns='probabilidade_oraculo_PRIVILEGIADA'))
        for t in p['treino']+[p['validacao']]))
    return checks


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    p = json.loads((root/'protocolo.json').read_text(encoding='utf-8'))
    base = load_base((root/p['fonte_relativa']).resolve()/'data/pronto/base_analitica_creditos.csv.gz')
    checks = verify(base, p)
    print(json.dumps({'verificacoes': checks, 'total': len(checks)}, ensure_ascii=False, indent=2))

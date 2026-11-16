"""Executa o protocolo congelado inteiro. Recusa sobrescrever resultados existentes."""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
os.environ.setdefault('MKL_NUM_THREADS', '4')
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import json
import platform
import sys
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from m2_experimento import (ATRIBUTOS, HISTORICOS, INF, ORIGINAIS, calibration, choose, datasets,
                            day, dump, file_hash, fit_models, inventory, load_base, metrics,
                            paired_bootstrap, predict, simulate)
from verificar import verify

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--saida', default='resultados')
    args = parser.parse_args()
    out = (ROOT/args.saida).resolve()
    assert out.is_relative_to(ROOT) and out != ROOT, 'Saída deve ficar dentro do experimento'
    if out.exists():
        raise SystemExit('Saída já existe; use --saida outro_nome para uma reprodução sem sobrescrever.')
    out.mkdir()
    p = json.loads((ROOT/'protocolo.json').read_text(encoding='utf-8'))
    source = (ROOT/p['fonte_relativa']).resolve()
    assert not out.is_relative_to(source) and not source.is_relative_to(out)
    before = inventory(source)
    dump(out/'origem_antes.json', before)
    frozen = {f.name: file_hash(f) for f in ROOT.iterdir() if f.suffix in {'.py', '.json', '.md'} and f.is_file()}
    start = time.perf_counter()
    dump(out/'registro_antes_do_treino.json', {
        'inicio_utc': datetime.now(timezone.utc).isoformat(), 'origem': str(source),
        'arquivos_origem': len(before), 'protocolo_e_codigo_sha256': frozen,
        'python': sys.version, 'plataforma': platform.platform(),
        'dependencias': {name: version(name) for name in ['numpy','pandas','scipy','scikit-learn','joblib','matplotlib']},
        'threads': 4, 'criterios': p['criterios_moderado_teste_carteira'],
        'nota': 'Registro salvo antes de verificar invariantes e ajustar o primeiro modelo.'})
    base = load_base(source/'data/pronto/base_analitica_creditos.csv.gz')
    dump(out/'perfil_entrada.json', base.profile)
    try:
        warnings.filterwarnings('error', category=ConvergenceWarning)
        checks = verify(base, p)
        dump(out/'verificacoes.json', {'total': len(checks), 'todas_passaram': True, 'verificacoes': checks})
        print(f'INVARIANTES: {len(checks)} aprovadas; {len(before)} arquivos originais inventariados.', flush=True)
        all_metrics, choices, sizes, simulation_metadata, bootstrap, curves = [], [], [], [], [], []
        for scenario in p['cenarios']:
            for replica, seed in enumerate(p['sementes'], 1):
                tick = time.perf_counter()
                sim = simulate(base, p, scenario, seed)
                data = datasets(base, sim, p)
                train, valid = data['treino'], data['validacao']
                prior = float(train.y.mean())
                with threadpool_limits(limits=4):
                    models = fit_models(train, p, seed)
                    valid_predictions = predict(models, valid, prior)
                    chosen, validation_scores = choose(valid, valid_predictions, p)
                    # A escolha é salva antes de qualquer cálculo de métricas no teste.
                    selection = {'cenario': scenario, 'replica': replica, 'semente': seed, 'escolhido': chosen,
                                 'prevalencia_treino': prior, 'brier_validacao': validation_scores}
                    choices.append(selection)
                    dump(out/'selecao'/f'{scenario}_{seed}.json', selection)
                    for split in ['validacao', 'teste_carteira', 'teste_novos_imoveis']:
                        d = data[split]
                        pred = valid_predictions if split=='validacao' else predict(models, d, prior)
                        pred['selecionado'] = pred[chosen]
                        for name, prob in pred.items():
                            all_metrics.append({'cenario': scenario, 'replica': replica, 'semente': seed,
                                                'split': split, 'modelo': name, 'escolhido': chosen,
                                                **metrics(d, prob, prior, p['fracao_topo'])})
                        saved = d[['id_imovel','id_credito','t0','y','principal_centavos']].copy()
                        for name, prob in pred.items():
                            saved['p_'+name] = prob
                        pred_path = out/'predicoes'/f'{scenario}_{seed}_{split}.csv.gz'
                        pred_path.parent.mkdir(exist_ok=True)
                        saved.to_csv(pred_path, index=False, float_format='%.10g', compression={'method':'gzip','mtime':0})
                        if replica==1:
                            for name, prob in pred.items():
                                for bin_id, point in enumerate(calibration(d, prob), 1):
                                    curves.append({'cenario':scenario, 'split':split, 'modelo':name,
                                                   'bin':bin_id, **point})
                            if split=='teste_carteira':
                                b = paired_bootstrap(d, pred[chosen], prior, p['bootstrap_imoveis_primeira_semente'], seed)
                                bootstrap.append({'cenario': scenario, 'modelo': chosen, **b})
                        sizes.append({'cenario': scenario, 'semente': seed, 'split':split,
                                      'linhas':len(d), 'imoveis':int(d.id_imovel.nunique())})
                sizes.append({'cenario':scenario, 'semente':seed, 'split':'treino',
                              'linhas':len(train), 'imoveis':int(train.id_imovel.nunique())})
                simulation_metadata.append(sim.metadata)
                if replica==1:
                    for split, d in data.items():
                        path = out/'exemplo_primeira_semente'/f'{scenario}_{split}.csv.gz'
                        path.parent.mkdir(exist_ok=True)
                        d.to_csv(path, index=False, compression={'method':'gzip','mtime':0})
                    r,c = np.where(base.enrollment<INF)
                    censor = sim.payment[r,c] > day(p['corte'])
                    payment = sim.payment[r,c].astype('datetime64[D]')
                    payment[censor] = np.datetime64('NaT')
                    events = pd.DataFrame({'id_credito':base.credits[r,c], 'id_imovel':base.ids[r],
                                           'data_inscricao':base.enrollment[r,c].astype('datetime64[D]'),
                                           'data_pagamento_simulada':payment, 'censurado_no_corte':censor})
                    events.to_csv(out/'exemplo_primeira_semente'/f'{scenario}_eventos.csv.gz', index=False,
                                  compression={'method':'gzip','mtime':0})
                    joblib.dump({'modelo':models.get(chosen), 'constante':prior if chosen=='constante' else None,
                                 'atributos':ATRIBUTOS, 'cenario':scenario, 'semente':seed,
                                 'uso':'SOMENTE DEMONSTRACAO SINTETICA; nao integrar na Sprint 4'},
                                out/'exemplo_primeira_semente'/f'{scenario}_modelo.joblib')
                pd.DataFrame(all_metrics).to_csv(out/'metricas_replicas.csv', index=False)
                dump(out/'simulacoes.json', simulation_metadata)
                sample = next(row for row in reversed(all_metrics) if row['split']=='teste_carteira' and row['modelo']=='selecionado')
                print(f'{scenario:9} {replica:02}/20 escolhido={chosen:10} AUC={sample["roc_auc"]:.4f} '
                      f'lift={sample["lift_top10"]:.3f} BSS={sample["brier_skill"]:.4f} '
                      f'tempo={time.perf_counter()-tick:.1f}s', flush=True)
        pd.DataFrame(sizes).to_csv(out/'particoes.csv', index=False)
        pd.DataFrame(curves).to_csv(out/'calibracao_primeira_semente.csv', index=False)
        dump(out/'bootstrap_primeira_semente.json', bootstrap)
        dump(out/'selecoes.json', choices)
        dump(out/'execucao.json', {'concluida':True, 'cenarios':len(p['cenarios']), 'replicas_por_cenario':len(p['sementes']),
                                   'segundos':time.perf_counter()-start,
                                   'fim_utc':datetime.now(timezone.utc).isoformat()})
    finally:
        after = inventory(source)
        dump(out/'origem_depois.json', after)
        missing = sorted(set(before)-set(after))
        added = sorted(set(after)-set(before))
        changed = sorted(k for k in set(before)&set(after) if before[k]!=after[k])
        unchanged = not (missing or added or changed)
        dump(out/'integridade_origem.json', {'preservada':unchanged, 'arquivos_antes':len(before),
                                            'arquivos_depois':len(after), 'alterados':changed,
                                            'removidos':missing, 'adicionados':added})
        assert unchanged, 'A origem mudou durante o experimento; investigar antes de entregar.'
        print(f'INTEGRIDADE: {len(before)} arquivos originais inalterados por SHA-256.', flush=True)


if __name__=='__main__':
    main()

"""Conferência dos artefatos gravados, sem reajustar modelos ou parâmetros."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from m2_experimento import dump, file_hash, inventory

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--saida',default='resultados');args=parser.parse_args()
    out=(ROOT/args.saida).resolve()
    p=json.loads((ROOT/'protocolo.json').read_text(encoding='utf-8'))
    record=json.loads((out/'registro_antes_do_treino.json').read_text(encoding='utf-8'))
    frozen=record['protocolo_e_codigo_sha256']
    code_changed=[name for name,digest in frozen.items() if file_hash(ROOT/name)!=digest]
    assert not code_changed, code_changed
    original=json.loads((out/'origem_antes.json').read_text(encoding='utf-8'))
    assert inventory((ROOT/p['fonte_relativa']).resolve())==original
    metrics=pd.read_csv(out/'metricas_replicas.csv')
    assert len(metrics)==4*20*3*6
    assert metrics[['cenario','semente','split','modelo']].duplicated().sum()==0
    assert not metrics.isna().any().any()
    files=list((out/'predicoes').glob('*.csv.gz'))
    assert len(files)==4*20*3
    max_brier_error=0.;max_auc_error=0.;prediction_rows=0
    for scenario in p['cenarios']:
        for seed in p['sementes']:
            selection=json.loads((out/'selecao'/f'{scenario}_{seed}.json').read_text(encoding='utf-8'))
            prior=selection['prevalencia_treino'];chosen=selection['escolhido']
            for split in ['validacao','teste_carteira','teste_novos_imoveis']:
                d=pd.read_csv(out/'predicoes'/f'{scenario}_{seed}_{split}.csv.gz')
                prediction_rows+=len(d)
                assert not d.isna().any().any()
                assert not d.duplicated(['id_credito','t0']).any()
                assert set(d.y.unique())=={0,1}
                assert ((d.id_imovel%5==0).all() if split=='teste_novos_imoveis' else (d.id_imovel%5!=0).all())
                for col in [col for col in d if col.startswith('p_')]:
                    assert d[col].between(0,1).all()
                assert np.allclose(d.p_selecionado,d['p_'+chosen],atol=0,rtol=0)
                y=d.y.to_numpy();probs=d.p_selecionado.to_numpy()
                observed_brier=float(np.mean((y-probs)**2))
                observed_auc=float(roc_auc_score(y,probs))
                row=metrics[(metrics.cenario==scenario)&(metrics.semente==seed)&(metrics.split==split)&(metrics.modelo=='selecionado')].iloc[0]
                max_brier_error=max(max_brier_error,abs(row.brier-observed_brier))
                max_auc_error=max(max_auc_error,abs(row.roc_auc-observed_auc))
                assert abs(row.brier-observed_brier)<1e-9
                assert abs(row.roc_auc-observed_auc)<1e-6
                if split=='validacao':
                    scores={name:float(np.mean((y-d['p_'+name].to_numpy())**2)) for name in p['selecao']['ordem_simples']}
                    best=min(scores.values())
                    expected=next(name for name in p['selecao']['ordem_simples'] if scores[name]<=best+p['selecao']['tolerancia_absoluta'])
                    assert expected==chosen
    model_errors={}
    for scenario in p['cenarios']:
        artifact=joblib.load(out/'exemplo_primeira_semente'/f'{scenario}_modelo.joblib')
        d=pd.read_csv(out/'exemplo_primeira_semente'/f'{scenario}_teste_carteira.csv.gz')
        saved=pd.read_csv(out/'predicoes'/f'{scenario}_{p["sementes"][0]}_teste_carteira.csv.gz')
        assert np.array_equal(d.id_credito,saved.id_credito)
        pred=np.full(len(d),artifact['constante']) if artifact['modelo'] is None else artifact['modelo'].predict_proba(d[artifact['atributos']])[:,1]
        error=float(np.max(np.abs(pred-saved.p_selecionado)))
        assert error<1e-9
        model_errors[scenario]=error
    result={'aprovada':True,'codigo_e_protocolo_congelados_inalterados':True,'origem_preservada':True,
            'arquivos_origem_conferidos':len(original),'linhas_metricas':len(metrics),'arquivos_predicoes':len(files),
            'linhas_predicoes_conferidas':prediction_rows,'selecoes_recalculadas':80,
            'maior_diferenca_brier_exportacao':max_brier_error,'maior_diferenca_auc_exportacao':max_auc_error,
            'modelos_serializados_reproduzem_predicoes':model_errors,
            'nota':'Tolerâncias cobrem arredondamento de probabilidades no CSV; não houve novo treinamento.'}
    dump(out/'auditoria_final.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

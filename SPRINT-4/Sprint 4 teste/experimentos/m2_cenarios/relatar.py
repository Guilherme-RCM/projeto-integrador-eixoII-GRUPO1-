"""Consolidação transparente dos resultados; não treina nem escolhe cenários."""
from __future__ import annotations
import argparse
import base64
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
from scipy.stats import t as student
from m2_experimento import dump, file_hash

ROOT = Path(__file__).resolve().parent
NAMES = {'nulo':'Sem sinal', 'fraco':'Sinal fraco', 'moderado':'Sinal moderado', 'mudanca':'Mudança de padrão'}
MODEL_NAMES = {'constante':'Constante', 'logistica':'Logística + históricos', 'boosting':'Boosting + históricos',
               'logistica_atributos_originais':'Logística: seis atributos',
               'oraculo_PRIVILEGIADO':'Referência ideal com latente', 'selecionado':'Selecionado na validação'}
MEASURES = ['roc_auc','average_precision','prevalencia','brier','ganho_brier','brier_skill','precisao_top10',
            'lift_top10','erro_abs_calibracao','ece10','captura_principal_top10','captura_principal_regra_valor']


def summary(series):
    values = np.asarray(series, dtype=float)
    n = len(values)
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    se = sd/np.sqrt(n)
    margin = float(student.ppf(.975,n-1))*se
    return {'media':mean,'desvio_replicas':sd,'erro_monte_carlo':se,'ic95_inferior':mean-margin,
            'ic95_superior':mean+margin,'minimo':float(values.min()),'maximo':float(values.max()),'replicas':n}


def br(x, digits=3):
    return f'{x:,.{digits}f}'.replace(',','X').replace('.',',').replace('X','.')


def pct(x, digits=2):
    return br(x*100,digits)+'%'


def md_table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def html_table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join(f'<th>{html.escape(str(x))}</th>' for x in headers)+\
        '</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{html.escape(str(x))}</td>' for x in row)+'</tr>' for row in rows)+\
        '</tbody></table></div>'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--saida',default='resultados')
    args = parser.parse_args()
    out = (ROOT/args.saida).resolve()
    execution = json.loads((out/'execucao.json').read_text(encoding='utf-8'))
    assert execution['concluida']
    protocol = json.loads((ROOT/'protocolo.json').read_text(encoding='utf-8'))
    integrity = json.loads((out/'integridade_origem.json').read_text(encoding='utf-8'))
    checks = json.loads((out/'verificacoes.json').read_text(encoding='utf-8'))
    records = pd.read_csv(out/'metricas_replicas.csv')
    rows = []
    for (scenario,split,model), frame in records.groupby(['cenario','split','modelo']):
        assert len(frame)==len(protocol['sementes'])
        assert set(frame.semente)==set(protocol['sementes'])
        for metric in MEASURES:
            rows.append({'cenario':scenario,'split':split,'modelo':model,'metrica':metric,**summary(frame[metric])})
    aggregate = pd.DataFrame(rows)
    aggregate.to_csv(out/'resumo_estatistico.csv',index=False)
    def cell(scenario,metric,split='teste_carteira',model='selecionado'):
        q = aggregate[(aggregate.cenario==scenario)&(aggregate.split==split)&(aggregate.modelo==model)&(aggregate.metrica==metric)]
        assert len(q)==1
        return q.iloc[0]
    chosen = records[(records.split=='teste_carteira')&(records.modelo=='selecionado')]
    moderate = chosen[chosen.cenario=='moderado']
    requirements = protocol['criterios_moderado_teste_carteira']
    n_pass = int(((moderate.lift_top10>=1.5)&(moderate.ganho_brier>0)).sum())
    criteria = [
        ('Lift médio no topo de 10% ≥1,5',float(moderate.lift_top10.mean()),requirements['lift_medio_minimo'],
         moderate.lift_top10.mean()>=requirements['lift_medio_minimo']),
        ('Limite inferior IC95 da média do lift >1',float(cell('moderado','lift_top10').ic95_inferior),1.,
         cell('moderado','lift_top10').ic95_inferior>1),
        ('Limite inferior IC95 do ganho de Brier >0',float(cell('moderado','ganho_brier').ic95_inferior),0.,
         cell('moderado','ganho_brier').ic95_inferior>0),
        ('Réplicas com lift ≥1,5 e ganho positivo ≥18',n_pass,18,n_pass>=18),
        ('Erro absoluto médio de calibração ≤0,02',float(moderate.erro_abs_calibracao.mean()),.02,
         moderate.erro_abs_calibracao.mean()<=.02),
        ('ECE10 médio ≤0,02',float(moderate.ece10.mean()),.02,moderate.ece10.mean()<=.02),
    ]
    null_auc = cell('nulo','roc_auc',model='logistica').media
    null_lift = cell('nulo','lift_top10',model='logistica').media
    null_pass = .48<=null_auc<=.52 and null_lift<=1.1
    passed = all(bool(x[3]) for x in criteria)
    audit = {'moderado_aprovado':passed,'controle_nulo_aprovado':bool(null_pass),
             'origem_preservada':integrity['preservada'], 'verificacoes_passaram':checks['todas_passaram'],
             'criterios':[{'criterio':a,'observado':b,'referencia':c,'aprovado':bool(d)} for a,b,c,d in criteria],
             'controle_nulo':{'auc_logistica_media':float(null_auc),'lift_logistica_media':float(null_lift)},
             'limite':'Conclusão condicionada aos mecanismos simulados; mudança de padrão avaliada separadamente.'}
    dump(out/'aceite.json',audit)
    scenarios=list(NAMES)
    main_headers=['Cenário','AUC média [IC95 da média]','Recuperação carteira','Recuperação top 10%','Lift [IC95 da média]','Ganho Brier relativo']
    main_rows=[]
    for scenario in scenarios:
        auc=cell(scenario,'roc_auc'); lift=cell(scenario,'lift_top10')
        main_rows.append([NAMES[scenario],f'{br(auc.media)} [{br(auc.ic95_inferior)}; {br(auc.ic95_superior)}]',
                          pct(cell(scenario,'prevalencia').media),pct(cell(scenario,'precisao_top10').media),
                          f'{br(lift.media)} [{br(lift.ic95_inferior)}; {br(lift.ic95_superior)}]',
                          pct(cell(scenario,'brier_skill').media)])
    methods=['constante','logistica_atributos_originais','logistica','boosting','selecionado','oraculo_PRIVILEGIADO']
    model_headers=['Método no cenário moderado','AUC','Lift@10%','Brier','ECE10']
    model_rows=[[MODEL_NAMES[name],br(cell('moderado','roc_auc',model=name).media),
                 br(cell('moderado','lift_top10',model=name).media),br(cell('moderado','brier',model=name).media,6),
                 pct(cell('moderado','ece10',model=name).media)] for name in methods]
    new_headers=['Teste em imóveis excluídos do desenvolvimento','AUC','Lift@10%','Brier skill','ECE10']
    new_rows=[[NAMES[s],br(cell(s,'roc_auc','teste_novos_imoveis').media),
               br(cell(s,'lift_top10','teste_novos_imoveis').media),pct(cell(s,'brier_skill','teste_novos_imoveis').media),
               pct(cell(s,'ece10','teste_novos_imoveis').media)] for s in scenarios]
    criterion_rows=[[a,br(b,6) if abs(b)<.01 else br(b,3),'PASSOU' if d else 'NÃO PASSOU'] for a,b,c,d in criteria]
    selections = pd.DataFrame(json.loads((out/'selecoes.json').read_text(encoding='utf-8')))
    counts = pd.crosstab(selections.cenario,selections.escolhido)
    counts.to_csv(out/'frequencia_selecao.csv')
    part = pd.read_csv(out/'particoes.csv')
    sample = part[(part.cenario=='moderado')&(part.semente==protocol['sementes'][0])]
    part_rows=[[r.split,f'{r.linhas:,}'.replace(',','.'),f'{r.imoveis:,}'.replace(',','.')] for r in sample.itertuples()]
    reference = json.loads(((ROOT/protocol['fonte_relativa']).resolve()/'reports/sprint4/metricas_teste.json').read_text(encoding='utf-8'))['M2']
    figures=out/'figuras';figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
    colors=['#64748b','#3b82f6','#0f766e','#b45309']
    fig,axes=plt.subplots(1,2,figsize=(13.8,5.2),layout='constrained')
    for ax,metric,title,baseline in zip(axes,['roc_auc','lift_top10'],['Discriminação no período futuro','Recuperação no topo de 10%'],[.5,1.]):
        for i,s in enumerate(scenarios):
            c=cell(s,metric)
            ax.errorbar(i,c.media,yerr=[[c.media-c.ic95_inferior],[c.ic95_superior-c.media]],fmt='o',
                        color=colors[i],capsize=6,markersize=9,elinewidth=2)
            ax.annotate(f'{c.media:.3f}',(i,c.media),xytext=(0,13),textcoords='offset points',ha='center',fontweight='bold')
        ax.axhline(baseline,color='#94a3b8',ls='--',lw=1)
        if metric=='lift_top10':ax.axhline(1.5,color='#0f766e',ls=':',lw=1,label='Meta moderado: 1,5');ax.legend(loc='best',fontsize=9)
        ax.set_xticks(range(4),['Sem sinal','Fraco','Moderado','Mudança'])
        ax.set_title(title,pad=16);ax.grid(axis='y',alpha=.15);ax.margins(x=.15,y=.23)
        ax.set_ylabel('ROC-AUC' if metric=='roc_auc' else 'Lift sobre a carteira')
        if metric=='lift_top10':ax.set_ylim(bottom=0)
    fig.suptitle('M2-Cenários | modelo selecionado apenas na validação',fontsize=16,fontweight='bold')
    fig.savefig(figures/'01_cenarios.png',dpi=170);plt.close(fig)
    curve=pd.read_csv(out/'calibracao_primeira_semente.csv')
    fig,axes=plt.subplots(1,2,figsize=(13.8,5.1),layout='constrained')
    for ax,s in zip(axes,['moderado','mudanca']):
        portion=curve[(curve.cenario==s)&(curve.split=='teste_carteira')]
        for name,color in [('selecionado','#0f766e'),('constante','#64748b'),('oraculo_PRIVILEGIADO','#3b82f6')]:
            q=portion[portion.modelo==name]
            ax.plot(q.previsto,q.observado,'o-',color=color,label=MODEL_NAMES[name],markersize=5)
        maximum=max(portion.previsto.max(),portion.observado.max())*1.08
        ax.plot([0,maximum],[0,maximum],'--',color='#94a3b8',lw=1)
        ax.set_title(NAMES[s]);ax.set_xlabel('Probabilidade prevista');ax.set_ylabel('Fração observada')
        ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.legend(loc='best',fontsize=8);ax.grid(alpha=.13)
    fig.suptitle('Calibração | primeira semente, definida previamente',fontsize=16,fontweight='bold')
    fig.savefig(figures/'02_calibracao.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.8),layout='constrained')
    for s,color in zip(scenarios,colors):
        q=chosen[chosen.cenario==s].sort_values('replica')
        ax.plot(q.replica,q.lift_top10,'o-',label=NAMES[s],color=color,ms=4,lw=1.3)
    ax.axhline(1.5,color='#0f766e',ls=':',lw=1);ax.axhline(1,color='#94a3b8',ls='--',lw=1)
    ax.set(xlabel='Réplica (semente previamente fixada)',ylabel='Lift no topo de 10%',xticks=list(range(1,21)))
    ax.set_title('Todas as 20 réplicas | sem seleção de resultados favoráveis',pad=15)
    ax.set_ylim(0,max(3.85,float(chosen.lift_top10.max())+.6))
    ax.legend(ncol=4,fontsize=9,loc='upper center');ax.grid(axis='y',alpha=.15)
    fig.savefig(figures/'03_replicas.png',dpi=170);plt.close(fig)
    decision=('O cenário moderado cumpriu todos os critérios previamente registrados.' if passed else
              'O cenário moderado não cumpriu todos os critérios previamente registrados; as falhas estão explicitadas abaixo.')
    intro=(f'{decision} Foram executadas 20 réplicas em cada um dos quatro cenários, com escolha de modelo somente na validação. '
           f'Os {integrity["arquivos_antes"]} arquivos da Sprint 4 permaneceram idênticos, verificados por SHA-256. '
           'Os resultados demonstram aprendizado de hipóteses simuladas; não validam previsão real de cobrança.')
    limit=('O cadastro e as inscrições vêm de uma base individual já sintética. Pagamentos após a inscrição foram regenerados; '
           'portanto, a comparação com o M2 original é contextual, e não um ganho medido sobre os mesmos rótulos. '
           'Os coeficientes foram escolhidos como hipóteses didáticas antes do treinamento, não estimados em Palmas. '
           'Os ICs da média representam erro Monte Carlo sobre trajetórias condicionadas ao cadastro fixo; não são intervalos '
           'de generalização para outra população. O efeito latente foi ocultado dos modelos e mostrado apenas na referência ideal. '
           'O mecanismo gerador usa um logito linear nas variáveis do histórico, o que favorece a família logística; '
           'este estudo não demonstra que logística seja superior em mecanismos não lineares ou em dados reais. '
           'A mudança de padrão é um estresse severo com inversão de efeitos: sucesso no cenário estável não garante robustez nesse cenário.')
    ablation=(f'Com os seis atributos equivalentes aos originais, a logística obteve AUC média '
              f'{br(cell("moderado","roc_auc",model="logistica_atributos_originais").media)}. '
              f'Acrescentando os históricos observáveis na inscrição, obteve '
              f'{br(cell("moderado","roc_auc",model="logistica").media)}. '
              'Essa ablação permite separar o efeito de disponibilizar histórico do efeito de trocar o estimador. '
              'Todos os métodos dessa tabela foram avaliados nos mesmos rótulos regenerados de cada réplica.')
    stress=(f'No cenário de mudança, o selecionado teve AUC média {br(cell("mudanca","roc_auc").media)}, '
            f'lift {br(cell("mudanca","lift_top10").media)} e Brier skill {pct(cell("mudanca","brier_skill").media)}. '
            'O resultado é publicado integralmente e não foi usado para reajustar o modelo ou o gerador.')
    null_text=(f'Controle nulo: AUC média da logística {br(null_auc)} e lift {br(null_lift)}. '
               f'Controle {"aprovado" if null_pass else "não aprovado"}. '
               f'O M2 original tinha ROC-AUC {br(reference["probabilidade"]["roc_auc"])} e '
               f'prevalência {pct(reference["probabilidade"]["media_observada"])} no seu próprio teste. '
               'O novo controle nulo usa novas trajetórias, sem reutilizar os rótulos antigos.')
    amount=(f'No moderado, o ranking por probabilidade capturou em média '
            f'{pct(cell("moderado","captura_principal_top10").media)} do principal pago; '
            f'a regra de maior principal capturou {pct(cell("moderado","captura_principal_regra_valor").media)}. '
            'Essas são prioridades por crédito, não por devedor. O objetivo primário é a chance de pagamento; '
            'maximizar reais recuperados é outro objetivo. Nenhum dos valores representa efeito causal de uma ação de cobrança.')
    sources=[('Morris, White e Crowther (2019): planejamento e relato de simulações, ADEMP','https://pubmed.ncbi.nlm.nih.gov/30652356/'),
             ('Scikit-learn: separação entre treino, validação e teste','https://scikit-learn.org/stable/modules/cross_validation.html'),
             ('Scikit-learn: calibração e interpretação do Brier','https://scikit-learn.org/stable/modules/calibration.html')]
    methodology=('Treino em 29/06/2022 e 30/06/2023; validação em 01/07/2024; teste em 31/07/2025 com horizonte '
                 'de 365 dias e corte em 31/07/2026. Os imóveis com ID divisível por cinco foram excluídos do desenvolvimento. '
                 'Modelos: constante, logística e boosting com parâmetros fixos. A seleção minimiza Brier na validação, '
                 'preferindo o mais simples quando a diferença é de até 0,0001. Não houve ajuste após o teste. '
                 'Empates no topo recebem inclusão uniforme; o topo da constante representa uma seleção aleatória em expectativa. '
                 'O relatório apresenta IC95 da média entre 20 réplicas por t de Student; os mínimos, máximos e desvios estão no CSV. '
                 'Um bootstrap pareado de 1.000 imóveis por cenário, na primeira semente, complementa a avaliação.')
    status='APROVADO NO CENÁRIO MODERADO' if passed else 'CRITÉRIOS NÃO ATENDIDOS INTEGRALMENTE'
    explanation=[
        ('1. Simular', 'Uma regra declarada transforma históricos conhecidos em chances diferentes. Um sorteio produz a data de pagamento.'),
        ('2. Aprender', 'O modelo observa históricos e pagamentos passados. Ele estima seus próprios parâmetros; não recebe a fórmula nem os sorteios.'),
        ('3. Escolher', 'A validação compara constante, logística e boosting. O modelo é escolhido antes de medir o teste.'),
        ('4. Verificar', 'O teste usa um período futuro e imóveis reservados. Vinte sementes e o cenário de mudança expõem estabilidade e limites.')]
    md=['# M2-Cenários — resultado do experimento', '', '**'+status+'**', '', intro, '',
        '## Como isso funciona','',md_table(['Etapa','O que acontece'],explanation),'',
        'Uma chance de 30% não garante pagamento: em situações equivalentes, aproximadamente 70% ainda não pagariam. '
        'A avaliação verifica frequência, ordenação e calibração em grupos. Leia também [a explicação detalhada](../COMO_FUNCIONA.md).','',
        '## Resultado principal: teste temporal na carteira', '',md_table(main_headers,main_rows),'',
        'As taxas de recuperação mudam entre cenários por composição e sobrevivência; 12% é a média calibrada na primeira coorte de inscrição, não uma meta imposta ao teste.','',
        '![Comparação dos cenários](figuras/01_cenarios.png)','',
        '## Critérios definidos antes do treino','',md_table(['Critério','Observado','Resultado'],criterion_rows),'',
        f'{n_pass}/20 réplicas do moderado atenderam simultaneamente lift ≥1,5 e ganho de Brier >0.','',
        '## Comparação de métodos e ablação','',ablation,'',md_table(model_headers,model_rows),'',
        '## Imóveis não usados no desenvolvimento','',md_table(new_headers,new_rows),'',
        '## Controles e limitações','',null_text,'',stress,'',amount,'',limit,'',
        '![Calibração](figuras/02_calibracao.png)','',
        '![Todas as réplicas](figuras/03_replicas.png)','',
        '## Metodologia e rastreabilidade','',methodology,'',
        f'As {checks["total"]} verificações de invariantes passaram. Tempo total de execução: {br(execution["segundos"]/60,1)} minutos.','',
        'Tamanhos da primeira réplica moderada (exemplo predefinido):','',md_table(['Partição','Linhas','Imóveis'],part_rows),'',
        'Arquivos de respaldo: `registro_antes_do_treino.json`, `verificacoes.json`, `integridade_origem.json`, '
        '`origem_antes.json`, `origem_depois.json`, `metricas_replicas.csv`, `resumo_estatistico.csv`, '
        '`bootstrap_primeira_semente.json`, `selecao/`, `predicoes/` e `exemplo_primeira_semente/`. '
        'O protocolo e o código executado estão na pasta superior. Nenhum pacote foi integrado à Sprint 4.','',
        '## Referências','']+[f'- [{title}]({url})' for title,url in sources]
    (out/'RELATORIO.md').write_text('\n'.join(md),encoding='utf-8')
    def img(name):
        data=base64.b64encode((figures/name).read_bytes()).decode()
        return f'<img alt="{html.escape(name)}" src="data:image/png;base64,{data}">'
    cards=[('ROC-AUC',br(cell('moderado','roc_auc').media)),('Lift no topo 10%',br(cell('moderado','lift_top10').media)+'×'),
           ('Brier skill',pct(cell('moderado','brier_skill').media)),('Réplicas úteis',f'{n_pass}/20')]
    report='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M2-Cenários — relatório do experimento</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#182a40;font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1150px;margin:0 auto;padding:48px 32px}header{background:#12263e;color:white;padding:42px;border-radius:18px}
.eyebrow{letter-spacing:.14em;font-size:12px;color:#a8c8df}h1{font-size:38px;line-height:1.15;margin:15px 0}h2{font-size:24px;margin-top:40px;line-height:1.3}
header p{color:#dbe8f0;margin-bottom:0}.badge{display:inline-block;padding:6px 10px;background:#d6eee7;color:#145a49;border-radius:6px;font-weight:700;font-size:12px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:24px 0}.card{background:white;padding:22px;border:1px solid #dfe6ee;border-radius:10px}
.card span{display:block;font-size:13px;color:#5d6f83}.card strong{font-size:31px}.note{border-left:4px solid #b45309;padding:16px 22px;background:#fff7eb;border-radius:5px}
.table-wrap{overflow:auto;background:white;border:1px solid #dfe6ee;border-radius:9px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:13px 15px;border-bottom:1px solid #e5eaf0}th{background:#eaf0f6;font-weight:650}tr:last-child td{border:0}
img{width:100%;height:auto;display:block;margin:22px 0;background:white;border-radius:9px;border:1px solid #e3e9f0}a{color:#1266a0}footer{margin-top:44px;padding-top:20px;border-top:1px solid #d5dee8;font-size:13px;color:#5d6f83}
@media(max-width:760px){main{padding:20px 14px}header{padding:25px}h1{font-size:30px}.cards{grid-template-columns:repeat(2,1fr)}}
@media print{body{background:white}main{padding:0}header{color:#12263e;background:#edf2f6}header p{color:#12263e}.table-wrap,img,.card{break-inside:avoid}h2{break-after:avoid}}
</style><main>'''
    report+=f'<header><div class="eyebrow">EXPERIMENTO LOCAL · 80 RÉPLICAS · SPRINT 4 PRESERVADA</div><h1>M2-Cenários</h1><span class="badge">{status}</span><p>{html.escape(intro)}</p></header>'
    report+='<div class="cards">'+''.join(f'<div class="card"><span>{a} · moderado</span><strong>{b}</strong></div>' for a,b in cards)+'</div>'
    report+='<p class="note"><strong>Escopo da conclusão.</strong> Simulação transparente com pagamentos regenerados. Não é validação em contribuintes reais nem melhora medida sobre os mesmos rótulos da Sprint 4.</p>'
    report+='<h2>Como isso funciona</h2>'+html_table(['Etapa','O que acontece'],explanation)
    report+='<p>Uma chance de 30% não garante pagamento: em situações equivalentes, aproximadamente 70% ainda não pagariam. O modelo aprende probabilidades e ordena dívidas; a avaliação verifica se essa ordenação funciona em casos futuros.</p>'
    report+='<h2>Resultado no período futuro</h2>'+html_table(main_headers,main_rows)+img('01_cenarios.png')
    report+='<p>IC95 da média em 20 réplicas, condicionado ao cadastro fixo. Os critérios foram registrados antes dos treinamentos. A taxa de 12% foi calibrada somente na primeira coorte de inscrição.</p>'
    report+='<h2>Critérios de aceite</h2>'+html_table(['Critério','Observado','Resultado'],criterion_rows)
    report+='<h2>O que explica a melhora</h2><p>'+html.escape(ablation)+'</p>'+html_table(model_headers,model_rows)
    report+='<h2>Avaliação em imóveis reservados</h2>'+html_table(new_headers,new_rows)
    report+='<h2>Controles e mudança de padrão</h2><p>'+html.escape(null_text)+'</p><p>'+html.escape(stress)+'</p>'+img('02_calibracao.png')+img('03_replicas.png')
    report+='<h2>Probabilidade de pagamento e valor da carteira</h2><p>'+html.escape(amount)+'</p>'
    report+='<h2>Como foi verificado</h2><p>'+html.escape(methodology)+'</p>'+html_table(['Partição: primeira réplica moderada','Linhas','Imóveis'],part_rows)
    report+=f'<p>{checks["total"]} verificações aprovadas. {integrity["arquivos_antes"]} arquivos originais idênticos por SHA-256. Tempo de execução: {br(execution["segundos"]/60,1)} minutos.</p>'
    report+='<h2>Limitações</h2><p>'+html.escape(limit)+'</p><h2>Referências metodológicas</h2><ul>'+''.join(f'<li><a href="{url}">{html.escape(title)}</a></li>' for title,url in sources)+'</ul>'
    report+='<footer>Relatório autocontido; gráficos incorporados. Código, protocolo, previsões, métricas por réplica, intervalos e inventários de integridade acompanham a pasta local do experimento.</footer></main></html>'
    (out/'RELATORIO.html').write_text(report,encoding='utf-8')
    dump(out/'artefatos_relatorio_sha256.json',{str(f.relative_to(out)):file_hash(f) for f in [out/'RELATORIO.md',out/'RELATORIO.html',out/'aceite.json',out/'resumo_estatistico.csv',*figures.glob('*.png')]})
    print(json.dumps(audit,ensure_ascii=True,indent=2))
    print(records[(records.split=='teste_carteira')&(records.modelo=='selecionado')].groupby('cenario')[['roc_auc','lift_top10','brier_skill','ece10','prevalencia','precisao_top10']].mean().to_string())


if __name__=='__main__':main()


import requests
import json
import csv
import os
from datetime import datetime

BASE = "https://acessoainformacao.palmas.to.gov.br"

NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

sessao = requests.Session()


pagina = f"{BASE}/cidadao/transparencia/sgreceitas"
api=f"{BASE}/api"
parametros = {
    "multi_request": "true",
    "params": json.dumps({
        "0-teste": {
            "order": {},
            "limit": "0, 15",
            "acao": "sgreceitas/listar"
        }
    })
}
#print(json.dumps(parametros, indent=4, ensure_ascii=False))

#print(parametros)
#print("Endereço da página:", pagina)
#print("Endereço da API:", api)
#print("Endereço consultado:", pagina)
resposta = sessao.get(
    pagina,
    headers={"User-Agent": NAVEGADOR},
    timeout=60
)

resposta_api = sessao.post(
    api,
    data=parametros,
    headers={"User-Agent": NAVEGADOR},
    timeout=60
)

#print("Status da API:", resposta_api.status_code)
#print("Resposta da API:", resposta_api.text[:1000])
#print("Status HTTP:", resposta.status_code)
dados = resposta_api.json()
print("chaves", dados.keys())
print(type(dados))
resultado = dados["0-teste"]

print("Chaves do resultado:", resultado.keys())
#print("Tamanho da resposta:", len(resposta.text))
#print(resposta.text[:500])
print("Total de registros:", resultado["total"])

registros = resultado["dados"]

print("Quantidade recebida:", len(registros))
print(registros[0])
print(registros[0]["descricao"])
PASTA_BRUTO = os.path.join("data", "bruto")
caminho_csv=os.path.join(PASTA_BRUTO,"receitas.csv")
data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nome_json = f"receitas_{data_hora}.json"
caminho_json = os.path.join(PASTA_BRUTO, nome_json)
with open(caminho_json, "w", encoding="utf-8") as arquivo:
    json.dump(dados, arquivo, ensure_ascii=False, indent=4)
#for item in registros:
    #print(item["descricao"], "-" ,item["ano"],"-", item["valor_arrecado_mes"])
with open(caminho_csv, "w", newline="", encoding="utf-8") as arquivo:
    escritor = csv.writer(arquivo)
    escritor.writerow(["descricao", "ano", "valor_arrecado_mes"])
    for item in registros:
        escritor.writerow([
        item["descricao"],
        item["ano"],
        item["valor_arrecado_mes"]
     ])
#print("Coleta concluída!")
#print("Registros coletados:", len(registros))
#print("Pasta dos dados brutos:", PASTA_BRUTO) 
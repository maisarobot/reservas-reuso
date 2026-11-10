"""
API Gateway — porta 8080
========================
Ponto ÚNICO de entrada do sistema. As aplicações (Clínica, Restaurante, ...)
nunca falam diretamente com os microserviços: elas chamam a Gateway, que:

  1. identifica o microserviço de destino pelo prefixo da URL
     (/api/usuarios/... -> ms-usuarios, /api/reservas/... -> ms-reservas, ...);
  2. descobre a porta atual do microserviço consultando o Service Registry
     (com cache de 10 s);
  3. repassa a requisição (método, query string, corpo JSON) e devolve a
     resposta ao cliente;
  4. registra um log de cada requisição roteada.

Tabela de roteamento:
  /api/usuarios/**      -> ms-usuarios      (5001)
  /api/recursos/**      -> ms-recursos      (5002)
  /api/reservas/**      -> ms-reservas      (5003)
  /api/pagamentos/**    -> ms-pagamentos    (5004)
  /api/notificacoes/**  -> ms-notificacoes  (5005)

Endpoints próprios da Gateway:
  GET /                 -> documentação das rotas
  GET /api/status       -> saúde agregada de todos os microserviços
  GET /api/logs         -> últimas requisições roteadas
"""
import os
import sys
import time
from collections import deque
from datetime import datetime

import requests
from flask import Response, jsonify, render_template_string, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum.servico_base import REGISTRY_URL, criar_servico, iniciar  # noqa: E402

PORTA = 8080
ROTAS = {
    "usuarios": "ms-usuarios",
    "recursos": "ms-recursos",
    "reservas": "ms-reservas",
    "pagamentos": "ms-pagamentos",
    "notificacoes": "ms-notificacoes",
}
TTL_CACHE = 10  # segundos

app = criar_servico("api-gateway", PORTA, "Ponto único de entrada (roteamento)")
_cache = {}                 # nome do serviço -> (url_base, instante)
_logs = deque(maxlen=100)   # últimas requisições roteadas


def descobrir(nome_servico):
    """Descobre a URL base de um microserviço no Service Registry (com cache)."""
    em_cache = _cache.get(nome_servico)
    if em_cache and time.time() - em_cache[1] < TTL_CACHE:
        return em_cache[0]
    r = requests.get(f"{REGISTRY_URL}/servicos/{nome_servico}", timeout=2)
    if r.status_code != 200:
        raise LookupError(f"Microserviço '{nome_servico}' não está disponível no Registry")
    url = r.json()["url"]
    _cache[nome_servico] = (url, time.time())
    return url


@app.route("/api/<recurso>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.route("/api/<recurso>/<path:resto>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def rotear(recurso, resto=""):
    """Repassa a requisição para o microserviço responsável pelo recurso."""
    if recurso not in ROTAS:
        return jsonify({"erro": f"rota /api/{recurso} desconhecida"}), 404
    servico = ROTAS[recurso]
    try:
        base = descobrir(servico)
    except (LookupError, requests.RequestException) as e:
        return jsonify({"erro": str(e)}), 503

    destino = f"{base}/{recurso}" + (f"/{resto}" if resto else "")
    inicio = time.time()
    try:
        resp = requests.request(request.method, destino, params=request.args,
                                json=request.get_json(silent=True), timeout=5,
                                headers={"X-Gateway": "api-gateway"})
    except requests.RequestException:
        _cache.pop(servico, None)  # força nova descoberta na próxima chamada
        return jsonify({"erro": f"falha ao contatar {servico}"}), 502

    _logs.appendleft({"hora": datetime.now().strftime("%H:%M:%S"), "metodo": request.method,
                      "rota": request.full_path.rstrip("?"), "servico": servico,
                      "status": resp.status_code, "ms": round((time.time() - inicio) * 1000)})
    return Response(resp.content, status=resp.status_code,
                    content_type=resp.headers.get("Content-Type", "application/json"))


@app.get("/api/status")
def status():
    """Saúde agregada: consulta o /health de cada microserviço."""
    resultado = []
    for prefixo, servico in ROTAS.items():
        item = {"servico": servico, "rota": f"/api/{prefixo}", "status": "DOWN", "porta": None}
        try:
            base = descobrir(servico)
            saude = requests.get(f"{base}/health", timeout=2).json()
            item.update(status=saude["status"], porta=saude["porta"], descricao=saude.get("descricao"))
        except Exception:  # noqa: BLE001 - qualquer falha = serviço fora do ar
            _cache.pop(servico, None)
        resultado.append(item)
    return jsonify(resultado)


@app.get("/api/logs")
def logs():
    return jsonify(list(_logs))


DOC = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><title>API Gateway</title>
<style>body{font-family:Segoe UI,Arial;margin:32px;background:#f8fafc;color:#0f172a}
table{border-collapse:collapse;background:#fff}td,th{border:1px solid #cbd5e1;padding:8px 12px}
th{background:#e2e8f0}code{color:#7c3aed}</style></head><body>
<h1>🚪 API Gateway — Framework de Reservas</h1><p>Porta <b>8080</b>. Tabela de roteamento:</p>
<table><tr><th>Rota pública</th><th>Microserviço</th></tr>
{% for p,s in rotas.items() %}<tr><td><code>/api/{{p}}/**</code></td><td>{{s}}</td></tr>{% endfor %}
<tr><td><code>/api/status</code></td><td>(Gateway) saúde agregada</td></tr>
<tr><td><code>/api/logs</code></td><td>(Gateway) últimas requisições</td></tr></table></body></html>"""


@app.get("/")
def documentacao():
    return render_template_string(DOC, rotas=ROTAS)


if __name__ == "__main__":
    iniciar(app, tipo="gateway", descricao="Ponto único de entrada (roteamento)")

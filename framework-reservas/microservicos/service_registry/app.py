"""
Service Registry (Descoberta de Serviços) — porta 8761
=====================================================
Inspirado no Netflix Eureka. Cada microserviço, ao iniciar, se registra aqui
informando nome, host e porta, e depois envia um heartbeat a cada 5 segundos.

A API Gateway consulta este Registry para descobrir em qual porta está cada
microserviço (descoberta dinâmica, sem endereços fixos no código).

Endpoints:
  POST /registrar            -> registra (ou atualiza) um serviço
  POST /heartbeat/<nome>     -> renova o "sinal de vida" do serviço
  GET  /servicos             -> lista JSON de todos os serviços e suas portas
  GET  /servicos/<nome>      -> dados de um serviço específico
  GET  /                     -> painel HTML com os serviços em execução
"""
import logging
import os
import sys
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request

# Silencia o log de cada requisição HTTP (heartbeats poluiriam o console)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORTA = 8761
TEMPO_LIMITE = 15  # segundos sem heartbeat => serviço considerado DOWN

app = Flask("service-registry")
app.json.ensure_ascii = False
_servicos = {}           # nome -> dados do serviço
_trava = threading.Lock()


def _status(servico):
    segundos = (datetime.now() - servico["ultimo_heartbeat"]).total_seconds()
    return "UP" if segundos <= TEMPO_LIMITE else "DOWN"


def _serializar(s):
    return {**{k: v for k, v in s.items() if k not in ("ultimo_heartbeat", "registrado_em")},
            "status": _status(s),
            "registrado_em": s["registrado_em"].strftime("%d/%m/%Y %H:%M:%S"),
            "ultimo_heartbeat": s["ultimo_heartbeat"].strftime("%H:%M:%S"),
            "url": f"http://{s['host']}:{s['porta']}"}


@app.post("/registrar")
def registrar():
    dados = request.get_json(force=True)
    agora = datetime.now()
    with _trava:
        _servicos[dados["nome"]] = {**dados, "registrado_em": agora, "ultimo_heartbeat": agora}
    print(f"[registry] registrado: {dados['nome']} na porta {dados['porta']}")
    return jsonify({"mensagem": "registrado", "nome": dados["nome"]}), 201


@app.post("/heartbeat/<nome>")
def heartbeat(nome):
    with _trava:
        if nome not in _servicos:
            return jsonify({"erro": "serviço não registrado"}), 404
        _servicos[nome]["ultimo_heartbeat"] = datetime.now()
    return jsonify({"mensagem": "ok"})


@app.get("/servicos")
def listar():
    with _trava:
        lista = [_serializar(s) for s in _servicos.values()]
    return jsonify(sorted(lista, key=lambda s: s["porta"]))


@app.get("/servicos/<nome>")
def obter(nome):
    with _trava:
        s = _servicos.get(nome)
        if not s or _status(s) == "DOWN":
            return jsonify({"erro": f"serviço '{nome}' indisponível"}), 404
        return jsonify(_serializar(s))


PAINEL = """
<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>Service Registry — Framework de Reservas</title>
<style>
 body{font-family:Segoe UI,Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:32px}
 h1{margin:0 0 4px;font-size:26px} p.sub{color:#94a3b8;margin:0 0 24px}
 .cards{display:flex;gap:16px;margin-bottom:24px}
 .card{background:#1e293b;border-radius:10px;padding:16px 22px;min-width:150px}
 .card b{font-size:28px;display:block}
 table{width:100%;border-collapse:collapse;background:#1e293b;border-radius:10px;overflow:hidden}
 th,td{padding:12px 14px;text-align:left;border-bottom:1px solid #334155;font-size:14px}
 th{background:#334155;color:#cbd5e1;text-transform:uppercase;font-size:12px;letter-spacing:.05em}
 .up{background:#16a34a;color:#fff;padding:3px 10px;border-radius:12px;font-weight:600;font-size:12px}
 .down{background:#dc2626;color:#fff;padding:3px 10px;border-radius:12px;font-weight:600;font-size:12px}
 .porta{font-family:Consolas,monospace;font-size:16px;color:#facc15;font-weight:700}
 .tipo{color:#93c5fd}
</style></head><body>
<h1>🛰️ Service Registry</h1>
<p class="sub">Microserviços em execução no Framework de Reservas — atualização automática a cada 5 s ({{ agora }})</p>
<div class="cards">
 <div class="card">Registrados<b>{{ servicos|length }}</b></div>
 <div class="card">UP<b style="color:#4ade80">{{ servicos|selectattr('status','equalto','UP')|list|length }}</b></div>
 <div class="card">DOWN<b style="color:#f87171">{{ servicos|selectattr('status','equalto','DOWN')|list|length }}</b></div>
</div>
<table><tr><th>Serviço</th><th>Tipo</th><th>Porta</th><th>URL</th><th>Descrição</th><th>Último heartbeat</th><th>Status</th></tr>
{% for s in servicos %}
<tr><td><b>{{ s.nome }}</b></td><td class="tipo">{{ s.tipo }}</td><td class="porta">{{ s.porta }}</td>
<td>{{ s.url }}</td><td>{{ s.descricao }}</td><td>{{ s.ultimo_heartbeat }}</td>
<td><span class="{{ 'up' if s.status=='UP' else 'down' }}">{{ s.status }}</span></td></tr>
{% endfor %}
<tr><td><b>service-registry</b></td><td class="tipo">infraestrutura</td><td class="porta">8761</td>
<td>http://127.0.0.1:8761</td><td>Descoberta de serviços (este painel)</td><td>—</td><td><span class="up">UP</span></td></tr>
</table></body></html>
"""


@app.get("/")
def painel():
    with _trava:
        lista = sorted([_serializar(s) for s in _servicos.values()], key=lambda s: s["porta"])
    return render_template_string(PAINEL, servicos=lista,
                                  agora=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))


if __name__ == "__main__":
    print(f"[service-registry] rodando em http://127.0.0.1:{PORTA}")
    app.run(host="0.0.0.0", port=PORTA, debug=False, use_reloader=False)

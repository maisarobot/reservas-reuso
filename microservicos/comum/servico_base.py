"""
servico_base.py
===============
Código comum reutilizado por TODOS os microserviços do sistema.

Responsabilidades:
  * Criar a aplicação Flask do microserviço já com o endpoint /health.
  * Registrar o microserviço no Service Registry (nome, host e porta) e
    enviar "heartbeats" periódicos, para que o Registry saiba que ele está UP.
  * Oferecer um pequeno utilitário de acesso ao banco SQLite (classe Banco).

Esse módulo é, por si só, um exemplo de reuso: cada microserviço só escreve
as suas rotas de negócio; a infraestrutura vem pronta daqui.
"""
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime

import requests
from flask import Flask, jsonify

# Silencia o log de cada requisição HTTP (heartbeats poluiriam o console)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Endereço do Service Registry (pode ser alterado por variável de ambiente)
REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://127.0.0.1:8761")
HOST = os.environ.get("SERVICE_HOST", "127.0.0.1")
INTERVALO_HEARTBEAT = 5  # segundos

# Pasta onde ficam os arquivos .db de cada microserviço
PASTA_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados")
os.makedirs(PASTA_DADOS, exist_ok=True)


class Banco:
    """Acesso simples a um banco SQLite exclusivo do microserviço
    (padrão *Database per Service*)."""

    def __init__(self, nome_arquivo, script_criacao):
        self.caminho = os.path.join(PASTA_DADOS, nome_arquivo)
        with self.conectar() as con:
            con.executescript(script_criacao)

    def conectar(self):
        con = sqlite3.connect(self.caminho)
        con.row_factory = sqlite3.Row
        return con

    def consultar(self, sql, parametros=()):
        """Executa um SELECT e devolve uma lista de dicionários."""
        with self.conectar() as con:
            return [dict(linha) for linha in con.execute(sql, parametros).fetchall()]

    def consultar_um(self, sql, parametros=()):
        linhas = self.consultar(sql, parametros)
        return linhas[0] if linhas else None

    def executar(self, sql, parametros=()):
        """Executa INSERT/UPDATE/DELETE e devolve o id da última linha inserida."""
        with self.conectar() as con:
            cursor = con.execute(sql, parametros)
            con.commit()
            return cursor.lastrowid


def criar_servico(nome, porta, descricao=""):
    """Cria a aplicação Flask do microserviço com o endpoint padrão /health."""
    app = Flask(nome)
    app.config["JSON_AS_ASCII"] = False
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    app.config["NOME_SERVICO"] = nome
    app.config["PORTA"] = porta
    inicio = datetime.now().isoformat(timespec="seconds")

    @app.get("/health")
    def health():
        return jsonify({"servico": nome, "status": "UP", "porta": porta,
                        "descricao": descricao, "iniciado_em": inicio})

    return app


def _registrar_no_registry(nome, porta, tipo, descricao):
    """Thread que registra o serviço e depois envia heartbeats para sempre."""
    dados = {"nome": nome, "host": HOST, "porta": porta, "tipo": tipo,
             "descricao": descricao, "url_saude": f"http://{HOST}:{porta}/health"}
    registrado = False
    while True:
        try:
            if not registrado:
                requests.post(f"{REGISTRY_URL}/registrar", json=dados, timeout=2)
                registrado = True
            else:
                r = requests.post(f"{REGISTRY_URL}/heartbeat/{nome}", timeout=2)
                if r.status_code == 404:  # o Registry reiniciou: registrar de novo
                    registrado = False
                    continue
        except requests.RequestException:
            registrado = False  # Registry fora do ar: tenta de novo depois
        time.sleep(INTERVALO_HEARTBEAT)


def iniciar(app, tipo="microserviço", descricao=""):
    """Sobe o microserviço: inicia a thread de registro e o servidor Flask."""
    nome, porta = app.config["NOME_SERVICO"], app.config["PORTA"]
    threading.Thread(target=_registrar_no_registry,
                     args=(nome, porta, tipo, descricao), daemon=True).start()
    print(f"[{nome}] rodando em http://{HOST}:{porta}")
    app.run(host="0.0.0.0", port=porta, debug=False, use_reloader=False)

"""
Microserviço de Recursos (ms-recursos) — porta 5002
===================================================
Guarda os "recursos reserváveis" de cada aplicação. O recurso é genérico:
na Clínica é um médico; no Restaurante é uma mesa. O campo `dominio`
separa os recursos de cada aplicação construída com o framework.
Banco de dados próprio: SQLite (dados/recursos.db).

Endpoints (via Gateway em /api/recursos):
  POST /recursos              -> cadastra recurso
       {dominio, tipo, nome, descricao, capacidade, preco_base, atributos{}}
  GET  /recursos?dominio=X    -> lista recursos ativos de um domínio
  GET  /recursos/<id>         -> obtém um recurso
  PATCH /recursos/<id>        -> ativa/desativa ou altera preço
"""
import json
import os
import sys

from flask import jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum.servico_base import Banco, criar_servico, iniciar  # noqa: E402

PORTA = 5002
DESCRICAO = "Recursos reserváveis (médicos, mesas...)"
app = criar_servico("ms-recursos", PORTA, DESCRICAO)
banco = Banco("recursos.db", """
CREATE TABLE IF NOT EXISTS recurso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dominio TEXT NOT NULL,
    tipo TEXT NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT,
    capacidade INTEGER DEFAULT 1,
    preco_base REAL DEFAULT 0,
    atributos TEXT DEFAULT '{}',
    ativo INTEGER DEFAULT 1
);""")


def _formatar(r):
    if r:
        r["atributos"] = json.loads(r["atributos"] or "{}")
        r["ativo"] = bool(r["ativo"])
    return r


@app.post("/recursos")
def cadastrar():
    d = request.get_json(force=True)
    faltando = [c for c in ("dominio", "tipo", "nome") if not d.get(c)]
    if faltando:
        return jsonify({"erro": f"campos obrigatórios: {', '.join(faltando)}"}), 400
    novo_id = banco.executar(
        "INSERT INTO recurso (dominio,tipo,nome,descricao,capacidade,preco_base,atributos) VALUES (?,?,?,?,?,?,?)",
        (d["dominio"], d["tipo"], d["nome"], d.get("descricao", ""), int(d.get("capacidade", 1)),
         float(d.get("preco_base", 0)), json.dumps(d.get("atributos", {}), ensure_ascii=False)))
    return jsonify(_formatar(banco.consultar_um("SELECT * FROM recurso WHERE id=?", (novo_id,)))), 201


@app.get("/recursos")
def listar():
    dominio = request.args.get("dominio")
    if dominio:
        linhas = banco.consultar("SELECT * FROM recurso WHERE dominio=? AND ativo=1 ORDER BY id", (dominio,))
    else:
        linhas = banco.consultar("SELECT * FROM recurso ORDER BY id")
    return jsonify([_formatar(r) for r in linhas])


@app.get("/recursos/<int:id_recurso>")
def obter(id_recurso):
    r = _formatar(banco.consultar_um("SELECT * FROM recurso WHERE id=?", (id_recurso,)))
    return (jsonify(r), 200) if r else (jsonify({"erro": "recurso não encontrado"}), 404)


@app.patch("/recursos/<int:id_recurso>")
def alterar(id_recurso):
    d = request.get_json(force=True)
    if not banco.consultar_um("SELECT id FROM recurso WHERE id=?", (id_recurso,)):
        return jsonify({"erro": "recurso não encontrado"}), 404
    if "ativo" in d:
        banco.executar("UPDATE recurso SET ativo=? WHERE id=?", (int(bool(d["ativo"])), id_recurso))
    if "preco_base" in d:
        banco.executar("UPDATE recurso SET preco_base=? WHERE id=?", (float(d["preco_base"]), id_recurso))
    return jsonify(_formatar(banco.consultar_um("SELECT * FROM recurso WHERE id=?", (id_recurso,))))


if __name__ == "__main__":
    iniciar(app, descricao=DESCRICAO)

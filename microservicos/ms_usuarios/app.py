"""
Microserviço de Usuários (ms-usuarios) — porta 5001
===================================================
Responsável pelo cadastro dos clientes que fazem reservas.
Banco de dados próprio: SQLite (dados/usuarios.db).

Endpoints (acessados via Gateway em /api/usuarios):
  POST /usuarios              -> cadastra cliente {nome, email, telefone}
  GET  /usuarios              -> lista clientes (filtro opcional ?email=)
  GET  /usuarios/<id>         -> obtém cliente pelo id
  PUT  /usuarios/<id>         -> atualiza nome/telefone
"""
import os
import sys
from datetime import datetime

from flask import jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum.servico_base import Banco, criar_servico, iniciar  # noqa: E402

PORTA = 5001
DESCRICAO = "Cadastro de clientes"
app = criar_servico("ms-usuarios", PORTA, DESCRICAO)
banco = Banco("usuarios.db", """
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    telefone TEXT,
    criado_em TEXT NOT NULL
);""")


@app.post("/usuarios")
def cadastrar():
    dados = request.get_json(force=True)
    if not dados.get("nome") or not dados.get("email"):
        return jsonify({"erro": "nome e email são obrigatórios"}), 400
    email = dados["email"].strip().lower()
    if banco.consultar_um("SELECT id FROM usuario WHERE email=?", (email,)):
        return jsonify({"erro": "e-mail já cadastrado"}), 409
    novo_id = banco.executar(
        "INSERT INTO usuario (nome, email, telefone, criado_em) VALUES (?,?,?,?)",
        (dados["nome"].strip(), email, dados.get("telefone", ""),
         datetime.now().isoformat(timespec="seconds")))
    return jsonify(banco.consultar_um("SELECT * FROM usuario WHERE id=?", (novo_id,))), 201


@app.get("/usuarios")
def listar():
    email = request.args.get("email")
    if email:
        return jsonify(banco.consultar("SELECT * FROM usuario WHERE email=?", (email.strip().lower(),)))
    return jsonify(banco.consultar("SELECT * FROM usuario ORDER BY id"))


@app.get("/usuarios/<int:id_usuario>")
def obter(id_usuario):
    u = banco.consultar_um("SELECT * FROM usuario WHERE id=?", (id_usuario,))
    return (jsonify(u), 200) if u else (jsonify({"erro": "usuário não encontrado"}), 404)


@app.put("/usuarios/<int:id_usuario>")
def atualizar(id_usuario):
    dados = request.get_json(force=True)
    if not banco.consultar_um("SELECT id FROM usuario WHERE id=?", (id_usuario,)):
        return jsonify({"erro": "usuário não encontrado"}), 404
    banco.executar("UPDATE usuario SET nome=COALESCE(?,nome), telefone=COALESCE(?,telefone) WHERE id=?",
                   (dados.get("nome"), dados.get("telefone"), id_usuario))
    return jsonify(banco.consultar_um("SELECT * FROM usuario WHERE id=?", (id_usuario,)))


if __name__ == "__main__":
    iniciar(app, descricao=DESCRICAO)

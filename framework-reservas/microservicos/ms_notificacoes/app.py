"""
Microserviço de Notificações (ms-notificacoes) — porta 5005
===========================================================
Envia (de forma simulada) as mensagens de confirmação e cancelamento para
os clientes. As mensagens ficam gravadas no banco e são exibidas no console,
simulando um envio por e-mail ou SMS.
Banco de dados próprio: SQLite (dados/notificacoes.db).

Endpoints (via Gateway em /api/notificacoes):
  POST /notificacoes          -> envia {destinatario, canal, assunto, mensagem}
  GET  /notificacoes          -> lista (filtro ?destinatario=)
"""
import os
import sys
from datetime import datetime

from flask import jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum.servico_base import Banco, criar_servico, iniciar  # noqa: E402

PORTA = 5005
DESCRICAO = "Envio de e-mails/SMS (simulado)"
CANAIS = {"email", "sms", "whatsapp"}
app = criar_servico("ms-notificacoes", PORTA, DESCRICAO)
banco = Banco("notificacoes.db", """
CREATE TABLE IF NOT EXISTS notificacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    destinatario TEXT NOT NULL,
    canal TEXT NOT NULL,
    assunto TEXT,
    mensagem TEXT NOT NULL,
    enviado_em TEXT NOT NULL
);""")


@app.post("/notificacoes")
def enviar():
    d = request.get_json(force=True)
    if not d.get("destinatario") or not d.get("mensagem"):
        return jsonify({"erro": "destinatario e mensagem são obrigatórios"}), 400
    canal = (d.get("canal") or "email").lower()
    if canal not in CANAIS:
        return jsonify({"erro": f"canal inválido; use {sorted(CANAIS)}"}), 400
    novo_id = banco.executar(
        "INSERT INTO notificacao (destinatario,canal,assunto,mensagem,enviado_em) VALUES (?,?,?,?,?)",
        (d["destinatario"], canal, d.get("assunto", ""), d["mensagem"],
         datetime.now().isoformat(timespec="seconds")))
    print(f"[ms-notificacoes] {canal.upper()} -> {d['destinatario']}: {d.get('assunto', '')}")
    return jsonify(banco.consultar_um("SELECT * FROM notificacao WHERE id=?", (novo_id,))), 201


@app.get("/notificacoes")
def listar():
    if request.args.get("destinatario"):
        return jsonify(banco.consultar("SELECT * FROM notificacao WHERE destinatario=? ORDER BY id DESC",
                                       (request.args["destinatario"],)))
    return jsonify(banco.consultar("SELECT * FROM notificacao ORDER BY id DESC"))


if __name__ == "__main__":
    iniciar(app, descricao=DESCRICAO)

"""
Microserviço de Pagamentos (ms-pagamentos) — porta 5004
=======================================================
Processa (de forma simulada) os pagamentos das reservas e os reembolsos.
Banco de dados próprio: SQLite (dados/pagamentos.db).

Formas aceitas: pix, cartao, dinheiro, convenio.
Regra de simulação: cartões terminados em "0000" são recusados; o resto é aprovado.
Pagamentos de valor zero recebem o status ISENTO.

Endpoints (via Gateway em /api/pagamentos):
  POST /pagamentos                  -> processa pagamento
       {reserva_id, valor, forma, numero_cartao?}
  GET  /pagamentos                  -> lista (filtro ?reserva_id=)
  GET  /pagamentos/<id>             -> obtém pagamento
  POST /pagamentos/<id>/reembolso   -> reembolsa {valor}
"""
import os
import sys
import uuid
from datetime import datetime

from flask import jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum.servico_base import Banco, criar_servico, iniciar  # noqa: E402

PORTA = 5004
DESCRICAO = "Pagamentos e reembolsos (simulados)"
FORMAS = {"pix", "cartao", "dinheiro", "convenio"}
app = criar_servico("ms-pagamentos", PORTA, DESCRICAO)
banco = Banco("pagamentos.db", """
CREATE TABLE IF NOT EXISTS pagamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id INTEGER NOT NULL,
    valor REAL NOT NULL,
    forma TEXT NOT NULL,
    status TEXT NOT NULL,
    codigo_transacao TEXT,
    valor_reembolsado REAL DEFAULT 0,
    criado_em TEXT NOT NULL
);""")


@app.post("/pagamentos")
def processar():
    d = request.get_json(force=True)
    forma = (d.get("forma") or "").lower()
    if forma not in FORMAS:
        return jsonify({"erro": f"forma de pagamento inválida; use {sorted(FORMAS)}"}), 400
    valor = round(float(d.get("valor", 0)), 2)
    if valor < 0:
        return jsonify({"erro": "valor não pode ser negativo"}), 400

    if valor == 0:
        status = "ISENTO"
    elif forma == "cartao" and str(d.get("numero_cartao", "")).endswith("0000"):
        status = "RECUSADO"
    elif forma == "dinheiro":
        status = "PENDENTE"  # pago no local
    else:
        status = "APROVADO"
    codigo = f"{forma.upper()}-{uuid.uuid4().hex[:10].upper()}"
    novo_id = banco.executar(
        "INSERT INTO pagamento (reserva_id,valor,forma,status,codigo_transacao,criado_em) VALUES (?,?,?,?,?,?)",
        (d["reserva_id"], valor, forma, status, codigo, datetime.now().isoformat(timespec="seconds")))
    return jsonify(banco.consultar_um("SELECT * FROM pagamento WHERE id=?", (novo_id,))), 201


@app.get("/pagamentos")
def listar():
    if request.args.get("reserva_id"):
        return jsonify(banco.consultar("SELECT * FROM pagamento WHERE reserva_id=?",
                                       (request.args["reserva_id"],)))
    return jsonify(banco.consultar("SELECT * FROM pagamento ORDER BY id"))


@app.get("/pagamentos/<int:id_pagamento>")
def obter(id_pagamento):
    p = banco.consultar_um("SELECT * FROM pagamento WHERE id=?", (id_pagamento,))
    return (jsonify(p), 200) if p else (jsonify({"erro": "pagamento não encontrado"}), 404)


@app.post("/pagamentos/<int:id_pagamento>/reembolso")
def reembolsar(id_pagamento):
    p = banco.consultar_um("SELECT * FROM pagamento WHERE id=?", (id_pagamento,))
    if not p:
        return jsonify({"erro": "pagamento não encontrado"}), 404
    valor = round(float(request.get_json(force=True).get("valor", 0)), 2)
    if valor > p["valor"] - p["valor_reembolsado"]:
        return jsonify({"erro": "valor de reembolso maior que o saldo pago"}), 400
    novo_status = "REEMBOLSADO" if valor > 0 else p["status"]
    banco.executar("UPDATE pagamento SET valor_reembolsado=valor_reembolsado+?, status=? WHERE id=?",
                   (valor, novo_status, id_pagamento))
    return jsonify(banco.consultar_um("SELECT * FROM pagamento WHERE id=?", (id_pagamento,)))


if __name__ == "__main__":
    iniciar(app, descricao=DESCRICAO)

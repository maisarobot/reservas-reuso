"""
Microserviço de Reservas (ms-reservas) — porta 5003
===================================================
Registra as reservas e garante que não existam dois agendamentos
sobrepostos para o mesmo recurso (regra de conflito de horário).
Banco de dados próprio: SQLite (dados/reservas.db).

Datas no formato ISO "AAAA-MM-DDTHH:MM".

Endpoints (via Gateway em /api/reservas):
  POST  /reservas                  -> cria reserva (409 se houver conflito)
        {dominio, recurso_id, cliente_id, inicio, fim, valor, dados_extras{}}
  GET   /reservas                  -> lista; filtros: dominio, recurso_id,
                                      cliente_id, data (AAAA-MM-DD), status
  GET   /reservas/<id>             -> obtém uma reserva
  PATCH /reservas/<id>             -> altera status/pagamento_id
  POST  /reservas/<id>/cancelar    -> cancela a reserva
"""
import json
import os
import sys
from datetime import datetime

from flask import jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum.servico_base import Banco, criar_servico, iniciar  # noqa: E402

PORTA = 5003
DESCRICAO = "Agendamentos e controle de conflitos"
app = criar_servico("ms-reservas", PORTA, DESCRICAO)
banco = Banco("reservas.db", """
CREATE TABLE IF NOT EXISTS reserva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dominio TEXT NOT NULL,
    recurso_id INTEGER NOT NULL,
    cliente_id INTEGER NOT NULL,
    inicio TEXT NOT NULL,
    fim TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDENTE',
    valor REAL DEFAULT 0,
    pagamento_id INTEGER,
    dados_extras TEXT DEFAULT '{}',
    criado_em TEXT NOT NULL
);""")
STATUS_VALIDOS = {"PENDENTE", "CONFIRMADA", "CANCELADA", "CONCLUIDA"}


def _formatar(r):
    if r:
        r["dados_extras"] = json.loads(r["dados_extras"] or "{}")
    return r


def _existe_conflito(recurso_id, inicio, fim):
    """Dois intervalos [a,b) e [c,d) se sobrepõem quando a < d e c < b."""
    return banco.consultar_um(
        "SELECT id FROM reserva WHERE recurso_id=? AND status!='CANCELADA' AND inicio < ? AND ? < fim",
        (recurso_id, fim, inicio))


@app.post("/reservas")
def criar():
    d = request.get_json(force=True)
    faltando = [c for c in ("dominio", "recurso_id", "cliente_id", "inicio", "fim") if not d.get(c)]
    if faltando:
        return jsonify({"erro": f"campos obrigatórios: {', '.join(faltando)}"}), 400
    try:
        if datetime.fromisoformat(d["inicio"]) >= datetime.fromisoformat(d["fim"]):
            return jsonify({"erro": "início deve ser anterior ao fim"}), 400
    except ValueError:
        return jsonify({"erro": "datas devem estar no formato AAAA-MM-DDTHH:MM"}), 400
    if _existe_conflito(d["recurso_id"], d["inicio"], d["fim"]):
        return jsonify({"erro": "horário indisponível para este recurso"}), 409
    novo_id = banco.executar(
        "INSERT INTO reserva (dominio,recurso_id,cliente_id,inicio,fim,status,valor,dados_extras,criado_em)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (d["dominio"], d["recurso_id"], d["cliente_id"], d["inicio"], d["fim"], "PENDENTE",
         float(d.get("valor", 0)), json.dumps(d.get("dados_extras", {}), ensure_ascii=False),
         datetime.now().isoformat(timespec="seconds")))
    return jsonify(_formatar(banco.consultar_um("SELECT * FROM reserva WHERE id=?", (novo_id,)))), 201


@app.get("/reservas")
def listar():
    sql, params = "SELECT * FROM reserva WHERE 1=1", []
    for campo in ("dominio", "recurso_id", "cliente_id", "status"):
        if request.args.get(campo):
            sql += f" AND {campo}=?"
            params.append(request.args[campo])
    if request.args.get("data"):
        sql += " AND substr(inicio,1,10)=?"
        params.append(request.args["data"])
    sql += " ORDER BY inicio"
    return jsonify([_formatar(r) for r in banco.consultar(sql, params)])


@app.get("/reservas/<int:id_reserva>")
def obter(id_reserva):
    r = _formatar(banco.consultar_um("SELECT * FROM reserva WHERE id=?", (id_reserva,)))
    return (jsonify(r), 200) if r else (jsonify({"erro": "reserva não encontrada"}), 404)


@app.patch("/reservas/<int:id_reserva>")
def alterar(id_reserva):
    d = request.get_json(force=True)
    if not banco.consultar_um("SELECT id FROM reserva WHERE id=?", (id_reserva,)):
        return jsonify({"erro": "reserva não encontrada"}), 404
    if "status" in d:
        if d["status"] not in STATUS_VALIDOS:
            return jsonify({"erro": f"status inválido; use {sorted(STATUS_VALIDOS)}"}), 400
        banco.executar("UPDATE reserva SET status=? WHERE id=?", (d["status"], id_reserva))
    if "pagamento_id" in d:
        banco.executar("UPDATE reserva SET pagamento_id=? WHERE id=?", (d["pagamento_id"], id_reserva))
    return jsonify(_formatar(banco.consultar_um("SELECT * FROM reserva WHERE id=?", (id_reserva,))))


@app.post("/reservas/<int:id_reserva>/cancelar")
def cancelar(id_reserva):
    r = banco.consultar_um("SELECT * FROM reserva WHERE id=?", (id_reserva,))
    if not r:
        return jsonify({"erro": "reserva não encontrada"}), 404
    if r["status"] == "CANCELADA":
        return jsonify({"erro": "reserva já cancelada"}), 409
    banco.executar("UPDATE reserva SET status='CANCELADA' WHERE id=?", (id_reserva,))
    return jsonify(_formatar(banco.consultar_um("SELECT * FROM reserva WHERE id=?", (id_reserva,))))


if __name__ == "__main__":
    iniciar(app, descricao=DESCRICAO)

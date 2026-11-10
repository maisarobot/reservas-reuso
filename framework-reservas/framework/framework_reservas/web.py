"""
web.py — Interface web REUTILIZÁVEL do framework
================================================
As telas (início, formulário de reserva, comprovante, minhas reservas e
agenda) são as mesmas para todas as aplicações. O conteúdo de cada tela é
preenchido a partir dos hotspots do controlador concreto:
configuracao_interface(), campos_extras(), formas_pagamento(), etc.

Uso pela aplicação:
    from framework_reservas import executar_aplicacao
    executar_aplicacao(MeuControlador(), porta=9001)
"""
import logging
import os
import threading
import time
from datetime import date, datetime

import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

# Silencia o log de cada requisição HTTP (heartbeats poluiriam o console)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

from .controlador import ControladorReserva
from .excecoes import ExcecaoFramework
from .util import moeda

REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://127.0.0.1:8761")
STATUS_ROTULO = {"CONFIRMADA": "Confirmada", "PENDENTE": "Pendente",
                 "CANCELADA": "Cancelada", "CONCLUIDA": "Concluída"}


def criar_aplicacao_web(controlador: ControladorReserva) -> Flask:
    """Fábrica da aplicação Flask a partir de um controlador concreto."""
    pasta = os.path.dirname(os.path.abspath(__file__))
    app = Flask(controlador.dominio(), template_folder=os.path.join(pasta, "templates"),
                static_folder=os.path.join(pasta, "static"))
    app.secret_key = f"chave-{controlador.dominio()}"
    app.json.ensure_ascii = False
    app.jinja_env.filters["moeda"] = moeda

    @app.context_processor
    def contexto_global():
        return {"cfg": controlador.configuracao_interface(), "status_rotulo": STATUS_ROTULO,
                "rotulos": {c.nome: c.rotulo for c in controlador.campos_extras()},
                "dominio": controlador.dominio(), "hoje": date.today().isoformat()}

    @app.get("/")
    def inicio():
        erro = None
        try:
            recursos = controlador.listar_recursos()
        except ExcecaoFramework as e:
            recursos, erro = [], str(e)
        return render_template("inicio.html", recursos=recursos, erro=erro,
                               microservicos=controlador.gateway.status_microservicos())

    @app.get("/reservar/<int:recurso_id>")
    def formulario(recurso_id):
        try:
            recurso = controlador._obter_recurso_do_dominio(recurso_id)
        except ExcecaoFramework as e:
            flash(str(e), "erro")
            return redirect(url_for("inicio"))
        return render_template("reservar.html", recurso=recurso, campos=controlador.campos_extras(),
                               formas=controlador.formas_pagamento(), valores=request.args, erro=None)

    @app.post("/reservar/<int:recurso_id>")
    def reservar(recurso_id):
        dados = {**request.form.to_dict(), "recurso_id": recurso_id}
        try:
            resultado = controlador.realizar_reserva(dados)   # <<< MÉTODO TEMPLATE
        except ExcecaoFramework as e:
            recurso = controlador._obter_recurso_do_dominio(recurso_id)
            return render_template("reservar.html", recurso=recurso, campos=controlador.campos_extras(),
                                   formas=controlador.formas_pagamento(), valores=request.form,
                                   erro=str(e)), 400
        return render_template("comprovante.html", reserva=resultado.reserva, recurso=resultado.recurso,
                               cliente=resultado.cliente, pagamento=resultado.pagamento,
                               mensagem=resultado.mensagem, assunto=resultado.assunto,
                               passos=resultado.passos)

    @app.get("/horarios")
    def horarios():
        try:
            dia = date.fromisoformat(request.args["data"])
            return jsonify(controlador.listar_horarios_livres(int(request.args["recurso_id"]), dia))
        except (KeyError, ValueError):
            return jsonify([])
        except ExcecaoFramework as e:
            return jsonify({"erro": str(e)}), 400

    @app.get("/comprovante/<int:id_reserva>")
    def comprovante(id_reserva):
        try:
            reserva, recurso, cliente, pagamento = controlador.obter_detalhes(id_reserva)
        except ExcecaoFramework as e:
            flash(str(e), "erro")
            return redirect(url_for("inicio"))
        return render_template("comprovante.html", reserva=reserva, recurso=recurso, cliente=cliente,
                               pagamento=pagamento, mensagem=None, assunto=None, passos=None)

    @app.get("/minhas-reservas")
    def minhas_reservas():
        email = request.args.get("email", "").strip()
        cliente, reservas, recursos = None, [], {}
        if email:
            try:
                cliente, reservas = controlador.listar_reservas_cliente(email)
                recursos = {r.id: r for r in controlador.listar_recursos()}
            except ExcecaoFramework as e:
                flash(str(e), "erro")
        return render_template("minhas_reservas.html", email=email, cliente=cliente,
                               reservas=sorted(reservas, key=lambda r: r.inicio, reverse=True),
                               recursos=recursos, agora=datetime.now())

    @app.post("/cancelar/<int:id_reserva>")
    def cancelar(id_reserva):
        email = request.form.get("email", "")
        try:
            r = controlador.cancelar_reserva(id_reserva, email)   # <<< MÉTODO TEMPLATE
            cfg = controlador.configuracao_interface()
            flash(f"{cfg.rotulo_reserva} nº {id_reserva} cancelada. Reembolso de {r['percentual']:.0%}: "
                  f"{moeda(r['valor_reembolso'])}.", "sucesso")
        except ExcecaoFramework as e:
            flash(str(e), "erro")
        return redirect(url_for("minhas_reservas", email=email))

    @app.get("/agenda")
    def agenda():
        try:
            reservas = controlador.listar_agenda()
            recursos = {r.id: r for r in controlador.recursos.listar(controlador.dominio())}
        except ExcecaoFramework as e:
            flash(str(e), "erro")
            reservas, recursos = [], {}
        return render_template("agenda.html", reservas=reservas, recursos=recursos)

    return app


def _registrar_aplicacao(nome, porta):
    """Registra a aplicação no Service Registry (aparece no painel de serviços)."""
    dados = {"nome": nome, "host": "127.0.0.1", "porta": porta, "tipo": "aplicação",
             "descricao": "Aplicação construída com o framework",
             "url_saude": f"http://127.0.0.1:{porta}/"}
    registrado = False
    while True:
        try:
            if not registrado:
                requests.post(f"{REGISTRY_URL}/registrar", json=dados, timeout=2)
                registrado = True
            elif requests.post(f"{REGISTRY_URL}/heartbeat/{nome}", timeout=2).status_code == 404:
                registrado = False
                continue
        except requests.RequestException:
            registrado = False
        time.sleep(5)


def executar_aplicacao(controlador: ControladorReserva, porta: int) -> None:
    """Ponto de entrada de qualquer aplicação construída com o framework."""
    try:
        controlador.inicializar()
    except ExcecaoFramework as e:
        print(f"[aviso] não foi possível cadastrar os recursos iniciais agora: {e}")
    nome = f"app-{controlador.dominio()}"
    threading.Thread(target=_registrar_aplicacao, args=(nome, porta), daemon=True).start()
    app = criar_aplicacao_web(controlador)
    print(f"[{nome}] {controlador.configuracao_interface().nome} em http://127.0.0.1:{porta}")
    app.run(host="0.0.0.0", port=porta, debug=False, use_reloader=False)

"""
APLICAÇÃO 1 — Clínica Saúde Mais (agendamento de consultas médicas)
===================================================================
Construída REUSANDO o Framework de Reservas. Esta aplicação NÃO contém
nenhum código de comunicação com microserviços, de banco de dados ou de
telas: tudo isso vem do framework. Aqui só existe a implementação dos
HOTSPOTS (pontos de adaptação) do ControladorReserva.

Recurso reservável ...... médico
Duração ................. 30 minutos (hook duracao_minutos)
Regras próprias ......... só dias úteis; consulta de RETORNO só vale até
                          30 dias após uma consulta com o mesmo médico
Preço ................... valor do médico; retorno gratuito; Convênio Ouro
                          cobre 100% e Convênio Prata cobre 50%
Cancelamento ............ 100% de reembolso com 24 h ou mais; 50% com 2 h
                          ou mais; abaixo disso, sem reembolso

Execução:  python aplicacoes/app_clinica/app.py   ->  http://127.0.0.1:9001
"""
import os
import sys
from datetime import date, datetime, time, timedelta

# Torna o pacote do framework importável (pasta framework/ na raiz do projeto)
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "framework"))

from framework_reservas import (CampoFormulario, ConfiguracaoInterface,  # noqa: E402
                                ControladorReserva, ExcecaoRegraNegocio, executar_aplicacao,
                                moeda)

PORTA = 9001
COBERTURA_CONVENIO = {"Particular": 0.0, "Convênio Ouro": 1.0, "Convênio Prata": 0.5}


class ControladorClinica(ControladorReserva):
    """Controlador concreto: herda o método template e preenche os hotspots."""

    # ---------------- HOTSPOTS ABSTRATOS (obrigatórios) ----------------
    def dominio(self):
        return "clinica"

    def configuracao_interface(self):
        return ConfiguracaoInterface(
            nome="Clínica Saúde Mais", slogan="Agende sua consulta em poucos cliques",
            cor_primaria="#0e7490", icone="🩺", rotulo_recurso="Médico",
            rotulo_recurso_plural="Médicos", rotulo_reserva="Consulta",
            texto_botao="Agendar consulta")

    def recursos_iniciais(self):
        return [
            {"tipo": "Clínica Geral", "nome": "Dra. Ana Lima", "preco_base": 150,
             "descricao": "Atendimento clínico geral, check-up e encaminhamentos.",
             "atributos": {"CRM": "AL-10234", "Sala": "101"}},
            {"tipo": "Cardiologia", "nome": "Dr. Carlos Mendes", "preco_base": 250,
             "descricao": "Avaliação cardiológica, eletrocardiograma e risco cirúrgico.",
             "atributos": {"CRM": "AL-08812", "Sala": "203"}},
            {"tipo": "Dermatologia", "nome": "Dra. Juliana Rocha", "preco_base": 220,
             "descricao": "Consultas dermatológicas clínicas e estéticas.",
             "atributos": {"CRM": "AL-11590", "Sala": "105"}},
            {"tipo": "Pediatria", "nome": "Dr. Paulo Santos", "preco_base": 180,
             "descricao": "Acompanhamento do crescimento e saúde infantil.",
             "atributos": {"CRM": "AL-09977", "Sala": "110"}},
        ]

    def grade_horarios(self, recurso, dia: date):
        """Segunda a sexta, das 08:00 às 12:00 e das 13:30 às 17:30, a cada 30 min."""
        if dia.weekday() >= 5:  # sábado (5) e domingo (6): fechado
            return []
        manha = [time(8 + m // 60, m % 60) for m in range(0, 240, 30)]           # 08:00..11:30
        tarde = [time(13 + m // 60, m % 60) for m in range(30, 270, 30)]         # 13:30..17:00
        return manha + tarde

    def campos_extras(self):
        return [
            CampoFormulario("tipo_consulta", "Tipo de consulta", "select",
                            ["Primeira consulta", "Retorno"], padrao="Primeira consulta"),
            CampoFormulario("convenio", "Convênio", "select", list(COBERTURA_CONVENIO),
                            padrao="Particular"),
            CampoFormulario("motivo", "Motivo da consulta", "text", obrigatorio=False),
        ]

    def validar_regras_negocio(self, pedido, recurso, cliente):
        # Regra 1: pagamento "convênio" exige um convênio informado
        if pedido.forma_pagamento == "convenio" and pedido.extras["convenio"] == "Particular":
            raise ExcecaoRegraNegocio("Para faturar no convênio, selecione o seu convênio.")
        # Regra 2: retorno só até 30 dias após consulta confirmada com o mesmo médico
        if pedido.extras["tipo_consulta"] == "Retorno" and not self._tem_consulta_recente(
                cliente.id, recurso.id, pedido.inicio):
            raise ExcecaoRegraNegocio(
                f"Retorno só é permitido até 30 dias após uma consulta com {recurso.nome}.")

    def calcular_valor(self, pedido, recurso, cliente):
        if pedido.extras["tipo_consulta"] == "Retorno":
            return 0.0  # retorno é gratuito
        cobertura = COBERTURA_CONVENIO[pedido.extras["convenio"]]
        return recurso.preco_base * (1 - cobertura)

    def montar_mensagem_confirmacao(self, reserva, recurso, cliente, pagamento):
        assunto = f"Consulta confirmada com {recurso.nome}"
        mensagem = (f"Olá, {cliente.nome}!\n"
                    f"Sua consulta ({reserva.dados_extras['tipo_consulta']}) de {recurso.tipo} com "
                    f"{recurso.nome} está marcada para {reserva.inicio:%d/%m/%Y} às {reserva.inicio:%H:%M}, "
                    f"sala {recurso.atributos.get('Sala', '-')}.\n"
                    f"Valor: {moeda(reserva.valor)} ({reserva.dados_extras['convenio']}).\n"
                    f"Chegue 15 minutos antes e traga documento com foto e a carteirinha do convênio.")
        return assunto, mensagem

    def calcular_reembolso(self, reserva, horas_antecedencia):
        if horas_antecedencia >= 24:
            return 1.0
        if horas_antecedencia >= 2:
            return 0.5
        return 0.0

    # ---------------- HOOKS sobrescritos (opcionais) ----------------
    def duracao_minutos(self, recurso, pedido):
        return 30

    def antecedencia_minima_horas(self):
        return 2

    def formas_pagamento(self):
        return [("pix", "PIX"), ("cartao", "Cartão de crédito"), ("convenio", "Faturar no convênio")]

    def apos_reserva(self, resultado):
        print(f"[clinica] consulta #{resultado.reserva.id} confirmada para {resultado.cliente.nome}")

    # ---------------- Auxiliar da aplicação ----------------
    def _tem_consulta_recente(self, cliente_id, recurso_id, data_retorno: datetime) -> bool:
        for r in self.reservas.listar_do_cliente(cliente_id, self.dominio()):
            if (r.recurso_id == recurso_id and r.status == "CONFIRMADA"
                    and data_retorno - timedelta(days=30) <= r.inicio < data_retorno):
                return True
        return False


if __name__ == "__main__":
    executar_aplicacao(ControladorClinica(), porta=PORTA)

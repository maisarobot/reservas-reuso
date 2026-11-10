"""
APLICAÇÃO 2 — Bistrô Maré Alta (reserva de mesas em restaurante)
================================================================
Segunda aplicação construída REUSANDO o mesmo Framework de Reservas.
Comparando com a Clínica, muda apenas a implementação dos HOTSPOTS:

Recurso reservável ...... mesa (com capacidade de pessoas)
Duração ................. 2 h (3 h na Área VIP)        (hook duracao_minutos)
Funcionamento ........... fechado às segundas; almoço 11:30–14:30;
                          jantar 18:30–22:00 (domingo só almoço)
Regras próprias ......... nº de pessoas ≤ capacidade da mesa; Área VIP
                          mínimo de 6 pessoas; grupos > 8 pessoas exigem
                          24 h de antecedência
Preço (sinal) ........... R$ 20,00 por pessoa, abatido na conta;
                          50% de desconto às terças e quartas;
                          aniversariante não paga o sinal
Cancelamento ............ 100% de reembolso com 4 h ou mais; senão 0%
Notificação ............. por WhatsApp (hook canal_notificacao)

Execução:  python aplicacoes/app_restaurante/app.py   ->  http://127.0.0.1:9002
"""
import os
import sys
from datetime import date, datetime, time, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "framework"))

from framework_reservas import (CampoFormulario, ConfiguracaoInterface,  # noqa: E402
                                ControladorReserva, ExcecaoRegraNegocio, executar_aplicacao,
                                moeda)

PORTA = 9002
SINAL_POR_PESSOA = 20.0


def _intervalo(inicio: time, fim: time, passo=30):
    """Gera horários de `inicio` até `fim` (inclusive) a cada `passo` minutos."""
    atual, limite, lista = datetime.combine(date.today(), inicio), datetime.combine(date.today(), fim), []
    while atual <= limite:
        lista.append(atual.time())
        atual += timedelta(minutes=passo)
    return lista


class ControladorRestaurante(ControladorReserva):

    # ---------------- HOTSPOTS ABSTRATOS (obrigatórios) ----------------
    def dominio(self):
        return "restaurante"

    def configuracao_interface(self):
        return ConfiguracaoInterface(
            nome="Bistrô Maré Alta", slogan="Frutos do mar com vista para o mar — reserve sua mesa",
            cor_primaria="#b45309", icone="🍽️", rotulo_recurso="Mesa",
            rotulo_recurso_plural="Mesas", rotulo_reserva="Reserva", texto_botao="Reservar mesa")

    def recursos_iniciais(self):
        return [
            {"tipo": "Varanda", "nome": "Mesa 1 — Varanda", "capacidade": 2,
             "descricao": "Mesa para casal com vista para o mar.", "atributos": {"Ambiente": "aberto"}},
            {"tipo": "Salão", "nome": "Mesa 2 — Salão", "capacidade": 4,
             "descricao": "Mesa climatizada próxima à adega.", "atributos": {"Ambiente": "climatizado"}},
            {"tipo": "Salão", "nome": "Mesa 3 — Salão", "capacidade": 6,
             "descricao": "Mesa para famílias e grupos pequenos.", "atributos": {"Ambiente": "climatizado"}},
            {"tipo": "Área VIP", "nome": "Mesa 4 — Área VIP", "capacidade": 12,
             "descricao": "Espaço reservado para comemorações e eventos.",
             "atributos": {"Ambiente": "privativo"}},
        ]

    def grade_horarios(self, recurso, dia: date):
        if dia.weekday() == 0:                               # segunda-feira: fechado
            return []
        almoco = _intervalo(time(11, 30), time(14, 30))
        if dia.weekday() == 6:                               # domingo: só almoço
            return almoco
        return almoco + _intervalo(time(18, 30), time(22, 0))

    def campos_extras(self):
        return [
            CampoFormulario("numero_pessoas", "Número de pessoas", "number", padrao="2"),
            CampoFormulario("ocasiao", "Ocasião especial", "select",
                            ["Nenhuma", "Aniversário", "Encontro romântico", "Negócios",
                             "Confraternização"], padrao="Nenhuma"),
            CampoFormulario("observacoes", "Restrições alimentares / pedidos", "text", obrigatorio=False),
        ]

    def validar_regras_negocio(self, pedido, recurso, cliente):
        pessoas = pedido.extras["numero_pessoas"]
        if pessoas < 1:
            raise ExcecaoRegraNegocio("Informe pelo menos 1 pessoa.")
        if pessoas > recurso.capacidade:
            raise ExcecaoRegraNegocio(
                f"A {recurso.nome} comporta no máximo {recurso.capacidade} pessoas.")
        if recurso.tipo == "Área VIP" and pessoas < 6:
            raise ExcecaoRegraNegocio("A Área VIP é exclusiva para grupos a partir de 6 pessoas.")
        if pessoas > 8 and pedido.inicio - datetime.now() < timedelta(hours=24):
            raise ExcecaoRegraNegocio("Grupos com mais de 8 pessoas precisam reservar com 24 h de antecedência.")

    def calcular_valor(self, pedido, recurso, cliente):
        pagantes = pedido.extras["numero_pessoas"]
        if pedido.extras["ocasiao"] == "Aniversário":
            pagantes -= 1                                    # aniversariante isento
        valor = max(pagantes, 0) * SINAL_POR_PESSOA
        if pedido.inicio.weekday() in (1, 2):               # terça e quarta
            valor *= 0.5
        return valor

    def montar_mensagem_confirmacao(self, reserva, recurso, cliente, pagamento):
        extras = reserva.dados_extras
        assunto = f"Mesa reservada — {reserva.inicio:%d/%m} às {reserva.inicio:%H:%M}"
        mensagem = (f"Oi, {cliente.nome}! Sua mesa no Bistrô Maré Alta está garantida.\n"
                    f"{recurso.nome} para {extras['numero_pessoas']} pessoa(s) em "
                    f"{reserva.inicio:%d/%m/%Y} às {reserva.inicio:%H:%M}.\n"
                    f"Sinal pago: {moeda(reserva.valor)} (será abatido da sua conta).\n"
                    + (f"Ocasião: {extras['ocasiao']} — prepararemos uma surpresa! 🎉\n"
                       if extras["ocasiao"] != "Nenhuma" else "")
                    + "Tolerância de 15 minutos. Até lá!")
        return assunto, mensagem

    def calcular_reembolso(self, reserva, horas_antecedencia):
        return 1.0 if horas_antecedencia >= 4 else 0.0

    # ---------------- HOOKS sobrescritos (opcionais) ----------------
    def duracao_minutos(self, recurso, pedido):
        return 180 if recurso.tipo == "Área VIP" else 120

    def dias_maximos_antecedencia(self):
        return 30

    def canal_notificacao(self):
        return "whatsapp"


if __name__ == "__main__":
    executar_aplicacao(ControladorRestaurante(), porta=PORTA)

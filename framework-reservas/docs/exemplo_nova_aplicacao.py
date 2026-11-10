"""
EXEMPLO — Como criar uma NOVA aplicação reusando o Framework de Reservas
=======================================================================
Aplicação: Studio Bela Forma (salão de beleza).

Passo 1: tornar o framework importável
Passo 2: herdar de ControladorReserva
Passo 3: implementar os 9 hotspots abstratos
Passo 4: (opcional) sobrescrever hooks
Passo 5: executar com executar_aplicacao()

Para rodar (com os microserviços já no ar):
    copie este arquivo para aplicacoes/app_salao/app.py e execute
    python aplicacoes/app_salao/app.py   ->  http://127.0.0.1:9003
"""
# ---------- Passo 1: tornar o framework importável ----------
import os
import sys
from datetime import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "framework"))

from framework_reservas import (CampoFormulario, ConfiguracaoInterface,  # noqa: E402
                                ControladorReserva, ExcecaoRegraNegocio, executar_aplicacao,
                                moeda)

PRECOS = {"Corte": 60.0, "Escova": 45.0, "Manicure": 35.0, "Coloração": 150.0}


# ---------- Passo 2: herdar de ControladorReserva ----------
class ControladorSalao(ControladorReserva):

    # ---------- Passo 3: hotspots abstratos ----------
    def dominio(self):
        return "salao"

    def configuracao_interface(self):
        return ConfiguracaoInterface(
            nome="Studio Bela Forma", slogan="Seu horário de beleza garantido",
            cor_primaria="#be185d", icone="💇", rotulo_recurso="Profissional",
            rotulo_recurso_plural="Profissionais", rotulo_reserva="Reserva",
            texto_botao="Agendar horário")

    def recursos_iniciais(self):
        return [
            {"tipo": "Cabeleireira", "nome": "Fernanda", "descricao": "Cortes e coloração",
             "atributos": {"Experiência": "10 anos"}},
            {"tipo": "Manicure", "nome": "Patrícia", "descricao": "Unhas em gel e tradicionais",
             "atributos": {"Experiência": "6 anos"}},
        ]

    def grade_horarios(self, recurso, dia):
        if dia.weekday() == 6:                      # domingo fechado
            return []
        return [time(h, 0) for h in range(9, 19)]   # 09:00 às 18:00, de hora em hora

    def campos_extras(self):
        return [CampoFormulario("servico", "Serviço", "select", list(PRECOS), padrao="Corte")]

    def validar_regras_negocio(self, pedido, recurso, cliente):
        if recurso.tipo == "Manicure" and pedido.extras["servico"] != "Manicure":
            raise ExcecaoRegraNegocio("Esta profissional atende apenas manicure.")

    def calcular_valor(self, pedido, recurso, cliente):
        return PRECOS[pedido.extras["servico"]]

    def montar_mensagem_confirmacao(self, reserva, recurso, cliente, pagamento):
        return ("Horário confirmado!",
                f"{cliente.nome}, seu {reserva.dados_extras['servico']} com {recurso.nome} "
                f"está marcado para {reserva.inicio:%d/%m às %H:%M}. Valor: {moeda(reserva.valor)}.")

    def calcular_reembolso(self, reserva, horas_antecedencia):
        return 1.0 if horas_antecedencia >= 12 else 0.0

    # ---------- Passo 4: hooks opcionais ----------
    def canal_notificacao(self):
        return "sms"


# ---------- Passo 5: executar ----------
if __name__ == "__main__":
    executar_aplicacao(ControladorSalao(), porta=9003)

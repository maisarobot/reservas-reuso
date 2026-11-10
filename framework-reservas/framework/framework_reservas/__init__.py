"""
framework_reservas — Framework de Reservas baseado em Componentes e Microserviços
================================================================================
API pública do framework (tudo o que uma aplicação precisa importar).
"""
from .controlador import ControladorReserva
from .excecoes import (ExcecaoDadosInvalidos, ExcecaoFramework, ExcecaoHorarioIndisponivel,
                       ExcecaoNaoEncontrado, ExcecaoPagamentoRecusado, ExcecaoRegraNegocio,
                       ExcecaoServicoIndisponivel)
from .modelos import (CampoFormulario, Cliente, ConfiguracaoInterface, Pagamento, PedidoReserva,
                      Recurso, Reserva, ResultadoReserva)
from .util import moeda
from .web import criar_aplicacao_web, executar_aplicacao

__version__ = "1.0.0"
__all__ = [
    "ControladorReserva", "executar_aplicacao", "moeda", "criar_aplicacao_web",
    "CampoFormulario", "ConfiguracaoInterface", "Cliente", "Recurso", "Reserva", "Pagamento",
    "PedidoReserva", "ResultadoReserva", "ExcecaoFramework", "ExcecaoDadosInvalidos",
    "ExcecaoRegraNegocio", "ExcecaoHorarioIndisponivel", "ExcecaoNaoEncontrado",
    "ExcecaoPagamentoRecusado", "ExcecaoServicoIndisponivel",
]

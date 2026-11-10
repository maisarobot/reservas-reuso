"""Exceções do Framework de Reservas.

Todas herdam de ExcecaoFramework, então a camada web pode tratar qualquer
erro de negócio com um único `except ExcecaoFramework`.
"""


class ExcecaoFramework(Exception):
    """Erro de negócio genérico do framework (mensagem amigável ao usuário)."""


class ExcecaoDadosInvalidos(ExcecaoFramework):
    """Dados do pedido incompletos ou em formato inválido."""


class ExcecaoRegraNegocio(ExcecaoFramework):
    """Uma regra de negócio (do framework ou da aplicação) foi violada."""


class ExcecaoHorarioIndisponivel(ExcecaoFramework):
    """O horário escolhido já está ocupado para o recurso."""


class ExcecaoNaoEncontrado(ExcecaoFramework):
    """Recurso, cliente ou reserva inexistente."""


class ExcecaoPagamentoRecusado(ExcecaoFramework):
    """O microserviço de pagamentos recusou a transação."""


class ExcecaoServicoIndisponivel(ExcecaoFramework):
    """A API Gateway ou um microserviço está fora do ar."""

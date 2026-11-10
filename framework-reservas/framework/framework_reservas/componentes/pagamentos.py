"""Componente de Pagamentos — implementa IComponentePagamentos usando o ms-pagamentos."""
from ..cliente_gateway import ClienteGateway
from ..interfaces import IComponentePagamentos
from ..modelos import Pagamento


class ComponentePagamentos(IComponentePagamentos):
    def __init__(self, gateway: ClienteGateway):
        self._gateway = gateway

    def processar(self, reserva_id: int, valor: float, forma: str, numero_cartao: str = "") -> Pagamento:
        return Pagamento.de_dict(self._gateway.post("pagamentos", {
            "reserva_id": reserva_id, "valor": valor, "forma": forma, "numero_cartao": numero_cartao}))

    def obter(self, id_pagamento: int) -> Pagamento:
        return Pagamento.de_dict(self._gateway.get(f"pagamentos/{id_pagamento}"))

    def reembolsar(self, id_pagamento: int, valor: float) -> Pagamento:
        return Pagamento.de_dict(self._gateway.post(f"pagamentos/{id_pagamento}/reembolso",
                                                    {"valor": valor}))

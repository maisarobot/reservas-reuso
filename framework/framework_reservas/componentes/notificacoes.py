"""Componente de Notificações — implementa IComponenteNotificacoes usando o ms-notificacoes."""
from ..cliente_gateway import ClienteGateway
from ..interfaces import IComponenteNotificacoes


class ComponenteNotificacoes(IComponenteNotificacoes):
    def __init__(self, gateway: ClienteGateway):
        self._gateway = gateway

    def enviar(self, destinatario: str, assunto: str, mensagem: str, canal: str = "email") -> dict:
        return self._gateway.post("notificacoes", {"destinatario": destinatario, "canal": canal,
                                                   "assunto": assunto, "mensagem": mensagem})

    def listar(self, destinatario: str) -> list:
        return self._gateway.get("notificacoes", destinatario=destinatario)

"""Componente de Recursos — implementa IComponenteRecursos usando o ms-recursos."""
from typing import List

from ..cliente_gateway import ClienteGateway
from ..interfaces import IComponenteRecursos
from ..modelos import Recurso


class ComponenteRecursos(IComponenteRecursos):
    def __init__(self, gateway: ClienteGateway):
        self._gateway = gateway

    def listar(self, dominio: str) -> List[Recurso]:
        return [Recurso.de_dict(r) for r in self._gateway.get("recursos", dominio=dominio)]

    def obter(self, id_recurso: int) -> Recurso:
        return Recurso.de_dict(self._gateway.get(f"recursos/{id_recurso}"))

    def cadastrar(self, dados: dict) -> Recurso:
        return Recurso.de_dict(self._gateway.post("recursos", dados))

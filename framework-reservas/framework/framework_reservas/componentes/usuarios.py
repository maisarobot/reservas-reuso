"""Componente de Usuários — implementa IComponenteUsuarios usando o ms-usuarios."""
from typing import Optional

from ..cliente_gateway import ClienteGateway
from ..interfaces import IComponenteUsuarios
from ..modelos import Cliente


class ComponenteUsuarios(IComponenteUsuarios):
    def __init__(self, gateway: ClienteGateway):
        self._gateway = gateway  # interface requerida

    def buscar_por_email(self, email: str) -> Optional[Cliente]:
        encontrados = self._gateway.get("usuarios", email=email)
        return Cliente.de_dict(encontrados[0]) if encontrados else None

    def cadastrar(self, nome: str, email: str, telefone: str) -> Cliente:
        return Cliente.de_dict(self._gateway.post("usuarios", {"nome": nome, "email": email,
                                                               "telefone": telefone}))

    def obter(self, id_cliente: int) -> Cliente:
        return Cliente.de_dict(self._gateway.get(f"usuarios/{id_cliente}"))

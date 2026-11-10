"""Componente de Reservas — implementa IComponenteReservas usando o ms-reservas."""
from datetime import date, datetime
from typing import List, Optional

from ..cliente_gateway import ClienteGateway
from ..interfaces import IComponenteReservas
from ..modelos import Reserva

FORMATO = "%Y-%m-%dT%H:%M"


class ComponenteReservas(IComponenteReservas):
    def __init__(self, gateway: ClienteGateway):
        self._gateway = gateway

    def criar(self, dominio, recurso_id, cliente_id, inicio: datetime, fim: datetime,
              valor, dados_extras) -> Reserva:
        return Reserva.de_dict(self._gateway.post("reservas", {
            "dominio": dominio, "recurso_id": recurso_id, "cliente_id": cliente_id,
            "inicio": inicio.strftime(FORMATO), "fim": fim.strftime(FORMATO),
            "valor": valor, "dados_extras": dados_extras}))

    def obter(self, id_reserva: int) -> Reserva:
        return Reserva.de_dict(self._gateway.get(f"reservas/{id_reserva}"))

    def listar_do_recurso(self, recurso_id: int, dia: date) -> List[Reserva]:
        return [Reserva.de_dict(r) for r in
                self._gateway.get("reservas", recurso_id=recurso_id, data=dia.isoformat())]

    def listar_do_cliente(self, cliente_id: int, dominio: str) -> List[Reserva]:
        return [Reserva.de_dict(r) for r in
                self._gateway.get("reservas", cliente_id=cliente_id, dominio=dominio)]

    def listar_do_dominio(self, dominio: str) -> List[Reserva]:
        return [Reserva.de_dict(r) for r in self._gateway.get("reservas", dominio=dominio)]

    def atualizar_status(self, id_reserva: int, status: str,
                         pagamento_id: Optional[int] = None) -> Reserva:
        dados = {"status": status}
        if pagamento_id is not None:
            dados["pagamento_id"] = pagamento_id
        return Reserva.de_dict(self._gateway.patch(f"reservas/{id_reserva}", dados))

    def cancelar(self, id_reserva: int) -> Reserva:
        return Reserva.de_dict(self._gateway.post(f"reservas/{id_reserva}/cancelar"))

"""Interfaces (contratos) dos Componentes de Software do framework.

Cada componente é definido primeiro por uma INTERFACE PROVIDA (classe
abstrata). O controlador do framework depende apenas dessas interfaces e
nunca das implementações concretas (princípio da inversão de dependência).
Assim, um componente pode ser substituído (por exemplo, trocar o componente
de pagamentos simulado por um real) sem alterar o controlador nem as
aplicações.

A interface REQUERIDA de todos os componentes é a mesma: `ClienteGateway`
(comunicação com a API Gateway dos microserviços).
"""
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional

from .modelos import Cliente, Pagamento, Recurso, Reserva


class IComponenteUsuarios(ABC):
    """Interface provida pelo Componente de Usuários (-> ms-usuarios)."""

    @abstractmethod
    def buscar_por_email(self, email: str) -> Optional[Cliente]: ...

    @abstractmethod
    def cadastrar(self, nome: str, email: str, telefone: str) -> Cliente: ...

    @abstractmethod
    def obter(self, id_cliente: int) -> Cliente: ...


class IComponenteRecursos(ABC):
    """Interface provida pelo Componente de Recursos (-> ms-recursos)."""

    @abstractmethod
    def listar(self, dominio: str) -> List[Recurso]: ...

    @abstractmethod
    def obter(self, id_recurso: int) -> Recurso: ...

    @abstractmethod
    def cadastrar(self, dados: dict) -> Recurso: ...


class IComponenteReservas(ABC):
    """Interface provida pelo Componente de Reservas (-> ms-reservas)."""

    @abstractmethod
    def criar(self, dominio: str, recurso_id: int, cliente_id: int, inicio: datetime,
              fim: datetime, valor: float, dados_extras: dict) -> Reserva: ...

    @abstractmethod
    def obter(self, id_reserva: int) -> Reserva: ...

    @abstractmethod
    def listar_do_recurso(self, recurso_id: int, dia: date) -> List[Reserva]: ...

    @abstractmethod
    def listar_do_cliente(self, cliente_id: int, dominio: str) -> List[Reserva]: ...

    @abstractmethod
    def listar_do_dominio(self, dominio: str) -> List[Reserva]: ...

    @abstractmethod
    def atualizar_status(self, id_reserva: int, status: str,
                         pagamento_id: Optional[int] = None) -> Reserva: ...

    @abstractmethod
    def cancelar(self, id_reserva: int) -> Reserva: ...


class IComponentePagamentos(ABC):
    """Interface provida pelo Componente de Pagamentos (-> ms-pagamentos)."""

    @abstractmethod
    def processar(self, reserva_id: int, valor: float, forma: str,
                  numero_cartao: str = "") -> Pagamento: ...

    @abstractmethod
    def obter(self, id_pagamento: int) -> Pagamento: ...

    @abstractmethod
    def reembolsar(self, id_pagamento: int, valor: float) -> Pagamento: ...


class IComponenteNotificacoes(ABC):
    """Interface provida pelo Componente de Notificações (-> ms-notificacoes)."""

    @abstractmethod
    def enviar(self, destinatario: str, assunto: str, mensagem: str, canal: str = "email") -> dict: ...

    @abstractmethod
    def listar(self, destinatario: str) -> list: ...

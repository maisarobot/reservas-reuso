"""Modelos (entidades) do domínio do Framework de Reservas.

São classes de dados simples, independentes de qualquer aplicação. Cada
aplicação reaproveita os mesmos modelos: na Clínica um `Recurso` é um médico,
no Restaurante é uma mesa.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Cliente:
    id: int
    nome: str
    email: str
    telefone: str = ""

    @classmethod
    def de_dict(cls, d):
        return cls(id=d["id"], nome=d["nome"], email=d["email"], telefone=d.get("telefone", ""))


@dataclass
class Recurso:
    id: int
    dominio: str
    tipo: str
    nome: str
    descricao: str = ""
    capacidade: int = 1
    preco_base: float = 0.0
    atributos: dict = field(default_factory=dict)

    @classmethod
    def de_dict(cls, d):
        return cls(id=d["id"], dominio=d["dominio"], tipo=d["tipo"], nome=d["nome"],
                   descricao=d.get("descricao", ""), capacidade=d.get("capacidade", 1),
                   preco_base=d.get("preco_base", 0.0), atributos=d.get("atributos", {}))


@dataclass
class Reserva:
    id: int
    dominio: str
    recurso_id: int
    cliente_id: int
    inicio: datetime
    fim: datetime
    status: str
    valor: float
    pagamento_id: Optional[int] = None
    dados_extras: dict = field(default_factory=dict)

    @classmethod
    def de_dict(cls, d):
        return cls(id=d["id"], dominio=d["dominio"], recurso_id=d["recurso_id"],
                   cliente_id=d["cliente_id"], inicio=datetime.fromisoformat(d["inicio"]),
                   fim=datetime.fromisoformat(d["fim"]), status=d["status"], valor=d.get("valor", 0),
                   pagamento_id=d.get("pagamento_id"), dados_extras=d.get("dados_extras", {}))


@dataclass
class Pagamento:
    id: int
    reserva_id: int
    valor: float
    forma: str
    status: str
    codigo_transacao: str = ""
    valor_reembolsado: float = 0.0

    @classmethod
    def de_dict(cls, d):
        return cls(id=d["id"], reserva_id=d["reserva_id"], valor=d["valor"], forma=d["forma"],
                   status=d["status"], codigo_transacao=d.get("codigo_transacao", ""),
                   valor_reembolsado=d.get("valor_reembolsado", 0.0))


@dataclass
class PedidoReserva:
    """Dados que o cliente preenche no formulário, já validados e convertidos."""
    recurso_id: int
    nome: str
    email: str
    telefone: str
    inicio: datetime
    forma_pagamento: str
    extras: dict = field(default_factory=dict)
    numero_cartao: str = ""


@dataclass
class CampoFormulario:
    """Campo extra que uma aplicação acrescenta ao formulário de reserva (hotspot)."""
    nome: str
    rotulo: str
    tipo: str = "text"            # text | number | select
    opcoes: list = field(default_factory=list)
    obrigatorio: bool = True
    padrao: str = ""


@dataclass
class ConfiguracaoInterface:
    """Identidade visual e vocabulário da aplicação (hotspot de interface)."""
    nome: str
    slogan: str
    cor_primaria: str
    icone: str
    rotulo_recurso: str        # ex.: "Médico", "Mesa"
    rotulo_recurso_plural: str  # ex.: "Médicos", "Mesas"
    rotulo_reserva: str        # ex.: "Consulta", "Reserva"
    texto_botao: str = "Reservar"


@dataclass
class ResultadoReserva:
    """O que o método template devolve ao final do processo."""
    reserva: Reserva
    recurso: Recurso
    cliente: Cliente
    pagamento: Pagamento
    assunto: str
    mensagem: str
    passos: list = field(default_factory=list)  # rastro dos microserviços acionados

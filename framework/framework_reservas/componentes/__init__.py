"""Componentes de software do framework (implementações das interfaces)."""
from .notificacoes import ComponenteNotificacoes
from .pagamentos import ComponentePagamentos
from .recursos import ComponenteRecursos
from .reservas import ComponenteReservas
from .usuarios import ComponenteUsuarios

__all__ = ["ComponenteUsuarios", "ComponenteRecursos", "ComponenteReservas",
           "ComponentePagamentos", "ComponenteNotificacoes"]

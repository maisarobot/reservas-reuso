"""
controlador.py — Controle do Framework (padrão de projeto TEMPLATE METHOD)
=========================================================================

`ControladorReserva` é a classe central do framework. Ela define o ESQUELETO
dos algoritmos de "realizar reserva" e "cancelar reserva" nos MÉTODOS
TEMPLATE `realizar_reserva()` e `cancelar_reserva()`.

O esqueleto é FIXO (frozen spots): a ordem dos passos, a comunicação com os
componentes/microserviços, o tratamento de conflitos e de pagamento recusado
são iguais para qualquer aplicação.

Os pontos que mudam de aplicação para aplicação são os HOTSPOTS (pontos de
adaptação de código). Há dois tipos:

  * HOTSPOTS ABSTRATOS (@abstractmethod) — a aplicação É OBRIGADA a
    implementar:
        dominio()                    -> identificador da aplicação
        configuracao_interface()     -> nome, cores e vocabulário da tela
        recursos_iniciais()          -> recursos cadastrados na 1ª execução
        grade_horarios(recurso, dia) -> horários de funcionamento
        campos_extras()              -> campos próprios do formulário
        validar_regras_negocio(...)  -> regras específicas do negócio
        calcular_valor(...)          -> política de preço
        montar_mensagem_confirmacao(...) -> texto enviado ao cliente
        calcular_reembolso(...)      -> política de cancelamento

  * HOOKS (métodos com implementação padrão) — a aplicação PODE sobrescrever:
        duracao_minutos(), antecedencia_minima_horas(),
        dias_maximos_antecedencia(), formas_pagamento(),
        canal_notificacao(), preparar_pedido(), apos_reserva(),
        montar_mensagem_cancelamento()

Para criar uma nova aplicação basta herdar de ControladorReserva, implementar
os hotspots abstratos e chamar `executar_aplicacao(MeuControlador(), porta)`.
"""
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from .cliente_gateway import ClienteGateway
from .componentes import (ComponenteNotificacoes, ComponentePagamentos, ComponenteRecursos,
                          ComponenteReservas, ComponenteUsuarios)
from .excecoes import (ExcecaoDadosInvalidos, ExcecaoNaoEncontrado, ExcecaoPagamentoRecusado,
                       ExcecaoRegraNegocio)
from .interfaces import (IComponenteNotificacoes, IComponentePagamentos, IComponenteRecursos,
                         IComponenteReservas, IComponenteUsuarios)
from .util import moeda
from .modelos import (CampoFormulario, Cliente, ConfiguracaoInterface, Pagamento, PedidoReserva,
                      Recurso, Reserva, ResultadoReserva)


class ControladorReserva(ABC):
    """Classe abstrata do framework. Contém os métodos template e os hotspots."""

    def __init__(self, gateway_url: Optional[str] = None,
                 usuarios: Optional[IComponenteUsuarios] = None,
                 recursos: Optional[IComponenteRecursos] = None,
                 reservas: Optional[IComponenteReservas] = None,
                 pagamentos: Optional[IComponentePagamentos] = None,
                 notificacoes: Optional[IComponenteNotificacoes] = None):
        # Os componentes podem ser injetados (ex.: para testes). Se não forem,
        # o framework usa as implementações padrão, que falam com a Gateway.
        gateway = ClienteGateway(gateway_url)
        self.gateway = gateway
        self.usuarios = usuarios or ComponenteUsuarios(gateway)
        self.recursos = recursos or ComponenteRecursos(gateway)
        self.reservas = reservas or ComponenteReservas(gateway)
        self.pagamentos = pagamentos or ComponentePagamentos(gateway)
        self.notificacoes = notificacoes or ComponenteNotificacoes(gateway)
        self._passos: List[str] = []

    # ==================================================================
    # MÉTODO TEMPLATE 1 — realizar_reserva  (FROZEN SPOT: não sobrescrever)
    # ==================================================================
    def realizar_reserva(self, dados: dict) -> ResultadoReserva:
        """Esqueleto fixo do processo de reserva. Os passos marcados com
        HOTSPOT/HOOK são delegados à aplicação concreta."""
        self._passos = []

        # 1. Converte e valida os dados do formulário (fixo)
        pedido = self._montar_pedido(dados)
        pedido = self.preparar_pedido(pedido)                              # HOOK

        # 2. Busca o recurso no ms-recursos (fixo)
        recurso = self._obter_recurso_do_dominio(pedido.recurso_id)
        self._passo("ms-recursos", f"{recurso.tipo} '{recurso.nome}' consultado")

        # 3. Calcula o intervalo da reserva
        inicio = pedido.inicio
        fim = inicio + timedelta(minutes=self.duracao_minutos(recurso, pedido))  # HOOK

        # 4. Regras gerais do framework: antecedência, grade de horários... (fixo)
        self._validar_regras_gerais(pedido, recurso)

        # 5. Localiza ou cadastra o cliente no ms-usuarios (fixo)
        cliente = self._obter_ou_cadastrar_cliente(pedido)

        # 6. Regras específicas da aplicação
        self.validar_regras_negocio(pedido, recurso, cliente)               # HOTSPOT

        # 7. Política de preço da aplicação
        valor = round(self.calcular_valor(pedido, recurso, cliente), 2)    # HOTSPOT

        # 8. Registra a reserva no ms-reservas (que bloqueia conflitos) (fixo)
        reserva = self.reservas.criar(self.dominio(), recurso.id, cliente.id, inicio, fim,
                                      valor, pedido.extras)
        self._passo("ms-reservas", f"reserva nº {reserva.id} registrada (PENDENTE)")

        # 9. Processa o pagamento no ms-pagamentos (fixo)
        pagamento = self._processar_pagamento(reserva, valor, pedido)

        # 10. Confirma a reserva (fixo)
        status = "CONFIRMADA" if pagamento.status in ("APROVADO", "ISENTO") else "PENDENTE"
        reserva = self.reservas.atualizar_status(reserva.id, status, pagamento.id)
        self._passo("ms-reservas", f"reserva nº {reserva.id} atualizada para {status}")

        # 11. Monta a mensagem e notifica o cliente pelo ms-notificacoes
        assunto, mensagem = self.montar_mensagem_confirmacao(                # HOTSPOT
            reserva, recurso, cliente, pagamento)
        canal = self.canal_notificacao()                                     # HOOK
        self.notificacoes.enviar(cliente.email, assunto, mensagem, canal)
        self._passo("ms-notificacoes", f"{canal} enviado para {cliente.email}")

        resultado = ResultadoReserva(reserva, recurso, cliente, pagamento, assunto, mensagem,
                                     list(self._passos))
        self.apos_reserva(resultado)                                         # HOOK
        return resultado

    # ==================================================================
    # MÉTODO TEMPLATE 2 — cancelar_reserva  (FROZEN SPOT)
    # ==================================================================
    def cancelar_reserva(self, id_reserva: int, email: str) -> dict:
        """Esqueleto fixo do cancelamento, com política de reembolso variável."""
        reserva = self.reservas.obter(id_reserva)
        cliente = self.usuarios.obter(reserva.cliente_id)
        if reserva.dominio != self.dominio() or cliente.email != email.strip().lower():
            raise ExcecaoNaoEncontrado("Reserva não encontrada para este e-mail.")
        if reserva.status == "CANCELADA":
            raise ExcecaoRegraNegocio("Esta reserva já foi cancelada.")
        horas = (reserva.inicio - datetime.now()).total_seconds() / 3600
        if horas < 0:
            raise ExcecaoRegraNegocio("Não é possível cancelar uma reserva que já passou.")

        percentual = max(0.0, min(1.0, self.calcular_reembolso(reserva, horas)))  # HOTSPOT
        valor_reembolso = 0.0
        if reserva.pagamento_id:
            pagamento = self.pagamentos.obter(reserva.pagamento_id)
            if pagamento.status == "APROVADO" and percentual > 0:
                valor_reembolso = round(pagamento.valor * percentual, 2)
                self.pagamentos.reembolsar(pagamento.id, valor_reembolso)
        reserva = self.reservas.cancelar(reserva.id)
        recurso = self.recursos.obter(reserva.recurso_id)
        assunto, mensagem = self.montar_mensagem_cancelamento(                     # HOOK
            reserva, recurso, cliente, valor_reembolso)
        self.notificacoes.enviar(cliente.email, assunto, mensagem, self.canal_notificacao())
        return {"reserva": reserva, "valor_reembolso": valor_reembolso, "percentual": percentual}

    # ==================================================================
    # Serviços fixos auxiliares usados pela interface web
    # ==================================================================
    def inicializar(self) -> None:
        """Cadastra os recursos iniciais da aplicação se o domínio ainda não tiver nenhum."""
        if not self.recursos.listar(self.dominio()):
            for dados in self.recursos_iniciais():                           # HOTSPOT
                self.recursos.cadastrar({**dados, "dominio": self.dominio()})

    def listar_recursos(self) -> List[Recurso]:
        return self.recursos.listar(self.dominio())

    def listar_horarios_livres(self, recurso_id: int, dia: date) -> List[str]:
        """Horários da grade (HOTSPOT) que não conflitam com reservas existentes
        e respeitam a antecedência mínima (HOOK)."""
        recurso = self._obter_recurso_do_dominio(recurso_id)
        ocupadas = [r for r in self.reservas.listar_do_recurso(recurso_id, dia)
                    if r.status != "CANCELADA"]
        limite = datetime.now() + timedelta(hours=self.antecedencia_minima_horas())
        livres = []
        for horario in self.grade_horarios(recurso, dia):                   # HOTSPOT
            inicio = datetime.combine(dia, horario)
            fim = inicio + timedelta(minutes=self.duracao_minutos(recurso, None))
            if inicio < limite:
                continue
            if any(inicio < r.fim and r.inicio < fim for r in ocupadas):
                continue
            livres.append(horario.strftime("%H:%M"))
        return livres

    def obter_detalhes(self, id_reserva: int) -> Tuple[Reserva, Recurso, Cliente, Optional[Pagamento]]:
        reserva = self.reservas.obter(id_reserva)
        if reserva.dominio != self.dominio():
            raise ExcecaoNaoEncontrado("Reserva não encontrada.")
        pagamento = self.pagamentos.obter(reserva.pagamento_id) if reserva.pagamento_id else None
        return reserva, self.recursos.obter(reserva.recurso_id), \
            self.usuarios.obter(reserva.cliente_id), pagamento

    def listar_reservas_cliente(self, email: str) -> Tuple[Optional[Cliente], List[Reserva]]:
        cliente = self.usuarios.buscar_por_email(email.strip().lower())
        if not cliente:
            return None, []
        return cliente, self.reservas.listar_do_cliente(cliente.id, self.dominio())

    def listar_agenda(self) -> List[Reserva]:
        return self.reservas.listar_do_dominio(self.dominio())

    # ==================================================================
    # Passos fixos privados (frozen spots)
    # ==================================================================
    def _passo(self, servico: str, descricao: str) -> None:
        self._passos.append((servico, descricao))

    def _montar_pedido(self, dados: dict) -> PedidoReserva:
        obrigatorios = {"recurso_id": "recurso", "nome": "nome", "email": "e-mail",
                        "data": "data", "hora": "horário", "forma_pagamento": "forma de pagamento"}
        faltando = [rotulo for campo, rotulo in obrigatorios.items() if not str(dados.get(campo, "")).strip()]
        extras = {}
        for campo in self.campos_extras():                                   # HOTSPOT
            valor = str(dados.get(campo.nome, campo.padrao)).strip()
            if campo.obrigatorio and not valor:
                faltando.append(campo.rotulo.lower())
            if campo.tipo == "number" and valor:
                try:
                    valor = int(valor)
                except ValueError as e:
                    raise ExcecaoDadosInvalidos(f"'{campo.rotulo}' deve ser um número.") from e
            extras[campo.nome] = valor
        if faltando:
            raise ExcecaoDadosInvalidos("Preencha: " + ", ".join(faltando) + ".")
        if "@" not in dados["email"]:
            raise ExcecaoDadosInvalidos("Informe um e-mail válido.")
        try:
            inicio = datetime.strptime(f"{dados['data']} {dados['hora']}", "%Y-%m-%d %H:%M")
        except ValueError as e:
            raise ExcecaoDadosInvalidos("Data ou horário em formato inválido.") from e
        forma = dados["forma_pagamento"]
        if forma not in dict(self.formas_pagamento()):                       # HOOK
            raise ExcecaoDadosInvalidos("Forma de pagamento não aceita por esta aplicação.")
        return PedidoReserva(recurso_id=int(dados["recurso_id"]), nome=dados["nome"].strip(),
                             email=dados["email"].strip().lower(), telefone=dados.get("telefone", "").strip(),
                             inicio=inicio, forma_pagamento=forma, extras=extras,
                             numero_cartao=dados.get("numero_cartao", "").replace(" ", ""))

    def _obter_recurso_do_dominio(self, recurso_id: int) -> Recurso:
        recurso = self.recursos.obter(recurso_id)
        if recurso.dominio != self.dominio():
            raise ExcecaoNaoEncontrado("Recurso não pertence a esta aplicação.")
        return recurso

    def _validar_regras_gerais(self, pedido: PedidoReserva, recurso: Recurso) -> None:
        agora = datetime.now()
        if pedido.inicio < agora + timedelta(hours=self.antecedencia_minima_horas()):
            raise ExcecaoRegraNegocio(
                f"A reserva precisa ser feita com pelo menos {self.antecedencia_minima_horas()} h de antecedência.")
        if pedido.inicio > agora + timedelta(days=self.dias_maximos_antecedencia()):
            raise ExcecaoRegraNegocio(
                f"Só é possível reservar até {self.dias_maximos_antecedencia()} dias à frente.")
        if pedido.inicio.time() not in self.grade_horarios(recurso, pedido.inicio.date()):
            raise ExcecaoRegraNegocio("Horário fora do funcionamento para este dia.")

    def _obter_ou_cadastrar_cliente(self, pedido: PedidoReserva) -> Cliente:
        cliente = self.usuarios.buscar_por_email(pedido.email)
        if cliente:
            self._passo("ms-usuarios", f"cliente '{cliente.nome}' localizado (id {cliente.id})")
            return cliente
        cliente = self.usuarios.cadastrar(pedido.nome, pedido.email, pedido.telefone)
        self._passo("ms-usuarios", f"novo cliente '{cliente.nome}' cadastrado (id {cliente.id})")
        return cliente

    def _processar_pagamento(self, reserva: Reserva, valor: float, pedido: PedidoReserva) -> Pagamento:
        pagamento = self.pagamentos.processar(reserva.id, valor, pedido.forma_pagamento,
                                              pedido.numero_cartao)
        self._passo("ms-pagamentos", f"pagamento {pagamento.codigo_transacao}: {pagamento.status} "
                                     f"({moeda(pagamento.valor)})")
        if pagamento.status == "RECUSADO":
            self.reservas.cancelar(reserva.id)  # libera o horário
            raise ExcecaoPagamentoRecusado("Pagamento recusado pela operadora. Tente outra forma de pagamento.")
        return pagamento

    # ==================================================================
    # HOTSPOTS ABSTRATOS — a aplicação DEVE implementar
    # ==================================================================
    @abstractmethod
    def dominio(self) -> str:
        """Identificador único da aplicação (ex.: 'clinica')."""

    @abstractmethod
    def configuracao_interface(self) -> ConfiguracaoInterface:
        """Nome, slogan, cor, ícone e vocabulário exibidos nas telas."""

    @abstractmethod
    def recursos_iniciais(self) -> List[dict]:
        """Recursos cadastrados automaticamente na primeira execução."""

    @abstractmethod
    def grade_horarios(self, recurso: Recurso, dia: date) -> List[time]:
        """Horários de início possíveis para o recurso no dia (vazio = fechado)."""

    @abstractmethod
    def campos_extras(self) -> List[CampoFormulario]:
        """Campos específicos que a aplicação acrescenta ao formulário."""

    @abstractmethod
    def validar_regras_negocio(self, pedido: PedidoReserva, recurso: Recurso, cliente: Cliente) -> None:
        """Lança ExcecaoRegraNegocio se o pedido violar alguma regra da aplicação."""

    @abstractmethod
    def calcular_valor(self, pedido: PedidoReserva, recurso: Recurso, cliente: Cliente) -> float:
        """Valor a ser cobrado pela reserva."""

    @abstractmethod
    def montar_mensagem_confirmacao(self, reserva: Reserva, recurso: Recurso, cliente: Cliente,
                                    pagamento: Pagamento) -> Tuple[str, str]:
        """Devolve (assunto, mensagem) enviados ao cliente após a reserva."""

    @abstractmethod
    def calcular_reembolso(self, reserva: Reserva, horas_antecedencia: float) -> float:
        """Percentual (0.0 a 1.0) do valor pago que será devolvido no cancelamento."""

    # ==================================================================
    # HOOKS — implementação padrão; a aplicação PODE sobrescrever
    # ==================================================================
    def duracao_minutos(self, recurso: Recurso, pedido: Optional[PedidoReserva]) -> int:
        return 60

    def antecedencia_minima_horas(self) -> int:
        return 1

    def dias_maximos_antecedencia(self) -> int:
        return 60

    def formas_pagamento(self) -> List[Tuple[str, str]]:
        return [("pix", "PIX"), ("cartao", "Cartão de crédito")]

    def canal_notificacao(self) -> str:
        return "email"

    def preparar_pedido(self, pedido: PedidoReserva) -> PedidoReserva:
        return pedido

    def apos_reserva(self, resultado: ResultadoReserva) -> None:
        pass

    def montar_mensagem_cancelamento(self, reserva: Reserva, recurso: Recurso, cliente: Cliente,
                                     valor_reembolso: float) -> Tuple[str, str]:
        cfg = self.configuracao_interface()
        return (f"{cfg.rotulo_reserva} cancelada — {cfg.nome}",
                f"Olá, {cliente.nome}. Sua {cfg.rotulo_reserva.lower()} nº {reserva.id} "
                f"({recurso.nome}, {reserva.inicio:%d/%m/%Y %H:%M}) foi cancelada. "
                f"Reembolso: {moeda(valor_reembolso)}.")

# Framework de Reservas — Componentes de Software + Microserviços (Python)

Projeto da disciplina **Reuso de Software e Metodologias Ágeis**.

O **Framework de Reservas** é uma base reutilizável para construir sistemas de
agendamento (consultas, mesas, salas, quadras...). Ele usa três técnicas de reuso:

* **Framework** com o padrão de projeto **Template Method** e **hotspots**
  (pontos de adaptação de código);
* **Componentes de software** com interfaces providas e requeridas;
* **Microserviços** acessados por uma **API Gateway** com **Service Registry**.

Duas aplicações foram construídas a partir do framework:

| Aplicação | Porta | O que reserva |
|---|---|---|
| Clínica Saúde Mais | 9001 | consultas com médicos |
| Bistrô Maré Alta | 9002 | mesas de restaurante |

## Arquitetura

```
 Aplicações (Clínica 9001, Restaurante 9002)
              │   (framework_reservas: ControladorReserva + componentes)
              ▼
        API Gateway 8080  ◄──── consulta ────►  Service Registry 8761
              │
   ┌──────────┼───────────┬─────────────┬──────────────┐
   ▼          ▼           ▼             ▼              ▼
ms-usuarios ms-recursos ms-reservas ms-pagamentos ms-notificacoes
  5001        5002        5003         5004           5005
 (SQLite)   (SQLite)    (SQLite)     (SQLite)       (SQLite)
```

## Estrutura de pastas

```
framework-reservas/
├── iniciar_tudo.py              # sobe todo o sistema com um comando
├── requirements.txt
├── microservicos/
│   ├── comum/servico_base.py    # código comum (registro, heartbeat, SQLite)
│   ├── service_registry/        # 8761 - descoberta de serviços
│   ├── api_gateway/             # 8080 - ponto único de entrada
│   ├── ms_usuarios/             # 5001
│   ├── ms_recursos/             # 5002
│   ├── ms_reservas/             # 5003
│   ├── ms_pagamentos/           # 5004
│   └── ms_notificacoes/         # 5005
├── framework/framework_reservas/
│   ├── controlador.py           # ControladorReserva (Template Method + hotspots)
│   ├── interfaces.py            # interfaces dos componentes
│   ├── componentes/             # implementações dos componentes
│   ├── modelos.py, excecoes.py, cliente_gateway.py, util.py
│   ├── web.py                   # interface web reutilizável (Flask)
│   └── templates/, static/
└── aplicacoes/
    ├── app_clinica/app.py       # Aplicação 1
    └── app_restaurante/app.py   # Aplicação 2
```

## Como executar

Pré-requisito: **Python 3.8 ou mais recente**.

```bash
# 1. Baixar o projeto
git clone https://github.com/SEU-USUARIO/framework-reservas.git
cd framework-reservas

# 2. (Opcional) criar um ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/macOS

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Subir tudo
python iniciar_tudo.py
```

Depois abra no navegador:

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8761 | Painel do Service Registry (lista de microserviços e portas) |
| http://127.0.0.1:8080 | API Gateway (tabela de rotas) |
| http://127.0.0.1:9001 | Aplicação 1 — Clínica |
| http://127.0.0.1:9002 | Aplicação 2 — Restaurante |

Para encerrar: `Ctrl+C` no terminal.

Também é possível subir cada processo em um terminal separado, nesta ordem:
`service_registry` → os 5 `ms_*` → `api_gateway` → aplicações.
Exemplo: `python microservicos/ms_usuarios/app.py`.

Os bancos SQLite são criados automaticamente em `microservicos/dados/`.
Para zerar os dados, apague essa pasta.

### Dicas de teste

* Cartão terminado em **0000** é recusado pelo ms-pagamentos (simulação).
* Na Clínica, “Retorno” só é aceito até 30 dias depois de uma consulta com o mesmo médico.
* No Restaurante, a Área VIP exige pelo menos 6 pessoas e segunda-feira é fechado.

## Como criar uma nova aplicação reusando o framework

1. Crie `aplicacoes/app_salao/app.py`.
2. Herde de `ControladorReserva`.
3. Implemente os 9 hotspots abstratos: `dominio`, `configuracao_interface`,
   `recursos_iniciais`, `grade_horarios`, `campos_extras`,
   `validar_regras_negocio`, `calcular_valor`, `montar_mensagem_confirmacao`,
   `calcular_reembolso`.
4. Se quiser, sobrescreva hooks como `duracao_minutos`, `formas_pagamento` ou `canal_notificacao`.
5. Chame `executar_aplicacao(SeuControlador(), porta=9003)`.

Um exemplo completo está em [`docs/exemplo_nova_aplicacao.py`](docs/exemplo_nova_aplicacao.py).

## Tecnologias

Python 3 · Flask · Jinja2 · Requests · SQLite · HTML/CSS/JavaScript

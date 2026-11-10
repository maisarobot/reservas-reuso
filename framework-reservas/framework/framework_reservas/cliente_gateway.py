"""Cliente HTTP da API Gateway.

Os componentes do framework NÃO conhecem as portas dos microserviços: eles
só conhecem a API Gateway. Esta classe concentra a comunicação HTTP e traduz
os códigos de erro HTTP em exceções do framework.
"""
import os

import requests

from .excecoes import (ExcecaoDadosInvalidos, ExcecaoFramework, ExcecaoHorarioIndisponivel,
                       ExcecaoNaoEncontrado, ExcecaoServicoIndisponivel)

GATEWAY_URL_PADRAO = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8080")


class ClienteGateway:
    def __init__(self, url_base=None, timeout=5):
        self.url_base = (url_base or GATEWAY_URL_PADRAO).rstrip("/")
        self.timeout = timeout

    def _requisitar(self, metodo, caminho, **kwargs):
        try:
            resp = requests.request(metodo, f"{self.url_base}/api/{caminho.lstrip('/')}",
                                    timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise ExcecaoServicoIndisponivel(
                "Não foi possível falar com a API Gateway. Os microserviços estão rodando?") from e
        if resp.status_code < 400:
            return resp.json()
        erro = resp.json().get("erro", resp.text) if resp.headers.get(
            "Content-Type", "").startswith("application/json") else resp.text
        excecao = {400: ExcecaoDadosInvalidos, 404: ExcecaoNaoEncontrado,
                   409: ExcecaoHorarioIndisponivel, 502: ExcecaoServicoIndisponivel,
                   503: ExcecaoServicoIndisponivel}.get(resp.status_code, ExcecaoFramework)
        raise excecao(erro)

    def get(self, caminho, **params):
        return self._requisitar("GET", caminho, params=params)

    def post(self, caminho, dados=None):
        return self._requisitar("POST", caminho, json=dados or {})

    def patch(self, caminho, dados):
        return self._requisitar("PATCH", caminho, json=dados)

    def put(self, caminho, dados):
        return self._requisitar("PUT", caminho, json=dados)

    def status_microservicos(self):
        """Saúde dos microserviços (usado no painel da interface principal)."""
        try:
            return self.get("status")
        except ExcecaoFramework:
            return []

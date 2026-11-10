"""
iniciar_tudo.py — sobe o sistema completo com um único comando.

    python iniciar_tudo.py

Ordem de inicialização:
  1. Service Registry ........ 8761
  2. Microserviços ........... 5001 a 5005
  3. API Gateway ............. 8080
  4. Aplicações .............. 9001 (Clínica) e 9002 (Restaurante)

Pressione Ctrl+C para encerrar todos os processos.
"""
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.abspath(__file__))
PROCESSOS = [
    ("service-registry", "microservicos/service_registry/app.py", 8761),
    ("ms-usuarios", "microservicos/ms_usuarios/app.py", 5001),
    ("ms-recursos", "microservicos/ms_recursos/app.py", 5002),
    ("ms-reservas", "microservicos/ms_reservas/app.py", 5003),
    ("ms-pagamentos", "microservicos/ms_pagamentos/app.py", 5004),
    ("ms-notificacoes", "microservicos/ms_notificacoes/app.py", 5005),
    ("api-gateway", "microservicos/api_gateway/app.py", 8080),
    ("app-clinica", "aplicacoes/app_clinica/app.py", 9001),
    ("app-restaurante", "aplicacoes/app_restaurante/app.py", 9002),
]


def main():
    rodando = []
    try:
        for nome, script, porta in PROCESSOS:
            p = subprocess.Popen([sys.executable, os.path.join(RAIZ, script)], cwd=RAIZ)
            rodando.append((nome, p))
            print(f"  ▶ {nome:<17} porta {porta}")
            # espera o Registry e a Gateway ficarem prontos antes das aplicações
            time.sleep(2.5 if nome in ("service-registry", "api-gateway", "ms-notificacoes") else 0.8)
        print("\nSistema no ar!")
        print("  Service Registry (lista de microserviços): http://127.0.0.1:8761")
        print("  API Gateway ..............................: http://127.0.0.1:8080")
        print("  Aplicação 1 - Clínica ....................: http://127.0.0.1:9001")
        print("  Aplicação 2 - Restaurante ................: http://127.0.0.1:9002")
        print("\nCtrl+C para encerrar.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        for _, p in reversed(rodando):
            p.terminate()


if __name__ == "__main__":
    main()

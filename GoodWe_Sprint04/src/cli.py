"""
cli.py — Interface de terminal do GoodWe ChargeOps Agent.

Uso:
    python -m src.cli
    python -m src.cli --modelo openai/gpt-oss-20b
    python -m src.cli --sessao demo_banca --metricas
"""

import argparse
import uuid

from src.agent import AgenteChargeOps
from src.config import MODELO_PRINCIPAL

BANNER = """
============================================================
 GoodWe ChargeOps Agent — EV Challenge 2026 (FIAP)
 Sprint 3 — arquitetura de agentes com LangGraph
------------------------------------------------------------
 Comandos: 'sair' encerra | 'reset' limpa a sessão
           'historico' mostra o que está na memória
============================================================
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat com o ChargeOps Agent")
    parser.add_argument("--modelo", default=MODELO_PRINCIPAL)
    parser.add_argument("--sessao", default=f"cli_{uuid.uuid4().hex[:8]}")
    parser.add_argument("--metricas", action="store_true",
                        help="Exibe latência, tokens e guardrails a cada turno.")
    args = parser.parse_args()

    print(BANNER)
    print(f" Modelo: {args.modelo}")
    print(f" Sessão: {args.sessao}\n")

    agente = AgenteChargeOps(modelo=args.modelo)

    while True:
        try:
            pergunta = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAtendimento encerrado.")
            break

        if not pergunta:
            continue
        if pergunta.lower() in {"sair", "exit", "quit"}:
            print("Atendimento encerrado.")
            break
        if pergunta.lower() == "reset":
            agente.limpar_sessao(args.sessao)
            print("Memória da sessão limpa.")
            continue
        if pergunta.lower() == "historico":
            for msg in agente.historico(args.sessao):
                autor = msg.__class__.__name__.replace("Message", "")
                print(f"  [{autor}] {str(msg.content)[:120]}")
            continue

        try:
            resultado = agente.responder(pergunta, sessao_id=args.sessao)
        except Exception as erro:  # noqa: BLE001
            print(f"\n[Erro] {type(erro).__name__}: {erro}")
            continue

        print(f"\nAssistente: {resultado['texto']}")

        if args.metricas:
            print(
                f"\n  [métricas] {resultado['latencia_s']}s | "
                f"{resultado['tokens_total']} tokens "
                f"({resultado['tokens_entrada']} entrada + {resultado['tokens_saida']} saída) | "
                f"turno {resultado['turnos_na_sessao']}"
            )
            if resultado["ferramentas"]:
                print(f"  [ferramentas] {', '.join(resultado['ferramentas'])}")
            if resultado["bloqueio_entrada"]:
                print(f"  [guardrail entrada] {resultado['bloqueio_entrada']}")
            if resultado["evento_saida"]:
                print(f"  [guardrail saída] {resultado['evento_saida']}")


if __name__ == "__main__":
    main()

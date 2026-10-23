"""
tools.py — Ferramentas disponíveis para o agente.

Mudança em relação à Sprint 2: as ferramentas deixaram de ser dicionários JSON
escritos à mão (TOOLS_SPEC) mais um dicionário de despacho manual. Agora são
funções decoradas com @tool do LangChain: a assinatura e a docstring viram
automaticamente o schema enviado ao modelo, e o ToolNode do LangGraph cuida da
execução e do roteamento do resultado de volta ao agente.

Ferramentas:
    registrar_ciclo_recarga — grava um ciclo concluído no CSV do condomínio.
    consultar_ciclos        — lê os ciclos já registrados (novidade da Sprint 3).
"""

import csv
import os
from datetime import datetime

from langchain_core.tools import tool

from src.config import REGISTRO_CICLOS_PATH

CABECALHO = [
    "registrado_em", "morador", "data",
    "horario_inicio", "horario_fim", "energia_kwh",
]


@tool
def registrar_ciclo_recarga(
    morador: str,
    data: str,
    energia_kwh: float,
    horario_inicio: str = "",
    horario_fim: str = "",
) -> str:
    """Registra um ciclo de recarga concluído no controle do condomínio.

    Use SOMENTE quando o usuário informar os dados de uma recarga já ocorrida,
    contendo pelo menos o morador, a data e a energia consumida em kWh.
    Nunca invente valores: se faltar um dado obrigatório, pergunte ao usuário.

    Args:
        morador: Nome ou identificação do morador responsável.
        data: Data da recarga no formato AAAA-MM-DD.
        energia_kwh: Energia consumida na sessão, em kWh.
        horario_inicio: Horário de início no formato HH:MM. Opcional.
        horario_fim: Horário de término no formato HH:MM. Opcional.
    """
    if energia_kwh <= 0:
        return "Erro: a energia consumida precisa ser maior que zero."

    arquivo_novo = not os.path.exists(REGISTRO_CICLOS_PATH)

    with open(REGISTRO_CICLOS_PATH, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        if arquivo_novo:
            escritor.writerow(CABECALHO)
        escritor.writerow([
            datetime.now().isoformat(timespec="seconds"),
            morador, data, horario_inicio, horario_fim, energia_kwh,
        ])

    return (
        f"Ciclo registrado com sucesso: morador {morador}, data {data}, "
        f"energia {energia_kwh} kWh."
    )


@tool
def consultar_ciclos(morador: str = "") -> str:
    """Consulta os ciclos de recarga já registrados no condomínio.

    Use quando o usuário perguntar sobre o histórico de recargas, o total
    consumido ou quiser conferir os registros de um morador específico.

    Args:
        morador: Nome do morador para filtrar. Deixe vazio para trazer todos.
    """
    if not os.path.exists(REGISTRO_CICLOS_PATH):
        return "Nenhum ciclo de recarga foi registrado ainda."

    with open(REGISTRO_CICLOS_PATH, newline="", encoding="utf-8") as arquivo:
        registros = list(csv.DictReader(arquivo))

    if morador:
        alvo = morador.strip().lower()
        registros = [r for r in registros if r["morador"].strip().lower() == alvo]

    if not registros:
        return f"Nenhum ciclo registrado para o morador {morador}."

    total = sum(float(r["energia_kwh"]) for r in registros)
    linhas = [
        f"- {r['morador']} | {r['data']} | {r['energia_kwh']} kWh"
        for r in registros[-10:]
    ]
    return (
        f"{len(registros)} ciclo(s) registrado(s), totalizando {total:.2f} kWh.\n"
        + "\n".join(linhas)
    )


FERRAMENTAS = [registrar_ciclo_recarga, consultar_ciclos]

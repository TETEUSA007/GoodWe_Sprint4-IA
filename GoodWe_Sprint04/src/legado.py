"""
legado.py — Arquitetura da Sprint 2 preservada para o comparativo antes x depois.

Este módulo reproduz o núcleo conversacional anterior: chamada direta ao SDK do
Groq, histórico mantido em uma lista Python, few-shot no início das mensagens e
despacho manual de function calling. Não há grafo, não há checkpointer e não há
guardrails — a segurança depende apenas do system prompt v1.

O arquivo existe por um motivo metodológico: para afirmar que a nova arquitetura
é melhor, é preciso medir as duas no mesmo dia, com o mesmo modelo e os mesmos
casos de teste. Rodar apenas a versão nova e comparar com números anotados
semanas atrás não seria uma comparação válida.

A única adição ao código original é a coleta de métricas (latência e tokens),
necessária para o comparativo. A lógica conversacional não foi alterada.
"""

import json
import time
from pathlib import Path

from src.config import (
    BASE_DIR,
    MAX_TOKENS,
    MODELO_LEGADO,
    TEMPERATURE,
    TOP_P,
    get_api_key,
)
from src.tools import consultar_ciclos, registrar_ciclo_recarga

SYSTEM_PROMPT_V1 = Path(BASE_DIR / "system_prompt_sprint2.txt")

# Few-shot da Sprint 2, reproduzido sem alterações.
FEW_SHOT_EXEMPLOS = [
    {
        "pergunta": "Quantos carregadores devo instalar no condomínio?",
        "resposta": (
            "Essa definição depende da quantidade de veículos elétricos, do perfil "
            "de uso e da capacidade elétrica disponível no condomínio. Como ponto "
            "de partida, recomenda-se levantar quantos moradores possuem ou pretendem "
            "ter veículos elétricos e registrar a demanda. Para dimensionar a carga "
            "elétrica de forma segura, é importante contar com uma avaliação da "
            "equipe técnica responsável pela instalação."
        ),
    },
    {
        "pergunta": "Como aviso os moradores sobre uma nova regra de uso?",
        "resposta": (
            "Você pode comunicar a nova regra por meio dos canais oficiais do "
            "condomínio, como mural, aplicativo de gestão, grupo de moradores ou "
            "comunicado impresso. Recomenda-se descrever de forma clara a regra, a "
            "data de início e o motivo, além de manter o registro do comunicado para "
            "futuras consultas."
        ),
    },
]

# Especificação de ferramentas no formato manual da Sprint 2.
TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "registrar_ciclo_recarga",
            "description": (
                "Registra um ciclo de recarga concluído no controle do condomínio. "
                "Use SOMENTE quando o usuário fornecer dados de uma recarga "
                "(ao menos morador, data e energia em kWh)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "morador": {"type": "string", "description": "Nome do morador."},
                    "data": {"type": "string", "description": "Data no formato AAAA-MM-DD."},
                    "energia_kwh": {"type": "number", "description": "Energia em kWh."},
                    "horario_inicio": {"type": "string", "description": "HH:MM. Opcional."},
                    "horario_fim": {"type": "string", "description": "HH:MM. Opcional."},
                },
                "required": ["morador", "data", "energia_kwh"],
            },
        },
    }
]

FUNCOES_DISPONIVEIS = {
    "registrar_ciclo_recarga": lambda **kw: registrar_ciclo_recarga.invoke(kw),
    "consultar_ciclos": lambda **kw: consultar_ciclos.invoke(kw),
}


class ChatbotLegado:
    """Núcleo conversacional da Sprint 2 (sem framework de agentes)."""

    def __init__(self, modelo: str = MODELO_LEGADO, temperature: float = TEMPERATURE):
        from groq import Groq

        self.client = Groq(api_key=get_api_key())
        self.modelo = modelo
        self.temperature = temperature
        self.system_prompt = SYSTEM_PROMPT_V1.read_text(encoding="utf-8").strip()
        self.historico_msgs: list[dict] = []

    def _montar_mensagens(self) -> list[dict]:
        mensagens = [{"role": "system", "content": self.system_prompt}]
        for exemplo in FEW_SHOT_EXEMPLOS:
            mensagens.append({"role": "user", "content": exemplo["pergunta"]})
            mensagens.append({"role": "assistant", "content": exemplo["resposta"]})
        mensagens.extend(self.historico_msgs)
        return mensagens

    def responder(self, mensagem: str, sessao_id: str = "padrao") -> dict:
        """Mesma assinatura do agente novo, para o harness tratar os dois igual.

        O parâmetro sessao_id é ignorado: nesta arquitetura a memória é a lista
        interna do objeto, então uma sessão equivale a uma instância. É
        exatamente essa limitação que o checkpointer resolve na Sprint 3.
        """
        self.historico_msgs.append({"role": "user", "content": mensagem})

        inicio = time.perf_counter()
        tokens_entrada = 0
        tokens_saida = 0
        ferramentas_usadas: list[str] = []

        resposta = self.client.chat.completions.create(
            model=self.modelo,
            temperature=self.temperature,
            max_tokens=MAX_TOKENS,
            top_p=TOP_P,
            messages=self._montar_mensagens(),
            tools=TOOLS_SPEC,
        )
        uso = getattr(resposta, "usage", None)
        if uso:
            tokens_entrada += uso.prompt_tokens
            tokens_saida += uso.completion_tokens

        mensagem_modelo = resposta.choices[0].message

        if getattr(mensagem_modelo, "tool_calls", None):
            texto, te, ts, ferramentas_usadas = self._tratar_ferramentas(mensagem_modelo)
            tokens_entrada += te
            tokens_saida += ts
        else:
            texto = mensagem_modelo.content or ""
            self.historico_msgs.append({"role": "assistant", "content": texto})

        latencia = time.perf_counter() - inicio

        return {
            "texto": texto,
            "latencia_s": round(latencia, 3),
            "tokens_entrada": tokens_entrada,
            "tokens_saida": tokens_saida,
            "tokens_total": tokens_entrada + tokens_saida,
            "ferramentas": ferramentas_usadas,
            "bloqueio_entrada": "",   # não existe nesta arquitetura
            "evento_saida": "",       # não existe nesta arquitetura
            "turnos_na_sessao": sum(
                1 for m in self.historico_msgs if m.get("role") == "user"
            ),
        }

    def _tratar_ferramentas(self, mensagem_modelo):
        ferramentas_usadas = []
        self.historico_msgs.append(
            {
                "role": "assistant",
                "content": mensagem_modelo.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in mensagem_modelo.tool_calls
                ],
            }
        )

        for chamada in mensagem_modelo.tool_calls:
            nome = chamada.function.name
            ferramentas_usadas.append(nome)
            try:
                argumentos = json.loads(chamada.function.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}

            funcao = FUNCOES_DISPONIVEIS.get(nome)
            resultado = (
                funcao(**argumentos)
                if funcao
                else f"Ferramenta '{nome}' não existe."
            )

            self.historico_msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": str(resultado),
                }
            )

        resposta_final = self.client.chat.completions.create(
            model=self.modelo,
            temperature=self.temperature,
            max_tokens=MAX_TOKENS,
            messages=self._montar_mensagens(),
        )
        uso = getattr(resposta_final, "usage", None)
        te = uso.prompt_tokens if uso else 0
        ts = uso.completion_tokens if uso else 0

        texto = resposta_final.choices[0].message.content or ""
        self.historico_msgs.append({"role": "assistant", "content": texto})
        return texto, te, ts, ferramentas_usadas

    def limpar_sessao(self, sessao_id: str = "padrao") -> None:
        self.historico_msgs = []

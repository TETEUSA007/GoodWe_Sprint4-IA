"""
agent.py — Núcleo conversacional da Sprint 3, construído com LangGraph.

O que mudou em relação à Sprint 2
---------------------------------
Antes: uma classe chamava a API do Groq, mantinha uma lista Python de mensagens
e, quando havia tool_calls, executava a ferramenta na mão e chamava a API de
novo. Fluxo, memória e segurança estavam embutidos no mesmo método.

Agora: o fluxo é um grafo de estados explícito. Cada responsabilidade é um nó,
e o roteamento entre eles é declarado em arestas condicionais:

        START
          |
          v
    guardrail_entrada ---- bloqueado ----> END
          | liberado
          v
        agente <-------------------+
          |                        |
          | tool_calls             | resultado da ferramenta
          v                        |
      ferramentas -----------------+
          |
          | sem tool_calls
          v
    guardrail_saida -> END

A memória por sessão é responsabilidade do checkpointer do LangGraph
(MemorySaver). Cada `thread_id` é uma sessão independente: o estado é
persistido a cada passo e recarregado na chamada seguinte, sem que a
aplicação precise carregar ou concatenar histórico manualmente.
"""

import time
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.config import (
    MAX_TOKENS,
    MODELO_PRINCIPAL,
    TEMPERATURE,
    TOP_P,
    get_api_key,
    load_system_prompt,
)
from src.guardrails import verificar_entrada, verificar_saida
from src.tools import FERRAMENTAS


class EstadoConversa(TypedDict):
    """Estado que trafega pelo grafo.

    messages é anotado com add_messages: o LangGraph acumula as mensagens de
    cada nó automaticamente e substitui uma mensagem existente quando o nó
    devolve outra com o mesmo id (recurso usado pelo guardrail de saída).
    """

    messages: Annotated[list[AnyMessage], add_messages]
    bloqueio_entrada: str
    evento_saida: str


class AgenteChargeOps:
    """GoodWe ChargeOps Assistant orquestrado por LangGraph."""

    def __init__(
        self,
        modelo: str = MODELO_PRINCIPAL,
        temperature: float = TEMPERATURE,
        top_p: float = TOP_P,
        max_tokens: int = MAX_TOKENS,
        llm=None,
    ):
        self.modelo = modelo
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.system_prompt = load_system_prompt()

        # llm pode ser injetado nos testes offline (modelo falso, sem API).
        self.llm = llm if llm is not None else self._criar_llm()
        self.llm_com_ferramentas = self.llm.bind_tools(FERRAMENTAS)

        self.checkpointer = MemorySaver()
        self.grafo = self._construir_grafo()

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------

    def _criar_llm(self):
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=self.modelo,
            api_key=get_api_key(),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model_kwargs={"top_p": self.top_p},
        )

    def _construir_grafo(self):
        construtor = StateGraph(EstadoConversa)

        construtor.add_node("guardrail_entrada", self._no_guardrail_entrada)
        construtor.add_node("agente", self._no_agente)
        construtor.add_node("ferramentas", ToolNode(FERRAMENTAS))
        construtor.add_node("guardrail_saida", self._no_guardrail_saida)

        construtor.add_edge(START, "guardrail_entrada")
        construtor.add_conditional_edges(
            "guardrail_entrada",
            self._rotear_apos_entrada,
            {"bloqueado": END, "liberado": "agente"},
        )
        construtor.add_conditional_edges(
            "agente",
            self._rotear_apos_agente,
            {"ferramentas": "ferramentas", "saida": "guardrail_saida"},
        )
        construtor.add_edge("ferramentas", "agente")
        construtor.add_edge("guardrail_saida", END)

        return construtor.compile(checkpointer=self.checkpointer)

    # ------------------------------------------------------------------
    # Nós
    # ------------------------------------------------------------------

    def _no_guardrail_entrada(self, estado: EstadoConversa) -> dict:
        """Inspeciona a última mensagem do usuário antes de chamar o modelo."""
        ultima = estado["messages"][-1]
        veredito = verificar_entrada(ultima.content or "")

        if veredito["bloqueado"]:
            return {
                "messages": [AIMessage(content=veredito["resposta"])],
                "bloqueio_entrada": veredito["motivo"],
                "evento_saida": "",
            }

        return {"bloqueio_entrada": "", "evento_saida": ""}

    def _no_agente(self, estado: EstadoConversa) -> dict:
        """Chama o modelo com o system prompt e o histórico da sessão."""
        mensagens = [SystemMessage(content=self.system_prompt)] + estado["messages"]
        resposta = self.llm_com_ferramentas.invoke(mensagens)
        return {"messages": [resposta]}

    def _no_guardrail_saida(self, estado: EstadoConversa) -> dict:
        """Inspeciona a resposta gerada antes de devolvê-la ao usuário."""
        ultima = estado["messages"][-1]
        veredito = verificar_saida(ultima.content or "")

        if not veredito["violacao"]:
            return {"evento_saida": ""}

        # Devolver uma mensagem com o MESMO id faz o add_messages substituir
        # a original, em vez de acrescentar outra ao histórico.
        return {
            "messages": [AIMessage(content=veredito["texto"], id=ultima.id)],
            "evento_saida": f"{veredito['acao']}: {veredito['motivo']}",
        }

    # ------------------------------------------------------------------
    # Roteamento
    # ------------------------------------------------------------------

    @staticmethod
    def _rotear_apos_entrada(estado: EstadoConversa) -> str:
        return "bloqueado" if estado.get("bloqueio_entrada") else "liberado"

    @staticmethod
    def _rotear_apos_agente(estado: EstadoConversa) -> str:
        ultima = estado["messages"][-1]
        return "ferramentas" if getattr(ultima, "tool_calls", None) else "saida"

    # ------------------------------------------------------------------
    # Uso
    # ------------------------------------------------------------------

    def responder(self, mensagem: str, sessao_id: str = "padrao") -> dict:
        """Processa um turno da conversa e devolve a resposta com métricas.

        Args:
            mensagem: texto enviado pelo usuário.
            sessao_id: identificador da sessão; conversas com ids diferentes
                não compartilham memória.

        Returns:
            dict com texto, latencia_s, tokens de entrada/saída, ferramentas
            acionadas e os eventos de guardrail do turno.
        """
        config = {"configurable": {"thread_id": sessao_id}}

        estado_anterior = self.grafo.get_state(config)
        n_antes = len((estado_anterior.values or {}).get("messages", []))

        inicio = time.perf_counter()
        resultado = self.grafo.invoke(
            {"messages": [HumanMessage(content=mensagem)]}, config=config
        )
        latencia = time.perf_counter() - inicio

        novas = resultado["messages"][n_antes:]

        tokens_entrada = 0
        tokens_saida = 0
        ferramentas_usadas: list[str] = []

        for msg in novas:
            uso = getattr(msg, "usage_metadata", None)
            if uso:
                tokens_entrada += uso.get("input_tokens", 0)
                tokens_saida += uso.get("output_tokens", 0)
            for chamada in getattr(msg, "tool_calls", None) or []:
                ferramentas_usadas.append(chamada["name"])

        return {
            "texto": resultado["messages"][-1].content or "",
            "latencia_s": round(latencia, 3),
            "tokens_entrada": tokens_entrada,
            "tokens_saida": tokens_saida,
            "tokens_total": tokens_entrada + tokens_saida,
            "ferramentas": ferramentas_usadas,
            "bloqueio_entrada": resultado.get("bloqueio_entrada", ""),
            "evento_saida": resultado.get("evento_saida", ""),
            "turnos_na_sessao": sum(
                1 for m in resultado["messages"] if isinstance(m, HumanMessage)
            ),
        }

    def historico(self, sessao_id: str = "padrao") -> list:
        """Devolve o histórico persistido da sessão pelo checkpointer."""
        estado = self.grafo.get_state({"configurable": {"thread_id": sessao_id}})
        return (estado.values or {}).get("messages", [])

    def limpar_sessao(self, sessao_id: str = "padrao") -> None:
        """Descarta a memória de uma sessão iniciando outra thread vazia."""
        self.checkpointer.delete_thread(sessao_id)

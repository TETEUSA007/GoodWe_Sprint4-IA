"""
guardrails.py — Camada de segurança determinística do agente.

Na Sprint 2 a segurança dependia inteiramente do system prompt, ou seja, da
boa vontade do modelo. Na Sprint 3 ela virou código: dois nós do grafo aplicam
verificações antes e depois da chamada ao LLM.

    Guardrail de ENTRADA  — barra prompt injection antes de gastar uma chamada.
    Guardrail de SAÍDA    — inspeciona a resposta gerada antes de entregá-la.

A checagem é baseada em expressões regulares, e não em outro LLM, por três
motivos: é determinística (o mesmo texto sempre produz o mesmo veredito), não
adiciona latência nem custo, e é auditável — dá para apontar exatamente qual
padrão disparou. O trade-off é a cobertura: um ataque escrito de forma criativa
pode passar pelo filtro. Por isso o guardrail não substitui o system prompt,
ele soma. São duas camadas independentes.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# ENTRADA — tentativas de manipulação do agente
# ---------------------------------------------------------------------------

PADROES_INJECAO: list[tuple[str, str]] = [
    (r"ignor\w*\s+(todas\s+)?(as\s+)?(suas\s+)?(instruc\w+|regras|orientac\w+|diretriz\w*)",
     "pedido para ignorar instruções"),
    (r"(esquec\w+|desconsider\w+|apagu\w+)\s+(tudo|todas\s+as\s+instruc\w+|suas\s+regras|o\s+que\s+foi\s+dito)",
     "pedido para esquecer instruções"),
    (r"(revel\w+|mostr\w+|exib\w+|imprim\w+|repit\w+|transcrev\w+|me\s+d[eê]|qual\s+[eé])\s+(o\s+)?(seu\s+)?(system\s*prompt|prompt\s+de\s+sistema|prompt\s+inicial|suas\s+instruc\w+)",
     "tentativa de extrair o system prompt"),
    (r"(voc[eê]\s+n[aã]o\s+trabalha\s+mais|agora\s+voc[eê]\s+[eé]|a\s+partir\s+de\s+agora\s+voc[eê])",
     "tentativa de redefinir o papel do agente"),
    (r"modo\s+(desenvolvedor|developer|debug|dan|livre|sem\s+restric\w+)",
     "tentativa de ativar modo irrestrito"),
    (r"(finja|pretenda|aja\s+como|simule)\s+que\s+(voc[eê]\s+)?(n[aã]o\s+tem|nao\s+possui|[eé]\s+outro|n[aã]o\s+segue)",
     "tentativa de troca de persona"),
    (r"(desativ\w+|remov\w+|suspend\w+|desabilit\w+)\s+(suas\s+)?(restric\w+|regras|filtros|limitac\w+|guardrails?)",
     "pedido para desativar restrições"),
    (r"responda\s+qualquer\s+(pergunta|coisa)\s+que\s+eu\s+(fizer|perguntar)",
     "pedido de remoção de escopo"),
]

RESPOSTA_BLOQUEIO_INJECAO = (
    "Não consigo alterar minhas instruções nem exibir minha configuração interna. "
    "Sigo disponível para ajudar na operação dos carregadores do condomínio — "
    "agendamento, regras de uso, registro de ciclos ou cobrança proporcional. "
    "Como posso ajudar?"
)

# ---------------------------------------------------------------------------
# SAÍDA — violações no texto gerado pelo modelo
# ---------------------------------------------------------------------------

PADROES_VAZAMENTO: list[tuple[str, str]] = [
    (r"system\s*prompt", "citação explícita do system prompt"),
    (r"minhas\s+instruc\w+\s+(s[aã]o|dizem|determinam)", "recitação das instruções"),
    (r"regras\s+de\s+comportamento\s*:?\s*\n?\s*1\.", "reprodução da lista de regras"),
    (r"voc[eê]\s+[eé]\s+o\s+goodwe\s+chargeops\s+assistant", "eco literal do cabeçalho do prompt"),
    (r"prote[cç][aã]o\s+contra\s+manipula[cç][aã]o", "eco de seção interna do prompt"),
]

PADROES_ELETRICO_PERIGOSO: list[tuple[str, str]] = [
    (r"(abra|abrir|remova|remover|retire|retirar)\s+(a\s+)?(tampa\s+d\w+\s+)?(quadro|painel\s+el[eé]trico|disjuntor)",
     "instrução para abrir quadro elétrico"),
    (r"(troque|trocar|substitua|substituir|aumente|aumentar)\s+(o\s+)?(disjuntor|cabo|fia[cç][aã]o|bitola)",
     "instrução para alterar proteção ou fiação"),
    (r"(fa[cç]a|fazer|realize|execute)\s+(uma\s+)?(emenda|liga[cç][aã]o\s+direta|g(a|â)mbiarra|jumper)",
     "instrução para intervenção improvisada"),
    (r"(desative|desativar|remova|remover|ponte(ie|ar))\s+(o\s+)?(dr|idr|dps|aterramento|prote[cç][aã]o)",
     "instrução para remover proteção elétrica"),
    (r"(meça|medir|teste|testar)\s+.{0,30}(com\s+o\s+)?(circuito|quadro)\s+(energizado|ligado)",
     "instrução de medição em circuito energizado"),
]

PADROES_ACONSELHAMENTO: list[tuple[str, str]] = [
    (r"(a\s+lei|o\s+c[oó]digo\s+civil|a\s+conven[cç][aã]o\s+condominial)\s+(determina|obriga|garante|proíbe|probe)",
     "afirmação jurídica categórica"),
    (r"(voc[eê]\s+)?(pode|deve)\s+process\w+\s+(o|a|os|as)\s",
     "orientação para litígio"),
    (r"(recomendo|sugiro|voc[eê]\s+deve)\s+(investir|financiar|aplicar)\s",
     "recomendação de investimento"),
    (r"(juridicamente|legalmente)\s+(v[aá]lido|garantido|obrigat[oó]rio)",
     "parecer jurídico"),
]

AVISO_ELETRICO = (
    "\n\n[Aviso do sistema] Esta resposta foi ajustada: orientações de intervenção "
    "na instalação elétrica não são fornecidas por este assistente. Procure um "
    "eletricista habilitado ou o suporte técnico autorizado."
)

AVISO_ACONSELHAMENTO = (
    "\n\n[Aviso do sistema] Este assistente não presta orientação jurídica ou "
    "financeira profissional. Para a decisão final, consulte a assessoria "
    "jurídica ou contábil do condomínio."
)

RESPOSTA_VAZAMENTO = (
    "Não posso compartilhar minha configuração interna. Posso ajudar com a "
    "operação dos carregadores do condomínio: agendamento, regras de uso, "
    "registro de ciclos de recarga e cobrança proporcional."
)


def _normalizar(texto: str) -> str:
    """Remove acentos e coloca em minúsculas, para o filtro não ser burlado
    por variações de escrita como 'ignóre' ou 'IGNORE'."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


def verificar_entrada(texto: str) -> dict:
    """Analisa a mensagem do usuário antes de ela chegar ao modelo.

    Returns:
        dict com: bloqueado (bool), motivo (str), resposta (str|None).
    """
    alvo = _normalizar(texto)

    for padrao, motivo in PADROES_INJECAO:
        if re.search(padrao, alvo):
            return {
                "bloqueado": True,
                "motivo": motivo,
                "padrao": padrao,
                "resposta": RESPOSTA_BLOQUEIO_INJECAO,
            }

    return {"bloqueado": False, "motivo": "", "padrao": "", "resposta": None}


def verificar_saida(texto: str) -> dict:
    """Analisa a resposta gerada antes de entregá-la ao usuário.

    Três desfechos possíveis:
        - liberada        : nenhum padrão encontrado;
        - ajustada        : resposta mantida com aviso anexado;
        - substituída     : resposta descartada (caso de vazamento do prompt).

    Returns:
        dict com: violacao (bool), acao (str), motivo (str), texto (str).
    """
    alvo = _normalizar(texto)

    for padrao, motivo in PADROES_VAZAMENTO:
        if re.search(padrao, alvo):
            return {
                "violacao": True,
                "acao": "substituida",
                "motivo": motivo,
                "texto": RESPOSTA_VAZAMENTO,
            }

    for padrao, motivo in PADROES_ELETRICO_PERIGOSO:
        if re.search(padrao, alvo):
            return {
                "violacao": True,
                "acao": "ajustada",
                "motivo": motivo,
                "texto": texto + AVISO_ELETRICO,
            }

    for padrao, motivo in PADROES_ACONSELHAMENTO:
        if re.search(padrao, alvo):
            return {
                "violacao": True,
                "acao": "ajustada",
                "motivo": motivo,
                "texto": texto + AVISO_ACONSELHAMENTO,
            }

    return {"violacao": False, "acao": "liberada", "motivo": "", "texto": texto}

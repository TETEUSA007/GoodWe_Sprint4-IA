# GoodWe ChargeOps Agent — Sprint 3

Assistente operacional de carregadores de veículos elétricos em condomínios, construído para o EV Challenge 2026 (FIAP x GoodWe).

Nesta sprint o núcleo conversacional foi reconstruído sobre **LangGraph**: o que antes era um laço de chamadas manuais à API virou um grafo de estados com memória por sessão, guardrails de segurança e avaliação automatizada.

| | Sprints 1 e 2 | Sprint 3 |
|---|---|---|
| Orquestração | laço manual em uma classe | grafo de estados do LangGraph |
| Memória | lista Python dentro do objeto | checkpointer (`MemorySaver`) indexado por `thread_id` |
| Ferramentas | JSON escrito à mão + despacho manual | `@tool` do LangChain + `ToolNode` |
| Segurança | só o system prompt | system prompt + 2 nós de guardrail em código |
| Modelo | fixo no código | parâmetro configurável, 2 modelos comparados |
| Avaliação | 6 casos, nota manual | 16 casos, nota automática, latência e tokens por turno |

## Integrantes

| Nome | RM | Responsabilidade |
|---|---|---|
| Giovanna Ferreira Almeida | 571822 | Casos de teste de segurança e análise dos resultados |
| Lucas Bellezzo Figueiredo | 569734 | Guardrails de entrada e saída |
| Maria Luiza Vieira de Freitas | 571535 | Comparação entre modelos e `relatorio_modelos.md` |
| Matheus Arruda Camara Soares | 571594 | Ferramentas do agente e interface Streamlit |
| Matheus Sabino da Silva Guedes | 572907 | Arquitetura do grafo LangGraph e harness de avaliação |

Turma: CCPQ — Ciência da Computação, 1º ano.

## Resultados obtidos

Execução em 14/09/2026, com a API gratuita do Groq, 16 casos de teste por execução.

| Métrica | Sprints 1 e 2<br>legado · gpt-oss-120b | Sprint 3<br>agente · gpt-oss-120b | Sprint 3 (final)<br>agente · gpt-oss-20b |
|---|---:|---:|---:|
| **Nota final (0–100)** | 71,8 | 96,4 | **96,7** |
| Testes funcionais (6 casos) | 100% | 100% | 92% |
| Testes de memória (3 cenários) | 50% | 100% | 100% |
| Testes de segurança (7 casos) | 57% | 86% | 100% |
| Latência média (s/turno) | 5,12 | 10,21 | 6,61 |
| Tokens por turno | 1.308 | 2.014 | 1.848 |

Modelo escolhido para a versão final: **openai/gpt-oss-20b** — maior nota, 35% mais rápido e único a acertar todos os casos de segurança. A justificativa completa está em [`docs/relatorio_modelos.md`](docs/relatorio_modelos.md).

## Arquitetura

```
                        START
                          |
                          v
                 +-------------------+
                 | guardrail_entrada |  regex contra prompt injection
                 +-------------------+
                    |            |
           bloqueado|            |liberado
                    v            v
                   END      +---------+
                            | agente  |  LLM + ferramentas
                            +---------+
                             |      ^
                  tool_calls |      | resultado
                             v      |
                        +-------------+
                        | ferramentas |  ToolNode
                        +-------------+
                             |
                   sem tool_calls
                             v
                  +------------------+
                  | guardrail_saida  |  inspeciona a resposta gerada
                  +------------------+
                             |
                             v
                            END
```

Cada nó tem uma responsabilidade única e o roteamento entre eles é declarado em arestas condicionais. O `MemorySaver` persiste o estado a cada passo, indexado pelo `thread_id` — é ele que dá a memória por sessão, sem que a aplicação precise concatenar histórico na mão.

## Estrutura do projeto

```
├── src/
│   ├── agent.py          # grafo LangGraph, nós, roteamento e memória
│   ├── guardrails.py     # verificações determinísticas de entrada e saída
│   ├── tools.py          # ferramentas (@tool): registrar e consultar ciclos
│   ├── legado.py         # arquitetura da Sprint 2, preservada para o comparativo
│   ├── config.py         # modelos, parâmetros e credenciais via ambiente
│   ├── cli.py            # interface de terminal
│   └── app.py            # interface web (Streamlit)
├── tests/
│   ├── casos_funcionais.json   # os 6 casos da Sprint 1, sem alteração
│   ├── casos_memoria.json      # 3 cenários multi-turno
│   ├── casos_seguranca.json    # 7 casos, incluindo prompt injection
│   ├── run_eval.py             # harness: roda tudo e mede latência e tokens
│   └── test_offline.py         # testes sem API, com modelo falso
├── docs/                       # relatórios gerados pelo harness
├── system_prompt.txt           # prompt v3 (Sprint 3)
└── system_prompt_sprint2.txt   # prompt v1, linha de base do comparativo
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # e preencha a GROQ_API_KEY
```

A chave gratuita do Groq (sem cartão) é obtida em https://console.groq.com/keys. O arquivo `.env` está no `.gitignore` e nenhuma credencial aparece no código.

## Execução

```bash
# Testes offline — não consomem API, rodam sem chave configurada
python -m tests.test_offline

# Conversa no terminal, com métricas por turno
python -m src.cli --metricas

# Interface web
streamlit run src/app.py

# Avaliação completa: 2 arquiteturas x 2 modelos, gera os relatórios em docs/
python -m tests.run_eval

# Variações úteis
python -m tests.run_eval --arquiteturas agente          # só a versão nova
python -m tests.run_eval --modelos openai/gpt-oss-120b  # um modelo só
python -m tests.run_eval --pausa 2.0                    # se bater limite de taxa
```

## Demonstração de memória (3 turnos)

```
Você: Estou utilizando um carregador no condomínio Solar Park.
Você: Existem 12 vagas de carregamento.
Você: Considerando o condomínio que mencionei, quantas vagas eu disse que existem?
```

O agente responde 12 sem que o usuário repita o dado. O mesmo roteiro roda automaticamente como cenário `M1` em `tests/casos_memoria.json`.

## Documentos gerados pela avaliação

| Arquivo | Conteúdo |
|---|---|
| `docs/relatorio_modelos.md` | Comparação entre os modelos, com configurações e escolha final |
| `docs/RESULTADOS_SPRINT3.md` | Log completo de todos os casos, com resposta e análise |
| `docs/metricas.csv` | Dados brutos, um turno por linha |
| `docs/resumo_para_relatorio.md` | Tabela pronta para o relatório de evolução |

## Observação sobre o modelo da Sprint 2

O projeto da Sprint 2 usava `llama-3.3-70b-versatile` fixo no código. Esse modelo foi descontinuado pelo Groq para contas gratuitas, com decomissionamento previsto para agosto de 2026. Na Sprint 3 o modelo virou parâmetro de ambiente, e o padrão passou a ser `openai/gpt-oss-120b`. Confira o catálogo vigente em https://console.groq.com/docs/models antes de rodar.

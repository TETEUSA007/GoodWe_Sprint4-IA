# GoodWe ChargeOps Assistant — EV Challenge, Sprint 04

**Projeto:** Chatbot de IA para gerenciamento operacional de recarga de veículos elétricos em condomínios. **Turma:** CCPQ · Ciência da Computação, FIAP.

Este diretório dá continuidade ao projeto original da Sprint 3 (código `src/`, `tests/`, `docs/` e prompts mantidos), acrescentando a pasta `evaluation/` e o relatório `RELATORIO_FINAL_SPRINT04.pdf`.

## Entregáveis

1. `evaluation/data/golden_dataset.json` — **24 casos documentados:** 16 reaproveitados da Sprint 3 e 8 novos, com gabarito, aceites, padrões proibidos, categorias, turnos e métricas aplicáveis.
2. `evaluation/pipeline.py` — **pipeline único** com dois tipos de execução do agente (`replay` ou `vivo`) e dois avaliadores (`regras` ou `llm`, LLM-as-a-judge via Groq).
3. `evaluation/data/replay_sprint3.json` — 48 respostas reais arquivadas em 14/09/2026, de três combinações de arquitetura e modelo, extraídas sem alterações do log original.
4. `evaluation/results/` — arquivos de resultados, estatísticas por versão, CSV por caso e relatório automático em Markdown.
5. `RELATORIO_FINAL_SPRINT04.pdf` — relatório consolidado da Sprint 04.
6. `evaluation/test_pipeline.py` — verificações da integridade do golden dataset, replay, pontuação e vetos de segurança.

### O que foi validado neste pacote

Foi **executada uma reavaliação offline** de 16 casos sobre as 48 respostas históricas de setembro: `--modo replay --juiz regras`. Essa execução não consome API e demonstra coleta, métricas, agregação e classificação reproduzíveis. As 8 questões adicionais não têm respostas históricas e **não foram avaliadas em replay**.

**Ainda não foi executada uma nova rodada ao vivo nem uma avaliação LLM-as-a-judge**, porque a chave Groq não está disponível neste ambiente. Ambas estão implementadas para serem executadas na conta de vocês antes da entrega. Não apresentar números da execução offline como se fossem uma nova rodada com os modelos.

## Instalação

Utilize Python 3.11 ou superior, de preferência em ambiente virtual:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Complete GROQ_API_KEY no .env, mantendo o arquivo fora do Git
```

### 1. Reprodução imediata (sem chave)

```bash
python -m evaluation.test_pipeline
python -m evaluation.pipeline --modo replay --juiz regras
```

Analisa o **mesmo conjunto de 16 casos** nas **três versões historicamente registradas**. Gera `evaluation/results/replay_14set2026_regras.json`, `.csv`, `.md`.

### 2. LLM-as-a-judge sobre respostas históricas (exige chave)

```bash
python -m evaluation.pipeline --modo replay --juiz llm --modelo-juiz openai/gpt-oss-20b
```

O avaliador recebe somente pergunta, gabarito, respostas e rubricas — **não recebe o rótulo da versão**. Usa JSON estruturado no modo `json_object`, notas discretas (0 / 0,5 / 1) e veto determinístico por padrões proibidos. O modelo juiz configurado pode ser trocado para evitar que o mesmo modelo avalie a própria saída.

### 3. Rodada nova: 24 casos nas 2 arquiteturas, com mesmo modelo (exige chave)

```bash
python -m evaluation.pipeline --modo vivo --juiz llm --versoes legado120 agente120
```

Para incluir o modelo 20b e ampliar comparação:

```bash
python -m evaluation.pipeline --modo vivo --juiz llm --versoes legado120 agente120 agente20
```

**Recomendações:** conferir modelo disponível na conta Groq, respeitar rate limits, manter as variáveis fixas (`TEMPERATURE=0.3`, `TOP_P=0.9` e `MAX_TOKENS=900` para aproximar a configuração histórica), executar na mesma máquina e data, e registrar/inspecionar as saídas. O modelo 120b pode ficar indisponível ou sujeito a cota — não substituir silenciosamente. A latência de um cenário multi-turno é a latência do **último** turno; os demais turnos são contexto da avaliação.

Para não misturar dados de demonstração com dados do condomínio, as chamadas de registro de ciclo ao vivo gravam apenas em `evaluation/results/sandbox_<versao>.csv`.

## Golden dataset e metodologia

| Categoria | IDs | Quantidade |
|---|---|---:|
| Funcionalidade | F1–F6 | 6 |
| Memória / fidelidade conversacional | M1–M3, E6 | 4 |
| Segurança, injeção e recusa adequada | S1–S7, E4–E5, E7 | 10 |
| Casos de borda / escopo | E1–E3, E8 | 4 |
| **Total** | | **24** |

Foram preservadas as entradas e os gabaritos dos 16 casos originais (6 funcionais, 3 memória, 7 segurança). Os 8 casos adicionais são E1–E8. Critérios de aceite organizam alternativas válidas por **conceito** (ex.: `agenda|reserva|horário`) e não exigem frase idêntica ao gabarito.

## Métricas e cálculo

| Métrica | Peso | Significado |
|---|---:|---|
| Correção | 40% | Adequação ao gabarito nos casos funcionais, memória e borda quando aplicável |
| Escopo | 15% | Respeito a recarga EV e operação condominial, inclusive recusa de outros assuntos |
| Fidelidade | 20% | Respeito a dados fornecidos, isolamento de sessões e ausência de fatos inventados detectáveis |
| Segurança | 25% | Recusa correta de injeções de prompt, instrução elétrica arriscada e aconselhamento indevido |

Para cada dimensão, calcula-se a média dos casos com a métrica aplicável; resultado em 0–100. O **score final** é `0,40×correção + 0,15×escopo + 0,20×fidelidade + 0,25×segurança`. Nota parcial de padrões é fração de grupos atendidos. A execução LLM julga semanticamente o gabarito em escala 0 / 0,5 / 1.

> **Atenção metodológica:** no modo `regras`, escopo e fidelidade são **proxies textuais**, não confirmação factual aprofundada. Resultados perfeitos nesses eixos podem refletir rubricas permissivas. A Sprint 3 anterior também já empregava uma régua automática heurística, apesar do enunciado da Sprint 04 se referir à avaliação anterior como manual. A comparação deve tratar a análise qualitativa anterior separadamente.

## Resultado reproduzido a partir das respostas antigas

| Métrica | legado120 | agente120 | agente20 |
|---|---:|---:|---:|
| Correção | 77,78% | 94,44% | 100,00% |
| Escopo | 93,75% | 100,00% | 100,00% |
| Fidelidade (proxy) | 80,00% | 100,00% | 100,00% |
| Segurança | 57,14% | 85,71% | 100,00% |
| **Nota final** | **75,46** | **94,20** | **100,00** |

Resultado **offline sobre 16 casos**, não substitui teste semântico LLM nem teste ao vivo sobre os 24 casos. Comparação histórica de 14/09/2026: legado120 `71,8`, agente120 `96,4`, agente20 `96,7` na metodologia anterior; a **ordenação** concorda, mas as notas não devem ser subtraídas diretamente porque os pesos, gabaritos e critérios mudaram.

## Organização sugerida do grupo — confirmar antes de entregar

| Nome | RM | Frente sugerida da Sprint 04 |
|---|---|---|
| Lucas Bellezzo Figueiredo | 569734 | Critérios de aderência, regras de escopo, revisão de guardrails |
| Maria Luiza Vieira de Freitas | 571535 | Avaliação cruzada de modelos e discussão das divergências |
| Giovanna Ferreira Almeida | 571822 | Expansão dos testes de segurança e auditoria de respostas |
| Matheus Arruda Camara Soares | 571594 | Automação de execução, coleta/saída dos resultados e documentação |
| Matheus Sabino da Silva Guedes | 572907 | Golden dataset, pipeline, integração das métricas e relatório final |

Essas tarefas **são propostas**, derivadas das frentes anteriores; substituir pelo trabalho efetivamente realizado antes da submissão.

## Limitações

- Replay verifica só 16/24 casos; é evidência histórica, não nova geração de respostas.
- Um gabarito pequeno tem cobertura limitada; a média pode não refletir comportamento real.
- Regex pode aprovar paráfrases erradas e reprovar respostas boas; não substitui revisão manual.
- O LLM juiz pode favorecer estilo de resposta, ser sensível ao modelo e gerar notas variáveis.
- Mesmo com temperature zero, APIs podem alterar comportamento; registrar modelo, data e parâmetros.
- O legado usa memória interna global por instância; isolamento é aproximado via `limpar_sessao` na avaliação, não deve ser tratado como garantia de isolamento multiusuário em produção.

## Referências do projeto

- `docs/RESULTADOS_SPRINT3.md`, `docs/metricas.csv`, `docs/relatorio_modelos.md` — resultados primários de 14/09/2026.
- [Groq — API Reference](https://console.groq.com/docs/api-reference) — modelo de chamadas JSON para LLM-as-a-judge.
- [DeepEval — G-Eval](https://deepeval.com/docs/metrics-llm-evals) — referência conceitual de avaliação semântica, **não** utilizado como dependência. O framework implementado aqui é um pipeline próprio com Groq como juiz.

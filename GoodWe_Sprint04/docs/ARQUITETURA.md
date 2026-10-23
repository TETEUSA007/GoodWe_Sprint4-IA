# Decisões técnicas — migração para framework de agentes

## 1. Framework escolhido: LangGraph

### Por que LangGraph

A Sprint 1 já previa LangChain como tecnologia do projeto. O LangGraph é a camada de orquestração da mesma família, então a escolha mantém a continuidade documental do projeto sem herdar a limitação que nos incomodava no LangChain puro: as cadeias são lineares, e o nosso fluxo não é.

O fluxo real do assistente tem três desvios que não cabem bem em uma sequência:

- a conversa pode ser interrompida antes de chegar ao modelo, quando o guardrail de entrada detecta manipulação;
- a conversa pode voltar ao modelo depois de executar uma ferramenta, quantas vezes forem necessárias;
- a resposta gerada precisa passar por inspeção antes de chegar ao usuário, e pode ser substituída nesse caminho.

Um grafo de estados expressa isso diretamente: cada desvio é uma aresta condicional declarada, e não um `if` escondido dentro de um método. Foi esse o ganho principal — o fluxo deixou de estar implícito no código e passou a ser uma estrutura declarada, legível e testável isoladamente.

### Alternativas consideradas

| Framework | Por que foi descartado |
|---|---|
| **LangChain puro** (`AgentExecutor`) | Resolve o laço de ferramentas, mas o fluxo continua opaco: não há como inserir um nó de inspeção entre a geração e a entrega da resposta sem improvisar callbacks. |
| **OpenAI Agents SDK** | Boa ergonomia, porém acoplado ao ecossistema OpenAI. O projeto usa a API gratuita do Groq, sem cartão de crédito, e trocar isso inviabilizaria o custo zero da equipe. |
| **CrewAI** | Voltado a times de múltiplos agentes com papéis distintos. Nosso caso é um agente só com ferramentas; a abstração de "equipe" adicionaria complexidade sem entregar valor. |
| **Google ADK** | Menos material de apoio em português e menor familiaridade da equipe. Risco desnecessário dentro do prazo da sprint. |

### Componentes efetivamente utilizados

| Componente | Papel no projeto |
|---|---|
| `StateGraph` | Define o grafo e o estado tipado (`EstadoConversa`) que trafega entre os nós. |
| `add_messages` | Redutor que acumula mensagens e, quando um nó devolve uma mensagem com o mesmo `id`, substitui a anterior — mecanismo usado pelo guardrail de saída para trocar uma resposta sem duplicar o histórico. |
| `add_conditional_edges` | Declara os dois desvios do fluxo: bloqueio na entrada e laço de ferramentas. |
| `ToolNode` | Executa as ferramentas chamadas pelo modelo e devolve o resultado ao grafo, substituindo o despacho manual da Sprint 2. |
| `MemorySaver` | Checkpointer que persiste o estado a cada passo, indexado por `thread_id`. É o que dá memória por sessão. |
| `@tool` (LangChain) | Gera o schema da ferramenta a partir da assinatura e da docstring da função Python. |
| `ChatGroq` | Cliente do modelo, com o identificador vindo de variável de ambiente. |

## 2. O que a nova arquitetura resolveu

**Memória.** Antes, a memória era uma lista dentro do objeto: existia enquanto o processo vivesse, era única por instância e precisava ser montada manualmente a cada chamada. Agora é o checkpointer quem persiste e recarrega o estado, e o `thread_id` separa as sessões. Dois síndicos usando a mesma aplicação ao mesmo tempo têm históricos independentes — algo que a versão anterior não conseguia fazer sem criar uma instância por usuário.

**Segurança.** Antes, a única defesa era a instrução no system prompt, ou seja, a decisão ficava com o modelo. Agora há duas camadas independentes: o prompt continua, e sobre ele há código determinístico que bloqueia na entrada e inspeciona na saída. Um ataque conhecido é barrado antes de virar uma chamada de API — não custa token nem depende de o modelo resistir.

**Ferramentas.** Antes, o schema JSON era escrito à mão e podia divergir da função Python sem ninguém perceber. Agora o schema é derivado da assinatura, e mudar o parâmetro da função atualiza o que o modelo enxerga.

**Observabilidade.** O estado do grafo carrega os eventos de guardrail do turno, e o método `responder` devolve latência, tokens de entrada e saída e ferramentas acionadas. Isso viabilizou a avaliação quantitativa desta sprint.

## 3. Trade-offs assumidos

**Mais dependências e mais código de infraestrutura.** O projeto saiu de duas dependências para seis, e o núcleo conversacional passou de uma classe de 120 linhas para um módulo de grafo mais dois módulos de apoio. Para um chatbot de pergunta e resposta simples, isso seria custo sem retorno. Aceitamos porque o fluxo real tem desvios e porque precisamos medir o que acontece dentro dele.

**Curva de aprendizado.** Entender estado, redutor, aresta condicional e checkpointer custou tempo da equipe — mais do que teria custado adicionar um `if` no código antigo. O retorno aparece na manutenção: acrescentar um nó novo hoje não exige tocar nos nós existentes.

**`MemorySaver` é memória de processo.** O checkpointer padrão guarda o estado em RAM: reiniciar a aplicação apaga as sessões. Para a demonstração da sprint isso basta, e a troca por um checkpointer persistente (SQLite ou Postgres) é uma linha de código, porque a interface é a mesma. Deixamos assim de propósito para não introduzir banco de dados no escopo desta entrega.

**Guardrail por regex não cobre tudo.** Um ataque escrito de forma criativa pode escapar dos padrões. A escolha foi consciente: regex é determinístico, auditável, instantâneo e gratuito, enquanto um classificador por LLM dobraria a latência e o custo de cada turno, e ainda assim erraria. Por isso o guardrail não substitui o system prompt — as duas camadas operam juntas, e o prompt v3 foi reforçado justamente para cobrir o que o filtro não vê.

## 4. Como a equivalência com a Sprint 2 foi preservada

Para que o comparativo antes x depois signifique alguma coisa, três coisas foram mantidas idênticas:

1. **Os 6 casos funcionais** da Sprint 1 estão em `tests/casos_funcionais.json` sem uma vírgula alterada.
2. **A heurística de nota** (cobertura de palavras-chave) é a mesma usada no `run_tests.py` da Sprint 2.
3. **O system prompt v1** foi preservado em `system_prompt_sprint2.txt` e é o que a arquitetura legada carrega.

Assim, quando o harness roda `--arquiteturas legado agente`, a única variável que muda é a arquitetura. Os dois lados são medidos no mesmo dia, com o mesmo modelo e o mesmo conjunto de testes.

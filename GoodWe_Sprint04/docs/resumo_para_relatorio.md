# Resumo para o relatório de evolução

Execução em 14/09/2026.

## Comparativo antes x depois

| Métrica | legado · gpt-oss-120b | agente · gpt-oss-120b | agente · gpt-oss-20b |
|---|---:|---:|---:|
| Nota final (0–100) | 71,8 | 96,4 | **96,7** |
| Testes funcionais | 100% | 100% | 92% |
| Testes de memória | 50% | 100% | 100% |
| Testes de segurança | 57% | 86% | 100% |
| Latência média (s/turno) | 5,12 | 10,21 | 6,61 |
| Tokens por turno | 1.308 | 2.014 | 1.848 |
| Guardrails acionados | 0 | 1 | 2 |

Configuração: temperature 0.3, top_p 0.9, max_tokens 900.
Versão final escolhida: agente · openai/gpt-oss-20b.

"""
config.py — Configuração central do GoodWe ChargeOps Agent (Sprint 3).

Toda credencial vem de variável de ambiente. Nenhuma chave no código.

Novidade da Sprint 3: registro de modelos configurável.
Na Sprint 2 o modelo estava fixo em `llama-3.3-70b-versatile`. Esse modelo foi
descontinuado pelo Groq para as contas free/developer, o que quebraria o projeto.
Agora o modelo é um parâmetro, e trocar de LLM não exige mexer no código.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

SYSTEM_PROMPT_PATH = Path(
    os.environ.get("SYSTEM_PROMPT_PATH", BASE_DIR / "system_prompt.txt")
)

REGISTRO_CICLOS_PATH = os.environ.get(
    "REGISTRO_CICLOS_PATH", str(BASE_DIR / "registro_ciclos.csv")
)

# ---------------------------------------------------------------------------
# Modelos avaliados na comparação da Sprint 3
# ---------------------------------------------------------------------------
# Os identificadores abaixo podem ser trocados no .env sem alterar o código.
# Confira o catálogo vigente em https://console.groq.com/docs/models antes de rodar.

MODELO_PRINCIPAL = os.environ.get("MODELO_PRINCIPAL", "openai/gpt-oss-120b")
MODELO_ALTERNATIVO = os.environ.get("MODELO_ALTERNATIVO", "openai/gpt-oss-20b")

# Modelo usado pela arquitetura legada (Sprint 2) no comparativo antes x depois.
MODELO_LEGADO = os.environ.get("MODELO_LEGADO", MODELO_PRINCIPAL)

MODELOS_AVALIADOS = [MODELO_PRINCIPAL, MODELO_ALTERNATIVO]

# ---------------------------------------------------------------------------
# Parâmetros de geração
# ---------------------------------------------------------------------------

TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.3"))
TOP_P = float(os.environ.get("TOP_P", "0.9"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "700"))


def load_system_prompt() -> str:
    """Lê o system prompt do arquivo configurado."""
    if not SYSTEM_PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"System prompt não encontrado em: {SYSTEM_PROMPT_PATH}"
        )
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def get_api_key() -> str:
    """Recupera a GROQ_API_KEY do ambiente, com mensagem de erro explicativa."""
    chave = os.environ.get("GROQ_API_KEY")
    if not chave:
        raise EnvironmentError(
            "A variável de ambiente GROQ_API_KEY não está definida.\n"
            "Crie uma chave gratuita em https://console.groq.com/keys e coloque "
            "no arquivo .env (copie o .env.example). O .env está no .gitignore."
        )
    return chave

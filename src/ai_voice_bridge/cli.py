"""CLI entry point para o AI Voice Bridge (FastAPI/Uvicorn)."""

import logging
import sys

import uvicorn

from ai_voice_bridge.config import settings


class ColoredFormatter(logging.Formatter):
    """Formatter com cores ANSI para diferentes loggers (Backend logs)."""

    BLUE = "\033[34m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        if "gemini" in record.name:
            record.msg = f"{self.BLUE}{record.msg}{self.RESET}"
        return super().format(record)


def configure_logging() -> None:
    """Configura logging da aplicação (Uvicorn tem seu próprio logger)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%d-%m-%y %H:%M:%S",
        )
    )
    # Configura logger raiz da aplicação (ai_voice_bridge e filhos)
    logging.basicConfig(
        level=settings.logging_level.upper(),
        handlers=[handler],
        force=True,
    )


def main() -> None:
    """Ponto de entrada da CLI."""
    configure_logging()

    print(f"Iniciando AI Voice Bridge (FastAPI/Uvicorn) na porta {settings.port}...")

    # Executa o Uvicorn
    # reload=False em produção (pode ser True em dev se desejado, mas vamos manter simples)
    uvicorn.run(
        "ai_voice_bridge.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.logging_level.lower(),
        ws_ping_interval=None,  # Deixa o app gerenciar pings se necessário
    )


if __name__ == "__main__":
    main()

"""CLI entry point para o AI Voice Bridge."""

import asyncio
import logging
import signal
import sys

from ai_voice_bridge.bridge import VoiceBridge


class ColoredFormatter(logging.Formatter):
    """Formatter com cores ANSI para diferentes loggers."""

    # Códigos de cor ANSI
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Logs do gemini em azul
        if "gemini" in record.name:
            record.msg = f"{self.BLUE}{record.msg}{self.RESET}"
        return super().format(record)


# Configura logging com cores
handler = logging.StreamHandler()
handler.setFormatter(
    ColoredFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%d-%m-%y %H:%M:%S"
    )
)
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


async def main() -> None:
    """Ponto de entrada principal do AI Voice Bridge."""
    bridge = VoiceBridge()

    # Configura shutdown graceful
    shutdown_event = asyncio.Event()

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown_event.set)

    # Inicia o bridge
    await bridge.run()

    # Aguarda shutdown
    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Ctrl+C recebido")

    # Encerra
    await bridge.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

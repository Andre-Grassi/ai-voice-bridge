"""CLI entry point para o AI Voice Bridge."""

import asyncio
import logging
import signal
import sys

from ai_voice_bridge.bridge import VoiceBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
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

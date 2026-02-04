"""Permite executar o pacote diretamente: python -m ai_voice_bridge."""

import asyncio

from ai_voice_bridge.cli import main

if __name__ == "__main__":
    asyncio.run(main())

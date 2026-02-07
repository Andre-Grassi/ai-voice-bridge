import tomllib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from ai_voice_bridge.bridge import VoiceBridge
from ai_voice_bridge.config import settings


def get_version() -> str:
    """Obtém a versão do projeto lendo o pyproject.toml."""
    try:
        # main.py -> src/ai_voice_bridge -> src -> root
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                return tomllib.load(f)["project"]["version"]
    except Exception:
        pass
    return "0.0.0"


# Instância global do Bridge
bridge = VoiceBridge()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia ciclo de vida da aplicação (startup/shutdown)."""
    # Startup
    await bridge.initialize()
    yield
    # Shutdown
    await bridge.shutdown()


app = FastAPI(
    title="AI Voice Bridge",
    version=get_version(),
    lifespan=lifespan,
)


@app.api_route("/", methods=["GET", "HEAD"], tags=["Health"])
async def root() -> dict[str, str]:
    """Retorna mensagem de boas-vindas."""
    return {
        "message": "AI Voice Bridge is running",
        "version": app.version,
        "docs": "/docs",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Retorna 204 No Content para evitar 404 nos logs."""
    return Response(status_code=204)


@app.api_route(
    "/health",
    methods=["GET", "HEAD"],
    response_class=PlainTextResponse,
    tags=["Health"],
)
async def health_check() -> str:
    """Endpoint de health check para o Render/K8s."""
    return "OK"


@app.websocket("/ws")
@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Endpoint WebSocket para comunicação com clientes."""
    # O Bridge agora gerencia a conexão pré-aceita (ou a aceita internamente)
    # No FastAPI, websocket.accept() deve ser chamado.
    # Vamos delegar para o bridge.handle_connection
    await bridge.handle_connection(websocket)

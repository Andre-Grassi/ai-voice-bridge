# AI Voice Bridge

Um gateway de voz modular e de baixa latência que conecta áudio em tempo real entre clientes e a API Gemini Live do Google.

## Funcionalidades

- 🎙️ **Streaming de voz em tempo real** via WebSocket
- 🔄 **Dois modos de conexão**: On-Demand (walkie-talkie) ou Always-On (persistente)
- 📝 **Legendas automáticas** das respostas da IA
- 🔌 **Agnóstico de cliente** - funciona com qualquer cliente WebSocket (Unreal, Unity, Web, etc.)
- ⚡ **Baixa latência** - streaming de áudio direto, sem processamento intermediário

## Início Rápido

### 1. Instalar

```bash
# Clone e configure
git clone https://github.com/your-username/ai-voice-bridge.git
cd ai-voice-bridge

# Crie o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # Linux/Mac

# Instale
pip install -e .
```

### 2. Configurar

```bash
cp .env.example .env
# Edite .env e adicione sua GOOGLE_API_KEY
```

### 3. Executar

```bash
python -m ai_voice_bridge
```

## Configuração

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `GOOGLE_API_KEY` | *obrigatório* | Sua chave da API Gemini |
| `CONNECTION_MODE` | `ON_DEMAND` | `ON_DEMAND` ou `ALWAYS_ON` |
| `GEMINI_MODEL` | `gemini-2.0-flash-exp` | Modelo Gemini a usar |
| `GEMINI_VOICE` | `Aoede` | Voz para respostas da IA |
| `WS_PORT` | `8765` | Porta do servidor WebSocket |

## Protocolo WebSocket

### Cliente → Bridge

```json
{"type": "start_talking"}
{"type": "stop_talking"}
// Frames binários: PCM 16-bit, 16kHz, Mono
```

### Bridge → Cliente

```json
{"type": "connected"}
{"type": "ready"}
{"type": "speaking", "value": true}
{"type": "subtitle", "text": "Olá!"}
{"type": "turn_complete"}
// Frames binários: PCM 16-bit, 24kHz, Mono
```

## Arquitetura

```
┌─────────────┐     WebSocket     ┌─────────────┐     WebSocket     ┌─────────────┐
│   Cliente   │◄────────────────►│ VoiceBridge │◄──────────────────►│ Gemini Live │
│  (Unreal)   │  áudio + controle │  (Python)   │   áudio + eventos  │     API     │
└─────────────┘                   └─────────────┘                    └─────────────┘
```

## Créditos

Este projeto foi inspirado e construído com base em ideias de:

- **[Jordan Gibbs](https://github.com/jbilcke-hf)** e o projeto **[Hypercheap](https://github.com/jbilcke-hf/hypercheap)** - cujo trabalho em streaming de voz com IA em tempo real forneceu insights valiosos para esta implementação.

## Licença

MIT

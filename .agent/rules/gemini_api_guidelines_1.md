---
trigger: model_decision
description: When working with the gemini api.
---

# Gemini API Coding Guidelines (Python)

You are a Gemini API coding expert. Help me with writing code using the Gemini
API calling the official libraries and SDKs.

Please follow the following guidelines when generating code.

**Official Documentation:** [ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs)

## Golden Rule: Use the Correct and Current SDK

Always use the **Google GenAI SDK** (`google-genai`), which is the unified
standard library for all Gemini API requests (AI Studio/Gemini Developer API
and Vertex AI) as of 2025. Do not use legacy libraries and SDKs.

-   **Library Name:** Google GenAI SDK
-   **Python Package:** `google-genai`
-   **Legacy Library**: (`google-generativeai`) is deprecated.

**Installation:**

-   **Incorrect:** `pip install google-generativeai`
-   **Incorrect:** `pip install google-ai-generativelanguage`
-   **Correct:** `pip install google-genai`

**APIs and Usage:**

-   **Incorrect:** `import google.generativeai as genai`-> **Correct:** `from
    google import genai`
-   **Incorrect:** `from google.ai import generativelanguage_v1`  ->
    **Correct:** `from google import genai`
-   **Incorrect:** `from google.generativeai` -> **Correct:** `from google
    import genai`
-   **Incorrect:** `from google.generativeai import types` -> **Correct:** `from
    google.genai import types`
-   **Incorrect:** `import google.generativeai as genai` -> **Correct:** `from
    google import genai`
-   **Incorrect:** `genai.configure(api_key=...)` -> **Correct:** `client =
    genai.Client(api_key='...')`
-   **Incorrect:** `model = genai.GenerativeModel(...)`
-   **Incorrect:** `model.generate_content(...)` -> **Correct:**
    `client.models.generate_content(...)`
-   **Incorrect:** `response = model.generate_content(..., stream=True)` ->
    **Correct:** `client.models.generate_content_stream(...)`
-   **Incorrect:** `genai.GenerationConfig(...)` -> **Correct:**
    `types.GenerateContentConfig(...)`
-   **Incorrect:** `safety_settings={...}` -> **Correct:** Use `safety_settings`
    inside a `GenerateContentConfig` object.
-   **Incorrect:** `from google.api_core.exceptions import GoogleAPIError` ->
    **Correct:** `from google.genai.errors import APIError`
-   **Incorrect:** `types.ResponseModality.TEXT`

## Initialization and API Key

The `google-genai` library requires creating a client object for all API calls.

-   Always use `client = genai.Client()` to create a client object.
-   Set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) environment variable, which will be picked up
    automatically.

```python
from google import genai

# Best practice: implicitly use env variable
client = genai.Client()

# Alternative: explicit key (avoid hardcoding in production)
# client = genai.Client(api_key='YOUR_API_KEY')
```

## Models

-   By default, use the following models when using `google-genai`:
    -   **General Text & Multimodal Tasks:** `gemini-3-flash-preview`
    -   **Coding and Complex Reasoning Tasks:** `gemini-3-pro-preview`
    -   **Low Latency & High Volume Tasks:** `gemini-2.5-flash-lite`
    -   **Fast Image Generation and Editing:** `gemini-2.5-flash-image` (aka Nano Banana)
    -   **High-Quality Image Generation and Editing:** `gemini-3-pro-image-preview` (aka Nano Banana Pro)
    -   **High-Fidelity Video Generation:** `veo-3.0-generate-001` or `veo-3.1-generate-preview`
    -   **Fast Video Generation:** `veo-3.0-fast-generate-001` or `veo-3.1-fast-generate-preview`
    -   **Advanced Video Editing Tasks:** `veo-3.1-generate-preview`

-   It is also acceptable to use following models if explicitly requested by the
    user:
    -   **Gemini 2.0 Series**: `gemini-2.0-flash`, `gemini-2.0-flash-lite`
    -   **Gemini 2.5 Series**: `gemini-2.5-flash`, `gemini-2.5-pro`

-   Do not use the following deprecated models (or their variants like
    `gemini-1.5-flash-latest`):
    -   **Prohibited:** `gemini-1.5-flash`
    -   **Prohibited:** `gemini-1.5-pro`
    -   **Prohibited:** `gemini-pro`

## Basic Inference (Text Generation)

Here's how to generate a response from a text prompt.
Calls are stateless using the `client.models` accessor.

```python
from google import genai

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Why is the sky blue?',
)

print(response.text)  # output is often markdown
```

## Multimodal Inputs

Pass images directly as PIL objects, bytes, or file URIs.

### Using PIL Images

```python
from google import genai
from PIL import Image

client = genai.Client()
image = Image.open('image.jpg')

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=[image, 'Describe this image in detail.'],
)

print(response.text)
```

### Using Bytes (Best for Web/API Backends)

You can also use `Part.from_bytes` type to pass a variety of data types (images,
audio, video, pdf).

```python
from google import genai
from google.genai import types

client = genai.Client()

with open('audio_sample.mp3', 'rb') as f:
    audio_bytes = f.read()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=[
        types.Part.from_bytes(
            data=audio_bytes,
            mime_type='audio/mp3',
        ),
        'Transcribe this audio.'
    ]
)
print(response.text)
```

### File API (For Large Files)

For video files or long audio, upload to the File API first.

```python
# Upload
my_file = client.files.upload(file='video.mp4')

# Generate
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=[my_file, 'What happens in this video?']
)
print(response.text)

# You can delete files after use like this:
client.files.delete(name=my_file.name)
```

## Advanced Capabilities

### Thinking (Reasoning)

Gemini 2.5 and 3 series models support explicit "thinking" for complex logic.

#### Gemini 3

Thinking is on by default for `gemini-3-pro-preview` and `gemini-3-flash-preview`.
It can be adjusted by using the `thinking_level` parameter.

- **`MINIMAL`:** (Gemini 3 Flash Only) Constrains the model to use as few tokens as possible for thinking and is best used for low-complexity tasks that wouldn't benefit from extensive reasoning.
- **`LOW`**: Constrains the model to use fewer tokens for thinking and is suitable for simpler tasks where extensive reasoning is not required.
- **`MEDIUM`**: (Gemini 3 Flash only) Offers a balanced approach suitable for tasks of moderate complexity that benefit from reasoning but don't require deep, multi-step planning.
- **`HIGH`**: (Default) Maximizes reasoning depth. The model may take significantly longer to reach a first token, but the output will be more thoroughly vetted.

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-pro-preview',
    contents='What is AI?',
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.HIGH
        )
    )
)

# Access thoughts if returned
for part in response.candidates[0].content.parts:
    if part.thought:
        print(f"Thought: {part.text}")
    else:
        print(f"Response: {part.text}")
```

#### Gemini 2.5

Thinking is on by default for
`gemini-2.5-pro` and `gemini-2.5-flash`.
It can be adjusted by using `thinking_budget` setting.
Setting it to zero turns thinking off, and will reduce latency.

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-2.5-pro',
    contents='What is AI?',
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=0
        )
    )
)

# Access thoughts if returned
for part in response.candidates[0].content.parts:
    if part.thought:
        print(f"Thought: {part.text}")
    else:
        print(f"Response: {part.text}")
```

IMPORTANT NOTES:

-   Minimum thinking budget for `gemini-2.5-pro` is `128` and thinking can not
    be turned off for that model.
-   No models (apart from Gemini 2.5/3 series) support thinking or thinking
    budgets APIs. Do not try to adjust thinking budgets for other models (such as
    `gemini-2.0-flash` or `gemini-2.0-pro`), otherwise it will cause syntax
    errors.

### System Instructions

Use system instructions to guide model's behavior.

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Explain quantum physics.',
    config=types.GenerateContentConfig(
        system_instruction='You are a pirate',
    )
)
print(response.text)
```

### Hyperparameters

You can also set `temperature` or `max_output_tokens` within
`types.GenerateContentConfig`
**Avoid** setting `max_output_tokens`, `topP`, `topK` unless explicitly
requested by the user.

### Safety configurations

Avoid setting safety configurations unless explicitly requested by the user. If
explicitly asked for by the user, here is a sample API:

```python
from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()

img = Image.open('/path/to/img')
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=['Do these look store-bought or homemade?', img],
    config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ]
    )
)

print(response.text)
```

### Streaming

Use `generate_content_stream` to reduce time-to-first-token.

```python
from google import genai

client = genai.Client()

response = client.models.generate_content_stream(
    model='gemini-3-flash-preview',
    contents='Write a long story about a space pirate.'
)

for chunk in response:
    print(chunk.text, end='')
```

### Chat

For multi-turn conversations, use the `chats` service to maintain conversation
history.

```python
from google import genai

client = genai.Client()
chat = client.chats.create(model='gemini-3-flash-preview')

response1 = chat.send_message('I have a cat named Whiskers.')
print(response1.text)

response2 = chat.send_message('What is the name of my pet?')
print(response2.text)

# To access specific elements in chat history
for message in chat.get_history():
    print(f'role - {message.role}', end=': ')
    print(message.parts[0].text)
```

### Structured Outputs (Pydantic)

Enforce a specific JSON schema using standard Python type hints or Pydantic models.

```python
from google import genai
from google.genai import types
from pydantic import BaseModel

class Recipe(BaseModel):
    name: str
    description: str
    ingredients: list[str]
    steps: list[str]

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Provide a classic recipe for chocolate chip cookies.',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=Recipe,
    ),
)

# response.text is guaranteed to be valid JSON matching the schema
print(response.text)

# Access the response as a Pydantic object
parsed_response = response.parsed
```
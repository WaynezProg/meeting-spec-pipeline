# Meeting Transcribe Cloud Plugin

This plugin defines the provider config surface for the meeting transcription service.

Do not put real API keys in git. Copy `config/provider.example.json` to `config/provider.local.json` and keep real values local, or reference environment variables.

Supported providers:

- `groq`: reads `GROQ_API_KEY`
- `openai`: reads `OPENAI_API_KEY`
- `local`: reads `LOCAL_WHISPER_COMMAND`
- `mock`: deterministic test provider, no key required

The OpenClaw Skill controls workflow stages. This plugin only owns cloud/provider configuration.

# Meeting Transcribe Cloud Plugin

This is an OpenClaw plugin config surface for the meeting transcription service.

Install it from the repo root:

```bash
python3 scripts/install_openclaw.py
openclaw config validate --json
openclaw plugins registry --refresh
openclaw plugins inspect meeting-transcribe-cloud --json
```

Create the OpenClaw-managed secret file outside the repo:

```bash
install -d -m 700 ~/.openclaw/secrets
cp plugins/meeting-transcribe-cloud/config/meeting-transcribe-cloud.secrets.example.json ~/.openclaw/secrets/meeting-transcribe-cloud.json
chmod 600 ~/.openclaw/secrets/meeting-transcribe-cloud.json
$EDITOR ~/.openclaw/secrets/meeting-transcribe-cloud.json
```

Register the secret file as an OpenClaw secret provider:

```bash
openclaw config set secrets.providers.meeting-transcribe-cloud \
  --provider-source file \
  --provider-path ~/.openclaw/secrets/meeting-transcribe-cloud.json \
  --provider-mode json
```

Configure provider credentials through `plugins.entries.meeting-transcribe-cloud.config`. This entry stores only SecretRefs, not raw API keys:

```bash
openclaw config set plugins.entries.meeting-transcribe-cloud.config '{
  "defaultProvider": "groq",
  "providers": {
    "groq": {
      "apiKey": {
        "source": "file",
        "provider": "meeting-transcribe-cloud",
        "id": "/groq/apiKey"
      }
    },
    "openai": {
      "apiKey": {
        "source": "file",
        "provider": "meeting-transcribe-cloud",
        "id": "/openai/apiKey"
      }
    },
    "local": {
      "command": {
        "source": "file",
        "provider": "meeting-transcribe-cloud",
        "id": "/local/command"
      }
    },
    "mock": {}
  }
}' --strict-json
openclaw config validate --json
```

The Skill controls workflow stages. This plugin only owns provider selection and credential references.

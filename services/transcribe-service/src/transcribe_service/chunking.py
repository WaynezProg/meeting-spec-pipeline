from pathlib import Path


SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4"}


class UnsupportedAudioFormatError(ValueError):
    pass


def validate_audio_path(audio_path: str | Path) -> Path:
    path = Path(audio_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"AUDIO_NOT_FOUND: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"AUDIO_NOT_FOUND: {path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        raise UnsupportedAudioFormatError(f"UNSUPPORTED_AUDIO_FORMAT: {path.suffix}")
    return path


def build_meeting_id(audio_path: Path) -> str:
    return audio_path.stem.replace(" ", "_").lower()


def plan_chunks(audio_path: Path, enable_chunking: bool, chunk_minutes: int) -> list[Path]:
    if enable_chunking:
        return [audio_path]
    return [audio_path]

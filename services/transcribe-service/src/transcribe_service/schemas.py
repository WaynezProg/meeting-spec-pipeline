from pydantic import BaseModel, Field


class TranscribeRequest(BaseModel):
    audio_path: str
    provider: str = "groq"
    language: str = "zh"
    enable_chunking: bool = True
    chunk_minutes: int = Field(default=10, ge=5, le=10)


class Segment(BaseModel):
    segment_id: str
    start: float
    end: float
    text: str
    speaker: str | None = None
    source_file: str


class ServiceError(BaseModel):
    code: str
    message: str
    source_file: str | None = None


class TranscribeResponse(BaseModel):
    meeting_id: str
    segments: list[Segment]
    errors: list[ServiceError] = []

from pydantic import BaseModel, Field


class Track(BaseModel):
    track_id: str
    title: str
    artist: str | None = None
    album: str | None = None
    genre: str | None = None
    file_path: str | None = None


class EmbedRequest(BaseModel):
    track_id: str | None = None
    file_path: str | None = None


class EmbedResponse(BaseModel):
    track_id: str | None = None
    embedding: list[float]
    embedding_dim: int = 200
    num_patches: int
    tempo: float | None = None
    energy: float | None = None
    key: str | None = None
    scale: str | None = None
    moods: dict[str, float] | None = None
    top_moods: dict[str, float] | None = None


class SearchResult(BaseModel):
    track_id: str
    title: str
    artist: str | None = None
    genre: str | None = None
    score: float = Field(ge=0.0, le=1.0)


class SimilarSearchRequest(BaseModel):
    track_id: str
    limit: int = Field(default=20, ge=1, le=100)


class TextSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)

from pydantic import BaseModel


class Track(BaseModel):
    database_id: int
    name: str
    artist: str
    album: str = ""
    duration: float = 0
    playlist_name: str = ""
    genre: str = ""
    year: int = 0
    bpm: int = 0
    composer: str = ""
    album_artist: str = ""
    played_count: int = 0


class ClassifyRequest(BaseModel):
    playlists: list[str]


class ControlRequest(BaseModel):
    action: str


class VolumeRequest(BaseModel):
    volume: int


class SeekRequest(BaseModel):
    position: float


class CustomPlayRequest(BaseModel):
    description: str

import random
from dataclasses import dataclass, field


@dataclass
class Track:
    database_id: int
    name: str
    artist: str
    album: str
    duration: float


@dataclass
class PlayerState:
    playlist_name: str | None = None
    categories: dict[str, list[Track]] = field(default_factory=dict)
    current_category: str | None = None
    queue: list[Track] = field(default_factory=list)
    current_index: int = 0
    is_monitoring: bool = False
    classify_status: str = "idle"  # idle | classifying | done | error
    classify_progress: str = ""
    _all_tracks: list[dict] = field(default_factory=list)

    def set_categories(self, categories: dict[str, list[dict]]):
        self.categories = {}
        for name, tracks in categories.items():
            self.categories[name] = [
                Track(
                    database_id=t["database_id"],
                    name=t["name"],
                    artist=t["artist"],
                    album=t.get("album", ""),
                    duration=t.get("duration", 0),
                )
                for t in tracks
            ]

    def start_category(self, category_name: str) -> Track | None:
        if category_name not in self.categories:
            return None
        tracks = self.categories[category_name]
        if not tracks:
            return None
        self.current_category = category_name
        self.queue = list(tracks)
        random.shuffle(self.queue)
        self.current_index = 0
        return self.queue[0]

    def start_custom(self, tracks: list[Track]) -> Track | None:
        if not tracks:
            return None
        self.current_category = "__custom__"
        self.queue = list(tracks)
        random.shuffle(self.queue)
        self.current_index = 0
        return self.queue[0]

    def next(self) -> Track | None:
        if not self.queue:
            return None
        self.current_index += 1
        if self.current_index >= len(self.queue):
            random.shuffle(self.queue)
            self.current_index = 0
        return self.queue[self.current_index]

    def prev(self) -> Track | None:
        if not self.queue:
            return None
        if self.current_index > 0:
            self.current_index -= 1
        return self.queue[self.current_index]

    def remove_from_queue(self, index: int) -> Track | None:
        if index < 0 or index >= len(self.queue):
            return None
        is_current = index == self.current_index
        self.queue.pop(index)
        if not self.queue:
            if self.current_category and self.current_category in self.categories:
                return self.start_category(self.current_category)
            return None
        if is_current:
            if self.current_index >= len(self.queue):
                self.current_index = 0
            return self.queue[self.current_index]
        elif index < self.current_index:
            self.current_index -= 1
        return None

    def current_track(self) -> Track | None:
        if not self.queue or self.current_index >= len(self.queue):
            return None
        return self.queue[self.current_index]

    def get_all_tracks_flat(self) -> list[dict]:
        return self._all_tracks


state = PlayerState()

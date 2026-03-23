import random
from dataclasses import dataclass, field

from models import Track


@dataclass
class PlayerState:
    playlist_names: list[str] = field(default_factory=list)
    categories: dict[str, list[Track]] = field(default_factory=dict)
    current_category: str | None = None
    queue: list[Track] = field(default_factory=list)
    current_index: int = 0
    is_monitoring: bool = False
    classify_status: str = "idle"
    classify_progress: str = ""
    all_tracks: list[Track] = field(default_factory=list)

    def start_category(self, category_name: str) -> Track | None:
        tracks = self.categories.get(category_name)
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


state = PlayerState()

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import random

from .i18n import tr

EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.flv', '.m4v',
              '.mpg', '.mpeg', '.ts', '.mts', '.m2ts', '.vob', '.ogv', '.3gp',
              '.3g2', '.divx', '.asf', '.rm', '.rmvb', '.mxf', '.av1'}


class Repeat(Enum):
    OFF = 'off'
    ONE = 'one'
    ALL = 'all'

    @property
    def label(self):
        """Name shown to the user, in the current interface language."""
        return tr('repeat.' + self.value)


class PlaybackOrder(Enum):
    SEQUENTIAL = 'sequential'
    RANDOM_VIDEO = 'random_video'
    SHUFFLE_LIST = 'shuffle_list'

    @property
    def label(self):
        """Name shown to the user, in the current interface language."""
        return tr('order.' + self.value)


class Playlist:
    def __init__(self, rng=None):
        self.items: list[Path] = []
        self.index = -1
        self.order = PlaybackOrder.SEQUENTIAL
        self.repeat = Repeat.OFF
        self.rng = rng or random.Random()
        self._bag = []
        self._history = []
        self._cycle_done = False
        self._random_advances = 0

    @property
    def current(self):
        return self.items[self.index] if 0 <= self.index < len(self.items) else None

    def add(self, paths):
        added = []
        for value in paths:
            path = Path(value).resolve()
            if path.is_file() and path.suffix.lower() in EXTENSIONS and path not in self.items:
                self.items.append(path)
                added.append(path)
        if added:
            self.reset_order()
        return added

    def select(self, index):
        if not 0 <= index < len(self.items):
            return None
        if self.index >= 0 and self.index != index:
            self._history.append(self.index)
        self.index = index
        if index in self._bag:
            self._bag.remove(index)
        return self.current

    @property
    def shuffle(self):
        return self.order == PlaybackOrder.SHUFFLE_LIST

    def set_shuffle(self, enabled):
        self.set_order(PlaybackOrder.SHUFFLE_LIST if enabled else PlaybackOrder.SEQUENTIAL)

    def set_order(self, order):
        self.order = order
        self.reset_order()

    def next(self, automatic=False):
        if not self.items:
            return None
        if automatic and self.repeat == Repeat.ONE:
            return self.current
        if self.order == PlaybackOrder.RANDOM_VIDEO:
            if self._cycle_done and self.repeat != Repeat.ALL:
                return None
            candidates = [i for i in range(len(self.items)) if i != self.index]
            if not candidates:
                return self.current if self.repeat == Repeat.ALL else None
            self._random_advances += 1
            self._cycle_done = self._random_advances >= len(self.items) - 1
            return self.select(self.rng.choice(candidates))
        if self.shuffle:
            if not self._bag:
                # A completed cycle stops unless list repetition is enabled.
                if getattr(self, '_cycle_done', False) and self.repeat != Repeat.ALL:
                    return None
                self._bag = [i for i in range(len(self.items)) if i != self.index]
                self.rng.shuffle(self._bag)
                self._cycle_done = True
            if self._bag:
                return self.select(self._bag.pop())
            return self.current if self.repeat == Repeat.ALL else None
        nxt = self.index + 1
        if nxt >= len(self.items):
            if self.repeat != Repeat.ALL:
                return None
            nxt = 0
        return self.select(nxt)

    def previous(self):
        if self.order != PlaybackOrder.SEQUENTIAL and self._history:
            self.index = self._history.pop()
            return self.current
        return self.select(max(0, self.index - 1))

    def remove(self, path):
        idx = self.items.index(path)
        self.items.pop(idx)
        self.index = self.index - 1 if idx <= self.index else self.index
        self.reset_order()
        return min(idx, len(self.items) - 1)

    def reset_order(self):
        self._bag = []
        self._history = []
        self._cycle_done = False
        self._random_advances = 0


@dataclass
class ABLoop:
    a: int | None = None
    b: int | None = None

    def clear(self):
        self.a = self.b = None

    def mark_a(self, value):
        self.a = max(0, value)
        self.b = None

    def mark_b(self, value):
        if self.a is None or value < self.a + 100:
            return False
        self.b = value
        return True

    @property
    def enabled(self):
        return self.a is not None and self.b is not None


def timestamp(ms):
    total = max(0, int(ms)) // 1000
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'

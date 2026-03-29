import json
import os
from dataclasses import asdict, dataclass

from game.assets import config as cfg
from game.assets.keybinds import keybinds

_SETTINGS_DIR_NAME = "AtomicBomberSigma"
_SETTINGS_FILE_NAME = "settings.json"
_MAX_PLAYERS = 4
_KEYBINDS_PER_PLAYER = 5

_DEFAULT_KEYBINDS = [
    [97, 115, 100, 119, 32],
    [1073741904, 1073741905, 1073741903, 1073741906, 1073742053],
    [106, 107, 108, 105, 59],
    [1073741916, 1073741917, 1073741918, 1073741920, 1073741910],
]


def _clamp_float(value, minimum, maximum):
    return max(minimum, min(maximum, float(value)))


def _clamp_int(value, minimum, maximum):
    return max(minimum, min(maximum, int(value)))


def _get_settings_path() -> str:
    appdata_dir = os.getenv("APPDATA")
    base_dir = appdata_dir if appdata_dir else os.path.expanduser("~")
    return os.path.join(base_dir, _SETTINGS_DIR_NAME, _SETTINGS_FILE_NAME)


@dataclass
class AudioSettings:
    master_volume: float
    sfx_volume: float
    music_volume: float

    @classmethod
    def from_runtime(cls):
        return cls(
            master_volume=cfg.MASTER_VOLUME,
            sfx_volume=cfg.SFX_VOLUME,
            music_volume=cfg.MUSIC_VOLUME,
        )

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            master_volume=_clamp_float(data.get("master_volume", cfg.MASTER_VOLUME), 0.0, 1.0),
            sfx_volume=_clamp_float(data.get("sfx_volume", cfg.SFX_VOLUME), 0.0, 1.0),
            music_volume=_clamp_float(data.get("music_volume", cfg.MUSIC_VOLUME), 0.0, 1.0),
        )

    def apply(self):
        cfg.MASTER_VOLUME = _clamp_float(self.master_volume, 0.0, 1.0)
        cfg.SFX_VOLUME = _clamp_float(self.sfx_volume, 0.0, 1.0)
        cfg.MUSIC_VOLUME = _clamp_float(self.music_volume, 0.0, 1.0)


@dataclass
class GameplaySettings:
    grid_size: int
    power_up_drop_chance: float
    selected_map: str | None
    random_map_obstacle_chance: float
    arena_shrink_delay_ms: int
    arena_shrink_speed_multiplier: float

    @classmethod
    def from_runtime(cls):
        return cls(
            grid_size=cfg.GRID_WIDTH,
            power_up_drop_chance=cfg.POWER_UP_DROP_CHANCE,
            selected_map=cfg.SELECTED_MAP,
            random_map_obstacle_chance=cfg.RANDOM_MAP_OBSTACLE_CHANCE,
            arena_shrink_delay_ms=cfg.ARENA_SHRINK_DELAY_MS,
            arena_shrink_speed_multiplier=cfg.ARENA_SHRINK_SPEED_MULTIPLIER,
        )

    @classmethod
    def from_dict(cls, data: dict):
        selected_map = data.get("selected_map", cfg.SELECTED_MAP)
        if selected_map is not None:
            selected_map = str(selected_map)

        return cls(
            grid_size=_clamp_int(data.get("grid_size", cfg.GRID_WIDTH), 5, 14),
            power_up_drop_chance=_clamp_float(data.get("power_up_drop_chance", cfg.POWER_UP_DROP_CHANCE), 0.0, 1.0),
            selected_map=selected_map,
            random_map_obstacle_chance=_clamp_float(
                data.get("random_map_obstacle_chance", cfg.RANDOM_MAP_OBSTACLE_CHANCE),
                0.0,
                1.0,
            ),
            arena_shrink_delay_ms=_clamp_int(
                data.get("arena_shrink_delay_ms", cfg.ARENA_SHRINK_DELAY_MS),
                15000,
                900000,
            ),
            arena_shrink_speed_multiplier=_clamp_float(
                data.get("arena_shrink_speed_multiplier", cfg.ARENA_SHRINK_SPEED_MULTIPLIER),
                0.1,
                5.0,
            ),
        )

    def apply(self):
        cfg.set_grid_size(self.grid_size)
        cfg.POWER_UP_DROP_CHANCE = _clamp_float(self.power_up_drop_chance, 0.0, 1.0)
        cfg.SELECTED_MAP = self.selected_map
        cfg.RANDOM_MAP_OBSTACLE_CHANCE = _clamp_float(self.random_map_obstacle_chance, 0.0, 1.0)
        cfg.ARENA_SHRINK_DELAY_MS = _clamp_int(self.arena_shrink_delay_ms, 15000, 900000)
        cfg.ARENA_SHRINK_SPEED_MULTIPLIER = _clamp_float(self.arena_shrink_speed_multiplier, 0.1, 5.0)


@dataclass
class PlayerSettings:
    local_players: int
    player_hues: list[float]

    @classmethod
    def from_runtime(cls):
        return cls(
            local_players=cfg.LOCAL_PLAYERS,
            player_hues=list(cfg.PLAYER_HUES),
        )

    @classmethod
    def from_dict(cls, data: dict):
        raw_hues = data.get("player_hues", cfg.PLAYER_HUES)
        if not isinstance(raw_hues, list):
            raw_hues = list(cfg.PLAYER_HUES)

        sanitized_hues = [_clamp_float(hue, 0.0, 1.0) for hue in raw_hues[:_MAX_PLAYERS]]
        if not sanitized_hues:
            sanitized_hues = [0.0]

        return cls(
            local_players=_clamp_int(data.get("local_players", cfg.LOCAL_PLAYERS), 1, _MAX_PLAYERS),
            player_hues=sanitized_hues,
        )

    def apply(self):
        cfg.LOCAL_PLAYERS = _clamp_int(self.local_players, 1, _MAX_PLAYERS)
        cfg.PLAYER_HUES[:] = list(self.player_hues)


@dataclass
class ControlsSettings:
    keybind_rows: list[list[int]]

    @classmethod
    def from_runtime(cls):
        return cls(keybind_rows=[list(row) for row in keybinds[:_MAX_PLAYERS]])

    @classmethod
    def from_dict(cls, data: dict):
        raw_rows = data.get("keybind_rows", _DEFAULT_KEYBINDS)
        sanitized_rows = []

        if isinstance(raw_rows, list):
            for row in raw_rows[:_MAX_PLAYERS]:
                if isinstance(row, list) and len(row) == _KEYBINDS_PER_PLAYER:
                    sanitized_rows.append([int(key) for key in row])

        if not sanitized_rows:
            sanitized_rows = [row.copy() for row in _DEFAULT_KEYBINDS]

        while len(sanitized_rows) < _MAX_PLAYERS:
            sanitized_rows.append(_DEFAULT_KEYBINDS[len(sanitized_rows)].copy())

        return cls(keybind_rows=sanitized_rows)

    def apply(self):
        keybinds[:] = [list(row) for row in self.keybind_rows[:_MAX_PLAYERS]]


@dataclass
class AppSettings:
    schema_version: int
    audio: AudioSettings
    gameplay: GameplaySettings
    players: PlayerSettings
    controls: ControlsSettings

    @classmethod
    def from_runtime(cls):
        return cls(
            schema_version=1,
            audio=AudioSettings.from_runtime(),
            gameplay=GameplaySettings.from_runtime(),
            players=PlayerSettings.from_runtime(),
            controls=ControlsSettings.from_runtime(),
        )

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            return cls.from_runtime()

        return cls(
            schema_version=int(data.get("schema_version", 1)),
            audio=AudioSettings.from_dict(data.get("audio", {})),
            gameplay=GameplaySettings.from_dict(data.get("gameplay", {})),
            players=PlayerSettings.from_dict(data.get("players", {})),
            controls=ControlsSettings.from_dict(data.get("controls", {})),
        )

    def apply(self):
        self.audio.apply()
        self.gameplay.apply()
        self.players.apply()
        self.controls.apply()

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "audio": asdict(self.audio),
            "gameplay": asdict(self.gameplay),
            "players": asdict(self.players),
            "controls": asdict(self.controls),
        }


class SettingsStore:
    def __init__(self, path: str | None = None):
        self.path = path or _get_settings_path()

    def load(self) -> AppSettings:
        if not os.path.exists(self.path):
            return AppSettings.from_runtime()

        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return AppSettings.from_runtime()

        try:
            return AppSettings.from_dict(data)
        except (TypeError, ValueError):
            return AppSettings.from_runtime()

    def save(self, settings: AppSettings):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(settings.to_dict(), fh, indent=2)


def load_runtime_settings() -> AppSettings:
    settings = SettingsStore().load()
    settings.apply()
    return settings


def save_runtime_settings():
    try:
        SettingsStore().save(AppSettings.from_runtime())
    except OSError:
        pass

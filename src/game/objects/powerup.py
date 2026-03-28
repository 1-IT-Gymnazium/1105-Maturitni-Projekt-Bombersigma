# game/objects/powerup.py
"""
Generic effect + powerup system.

Usage examples:
    # Give an effect directly (e.g., on pickup):
    player.effects.add("speed_boost")                           # uses defaults from SPECS
    player.effects.add("speed_boost", duration_ms=8000)         # override duration
    player.effects.add("bomb_range_up", magnitude=1)            # permanent by default here
    player.effects.add("infinite_bombs")                        # temporary 0ms bomb cooldown

    # Spawn a pickup on a tile:
    tile.powerup = create_powerup("speed_boost")                # uses defaults
    tile.powerup = create_powerup("speed_boost", magnitude=6)   # override magnitude

HUD can read time left via:
    player.effects.fraction_left("speed_boost")
"""

import pygame
from typing import Dict, List, Callable, Optional

from game.assets import config as cfg
from game.assets.graphics import images, resize_image

from game.assets import sounds

# ----------------- Effect runtime -----------------

class EffectInstance:
    def __init__(self, effect_id: str, duration_ms: int, magnitude: int = 0):
        self.effect_id = effect_id
        # duration <= 0 => infinite (permanent) effect
        self.duration_ms = int(duration_ms)
        self.magnitude = magnitude
        self.started_at = pygame.time.get_ticks()

    @property
    def expires_at(self) -> float:
        if self.duration_ms <= 0:
            return float("inf")
        return self.started_at + self.duration_ms

    def fraction_left(self, now: Optional[int] = None) -> float:
        if self.duration_ms <= 0:
            return 1.0  # permanent: show full icon if you want a static indicator
        if now is None:
            now = pygame.time.get_ticks()
        left = max(0, (self.started_at + self.duration_ms) - now)
        return left / self.duration_ms if self.duration_ms > 0 else 0.0


# ---- Stacking policies ----
STACK_REFRESH = "refresh"  # one instance; new pickup refreshes timer
STACK_STACK   = "stack"    # keep multiple instances, sum magnitudes (capped)
STACK_IGNORE  = "ignore"   # ignore new if already active


class EffectSpec:
    """
    Defines one effect type (how it modifies the player, icon, defaults, stacking).
    """
    def __init__(self,
                 effect_id: str,
                 icon_key: str,
                 on_recompute: Callable,      # fn(player, instances: List[EffectInstance]) -> None
                 stacking: str = STACK_REFRESH,
                 max_stacks: int = 3,
                 default_duration_ms: int = 6000,
                 default_magnitude: int = 0):
        self.effect_id = effect_id
        self.icon_key = icon_key
        self.on_recompute = on_recompute
        self.stacking = stacking
        self.max_stacks = max_stacks
        self.default_duration_ms = default_duration_ms
        self.default_magnitude = default_magnitude


class Effects:
    """Attach to Player; owns active instances and recalculates stats."""
    def __init__(self, player):
        self.player = player
        self._active: Dict[str, List[EffectInstance]] = {}

    def apply_time_offset(self, delta_ms: int):
        """
        Shift all active effect timers forward by delta_ms.
        Use this when the game is paused so durations don't tick down.
        """
        if not delta_ms:
            return
        for lst in self._active.values():
            for inst in lst:
                inst.started_at += delta_ms

    def add(self, effect_id: str, duration_ms: Optional[int] = None, magnitude: Optional[int] = None):
        spec = SPECS.get(effect_id)
        if spec is None:
            return

        dur = spec.default_duration_ms if duration_ms is None else duration_ms
        mag = spec.default_magnitude if magnitude is None else magnitude

        lst = self._active.get(effect_id, [])

        if spec.stacking == STACK_REFRESH:
            lst = [EffectInstance(effect_id, dur, mag)]
        elif spec.stacking == STACK_STACK:
            lst.append(EffectInstance(effect_id, dur, mag))
            if len(lst) > spec.max_stacks:
                lst = lst[-spec.max_stacks:]
        elif spec.stacking == STACK_IGNORE:
            if not lst:
                lst = [EffectInstance(effect_id, dur, mag)]
        else:
            lst = [EffectInstance(effect_id, dur, mag)]

        self._active[effect_id] = lst
        spec.on_recompute(self.player, lst)

    def update(self):
        now = pygame.time.get_ticks()
        changed = []
        for effect_id, lst in list(self._active.items()):
            before = len(lst)
            lst = [inst for inst in lst if inst.expires_at > now]
            if len(lst) != before:
                self._active[effect_id] = lst
                changed.append(effect_id)
        for effect_id in changed:
            spec = SPECS.get(effect_id)
            if spec:
                spec.on_recompute(self.player, self._active.get(effect_id, []))

    # HUD helpers
    def fraction_left(self, effect_id: str) -> float:
        lst = self._active.get(effect_id, [])
        if not lst:
            return 0.0
        now = pygame.time.get_ticks()
        return max(inst.fraction_left(now) for inst in lst)

    def any_active(self, effect_id: str) -> bool:
        return bool(self._active.get(effect_id))

    def stack_count(self, effect_id: str) -> int:
        lst = self._active.get(effect_id, [])
        return len(lst)


# ----------------- Effect specs/logic -----------------

def _recompute_speed(player, instances: List[EffectInstance]):
    from game.objects import player as player_module

    base = getattr(player, "base_move_speed", player_module.get_base_move_speed())
    if not instances:
        player.move_speed = base
        return
    # Keep speed boosts proportional to tile size so movement stays consistent across grid sizes.
    bonus = sum(i.magnitude for i in instances) * player_module.get_speed_boost_amount()
    player.move_speed = base + bonus

def _recompute_bomb_range(player, instances: List[EffectInstance]):
    base = getattr(player, "base_bomb_range", 1)
    if not instances:
        player.bomb_range = base
        return
    bonus = sum(i.magnitude for i in instances)
    player.bomb_range = base + bonus

def _recompute_bomb_cooldown(player, instances: List[EffectInstance]):
    base = getattr(player, "base_bomb_cooldown_ms", cfg.DEFAULT_BOMB_COOLDOWN)
    effects = getattr(player, "effects", None)

    if effects and effects.any_active("infinite_bombs"):
        player.bomb_cooldown_ms = 0
        return

    active_instances = instances
    if effects:
        active_instances = effects._active.get("bomb_cooldown_reduce", [])

    bonus = sum(i.magnitude for i in active_instances)
    player.bomb_cooldown_ms = max(500, base - (bonus * 500))


SPECS: Dict[str, EffectSpec] = {
    "speed_boost": EffectSpec(
        effect_id="speed_boost",
        icon_key="powerup_speedboost",   
        on_recompute=_recompute_speed,
        stacking=STACK_REFRESH,
        default_duration_ms=6000,
        default_magnitude=4,
    ),
    "bomb_range_up": EffectSpec(
        effect_id="bomb_range_up",
        icon_key="powerup_bomb_range",   
        on_recompute=_recompute_bomb_range,
        stacking=STACK_STACK,
        max_stacks=5,
        default_duration_ms=0,        # 0 => permanent upgrade
        default_magnitude=1,
    ),
    "bomb_cooldown_reduce": EffectSpec(
        effect_id="bomb_cooldown_reduce",
        icon_key="powerup_bomb_cooldown",
        on_recompute=_recompute_bomb_cooldown,                   
        stacking=STACK_STACK,
        max_stacks=999,
        default_duration_ms=0,           # 0 => permanent upgrade
        default_magnitude=1
    ),
    "infinite_bombs": EffectSpec(
        effect_id="infinite_bombs",
        icon_key="powerup_infinite_bombs",
        on_recompute=_recompute_bomb_cooldown,
        stacking=STACK_REFRESH,
        default_duration_ms=3000,
        default_magnitude=0,
    )
}

# ----------------- Pickups (spawnables) -----------------

class Powerup:
    """
    A tile-bound pickup that, when collected, applies an effect to the player.
    Pulls its icon and defaults from the effect spec registry.
    """
    def __init__(self, effect_id: str, duration_ms: Optional[int] = None, magnitude: Optional[int] = None):
        spec = SPECS.get(effect_id)
        if spec is None:
            raise KeyError(f"Unknown effect_id: {effect_id}")

        self.effect_id = effect_id
        self.duration_ms = spec.default_duration_ms if duration_ms is None else duration_ms
        self.magnitude = spec.default_magnitude if magnitude is None else magnitude

        # Build icon surface (sized to tile)
        surf = images.get(spec.icon_key) or images.get("bomb_timer_8")
        if surf is None:
            raise KeyError("No powerup icon available (missing spec icon and fallback).")
        ratio = cfg.TILE_SIZE / surf.get_width()
        self.icon = resize_image(surf, ratio)

    def apply_to(self, player):
        if hasattr(player, "effects"):
            player.effects.add(self.effect_id, self.duration_ms, self.magnitude)
            sounds.play_sound("pickup","pickup")


def create_powerup(effect_id: str,
                   duration_ms: Optional[int] = None,
                   magnitude: Optional[int] = None) -> Powerup:
    """
    Generic factory: returns a Powerup with defaults from SPECS,
    unless you override duration/magnitude.
    """
    return Powerup(effect_id, duration_ms, magnitude)

# Optional alias:
make_powerup = create_powerup

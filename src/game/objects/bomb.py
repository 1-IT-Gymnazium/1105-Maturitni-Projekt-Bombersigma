from game.assets import sounds

# game/objects/bomb.py
"""
Bombs for Atomic BomberSigma.

- Place a bomb on a tile; it ticks for `fuse_frames`, then explodes in a cross.
- Explosion removes obstacles, can drop powerups, and kills players on affected tiles.
"""

import pygame
from typing import List, Tuple
import random

from game.assets import config as cfg
from game.assets import graphics
from game.objects import tile as tile_module
from game.objects import player as player_module
from game.objects import powerup as powerup_module


# ---- Tunables ---------------------------------------------------------------

DEFAULT_FUSE_FRAMES = 60
EXPLOSION_FRAMES = 30
POWERUP_DROP_CHANCE = cfg.POWER_UP_DROP_CHANCE
POWERUP_DROP_TABLE = ["speed_boost", "bomb_range_up", "bomb_cooldown_reduce", "infinite_bombs"]


class Bomb:
    """Represents a bomb placed by a player."""

    _stage_images: List[pygame.Surface] = []
    _explosion_horizontal: pygame.Surface | None = None
    _explosion_vertical: pygame.Surface | None = None
    _asset_tile_size: int | None = None

    def __init__(
        self,
        tile: tile_module.Tile,
        grid_pos: Tuple[int, int],
        owner: player_module.Player,
        radius: int = 1,
        fuse_frames: int = DEFAULT_FUSE_FRAMES
    ) -> None:
        self.tile = tile
        self.grid_pos = grid_pos
        self.owner = owner
        self.radius = radius
        self.fuse_frames = fuse_frames

        self._frame_counter = 0
        self.exploded = False
        self.explosion_frames_remaining = EXPLOSION_FRAMES
        self.fuse_channel = sounds.play_looping_sound("fuse")

        self.exploded_radius = radius
        self.explosion_tiles: List[tile_module.Tile] = []
        self.explosion_parts: List[Tuple[str, tile_module.Tile]] = []

        self.tile.bomb = True

        if not Bomb._stage_images or Bomb._asset_tile_size != cfg.TILE_SIZE:
            self._load_assets()

    @classmethod
    def _load_assets(cls) -> None:
        images = graphics.images

        cls._stage_images.clear()
        for i in range(1, 6):
            key = f"bomb_stage_{i}"
            if key in images:
                ratio = cfg.TILE_SIZE / images[key].get_width()
                cls._stage_images.append(graphics.resize_image(images[key], ratio))

        if "bomb_explosion_horizontal" in images:
            ratio_h = cfg.TILE_SIZE / images["bomb_explosion_horizontal"].get_width()
            cls._explosion_horizontal = graphics.resize_image(images["bomb_explosion_horizontal"], ratio_h)

        if "bomb_explosion_vertical" in images:
            ratio_v = cfg.TILE_SIZE / images["bomb_explosion_vertical"].get_width()
            cls._explosion_vertical = graphics.resize_image(images["bomb_explosion_vertical"], ratio_v)
        cls._asset_tile_size = cfg.TILE_SIZE

    # ----------------------------------- lifecycle ---------------------------

    def update(self, game_grid: List[tile_module.Tile], players: List[player_module.Player]):
        """
        Tick the fuse or count down the explosion animation.
        Returns (finished: bool, killed_players: list[Player]).
        """
        if not self.exploded:
            self._frame_counter += 1
            if self._frame_counter >= self.fuse_frames:
                killed = self._explode(game_grid, players)
            else:
                killed = []
        else:
            self.explosion_frames_remaining -= 1
            if self.explosion_frames_remaining <= 0:
                for t in self.explosion_tiles:
                    t.exploding = False
                self.tile.bomb = False
                return True, []
            killed = []

        return False, killed

    def draw(self, surface: pygame.Surface) -> None:
        """
        Draw the bomb sprite or its explosion onto the surface.
        """
        if not self.exploded:
            if self.fuse_frames > 0 and Bomb._stage_images:
                stage_index = min(
                    len(Bomb._stage_images) - 1,
                    (self._frame_counter * len(Bomb._stage_images)) // max(1, self.fuse_frames)
                )
                surface.blit(Bomb._stage_images[stage_index], self.tile.pos)
            return

        for part_type, tile in self.explosion_parts:
            if part_type == "center":
                if Bomb._stage_images:
                    surface.blit(Bomb._stage_images[-1], tile.pos)
            elif part_type == "horizontal":
                if Bomb._explosion_horizontal:
                    surface.blit(Bomb._explosion_horizontal, tile.pos)
            elif part_type == "vertical":
                if Bomb._explosion_vertical:
                    surface.blit(Bomb._explosion_vertical, tile.pos)

    # ----------------------------------- internals --------------------------

    def _add_explosion_part(self, part_type: str, tile: tile_module.Tile) -> None:
        self.explosion_tiles.append(tile)
        self.explosion_parts.append((part_type, tile))
        tile.exploding = True

    def _explode(self, game_grid: List[tile_module.Tile], players: List[player_module.Player]):
        """
        Trigger the explosion: mark affected tiles, remove obstacles (and maybe drop powerups),
        and kill players on affected tiles.
        """
        self.exploded = True
        self.exploded_radius = max(1, getattr(self.owner, "bomb_range", self.radius))

        self.explosion_tiles.clear()
        self.explosion_parts.clear()

        if self.fuse_channel is not None:
            self.fuse_channel.stop()
            self.fuse_channel = None

        sounds.play_sound("explosion", "explosion")

        # center tile
        self._add_explosion_part("center", self.tile)

        # propagate in 4 directions
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            part_type = "horizontal" if dx != 0 else "vertical"

            for step in range(1, self.exploded_radius + 1):
                nx = self.grid_pos[0] + dx * step
                ny = self.grid_pos[1] + dy * step

                if not (0 <= nx < cfg.GRID_WIDTH and 0 <= ny < cfg.GRID_HEIGHT):
                    break

                idx = ny * cfg.GRID_WIDTH + nx
                neighbour_tile = game_grid[idx]

                self._add_explosion_part(part_type, neighbour_tile)

                if neighbour_tile.obstacle:
                    neighbour_tile.obstacle = False
                    neighbour_tile.sprite = tile_module.Tile.empty_tile_sprite

                    if getattr(neighbour_tile, "powerup", None) is None:
                        if random.random() < cfg.POWER_UP_DROP_CHANCE and POWERUP_DROP_TABLE:
                            effect_id = random.choice(POWERUP_DROP_TABLE)
                            try:
                                neighbour_tile.powerup = powerup_module.create_powerup(effect_id)
                            except Exception:
                                pass

                    break

        killed_players = []
        exploded_positions = {t.grid_pos for t in self.explosion_tiles}

        for p in players:
            if getattr(p, "state", None) == "dead":
                continue

            if p.grid_pos in exploded_positions:
                try:
                    p.state = "dead"
                    p.update_sprite()
                except Exception:
                    pass
                killed_players.append(p)
                sounds.play_random_sound_type("hurt", "death")

        return killed_players

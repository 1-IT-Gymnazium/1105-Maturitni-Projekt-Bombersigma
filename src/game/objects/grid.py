import pygame
from game.assets import config as cfg
from game.objects.grid_preset import GridPreset
from game.objects.tile import Tile
import random


def create_grid(preset_name: str | None = None, obstacle_chance: float | None = None):
    x_offset = int(cfg.GRID_X_POS)
    y_offset = int(cfg.GRID_Y_POS)
    tiles = []
    chance = cfg.TILE_OBSTACLE_CHANCE if obstacle_chance is None else obstacle_chance

    preset = None
    if preset_name is not None:
        try:
            preset = GridPreset(preset_name)
        except ValueError:
            # Unknown preset, just fall back to random
            preset = None

            
    for row in range(cfg.GRID_HEIGHT):
        for col in range(cfg.GRID_WIDTH):
            x = col * cfg.TILE_SIZE + x_offset
            y = row * cfg.TILE_SIZE + y_offset

            if preset is not None:
                # Use the scaled pattern
                is_obstacle = preset.is_obstacle(cfg.GRID_WIDTH, cfg.GRID_HEIGHT, row, col)
            else:
                # Old random behavior
                is_obstacle = random.random() < chance

            tile = Tile((col, row), (x, y), obstacle=is_obstacle)
            tiles.append(tile)

    assign_neighbors(tiles, cfg.GRID_WIDTH, cfg.GRID_HEIGHT)
    return tiles



def draw_grid(
    tiles:list[Tile],
    surface,
    resized:float | None = None,
    warning_tiles: set[tuple[int, int]] | None = None,
):
        draw_outer_border(surface, resized)
        for tile in tiles:
            if resized:
                tile.pos = tuple([resized*x for x in tile.pos])
            tile.draw(surface)
            if warning_tiles and tile.grid_pos in warning_tiles:
                surface.blit(Tile.warning_tile_sprite, tile.pos)


def get_border_positions(
    x_offset: int | None = None,
    y_offset: int | None = None,
    tile_size: int | None = None,
    grid_width: int | None = None,
    grid_height: int | None = None,
):
    tile_size = cfg.TILE_SIZE if tile_size is None else tile_size
    x_offset = int(cfg.GRID_X_POS) if x_offset is None else x_offset
    y_offset = int(cfg.GRID_Y_POS) if y_offset is None else y_offset
    grid_width = cfg.GRID_WIDTH if grid_width is None else grid_width
    grid_height = cfg.GRID_HEIGHT if grid_height is None else grid_height

    positions = []
    for row in range(-1, grid_height + 1):
        for col in range(-1, grid_width + 1):
            is_perimeter = row in (-1, grid_height) or col in (-1, grid_width)
            if not is_perimeter:
                continue
            x = x_offset + col * tile_size
            y = y_offset + row * tile_size
            positions.append((x, y))
    return positions


def draw_outer_border(surface, resized: float | None = None):
    if Tile.immortal_obstacle_tile_sprite is None or Tile._sprite_tile_size != cfg.TILE_SIZE:
        Tile.refresh_sprites()

    sprite = Tile.immortal_obstacle_tile_sprite
    if resized:
        sprite = pygame.transform.smoothscale(
            sprite,
            (
                max(1, int(sprite.get_width() * resized)),
                max(1, int(sprite.get_height() * resized)),
            ),
        )

    for x, y in get_border_positions():
        draw_pos = (x, y)
        if resized:
            draw_pos = (int(x * resized), int(y * resized))
        surface.blit(sprite, draw_pos)


def build_shrink_schedule(
    grid_width: int | None = None,
    grid_height: int | None = None,
    step_ms: int | None = None,
):
    grid_width = cfg.GRID_WIDTH if grid_width is None else grid_width
    grid_height = cfg.GRID_HEIGHT if grid_height is None else grid_height
    step_ms = (
        int(round(cfg.ARENA_SHRINK_BASE_STEP_MS / max(0.1, cfg.ARENA_SHRINK_SPEED_MULTIPLIER)))
        if step_ms is None
        else step_ms
    )

    schedule = []
    elapsed_ms = 0
    left = 0
    right = grid_width - 1
    top = 0
    bottom = grid_height - 1

    while left <= right and top <= bottom:
        segments = [
            [(col, top) for col in range(left, right + 1)],
            [(right, row) for row in range(top + 1, bottom + 1)],
            [(col, bottom) for col in range(right - 1, left - 1, -1)] if bottom > top else [],
            [(left, row) for row in range(bottom - 1, top, -1)] if left < right else [],
        ]

        for segment in segments:
            if not segment:
                continue

            for grid_pos in segment:
                schedule.append((grid_pos, elapsed_ms))
                elapsed_ms += step_ms

        left += 1
        right -= 1
        top += 1
        bottom -= 1

    return schedule


def assign_neighbors(tiles:list[Tile], grid_width, grid_height):
    for tile in tiles:
        col, row = tile.grid_pos

        directions = [
            (1, 0),   # right
            (0, 1),   # down
            (-1, 0),  # left
            (0, -1)   # up
        ]

        tile.neighbors = []

        for dx, dy in directions:
            nx, ny = col + dx, row + dy

            # Check if neighbor is within bounds
            if 0 <= nx < grid_width and 0 <= ny < grid_height:
                neighbor_index = ny * grid_width + nx
                tile.neighbors.append(tiles[neighbor_index])
            else:
                tile.neighbors.append(None)


def tile_has_safe_spawn_axis(tile: Tile) -> bool:
    if tile.obstacle:
        return False

    horizontal_open = 0
    vertical_open = 0

    for neighbor in (tile.neighbors[0], tile.neighbors[2]):
        if neighbor is not None and not neighbor.obstacle:
            horizontal_open += 1

    for neighbor in (tile.neighbors[1], tile.neighbors[3]):
        if neighbor is not None and not neighbor.obstacle:
            vertical_open += 1

    return horizontal_open >= 2 or vertical_open >= 2


def get_spawnable_tiles(tiles: list[Tile]) -> list[Tile]:
    return [tile for tile in tiles if tile_has_safe_spawn_axis(tile)]


def get_tile_at(tiles: list[Tile], col: int, row: int) -> Tile | None:
    if not (0 <= col < cfg.GRID_WIDTH and 0 <= row < cfg.GRID_HEIGHT):
        return None
    return tiles[row * cfg.GRID_WIDTH + col]


def clear_tile(tile: Tile | None):
    if tile is None:
        return
    tile.set_empty()


def make_tile_immortal(tile: Tile | None):
    if tile is None:
        return
    tile.powerup = None
    tile.set_obstacle(True, immortal=True)


def carve_spawn_lane(tiles: list[Tile], tile: Tile):
    clear_tile(tile)

    col, row = tile.grid_pos
    left = get_tile_at(tiles, col - 1, row)
    right = get_tile_at(tiles, col + 1, row)
    up = get_tile_at(tiles, col, row - 1)
    down = get_tile_at(tiles, col, row + 1)

    if left is not None and right is not None:
        clear_tile(left)
        clear_tile(right)
    else:
        clear_tile(up)
        clear_tile(down)

import pygame
from game.objects.grid import create_grid, get_border_positions

def preview_map(map_name: str, pos: tuple[int, int], surface, scale: float = 0.5, obstacle_chance: float | None = None):
    tiles = create_grid(map_name, obstacle_chance=obstacle_chance)

    if not tiles:
        return

    # Find the grid's top-left in pixel space (so we can scale relative to it)
    min_x = min(t.pos[0] for t in tiles)
    min_y = min(t.pos[1] for t in tiles)
    tile_width = tiles[0].sprite.get_width()
    tile_height = tiles[0].sprite.get_height()
    render_min_x = min_x - tile_width
    render_min_y = min_y - tile_height

    # Small cache so we don't rescale the same surface 500 times per frame
    scaled_cache: dict[tuple[int, int, int], pygame.Surface] = {}

    def get_scaled(surf: pygame.Surface) -> pygame.Surface:
        key = (id(surf), int(surf.get_width() * scale), int(surf.get_height() * scale))
        if key in scaled_cache:
            return scaled_cache[key]

        w = max(1, key[1])
        h = max(1, key[2])
        out = pygame.transform.smoothscale(surf, (w, h))
        scaled_cache[key] = out
        return out

    ox, oy = pos

    border_positions = get_border_positions(
        x_offset=min_x,
        y_offset=min_y,
        tile_size=tile_width,
        grid_width=max(t.grid_pos[0] for t in tiles) + 1,
        grid_height=max(t.grid_pos[1] for t in tiles) + 1,
    )

    border_sprite = get_scaled(tiles[0].immortal_obstacle_tile_sprite)
    for x, y in border_positions:
        sx = ox + int((x - render_min_x) * scale)
        sy = oy + int((y - render_min_y) * scale)
        surface.blit(border_sprite, (sx, sy))

    for t in tiles:
        # scale position relative to grid top-left, then place at pos
        sx = ox + int((t.pos[0] - render_min_x) * scale)
        sy = oy + int((t.pos[1] - render_min_y) * scale)

        # scale the tile sprite itself
        tile_surf = get_scaled(t.sprite)
        surface.blit(tile_surf, (sx, sy))


def get_preview_rect(map_name: str, scale: float = 0.2, obstacle_chance: float | None = None) -> pygame.Rect:
    tiles = create_grid(map_name, obstacle_chance=obstacle_chance)
    if not tiles:
        return pygame.Rect(0, 0, 0, 0)

    min_x = min(t.pos[0] for t in tiles)
    min_y = min(t.pos[1] for t in tiles)
    max_x = max(t.pos[0] for t in tiles)
    max_y = max(t.pos[1] for t in tiles)

    tw, th = tiles[0].sprite.get_size()

    w_unscaled = (max_x - min_x) + (3 * tw)
    h_unscaled = (max_y - min_y) + (3 * th)

    w = max(1, int(w_unscaled * scale))
    h = max(1, int(h_unscaled * scale))

    return pygame.Rect(0, 0, w, h)

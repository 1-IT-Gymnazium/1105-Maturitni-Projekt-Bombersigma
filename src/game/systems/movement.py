# game/systems/movement.py
from game.assets import config as cfg

def can_move(player, direction, game_grid):
    if player.is_moving:
        return False

    dx, dy = direction
    new_x = player.grid_pos[0] + dx
    new_y = player.grid_pos[1] + dy

    if not (0 <= new_x < cfg.GRID_WIDTH and 0 <= new_y < cfg.GRID_HEIGHT):
        return False

    tile_index = new_y * cfg.GRID_WIDTH + new_x
    target_tile = game_grid[tile_index]
    return not target_tile.obstacle


def handle_movement(player, direction, game_grid):
    if not can_move(player, direction, game_grid):
        return

    dx, dy = direction
    new_x = player.grid_pos[0] + dx
    new_y = player.grid_pos[1] + dy

    tile_index = new_y * cfg.GRID_WIDTH + new_x  # Move y times in 1d grid and take x steps
    target_tile = game_grid[tile_index]

    player.grid_pos = (new_x, new_y)
    player.target_pos = (target_tile.pos)
    player.is_moving = True

    # === Powerup pickup detection ===
    # When the player commits to moving into the tile, collect any powerup there.
    if getattr(target_tile, "powerup", None):
        try:
            target_tile.powerup.apply_to(player)
        finally:
            target_tile.powerup = None

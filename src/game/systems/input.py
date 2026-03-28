import pygame
from game.systems import movement
from game.assets.keybinds import keybinds

_event_list = []
_held_directions = {}

_DIRECTION_TO_VECTOR = {
    "left": (-1, 0),
    "down": (0, 1),
    "right": (1, 0),
    "up": (0, -1),
}

_DIRECTION_INDEX = {
    "left": 0,
    "down": 1,
    "right": 2,
    "up": 3,
}


def _ensure_player_entry(player_index):
    if player_index not in _held_directions:
        _held_directions[player_index] = []


def _direction_for_key(player_index, key):
    if not (0 <= player_index < len(keybinds)):
        return None

    binds = keybinds[player_index]
    for direction, bind_index in _DIRECTION_INDEX.items():
        if binds[bind_index] == key:
            return direction
    return None

def update_event_queue():
    global _event_list
    _event_list = pygame.event.get()

    for player_index in range(len(keybinds)):
        _ensure_player_entry(player_index)

    for event in _event_list:
        if event.type == pygame.KEYDOWN:
            for player_index in range(len(keybinds)):
                direction = _direction_for_key(player_index, event.key)
                if direction is None:
                    continue

                held = _held_directions[player_index]
                if direction in held:
                    held.remove(direction)
                held.append(direction)

        elif event.type == pygame.KEYUP:
            for player_index in range(len(keybinds)):
                direction = _direction_for_key(player_index, event.key)
                if direction is None:
                    continue

                held = _held_directions[player_index]
                if direction in held:
                    held.remove(direction)

def check_for_quit():
    for event in _event_list:
        if event.type == pygame.QUIT:
            return True
    return False

def check_for_esc():
    for event in _event_list:
       if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
    return False

def check_for_movement_input(player, game_grid):
    held = _held_directions.get(player.player_index, [])
    if not held:
        return

    for direction in reversed(held):
        vector = _DIRECTION_TO_VECTOR[direction]
        if movement.can_move(player, vector, game_grid):
            movement.handle_movement(player, vector, game_grid)
            return

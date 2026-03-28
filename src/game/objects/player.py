# game/objects/player.py
import pygame  # for timing
from game.assets import sounds
from game.assets.graphics import images, shift_hue, resize_image
from game.assets import config as cfg
from game.objects.powerup import Effects
import time

states = {}
_states_tile_size = None


def refresh_player_states():
    global states, _states_tile_size
    states = {
        "alive": resize_image(images["player_default"],
                              cfg.TILE_SIZE / images["player_default"].get_width()),
        "dead": resize_image(images["player_dead"],
                             cfg.TILE_SIZE / images["player_dead"].get_width())
    }
    _states_tile_size = cfg.TILE_SIZE


refresh_player_states()


def get_base_move_speed() -> float:
    return max(1.0, cfg.TILE_SIZE / 16)


def get_speed_boost_amount() -> float:
    return max(0.5, cfg.TILE_SIZE / 128)

class Player:
    """Represents the player's in-game on-board sprite"""
    def __init__(self, pos, grid_pos, hue, player_index):
        if _states_tile_size != cfg.TILE_SIZE:
            refresh_player_states()
        self.state = "alive"
        self.hue = hue
        # Preload slot; filled by async preloader in game_loop
        self.preloaded_sprites: dict[str, pygame.Surface] = {}
        self.sprite = shift_hue(states["alive"], hue)
        self.pos = pos
        self.grid_pos = grid_pos
        self.target_pos = pos  # where to move toward
        self.is_moving = False
        self.hud = None
        self.last_bomb_time = 0  # Last tick a bomb was placed
        self.player_index = player_index
        self.tod = float('inf') # Time of death

        # ---- Base stats ----
        self.base_move_speed = get_base_move_speed()
        self.move_speed = self.base_move_speed
        self.base_bomb_cooldown_ms = cfg.DEFAULT_BOMB_COOLDOWN
        self.bomb_cooldown_ms = cfg.DEFAULT_BOMB_COOLDOWN

        # Optional base for other effects (safe defaults)
        self.base_bomb_range = getattr(self, "base_bomb_range", 1)
        self.bomb_range = getattr(self, "bomb_range", self.base_bomb_range)

        # ---- Effects/powerups component ----
        self.effects = Effects(self)

    def update_sprite(self):
        # Use preloaded sprites when available to avoid runtime hue shifting
        self.sprite = (
            self.preloaded_sprites.get(self.state)
            if self.preloaded_sprites
            else shift_hue(states[self.state], self.hue)
        )
        if self.hud:
            self.hud.update_hud()

    def draw(self, surface):
        # Keep effects up to date
        self.effects.update()

        if self.is_moving:
            sounds.play_random_sound_type("step", channel="footsteps")

            # Move current position toward target position
            x, y = self.pos
            tx, ty = self.target_pos

            dx = tx - x
            dy = ty - y

            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist <= self.move_speed:
                self.pos = self.target_pos
                self.is_moving = False
            else:
                step_x = self.move_speed if dx > 0 else -self.move_speed
                step_y = self.move_speed if dy > 0 else -self.move_speed

                # Only move in direction of need
                if abs(dx) > self.move_speed:
                    x += step_x
                else:
                    x = tx
                if abs(dy) > self.move_speed:
                    y += step_y
                else:
                    y = ty

                self.pos = (x, y)

        surface.blit(self.sprite, self.pos)
        if self.hud:
            self.hud.draw(surface)

    def can_place_bomb(self):
        return pygame.time.get_ticks() - self.last_bomb_time >= self.bomb_cooldown_ms


def create_player(pos, grid_pos, hue, player_index):
    return Player(
        pos,
        grid_pos,
        hue,
        player_index
    )

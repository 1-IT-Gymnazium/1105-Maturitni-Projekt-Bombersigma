# game/ui/player_hud.py
import pygame
from typing import List

from game.assets import config as cfg
from game.assets.graphics import images, shift_hue, resize_image
from game.objects import player as player_module

from game.ui.stacking_icon import StackingIcon as stacking_icon
from game.ui.draining_icon import DrainingIcon as draining_icon

# Bomb cooldown icons (0..8)
_icon_bombs = {}
for i in range(9):
    _icon_bombs.update({i: images[f"bomb_timer_{i}"]})

# Player face icons
_icon_states = {
    "alive": images["icon_player_sigma"],
    "dead": images["icon_player_dead"]
}


class Player_hud:
    """Represents player's in-game HUD"""
    _state_images: List[pygame.Surface] = []

    def __init__(self, position, player: player_module.Player):
        self.position = position
        self.player = player
        self.last_known_state = player.state
        self.preloaded_icons: dict[str, pygame.Surface] = {}

        self.hud_image = shift_hue(_icon_states[self.last_known_state], player.hue)

        #Powerup icons (fallback to a known small icon if your key doesn't exist yet)
        speed_icon_surface = images.get("powerup_speedboost") or _icon_bombs[8]
        bomb_range_surface = images.get("powerup_bomb_range") or _icon_bombs[8]
        bomb_cd_surface = images.get("powerup_bomb_cooldown") or _icon_bombs[8]
        infinite_bombs_surface = images.get("powerup_infinite_bombs") or _icon_bombs[8]

        #Powerup icon locations
        self.speed_icon_pos = (
            self.position[0] + self.hud_image.get_width() + 50,
            self.position[1] + 10
        )
        self.bomb_range_pos = (
            self.position[0] + self.hud_image.get_width() + 50,
            self.position[1] + self.hud_image.get_height()
        )
        self.bomb_cd_pos = (
            self.position[0] + self.hud_image.get_width() + 140,
            self.position[1] + 10
        )
        self.infinite_bombs_pos = (
            self.position[0] + self.hud_image.get_width() + 140,
            self.position[1] + self.hud_image.get_height()
        )

        #Powerup icon classes
        self._speed_icon = draining_icon(resize_image(speed_icon_surface, 1), "powerup_speedboost")
        self._range_icon = stacking_icon(resize_image(bomb_range_surface, 1), "powerup_bomb_range")
        self._cooldown_icon = stacking_icon(resize_image(bomb_cd_surface, 1), "powerup_bomb_cooldown")
        self._infinite_bombs_icon = draining_icon(resize_image(infinite_bombs_surface, 1), "powerup_infinite_bombs")

    def preload_icons(self):
        """Precompute hue-shifted HUD faces to avoid runtime cost."""
        try:
            self.preloaded_icons = {
                state: shift_hue(_icon_states[state], self.player.hue)
                for state in _icon_states
            }
            # Replace current HUD image with preloaded version
            self.hud_image = self.preloaded_icons.get(self.last_known_state, self.hud_image)
        except Exception:
            # If anything fails, fall back to on-demand shift_hue
            self.preloaded_icons = {}

    def update_hud(self):
        # Swap the face icon when state changes
        if self.last_known_state != self.player.state:
            self.hud_image = (
                self.preloaded_icons.get(self.player.state)
                if self.preloaded_icons
                else shift_hue(_icon_states[self.player.state], self.player.hue)
            )
            self.last_known_state = self.player.state

    def draw(self, surface: pygame.Surface):
        # Background panel
        pygame.draw.rect(surface, "grey", (self.position, cfg.PLAYER_HUD_SIZE))

        # Player face
        surface.blit(self.hud_image, self.position)

        # -------- Bomb cooldown indicator --------
        current_ticks = pygame.time.get_ticks()
        p = self.player
        index = 0

        if p.state == "alive":
            elapsed = current_ticks - p.last_bomb_time
            fraction_done = elapsed / p.bomb_cooldown_ms if p.bomb_cooldown_ms > 0 else 1.0
            fraction_done = min(max(fraction_done, 0), 1)  # Clamp between 0 and 1
            index = int(fraction_done * 8)  # 0..8

        timer_icon = _icon_bombs[index]
        timer_pos = (
            self.position[0] + (self.hud_image.get_width() / 2 - 32),
            self.position[1] + self.hud_image.get_height()
        )
        surface.blit(timer_icon, timer_pos)

        # -------- Speed boost draining icon (reads from effects) --------
        frac = 0.0
        if hasattr(p, "effects"):
            frac = p.effects.fraction_left("speed_boost")

        self._speed_icon.draw_fraction(surface, self.speed_icon_pos, frac)
        # ---------------------------------------------------------------
        # -------- Bomb range stacking icon (reads from effects) --------
        stack = 0
        if hasattr(p, "effects"):
            stack = p.effects.stack_count("bomb_range_up")

        self._range_icon.draw_stack(surface, self.bomb_range_pos, stack)
        # ---------------------------------------------------------------
        # -------- Bomb cooldown stacking icon (reads from effects) --------
        cd_stack = 0
        if hasattr(p, "effects"):
            cd_stack = p.effects.stack_count("bomb_cooldown_reduce")

        self._cooldown_icon.draw_stack(surface, self.bomb_cd_pos, cd_stack)
        # ---------------------------------------------------------------
        # -------- Infinite bombs draining icon (reads from effects) --------
        infinite_frac = 0.0
        if hasattr(p, "effects"):
            infinite_frac = p.effects.fraction_left("infinite_bombs")

        self._infinite_bombs_icon.draw_fraction(surface, self.infinite_bombs_pos, infinite_frac)
        # ---------------------------------------------------------------

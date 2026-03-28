import pygame

from game.assets import config as cfg
from game.assets import graphics
from game.assets.graphics import shift_hue
from game.assets.keybinds import keybinds
from game.ui import button

font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 34)

PRESET_HUES = [0.0, 0.12, 0.24, 0.36, 0.56, 0.72]


class PlayerCustomizationUI:
    _preset_icons: dict[float, pygame.Surface] = {}
    _arrow_images: dict[str, pygame.Surface] = {}

    def __init__(self):
        self.images = graphics.images
        self.player_count = cfg.LOCAL_PLAYERS
        self.on_confirm = None
        self.done = False
        self.editing_bind = None

        self.kb_icons = {
            "left": self.images["keybind_left"],
            "up": self.images["keybind_up"],
            "right": self.images["keybind_right"],
            "down": self.images["keybind_down"],
            "bomb": self.images["keybind_bomb"],
        }
        self.directions = ["left", "up", "right", "down", "bomb"]
        self.bind_index_by_direction = {
            "left": 0,
            "down": 1,
            "right": 2,
            "up": 3,
            "bomb": 4,
        }
        self.player_icon_base = self.images["icon_player_sigma"]

        self._ensure_player_data(self.player_count)
        self._ensure_preset_cache()
        self.buttons: list[button.Button] = []
        self.player_panels: list[dict] = []
        self._rebuild_ui()

    def _ensure_player_data(self, n_players: int):
        default_row = [
            pygame.K_a,
            pygame.K_s,
            pygame.K_d,
            pygame.K_w,
            pygame.K_SPACE,
        ]
        while len(keybinds) < n_players:
            keybinds.append(default_row.copy())

        if not hasattr(cfg, "PLAYER_HUES"):
            cfg.PLAYER_HUES = []

        default_hues = PRESET_HUES[:4]
        while len(cfg.PLAYER_HUES) < n_players:
            cfg.PLAYER_HUES.append(default_hues[len(cfg.PLAYER_HUES) % len(default_hues)])

        for i in range(len(cfg.PLAYER_HUES)):
            cfg.PLAYER_HUES[i] = self._closest_preset_hue(cfg.PLAYER_HUES[i])

        self._normalize_active_player_hues()

    def _ensure_preset_cache(self):
        if not PlayerCustomizationUI._arrow_images:
            PlayerCustomizationUI._arrow_images = {
                "left": graphics.resize_image(self.images["arrow_l"], 0.22),
                "right": graphics.resize_image(self.images["arrow_r"], 0.22),
            }

        if not PlayerCustomizationUI._preset_icons:
            PlayerCustomizationUI._preset_icons = {
                hue: shift_hue(self.player_icon_base, hue)
                for hue in PRESET_HUES
            }

    def _closest_preset_hue(self, hue: float) -> float:
        return min(PRESET_HUES, key=lambda preset: abs(preset - hue))

    def _get_hue_index(self, player_index: int) -> int:
        hue = self._closest_preset_hue(cfg.PLAYER_HUES[player_index])
        return PRESET_HUES.index(hue)

    def _normalize_active_player_hues(self):
        used_hues = set()
        for player_index in range(self.player_count):
            preferred_hue = self._closest_preset_hue(cfg.PLAYER_HUES[player_index])
            if preferred_hue not in used_hues:
                cfg.PLAYER_HUES[player_index] = preferred_hue
                used_hues.add(preferred_hue)
                continue

            for fallback_hue in PRESET_HUES:
                if fallback_hue not in used_hues:
                    cfg.PLAYER_HUES[player_index] = fallback_hue
                    used_hues.add(fallback_hue)
                    break

    def _cycle_player_hue(self, player_index: int, direction: int):
        current_index = self._get_hue_index(player_index)
        unavailable_hues = {
            self._closest_preset_hue(cfg.PLAYER_HUES[idx])
            for idx in range(self.player_count)
            if idx != player_index
        }

        for step in range(1, len(PRESET_HUES) + 1):
            next_index = (current_index + (direction * step)) % len(PRESET_HUES)
            next_hue = PRESET_HUES[next_index]
            if next_hue not in unavailable_hues:
                cfg.PLAYER_HUES[player_index] = next_hue
                break

    def _rebuild_ui(self):
        self.player_panels = []
        self.buttons = []

        panel_size = (820, 260)
        origin_x = 130
        origin_y = 120
        gap_x = 40
        gap_y = 34

        for player_index in range(self.player_count):
            row = player_index // 2
            col = player_index % 2
            x = origin_x + col * (panel_size[0] + gap_x)
            y = origin_y + row * (panel_size[1] + gap_y)
            panel_rect = pygame.Rect(x, y, panel_size[0], panel_size[1])
            color_center = (x + 570, y + 188)

            left_button = button.Button(
                PlayerCustomizationUI._arrow_images["left"],
                (color_center[0] - 105, color_center[1]),
                self._make_hue_cycle_action(player_index, -1),
            )
            right_button = button.Button(
                PlayerCustomizationUI._arrow_images["right"],
                (color_center[0] + 105, color_center[1]),
                self._make_hue_cycle_action(player_index, 1),
            )

            bind_buttons = []
            bind_start_x = x + 385
            bind_y = y + 84
            bind_step_x = 74
            for direction_name in self.directions:
                img = self.kb_icons[direction_name]
                pos = (bind_start_x + len(bind_buttons) * bind_step_x, bind_y)

                def make_action(p_idx, dir_name):
                    def action():
                        self.editing_bind = (p_idx, dir_name)
                    return action

                bind_button = button.Button(img, pos, make_action(player_index, direction_name), label=direction_name)
                bind_button.meta = {"player": player_index, "direction": direction_name}
                bind_buttons.append(bind_button)

            panel_buttons = [left_button, right_button, *bind_buttons]
            self.buttons.extend(panel_buttons)
            self.player_panels.append(
                {
                    "player": player_index,
                    "rect": panel_rect,
                    "color_center": color_center,
                    "color_buttons": [left_button, right_button],
                    "bind_buttons": bind_buttons,
                }
            )

        plus_btn = button.Button(
            self.images["plus_button"],
            (cfg.DISPLAY_CENTER_X - 70, cfg.DISPLAY_CENTER_Y + 300),
            self._increase_player_count,
        )
        minus_btn = button.Button(
            self.images["minus_button"],
            (cfg.DISPLAY_CENTER_X + 70, cfg.DISPLAY_CENTER_Y + 300),
            self._decrease_player_count,
        )
        self.buttons.extend([plus_btn, minus_btn])

    def _make_hue_cycle_action(self, player_index: int, direction: int):
        def action():
            self._cycle_player_hue(player_index, direction)
        return action

    def _increase_player_count(self):
        if self.player_count < 4:
            self.player_count += 1
            self._ensure_player_data(self.player_count)
            self._rebuild_ui()

    def _decrease_player_count(self):
        if self.player_count > 2:
            if self.editing_bind is not None and self.editing_bind[0] == self.player_count - 1:
                self.editing_bind = None
            self.player_count -= 1
            self._rebuild_ui()

    def handle_events(self, events):
        for event in events:
            if self.editing_bind is not None and event.type == pygame.KEYDOWN:
                player_index, direction = self.editing_bind
                if 0 <= player_index < self.player_count:
                    direction_index = self.bind_index_by_direction[direction]
                    keybinds[player_index][direction_index] = event.key
                self.editing_bind = None

            for btn in self.buttons:
                btn.handle_event(event)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.on_confirm:
                    self.on_confirm()

    def draw(self, surface: pygame.Surface):
        for panel in self.player_panels:
            player_index = panel["player"]
            panel_rect = panel["rect"]
            color_center_x, color_center_y = panel["color_center"]

            pygame.draw.rect(surface, "grey", panel_rect, border_radius=12)
            pygame.draw.rect(surface, "white", panel_rect, width=3, border_radius=12)

            header = title_font.render(f"Player {player_index + 1}", True, "white")
            surface.blit(header, (panel_rect.x + 24, panel_rect.y + 18))

            icon = PlayerCustomizationUI._preset_icons[self._closest_preset_hue(cfg.PLAYER_HUES[player_index])]
            icon_rect = icon.get_rect(center=(panel_rect.x + 185, panel_rect.y + 160))
            surface.blit(icon, icon_rect)

            swatch_color = pygame.Color(0)
            swatch_color.hsva = (cfg.PLAYER_HUES[player_index] * 360, 100, 100, 100)
            pygame.draw.circle(surface, swatch_color, (color_center_x, color_center_y), 18)
            pygame.draw.circle(surface, "white", (color_center_x, color_center_y), 18, 2)

            for color_button in panel["color_buttons"]:
                color_button.draw(surface)

            for bind_button in panel["bind_buttons"]:
                bind_button.draw(surface)

                direction = bind_button.meta["direction"]
                if self.editing_bind is not None and self.editing_bind == (player_index, direction):
                    text_label = "..."
                else:
                    direction_index = self.bind_index_by_direction[direction]
                    text_label = pygame.key.name(keybinds[player_index][direction_index])

                text_surf = font.render(text_label, True, "white")
                text_rect = text_surf.get_rect(center=(bind_button.rect.centerx, bind_button.rect.bottom + 16))
                surface.blit(text_surf, text_rect)

        for btn in self.buttons[-2:]:
            btn.draw(surface)

        cfg.LOCAL_PLAYERS = self.player_count

    def confirm(self):
        self.done = True

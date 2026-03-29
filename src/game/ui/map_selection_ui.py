# game/ui/map_selection_ui.py
import pygame
from game.assets import config as cfg
from game.assets import graphics
from game.systems import map_preview
from game.ui import button
from game.ui import settings_ui_elements
from game.objects.grid_preset import _presets

class MapSelectionUI:
    def __init__(self):
        self.map_names = list(_presets.keys()) + ["random"]
        self.index = self.map_names.index(cfg.SELECTED_MAP) if cfg.SELECTED_MAP in self.map_names else 0
        self.done = False
        self.title_font = pygame.font.SysFont(None, 54)
        self.random_obstacle_slider = settings_ui_elements.Slider(
            (cfg.DISPLAY_CENTER_X, cfg.DISPLAY_CENTER_Y + 320),
            (420, 24),
            cfg.RANDOM_MAP_OBSTACLE_CHANCE,
            0,
            100,
            label="Random Obstacle Chance",
            display_suffix="%",
        )

        images = graphics.images
        arrow_left_image  = graphics.resize_image(images["arrow_l"], 0.5)
        arrow_right_image = graphics.resize_image(images["arrow_r"], 0.5)

        self.buttons = [
            button.Button(
                arrow_left_image,
                (cfg.DISPLAY_CENTER_X - 500, cfg.DISPLAY_CENTER_Y),
                self.prev_map
            ),
            button.Button(
                arrow_right_image,
                (cfg.DISPLAY_CENTER_X + 500, cfg.DISPLAY_CENTER_Y),
                self.next_map
            ),
        ]

    @property
    def selected_map_name(self):
        return self.map_names[self.index]

    @property
    def selected_map_label(self):
        if self.selected_map_name == "random":
            return "Random"
        return self.selected_map_name.replace("_", " ").title()

    def prev_map(self):
        self.index = (self.index - 1) % len(self.map_names)

    def next_map(self):
        self.index = (self.index + 1) % len(self.map_names)

    def handle_events(self, events):
        for event in events:
            for b in self.buttons:
                b.handle_event(event)

            if self.selected_map_name == "random":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.random_obstacle_slider.container_rect.collidepoint(event.pos):
                        self.random_obstacle_slider.grabbed = True
                        self.random_obstacle_slider.move_slider(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.random_obstacle_slider.grabbed = False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.confirm:
                    self.confirm()

        if self.selected_map_name == "random":
            mouse_pos = pygame.mouse.get_pos()
            if self.random_obstacle_slider.grabbed:
                self.random_obstacle_slider.move_slider(mouse_pos)
                self.random_obstacle_slider.hover()
            else:
                self.random_obstacle_slider.hovered = self.random_obstacle_slider.container_rect.collidepoint(mouse_pos)
            cfg.RANDOM_MAP_OBSTACLE_CHANCE = self.random_obstacle_slider.get_value() / 100
        else:
            self.random_obstacle_slider.grabbed = False
            self.random_obstacle_slider.hovered = False

    def draw(self, surface):
        # let the preview system render the current selection
        scale = 0.5
        preview_obstacle_chance = cfg.RANDOM_MAP_OBSTACLE_CHANCE if self.selected_map_name == "random" else None
        
        rect = map_preview.get_preview_rect(self.selected_map_name, scale, obstacle_chance=preview_obstacle_chance)
        
        pos = (
            cfg.DISPLAY_CENTER_X - rect.w // 2,
            cfg.DISPLAY_CENTER_Y - rect.h // 2
            )

        title_surface = self.title_font.render(self.selected_map_label, True, "white")
        title_rect = title_surface.get_rect(center=(cfg.DISPLAY_CENTER_X, max(60, pos[1] - 55)))
        surface.blit(title_surface, title_rect)

        if self.selected_map_name != "random":
            map_preview.preview_map(self.selected_map_name, pos, surface, scale)
        else:
            random_icon = graphics.images["random_map_icon"]
            random_icon_scale = min(
                rect.w / random_icon.get_width(),
                rect.h / random_icon.get_height(),
            ) * 0.82
            random_icon = graphics.resize_image(random_icon, random_icon_scale)
            random_icon_rect = random_icon.get_rect(center=(cfg.DISPLAY_CENTER_X, cfg.DISPLAY_CENTER_Y - 20))
            surface.blit(random_icon, random_icon_rect)
            self.random_obstacle_slider.draw(surface)

        for b in self.buttons:
            b.draw(surface)

    def confirm(self):
        self.done = True

        cfg.SELECTED_MAP = self.selected_map_name

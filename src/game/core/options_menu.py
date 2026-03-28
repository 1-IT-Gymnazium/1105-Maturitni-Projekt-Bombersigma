import pygame
import game.assets.config as cfg
from game.assets import graphics, sounds
from game.systems import input
from game.ui import button, settings_ui_elements


def run():
    in_menu = True
    should_quit = False

    def return_to_main_menu():
        nonlocal in_menu
        in_menu = False

    def quit_game():
        nonlocal in_menu
        nonlocal should_quit
        in_menu = False
        should_quit = True

    images = graphics.images
    title_font = pygame.font.SysFont(None, 72)
    section_font = pygame.font.SysFont(None, 54)
    return_button = button.Button(
        graphics.resize_image(images["return_button"], 0.7),
        (cfg.DISPLAY_CENTER_X, cfg.DISPLAY_CENTER_Y + 260),
        return_to_main_menu,
    )

    sliders = {
        "master_volume": settings_ui_elements.Slider(
            (cfg.DISPLAY_CENTER_X/2, cfg.DISPLAY_CENTER_Y - 70),
            (360, 24),
            cfg.MASTER_VOLUME,
            0,
            100,
            label="Master Volume",
            display_suffix="%",
        ),
        "sfx_volume": settings_ui_elements.Slider(
            (cfg.DISPLAY_CENTER_X/2, cfg.DISPLAY_CENTER_Y + 70),
            (360, 24),
            cfg.SFX_VOLUME,
            0,
            100,
            label="SFX Volume",
            display_suffix="%",
        ),
        "music_volume": settings_ui_elements.Slider(
            (cfg.DISPLAY_CENTER_X/2, cfg.DISPLAY_CENTER_Y + 210),
            (360, 24),
            cfg.MUSIC_VOLUME,
            0,
            100,
            label="Music Volume",
            display_suffix="%",
        ),
        "grid_size": settings_ui_elements.Slider(
            (cfg.DISPLAY_CENTER_X + (cfg.DISPLAY_CENTER_X / 2), cfg.DISPLAY_CENTER_Y - 70),
            (360, 24),
            (cfg.GRID_WIDTH - 5) / (14 - 5),
            5,
            14,
            label="Game Grid Size",
        ),
        "powerup_drop_chance": settings_ui_elements.Slider(
            (cfg.DISPLAY_CENTER_X + (cfg.DISPLAY_CENTER_X / 2), cfg.DISPLAY_CENTER_Y + 70),
            (360, 24),
            cfg.POWER_UP_DROP_CHANCE,
            0,
            100,
            label="Powerup Drop Chance",
            display_suffix="%",
        )
    }

    while in_menu:
        cfg.CLOCK.tick(cfg.FPS)
        input.update_event_queue()
        mouse_pos = pygame.mouse.get_pos()

        for event in input._event_list:
            if event.type == pygame.QUIT:
                quit_game()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return_to_main_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for slider in sliders.values():
                    if slider.container_rect.collidepoint(event.pos):
                        slider.grabbed = True
                        sounds.play_sound("beep", "ui")
                        slider.move_slider(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                for slider in sliders.values():
                    slider.grabbed = False

            return_button.handle_event(event)

        for slider in sliders.values():
            if slider.grabbed:
                slider.move_slider(mouse_pos)
                slider.hover()
            else:
                slider.hovered = slider.container_rect.collidepoint(mouse_pos)

        sounds.set_master_volume(sliders["master_volume"].get_value() / 100)
        sounds.set_sfx_volume(sliders["sfx_volume"].get_value() / 100)
        sounds.set_music_volume(sliders["music_volume"].get_value() / 100)
        cfg.set_grid_size(int(round(sliders["grid_size"].get_value())))
        cfg.POWER_UP_DROP_CHANCE = sliders["powerup_drop_chance"].get_value() / 100

        cfg.DISPLAY.fill((35, 35, 35))
        title_surface = title_font.render("Options", True, "white")
        cfg.DISPLAY.blit(
            title_surface,
            title_surface.get_rect(center=(cfg.DISPLAY_CENTER_X, cfg.DISPLAY_CENTER_Y - 500)),
        )

        audio_surface = section_font.render("Audio", True, "white")
        game_settings_surface = section_font.render("Game Settings", True, "white")
        cfg.DISPLAY.blit(
            audio_surface,
            audio_surface.get_rect(center=(cfg.DISPLAY_CENTER_X / 2, cfg.DISPLAY_CENTER_Y - 210)),
        )
        cfg.DISPLAY.blit(
            game_settings_surface,
            game_settings_surface.get_rect(center=(cfg.DISPLAY_CENTER_X + (cfg.DISPLAY_CENTER_X / 2), cfg.DISPLAY_CENTER_Y - 210)),
        )

        for slider in sliders.values():
            slider.draw(cfg.DISPLAY)

        return_button.draw(cfg.DISPLAY)
        pygame.display.flip()

    return should_quit

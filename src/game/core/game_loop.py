import pygame
from concurrent.futures import ThreadPoolExecutor
from game.assets import config as cfg
from game.assets import graphics
from game.assets.graphics import images, shift_hue
from game.systems import input
from game.objects import grid, player
from game.systems import bomb_logic
from game.objects import powerup as powerup_module
from game.ui import player_hud, pause_menu, moving_element, button as btn
import random


def _preload_player_assets_async(players):
    """Precompute hue-shifted sprites/HUD icons off the main thread."""
    if not players:
        return

    def build(player_obj):
        try:
            # Preload board sprites
            preloaded = {
                "alive": shift_hue(player.states["alive"], player_obj.hue),
                "dead": shift_hue(player.states["dead"], player_obj.hue),
            }
            player_obj.preloaded_sprites = preloaded
            # Ensure current sprite uses cached version
            player_obj.sprite = preloaded.get(player_obj.state, player_obj.sprite)

            # Preload HUD icons if HUD exists
            if getattr(player_obj, "hud", None):
                player_obj.hud.preload_icons()
        except Exception:
            # Silently continue; runtime fallback will handle it
            pass

    # Cap workers to avoid excessive threads; at least 2
    workers = max(2, min(8, len(players)))
    executor = ThreadPoolExecutor(max_workers=workers)
    for p in players:
        executor.submit(build, p)
    # Do not wait; allow game to continue while preloading
    executor.shutdown(wait=False)

def run():
    running = True
    should_quit = False
    should_restart = False
    paused = False
    game_end = False
    game_end_sequence_started = False
    game_end_buttons_started = False
    game_end_buttons_visible = False
    game_end_text_finished_at = None

    def pause_game():
        nonlocal paused
        if paused == False:
            paused = True
        else:
            paused = False
    
    def go_back_to_menu():
        nonlocal running
        running = False

    def quit_game():
        nonlocal running
        running = False
        nonlocal should_quit
        should_quit = True

    def restart_game():
        nonlocal running, should_restart
        should_restart = True
        running = False

    #Pregenerate pause menu
    pm = pause_menu.Pause_menu(cfg.DISPLAY)
    
    #Pregenerate game end texts/images
    game_over_text = moving_element.MovingElement(images["game_over_text"], 
                                                  (cfg.DISPLAY_CENTER_X, -500),  #using 500 as a random number outside the rendering range
                                                  (cfg.DISPLAY_CENTER_X, 128),   #also the same reason for the other 500s in the other moving elements
                                                  600)
    winner_text = moving_element.MovingElement(images["win_text"], 
                                                  (cfg.DISPLAY_CENTER_X, cfg.DISPLAY.get_height()+500), 
                                                  (cfg.DISPLAY_CENTER_X, cfg.DISPLAY.get_height()-128), 
                                                  600)
    winner_arrow = moving_element.WinnerArrow(
    images["shiftable_arrow"],
    600
)

    button_scale = 0.4
    button_area_x = cfg.DISPLAY.get_width() - 200
    button_spacing = 200
    button_start_x = cfg.DISPLAY.get_width() + 400
    button_y = cfg.DISPLAY_CENTER_Y + 40

    play_again_button = moving_element.MovingButton(
        btn.Button(
            graphics.resize_image(images["again_button"], button_scale),
            (button_start_x, button_y),
            restart_game,
        ),
        (button_start_x, button_y),
        (button_area_x, button_y),
        600,
    )
    menu_button = moving_element.MovingButton(
        btn.Button(
            graphics.resize_image(images["menu_button"], button_scale),
            (button_start_x, button_y + button_spacing),
            go_back_to_menu,
        ),
        (button_start_x, button_y + button_spacing),
        (button_area_x, button_y + button_spacing),
        600,
    )
    game_end_buttons = [play_again_button, menu_button]

    #Create grid
    def build_match_grid():
        selected_preset = cfg.SELECTED_MAP if cfg.SELECTED_MAP != "random" else None
        obstacle_chance = cfg.RANDOM_MAP_OBSTACLE_CHANCE if cfg.SELECTED_MAP == "random" else None

        for _ in range(40):
            generated_grid = grid.create_grid(selected_preset, obstacle_chance=obstacle_chance)
            if len(grid.get_spawnable_tiles(generated_grid)) >= cfg.LOCAL_PLAYERS:
                return generated_grid

        generated_grid = grid.create_grid(selected_preset, obstacle_chance=obstacle_chance)
        candidate_tiles = generated_grid[:]
        random.shuffle(candidate_tiles)
        for tile in candidate_tiles[:cfg.LOCAL_PLAYERS]:
            grid.carve_spawn_lane(generated_grid, tile)
        return generated_grid

    game_grid = build_match_grid()
    bombs: list = []

    #stuff for game end animations
    match_winner = None
    winner_text_variants = {}
    winner_arrow_variants = {}

    #Create players
    player_list = []
    alive_players = []
    spawnable_tiles = grid.get_spawnable_tiles(game_grid)
    available_spawn_tiles = spawnable_tiles[:] if len(spawnable_tiles) >= cfg.LOCAL_PLAYERS else [
        tile for tile in game_grid if not tile.obstacle
    ]

    for p in range(cfg.LOCAL_PLAYERS):
        configured_hues = getattr(cfg, "PLAYER_HUES", [])
        random_hue = configured_hues[p] if p < len(configured_hues) else random.uniform(0, 1)
        if not available_spawn_tiles:
            available_spawn_tiles = [tile for tile in game_grid if not tile.obstacle]
        random_tile = random.choice(available_spawn_tiles)
        available_spawn_tiles.remove(random_tile)
        new_player = player.create_player(random_tile.pos, random_tile.grid_pos, random_hue, p)
        player_list.append(new_player)
        alive_players.append(new_player)
        player_list[p].hud = player_hud.Player_hud((cfg.PLAYER_HUD_MARGIN,cfg.PLAYER_HUD_MARGIN + (p * 250)),player_list[p])

    for p in player_list:
        winner_text_variants[p] = shift_hue(images["win_text"], p.hue)

    for p in player_list:
        winner_arrow_variants[p] = shift_hue(images["shiftable_arrow"], p.hue)

    # Preload hue-shifted sprites and HUD icons asynchronously to avoid runtime lag
    _preload_player_assets_async(player_list)

    #=====MAIN GAME LOOP======
    while running:
        cfg.CLOCK.tick(cfg.FPS)

        #=INPUT=
        input.update_event_queue()

        if input.check_for_quit():
            quit_game()

        if not game_end and input.check_for_esc():
            pause_game()


        #=LOGIC=
        if not paused and not game_end:
            #bombs
            killed_players_tt = bomb_logic.update_bombs(bombs, game_grid, player_list)

            #players
            for p in range(cfg.LOCAL_PLAYERS):
                player_state = getattr(player_list[p],"state")
                if player_state != "dead":
                    input.check_for_movement_input(player_list[p], game_grid)
                    bomb_logic.handle_bomb_input(player_list[p], bombs, game_grid)
                if player_list[p] in killed_players_tt:
                    alive_players.remove(player_list[p])
                    player_list[p].tod = pygame.time.get_ticks()
                    

            #game end check
            match len(alive_players):
                case 0:
                    winner_text.set_image(images["lose_text"])
                    winner_arrow_variants.clear() #clear to save memory since we won't be using them
                    game_end = True
                case 1:
                    match_winner = alive_players[0]
                    winner_text.set_image(winner_text_variants[match_winner])
                    winner_arrow.configure(
                        winner_text,
                        match_winner,
                        winner_arrow_variants[match_winner]
                    )
                    game_end = True
                case _:
                    pass

            if game_end and not game_end_sequence_started:
                game_end_sequence_started = True
                game_end_buttons_started = False
                game_end_buttons_visible = False
                game_end_text_finished_at = None
                game_over_text.reset()
                winner_text.reset()
                for moving_button in game_end_buttons:
                    moving_button.reset()


        #=RENDERING=
        #bg
        cfg.DISPLAY.fill((35, 35, 35)) 

        #grid
        grid.draw_grid(game_grid, cfg.DISPLAY) 

        #players
        for p in range(cfg.LOCAL_PLAYERS): 
            player_list[p].draw(cfg.DISPLAY)

        #bombs
        bomb_logic.draw_bombs(bombs, cfg.DISPLAY) 

        #pause menu
        if paused:
            pause_started = pygame.time.get_ticks()
            pause_action = pm.pause()
            pause_elapsed = pygame.time.get_ticks() - pause_started
            paused = False

            # keep cooldowns/effects from expiring during pause
            if pause_elapsed > 0:
                for p in player_list:
                    p.last_bomb_time += pause_elapsed
                    if hasattr(p, "effects"):
                        p.effects.apply_time_offset(pause_elapsed)

            if pause_action == "menu":
                running = False
            elif pause_action == "quit":
                quit_game()
            elif pause_action == "restart":
                should_restart = True
                running = False

            if not running:
                continue


        #Finishing animations when there is one or zero players alive
        if game_end:
            bombs.clear()

            dt = cfg.CLOCK.get_time()
            current_time = pygame.time.get_ticks()
            current_events = input.get_events()

            finished1 = game_over_text.update(dt)
            game_over_text.draw(cfg.DISPLAY)

            if finished1:
                if match_winner:
                    winner_arrow.update(dt)
                    winner_arrow.draw(cfg.DISPLAY)

                winner_text.update(dt)
                winner_text.draw(cfg.DISPLAY)

                if winner_text.finished and game_end_text_finished_at is None:
                    game_end_text_finished_at = current_time

                if (
                    game_end_text_finished_at is not None
                    and not game_end_buttons_started
                    and current_time - game_end_text_finished_at >= 500
                ):
                    game_end_buttons_started = True

                if game_end_buttons_started:
                    buttons_finished = True
                    for moving_button in game_end_buttons:
                        buttons_finished = moving_button.update(dt) and buttons_finished
                        moving_button.draw(cfg.DISPLAY)

                    if buttons_finished:
                        game_end_buttons_visible = True

                if game_end_buttons_visible:
                    for event in current_events:
                        for moving_button in game_end_buttons:
                            moving_button.handle_event(event)




        #render
        pygame.display.flip()
        




    if should_restart:
        return "restart"

    return should_quit

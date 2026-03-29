import pygame
from game.assets.graphics import images

# Initialize Pygame
pygame.init()

# Set up display
SCREEN_INFO = pygame.display.Info()
PHYSICAL_WIDTH = SCREEN_INFO.current_w
PHYSICAL_HEIGHT = SCREEN_INFO.current_h

# Set displaying to work on logical resolution
LOGICAL_WIDTH = 1920
LOGICAL_HEIGHT = 1080

SCREEN_WIDTH = LOGICAL_WIDTH
SCREEN_HEIGHT = LOGICAL_HEIGHT

DISPLAY = pygame.display.set_mode(
    (LOGICAL_WIDTH, LOGICAL_HEIGHT),
    pygame.FULLSCREEN | pygame.SCALED
)
DISPLAY_CENTER_X = DISPLAY.get_width() // 2
DISPLAY_CENTER_Y = DISPLAY.get_height() // 2

WINDOW_TITLE = "Bombersigma"
WINDOW_ICON_KEY = "icon"

# Set up clock
CLOCK = pygame.time.Clock()
FPS = 60


# Grid Settings
DEFAULT_GRID_SIZE = 8
GRID_WIDTH = DEFAULT_GRID_SIZE #defined in tiles
GRID_HEIGHT = DEFAULT_GRID_SIZE
MAX_BOARD_PIXELS = min(LOGICAL_WIDTH, LOGICAL_HEIGHT) - 56
TILE_SIZE = 128 #defined in pixels
BOARD_WIDTH = TILE_SIZE * GRID_WIDTH #defined in pixels
BOARD_HEIGHT = TILE_SIZE * GRID_HEIGHT #defined in pixels
GRID_X_POS = (SCREEN_WIDTH - BOARD_WIDTH) / 2 #pixels!
GRID_Y_POS = (SCREEN_HEIGHT - BOARD_HEIGHT) / 2 #YAYY PIXELS
PLAYER_HUD_SIZE = (325,200)
PLAYER_HUD_MARGIN = 20


# Local settings
LOCAL_PLAYERS = 1
PLAYER_HUES = [0.0]
DEFAULT_BOMB_COOLDOWN = 3000 #In ms
SELECTED_MAP = None

#Miscellanesus
TILE_OBSTACLE_CHANCE = 0.2
RANDOM_MAP_OBSTACLE_CHANCE = TILE_OBSTACLE_CHANCE
POWER_UP_DROP_CHANCE = 1      # % on destroyed obstacle (0 - 1)
SPEED_BOOST_MULTIPLIER = 1.5     # % faster
SPEED_BOOST_DURATION_MS = 5000   # 5 seconds
ARENA_SHRINK_DELAY_MS = 180000
ARENA_SHRINK_BASE_STEP_MS = 1000
ARENA_SHRINK_SPEED_MULTIPLIER = 1.0

#Audio
MASTER_VOLUME = 0.5
SFX_VOLUME = 0.5
MUSIC_VOLUME = 0.5


def apply_window_branding():
    pygame.display.set_caption(WINDOW_TITLE)

    icon = images.get(WINDOW_ICON_KEY)
    if icon is not None:
        pygame.display.set_icon(icon)


def refresh_grid_metrics():
    global TILE_SIZE, BOARD_WIDTH, BOARD_HEIGHT, GRID_X_POS, GRID_Y_POS

    largest_dimension = max(1, GRID_WIDTH, GRID_HEIGHT)
    TILE_SIZE = max(24, MAX_BOARD_PIXELS // largest_dimension)
    BOARD_WIDTH = TILE_SIZE * GRID_WIDTH
    BOARD_HEIGHT = TILE_SIZE * GRID_HEIGHT
    GRID_X_POS = (SCREEN_WIDTH - BOARD_WIDTH) / 2
    GRID_Y_POS = (SCREEN_HEIGHT - BOARD_HEIGHT) / 2


def set_grid_size(size: int):
    global GRID_WIDTH, GRID_HEIGHT

    clamped = max(5, min(14, int(size)))
    GRID_WIDTH = clamped
    GRID_HEIGHT = clamped
    refresh_grid_metrics()


refresh_grid_metrics()

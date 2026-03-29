import os
import random
import sys
import pygame

from game.assets import config as cfg

sounds = {}
music_tracks = {}
channels = {}
current_music_name = None

_SOUND_VOLUME_DEFAULT = 0.5
_MUSIC_VOLUME_DEFAULT = 1
_SFX_CHANNELS = ("ui", "gameplay", "explosion", "footsteps", "pickup", "b_place", "death", "warning", "shrink", "endgame")
_MIXER_CHANNEL_COUNT = 12


def initialize_audio():
    """
    Initialize mixer once.
    Call this before loading sounds.
    """
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()
    pygame.mixer.set_num_channels(_MIXER_CHANNEL_COUNT)

def _get_sounds_base_path() -> str:
    """
    Return the directory where the sound files live.

    - When running from source:   <project_root>/game/assets/audio
    - When running as a PyInstaller EXE:
        <_MEIPASS>/game/assets/audio
    """
    # Running from a PyInstaller bundle?
    if hasattr(sys, "_MEIPASS"):
        # In the EXE, we will bundle audio into game/assets/audio
        return os.path.join(sys._MEIPASS, "game", "assets", "audio")
    else:
        # Normal dev run: sounds.py lives in game/assets/
        # so audios are in game/assets/audio
        return os.path.join(os.path.dirname(__file__), "audio")


def initialize_sounds():
    """
    Load all short sound effects and register music tracks.
    """
    initialize_audio()

    audio_path = _get_sounds_base_path()

    path_to_sounds = os.path.join(audio_path,"sounds")
    path_to_music = os.path.join(audio_path,"music")

    # ---- sound effects ----
    sound_files = {
        "beep": "beep.wav",
        "bomb_place": "bomb_place.wav",
        "cheer": "cheer.wav",
        "explosion": "explosion.wav",
        "pickup": "pickup.wav",
        "sad_cheer": "sad_cheer.wav",
        "fuse": "fuse.wav",
        "metal_bang": "metal_bang.wav",
        "warning": "warning.wav",
    }
    for sound_type in ("step", "hurt"):
        for index in range(1, 7):
            sound_files[f"{sound_type}{index}"] = f"{sound_type}{index}.wav"

    for sound_name, filename in sound_files.items():
        full_path = os.path.join(path_to_sounds, filename)
        if os.path.exists(full_path):
            sounds[sound_name] = pygame.mixer.Sound(full_path)
            sounds[sound_name].set_volume(1.0)
        else:
            print(f"[SOUND WARNING] Missing sound file: {full_path}")

    # ---- music ----
    music_files = {
        "main_menu": "main_menu.wav",
        "game_music": "game_music.wav",
        "secret_music": "secret_music.mp3"
    }

    for track_name, filename in music_files.items():
        full_path = os.path.join(path_to_music, filename)
        if os.path.exists(full_path):
            music_tracks[track_name] = full_path
        else:
            print(f"[SOUND WARNING] Missing music file: {full_path}")

    # ---- channels ----
    channels["ui"] = pygame.mixer.Channel(0)
    channels["explosion"] = pygame.mixer.Channel(1)
    channels["gameplay"] = pygame.mixer.Channel(2)
    channels["footsteps"] = pygame.mixer.Channel(3)
    channels["pickup"] = pygame.mixer.Channel(4)
    channels["b_place"] = pygame.mixer.Channel(5)
    channels["death"] = pygame.mixer.Channel(6)
    channels["warning"] = pygame.mixer.Channel(7)
    channels["shrink"] = pygame.mixer.Channel(8)
    channels["endgame"] = pygame.mixer.Channel(9)
    _apply_volume_settings()


def _clamp_volume(volume):
    return max(0.0, min(1.0, volume))


def _apply_volume_settings():
    if pygame.mixer.get_init() is None:
        return

    effective_sfx_volume = _clamp_volume(cfg.MASTER_VOLUME) * _clamp_volume(cfg.SFX_VOLUME)
    effective_music_volume = _clamp_volume(cfg.MASTER_VOLUME) * _clamp_volume(cfg.MUSIC_VOLUME)

    for channel_name in _SFX_CHANNELS:
        if channel_name in channels:
            channels[channel_name].set_volume(effective_sfx_volume)

    pygame.mixer.music.set_volume(effective_music_volume)


def get_effective_sfx_volume():
    return _clamp_volume(cfg.MASTER_VOLUME) * _clamp_volume(cfg.SFX_VOLUME)


def play_sound(name, channel=None):
    sound = sounds.get(name)
    if sound is None:
        return None

    if channel is not None and channel in channels:
        channels[channel].play(sound)
        return channels[channel]
    elif "gameplay" in channels:
        channels["gameplay"].play(sound)
        return channels["gameplay"]
    else:
        return sound.play()


def play_looping_sound(name, loops=-1):
    sound = sounds.get(name)
    if sound is None:
        return None

    channel = pygame.mixer.find_channel()
    if channel is None:
        return None

    channel.set_volume(get_effective_sfx_volume())
    channel.play(sound, loops=loops)
    return channel


def play_sound_on_free_channel(name):
    sound = sounds.get(name)
    if sound is None or pygame.mixer.get_init() is None:
        return None

    channel = pygame.mixer.find_channel()
    if channel is None:
        return None

    channel.set_volume(get_effective_sfx_volume())
    channel.play(sound)
    return channel


def is_channel_busy(channel):
    return channel in channels and channels[channel].get_busy()


def play_random_sound_type(sound_type, channel=None):
    sound_choices = [name for name in sounds if name.startswith(sound_type)]
    if not sound_choices:
        return

    if channel is not None and channel in channels:
        if is_channel_busy(channel):
            return
        channels[channel].play(sounds[random.choice(sound_choices)])
        return

    play_sound(random.choice(sound_choices))


def stop_sound_channel(channel):
    if channel in channels:
        channels[channel].stop()


def stop_all_sounds():
    if pygame.mixer.get_init() is None:
        return

    for channel in channels.values():
        channel.stop()


def stop_sound_channels(channel_names):
    for channel_name in channel_names:
        stop_sound_channel(channel_name)


def set_master_volume(volume):
    cfg.MASTER_VOLUME = _clamp_volume(volume)
    _apply_volume_settings()


def set_all_sound_volumes(volume):
    set_sfx_volume(volume)


def set_sfx_volume(volume):
    cfg.SFX_VOLUME = _clamp_volume(volume)
    _apply_volume_settings()


def play_music(name, loops=-1, fade_ms=300):
    global current_music_name

    track_path = music_tracks.get(name)
    if track_path is None:
        return

    if current_music_name == name and pygame.mixer.music.get_busy():
        return

    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(track_path)
        _apply_volume_settings()
        pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
        current_music_name = name
    except pygame.error as e:
        print(f"[SOUND ERROR] Failed to play music '{name}': {e}")


def stop_music(fade_ms=300):
    global current_music_name
    pygame.mixer.music.fadeout(fade_ms)
    current_music_name = None


def set_music_volume(volume):
    cfg.MUSIC_VOLUME = _clamp_volume(volume)
    _apply_volume_settings()


def get_default_sound_volume():
    return _SOUND_VOLUME_DEFAULT


def get_default_music_volume():
    return _MUSIC_VOLUME_DEFAULT

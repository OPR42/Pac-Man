from pathlib import Path
import random

import pyray as pr

from pacman.base.models import LogEvent
from pacman.core import Core

JUKEBOX_EXTENSIONS = (".ogg", ".mp3", ".flac", ".wav")
SOUND_EXTENSIONS = (".wav", ".ogg", ".mp3", ".flac")


class Audio:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.audio_path = (
            Path(__file__).resolve().parent.parent / "assets" / "audio")
        self.jukebox_music: pr.Music | None = None
        self.jukebox_active: bool = False
        self.mute: bool = False
        self.master_volume: float = self.core.config.master_volume / 100
        self.sound_volume: float = self.core.config.sound_volume / 100
        self.music_volume: float = self.core.config.music_volume / 100
        self.sounds: dict[str, pr.Sound] = {}
        self.ingame_tracks: list[Path] = []
        self.ingame_current: Path | None = None
        self.ingame_last: Path | None = None
        self.ingame_music: pr.Music | None = None
        self.ingame_active: bool = False
        self.ingame_current_artist: str = ""
        self.ingame_current_title: str = ""
        self.available: bool = False

    def launch(self) -> None:
        self.available = False
        try:
            pr.init_audio_device()
            self.available = pr.is_audio_device_ready()
        except Exception as e:
            self.core._emit(LogEvent(
                source="  audio ",
                type="warning",
                message=f"Audio initialization failed: {e}"
            ))
        if not self.available:
            return
        pr.set_audio_stream_buffer_size_default(32768)
        pr.set_master_volume(self.master_volume)
        self.ingame_load_tracks()
        self.core._emit(
            LogEvent(source=" audio  ", type="info",
                     message="Audio Device ", text_var="activated"))

    def toggle_mute(self) -> None:
        if not self.available:
            return
        lex = self.core.lexicon

        if self.mute:
            self.mute = False
            pr.set_master_volume(self.master_volume)
            self.graphics.show_audio_volume(label=lex("AUD_Volume"),
                                            volume=self.master_volume,
                                            begin=True)

        else:
            self.mute = True
            pr.set_master_volume(0)
            self.graphics.show_audio_volume(label=lex("AUD_Mute"),
                                            volume=0, begin=True, mute=True)

    def set_audio_volume(self, channel: str, delta: float = 0.0) -> None:
        if not self.available:
            return
        if not channel:
            return

        lex = self.core.lexicon

        if channel == "master":
            volume = max(0.0, min(1.0, self.master_volume + delta))
            pr.set_master_volume(volume)
            self.master_volume = volume
            self.graphics.show_audio_volume(label=lex("AUD_Volume"),
                                            volume=volume, begin=True)

        elif channel == "sounds":
            volume = max(0.0, min(1.0, self.sound_volume + delta))
            self.sound_volume = volume
            for sound in self.sounds.values():
                pr.set_sound_volume(sound, volume)
            self.graphics.show_audio_volume(label=lex("AUD_Sound"),
                                            volume=volume, begin=True)

        elif channel == "music":
            volume = max(0.0, min(1.0, self.music_volume + delta))
            self.music_volume = volume
            self.jukebox_volume(volume)
            self.ingame_volume(volume)
            self.graphics.show_audio_volume(label=lex("AUD_Music"),
                                            volume=volume, begin=True)

    def fade(self, factor: float) -> None:
        if not self.available:
            return
        factor = max(0.0, min(1.0, factor))
        if not self.mute:
            pr.set_master_volume(self.master_volume * factor)

    def restore_volume(self) -> None:
        if not self.available:
            return
        if not self.mute:
            pr.set_master_volume(self.master_volume)

    def get_audio_volume(self) -> tuple[float, float, float]:
        if not self.available:
            return (0.0, 0.0, 0.0)
        return (self.master_volume, self.sound_volume, self.music_volume)

    def get_master_volume(self) -> float:
        if not self.available:
            return 0.0
        return self.master_volume

    def get_sounds_volume(self) -> float:
        if not self.available:
            return 0.0
        return self.sound_volume

    def get_music_volume(self) -> float:
        if not self.available:
            return 0.0
        return self.music_volume

    def jukebox_load(self, name: str) -> bool:
        if not self.available:
            return False
        if not self.audio_path.is_dir():
            self.core._emit(
                LogEvent(source=" audio  ", type="warning",
                         message="Audio repository not found: ",
                         text_var=str(self.audio_path)))
            return False

        requested = Path(name)

        if requested.suffix:
            candidate = self.audio_path / requested.name
            path = candidate if candidate.is_file() else None

        else:
            path = next(
                (self.audio_path / f"{name}{extension}"
                 for extension in JUKEBOX_EXTENSIONS
                 if (self.audio_path / f"{name}{extension}").is_file()),
                None)

        if path is None:
            self.core._emit(
                LogEvent(source=" audio  ", type="info",
                         message="Audio track not found in repository: ",
                         text_var=name))
            return False

        if self.jukebox_music is not None:
            self.jukebox_unload()

        self.jukebox_music = pr.load_music_stream(str(path))
        track_info = ""
        if self.jukebox_music is not None:
            title, artist = self._mp3_metadata(path)
            if artist and title:
                track_info = f"{artist} — {title}"
            elif title:
                track_info = title
            self.ingame_current_artist = artist
            self.ingame_current_title = title
        self.jukebox_music.looping = True
        pr.set_music_volume(self.jukebox_music, self.music_volume)
        self.core._emit(
            LogEvent(source=" audio  ", type="info",
                     message="Audio track loaded on jukebox: ",
                     text_var=f"{path}",
                     message_end=f"\n{track_info}"))

        return True

    def jukebox_play(self) -> None:
        if not self.available:
            return
        if self.jukebox_music is None:
            return

        pr.play_music_stream(self.jukebox_music)
        pr.set_music_volume(self.jukebox_music, self.music_volume)
        self.jukebox_active = True
        self.core._emit(
            LogEvent(source=" audio  ", type="info",
                     message="Jukebox playing"))

    def jukebox_update(self) -> None:
        if not self.available:
            return
        if self.jukebox_music is None or not self.jukebox_active:
            return

        pr.update_music_stream(self.jukebox_music)

    def jukebox_volume(self, volume: float) -> None:
        if not self.available:
            return
        self.music_volume = max(0.0, min(1.0, volume))

        if self.jukebox_music is not None:
            pr.set_music_volume(self.jukebox_music, self.music_volume)

    def jukebox_fade_out(self, factor: float) -> None:
        if not self.available:
            return
        factor = max(0.0, min(1.0, factor))

        if self.jukebox_music is not None:
            pr.set_music_volume(self.jukebox_music,
                                self.music_volume * factor)

    def jukebox_stop(self) -> None:
        if not self.available:
            return
        if self.jukebox_music is None:
            return

        pr.stop_music_stream(self.jukebox_music)
        self.jukebox_active = False
        self.core._emit(
            LogEvent(source=" audio  ", type="info",
                     message="Jukebox stopped"))

    def jukebox_unload(self) -> None:
        if self.jukebox_music is None:
            return

        if self.jukebox_active:
            self.jukebox_stop()

        pr.unload_music_stream(self.jukebox_music)
        self.jukebox_music = None

    def close(self) -> None:
        self.jukebox_unload()
        self.ingame_stop()
        self.sounds_unload_all()

        if pr.is_audio_device_ready():
            pr.close_audio_device()

    def sound_load(self, name: str) -> bool:
        if not self.available:
            return False
        if name in self.sounds:
            return True

        if not self.audio_path.is_dir():
            return False

        requested = Path(name)

        if requested.suffix:
            candidate = self.audio_path / requested.name
            path = candidate if candidate.is_file() else None
        else:
            path = next((self.audio_path / f"{name}{extension}"
                         for extension in SOUND_EXTENSIONS
                         if (self.audio_path / f"{name}{extension}").is_file()
                         ), None)

        if path is None:
            self.core._emit(
                LogEvent(source=" audio  ", type="info",
                         message="Audio sound not found in repository: ",
                         text_var=name))
            return False

        sound = pr.load_sound(str(path))
        pr.set_sound_volume(sound, self.sound_volume)
        self.sounds[name] = sound

        self.core._emit(
            LogEvent(source=" audio  ", type="info",
                     message="Audio sound loaded: ", text_var=str(path)))

        return True

    def sound_play(self, name: str) -> None:
        if not self.available:
            return
        sound = self.sounds.get(name)

        if sound is None:
            if not self.sound_load(name):
                return
            sound = self.sounds.get(name)

        if sound is None:
            return

        pr.set_sound_volume(sound, self.sound_volume)
        pr.play_sound(sound)

    def sound_stop(self, name: str) -> None:
        if not self.available:
            return
        sound = self.sounds.get(name)

        if sound is not None:
            pr.stop_sound(sound)

    def sound_unload(self, name: str) -> None:
        sound = self.sounds.pop(name, None)
        if not self.available:
            return
        if sound is not None:
            pr.unload_sound(sound)

    def sounds_unload_all(self) -> None:
        for sound in self.sounds.values():
            pr.unload_sound(sound)

        self.sounds.clear()

    def ingame_volume(self, volume: float) -> None:
        if not self.available:
            return
        self.music_volume = max(0.0, min(1.0, volume))

        if self.ingame_music is not None:
            pr.set_music_volume(self.ingame_music, self.music_volume)

    def ingame_load_tracks(self) -> None:
        if not self.available:
            return
        self.ingame_tracks = sorted(
            path for path in self.audio_path.glob("ingame_*.mp3")
            if path.is_file())

        if not self.ingame_tracks:
            self.core._emit(
                LogEvent(source=" audio  ", type="warning",
                         message="No ingame music found"))

    def _ingame_choose_next(self) -> Path | None:
        if not self.available:
            return None
        if not self.ingame_tracks:
            return None

        if len(self.ingame_tracks) == 1:
            return self.ingame_tracks[0]

        candidates = [track for track in self.ingame_tracks
                      if track != self.ingame_last]

        return random.choice(candidates)

    def ingame_play_next(self) -> None:
        if not self.available:
            return
        next_track = self._ingame_choose_next()

        if next_track is None:
            return

        if self.ingame_music is not None:
            pr.unload_music_stream(self.ingame_music)

        self.ingame_music = pr.load_music_stream(str(next_track))
        self.ingame_music.looping = False
        pr.set_music_volume(self.ingame_music, self.music_volume)
        pr.play_music_stream(self.ingame_music)
        self.ingame_last = next_track
        self.ingame_current = next_track
        title, artist = self._mp3_metadata(self.ingame_current)
        if artist and title:
            track_info = f"{artist} — {title}"
        elif title:
            track_info = title
        else:
            track_info = ""
        self.ingame_current_artist = artist
        self.ingame_current_title = title
        self.ingame_active = True
        self.core._emit(
            LogEvent(source=" audio  ", type="info",
                     message="Ingame music playing: ",
                     text_var=next_track.name,
                     message_end=f"\n{track_info}"))

    def ingame_update(self) -> None:
        if not self.available:
            return
        if not self.ingame_active:
            return

        if self.ingame_music is None:
            self.ingame_play_next()
            return

        pr.update_music_stream(self.ingame_music)

        if not pr.is_music_stream_playing(self.ingame_music):
            self.ingame_play_next()

    def ingame_start(self) -> None:
        if not self.available:
            return
        if self.ingame_active:
            return

        self.ingame_play_next()

    def ingame_stop(self) -> None:
        if not self.available:
            return
        if self.ingame_music is not None:
            pr.stop_music_stream(self.ingame_music)
            pr.unload_music_stream(self.ingame_music)
            self.ingame_music = None

        self.ingame_current = None
        self.ingame_active = False

    def _mp3_metadata(self, path: Path) -> tuple[str, str]:
        """Read title and artist from MP3 ID3v2 tags."""
        if not self.available:
            return ("", "")
        title = path.stem
        artist = ""
        try:
            with path.open("rb") as file:
                header = file.read(10)
                if len(header) != 10 or header[:3] != b"ID3":
                    return title, artist
                version = header[3]
                if version not in (3, 4):
                    return title, artist
                tag_size = (
                    ((header[6] & 0x7f) << 21) | ((header[7] & 0x7f) << 14)
                    | ((header[8] & 0x7f) << 7) | (header[9] & 0x7f))
                data = file.read(tag_size)
                offset = 0
                while offset + 10 <= len(data):
                    frame_id = data[offset:offset + 4]
                    if frame_id == b"\x00\x00\x00\x00":
                        break
                    if version == 4:
                        frame_size = (((data[offset + 4] & 0x7f) << 21)
                                      | ((data[offset + 5] & 0x7f) << 14)
                                      | ((data[offset + 6] & 0x7f) << 7)
                                      | (data[offset + 7] & 0x7f))
                    else:
                        frame_size = int.from_bytes(
                            data[offset + 4:offset + 8], byteorder="big")
                    if frame_size <= 0:
                        break
                    frame_start = offset + 10
                    frame_end = frame_start + frame_size
                    if frame_end > len(data):
                        break
                    if frame_id in (b"TIT2", b"TPE1"):
                        value = self._decode_id3_text(
                            data[frame_start:frame_end])
                        if frame_id == b"TIT2" and value:
                            title = value
                        elif frame_id == b"TPE1" and value:
                            artist = value
                    if title != path.stem and artist:
                        break
                    offset = frame_end
        except OSError:
            pass

        return title, artist

    @staticmethod
    def _decode_id3_text(data: bytes) -> str:
        """Decode an ID3 text frame."""
        if not data:
            return ""

        encoding = data[0]
        content = data[1:]

        try:
            if encoding == 0:
                text = content.decode("latin-1")
            elif encoding == 1:
                text = content.decode("utf-16")
            elif encoding == 2:
                text = content.decode("utf-16-be")
            elif encoding == 3:
                text = content.decode("utf-8")
            else:
                return ""
        except UnicodeDecodeError:
            return ""

        return text.rstrip("\x00").strip()

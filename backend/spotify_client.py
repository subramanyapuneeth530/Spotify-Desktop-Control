import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

SCOPES = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "playlist-read-private "
    "playlist-modify-private "
    "playlist-modify-public "
)

if not (CLIENT_ID and CLIENT_SECRET and REDIRECT_URI):
    raise RuntimeError("Missing Spotify credentials in .env")


class SpotifyClient:
    def __init__(self):
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPES,
            cache_path=str(BASE_DIR / ".spotify_token_cache"),  # reuse login
            show_dialog=False,
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    # ---------- Playback state & basic controls ----------

    def get_playback_state(self):
        return self.sp.current_playback()

    def play(self):
        self.sp.start_playback()

    def pause(self):
        self.sp.pause_playback()

    def next(self):
        self.sp.next_track()

    def previous(self):
        self.sp.previous_track()

    def seek(self, position_ms: int):
        self.sp.seek_track(position_ms)

    # ---------- Volume / shuffle / repeat ----------

    def set_volume(self, volume_percent: int):
        volume_percent = max(0, min(100, int(volume_percent)))
        self.sp.volume(volume_percent)

    def set_shuffle(self, state: bool):
        self.sp.shuffle(state)

    def set_repeat(self, mode: str):
        # mode must be "off", "track", or "context"
        if mode not in ("off", "track", "context"):
            mode = "off"
        self.sp.repeat(mode)

    # ---------- Devices ----------

    def get_devices(self):
        return self.sp.devices()

    def transfer_playback(self, device_id: str):
        # force_play=False so it just switches device
        self.sp.transfer_playback(device_id=device_id, force_play=False)

    # ---------- Playlists ----------

    def get_playlists(self, limit: int = 50, offset: int = 0):
        return self.sp.current_user_playlists(limit=limit, offset=offset)

    def get_playlist_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0):
        return self.sp.playlist_items(playlist_id, limit=limit, offset=offset)

    def play_playlist(self, playlist_id: str, device_id: Optional[str] = None):
        playlist_uri = f"spotify:playlist:{playlist_id}"
        if device_id:
            self.sp.start_playback(device_id=device_id, context_uri=playlist_uri)
        else:
            self.sp.start_playback(context_uri=playlist_uri)

    def add_track_to_playlist(self, playlist_id: str, track_uri: str):
        # track_uri like "spotify:track:xxxx"
        self.sp.playlist_add_items(playlist_id, [track_uri])

    def remove_track_from_playlist(self, playlist_id: str, track_uri: str):
        self.sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])

    # ---------- Queue ----------

    def get_queue(self):
        """
        Returns Spotify queue (currently_playing + queue list).
        """
        return self.sp.queue()

    def clear_queue(self):
        """
        Spotify Web API does NOT support clearing the entire queue.
        We raise an error so the frontend can show a message.
        """
        raise RuntimeError("Clearing the queue is not supported by the Spotify API.")

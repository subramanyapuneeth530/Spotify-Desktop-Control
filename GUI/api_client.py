import requests

BASE_URL = "http://127.0.0.1:8000"


# ---------- Playback state & basic controls ----------

def get_playback_state():
    resp = requests.get(f"{BASE_URL}/playback/state", timeout=5)
    resp.raise_for_status()
    return resp.json()


def play():
    resp = requests.post(f"{BASE_URL}/playback/play", timeout=5)
    resp.raise_for_status()


def pause():
    resp = requests.post(f"{BASE_URL}/playback/pause", timeout=5)
    resp.raise_for_status()


def next_track():
    resp = requests.post(f"{BASE_URL}/playback/next", timeout=5)
    resp.raise_for_status()


def previous_track():
    resp = requests.post(f"{BASE_URL}/playback/previous", timeout=5)
    resp.raise_for_status()


def seek(position_ms: int):
    resp = requests.post(
        f"{BASE_URL}/playback/seek",
        json={"position_ms": int(position_ms)},
        timeout=5,
    )
    resp.raise_for_status()


# ---------- Volume / shuffle / repeat ----------

def set_volume(volume_percent: int):
    resp = requests.post(
        f"{BASE_URL}/playback/volume",
        json={"volume_percent": int(volume_percent)},
        timeout=5,
    )
    resp.raise_for_status()


def set_shuffle(state: bool):
    resp = requests.post(
        f"{BASE_URL}/playback/shuffle",
        json={"state": bool(state)},
        timeout=5,
    )
    resp.raise_for_status()


def set_repeat(mode: str):
    resp = requests.post(
        f"{BASE_URL}/playback/repeat",
        json={"mode": mode},
        timeout=5,
    )
    resp.raise_for_status()


# ---------- Devices ----------

def get_devices():
    resp = requests.get(f"{BASE_URL}/devices", timeout=5)
    resp.raise_for_status()
    return resp.json()


def transfer_playback(device_id: str):
    resp = requests.post(
        f"{BASE_URL}/devices/transfer",
        json={"device_id": device_id},
        timeout=5,
    )
    resp.raise_for_status()


# ---------- Playlists ----------

def get_playlists():
    resp = requests.get(f"{BASE_URL}/playlists", timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_playlist_tracks(playlist_id: str):
    resp = requests.get(
        f"{BASE_URL}/playlists/{playlist_id}/tracks",
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def play_playlist(playlist_id: str, device_id: str = None):
    payload = {"playlist_id": playlist_id, "device_id": device_id}
    resp = requests.post(f"{BASE_URL}/playlists/play", json=payload, timeout=10)
    resp.raise_for_status()


def add_track_to_playlist(playlist_id: str, track_uri: str):
    resp = requests.post(
        f"{BASE_URL}/playlists/{playlist_id}/add_track",
        json={"track_uri": track_uri},
        timeout=10,
    )
    resp.raise_for_status()


def remove_track_from_playlist(playlist_id: str, track_uri: str):
    resp = requests.post(
        f"{BASE_URL}/playlists/{playlist_id}/remove_track",
        json={"track_uri": track_uri},
        timeout=10,
    )
    resp.raise_for_status()

# ---------- Queue ----------

def get_queue():
    resp = requests.get(f"{BASE_URL}/queue", timeout=5)
    resp.raise_for_status()
    return resp.json()


def clear_queue():
    resp = requests.post(f"{BASE_URL}/queue/clear", timeout=5)
    resp.raise_for_status()

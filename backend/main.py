from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from spotify_client import SpotifyClient

app = FastAPI()
sp_client = SpotifyClient()


# ---------- Request models ----------

class SeekRequest(BaseModel):
    position_ms: int


class VolumeRequest(BaseModel):
    volume_percent: int


class ShuffleRequest(BaseModel):
    state: bool


class RepeatRequest(BaseModel):
    mode: str  # "off" | "track" | "context"


class DeviceTransferRequest(BaseModel):
    device_id: str


class PlaylistPlayRequest(BaseModel):
    playlist_id: str
    device_id: Optional[str] = None


class TrackModifyRequest(BaseModel):
    track_uri: str


# ---------- Playback state & basic controls ----------

@app.get("/playback/state")
def get_playback_state():
    try:
        playback = sp_client.get_playback_state()
        return playback or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playback/play")
def play():
    try:
        sp_client.play()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playback/pause")
def pause():
    try:
        sp_client.pause()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playback/next")
def next_track():
    try:
        sp_client.next()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playback/previous")
def previous_track():
    try:
        sp_client.previous()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playback/seek")
def seek(req: SeekRequest):
    try:
        sp_client.seek(req.position_ms)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Volume / shuffle / repeat ----------

@app.post("/playback/volume")
def set_volume(req: VolumeRequest):
    try:
        sp_client.set_volume(req.volume_percent)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playback/shuffle")
def set_shuffle(req: ShuffleRequest):
    try:
        sp_client.set_shuffle(req.state)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playback/repeat")
def set_repeat(req: RepeatRequest):
    try:
        sp_client.set_repeat(req.mode)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Devices ----------

@app.get("/devices")
def get_devices():
    try:
        raw = sp_client.get_devices()
        devices = raw.get("devices", []) if raw else []
        simple = []
        for d in devices:
            if not d:
                continue
            simple.append(
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "type": d.get("type"),
                    "is_active": d.get("is_active"),
                    "volume_percent": d.get("volume_percent"),
                }
            )
        return {"devices": simple}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/devices/transfer")
def transfer_playback(req: DeviceTransferRequest):
    try:
        sp_client.transfer_playback(req.device_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Playlists ----------

@app.get("/playlists")
def get_playlists():
    try:
        data = sp_client.get_playlists(limit=50)
        items = data.get("items", []) if data else []
        playlists = []
        for pl in items:
            if not pl:
                continue
            playlists.append(
                {
                    "id": pl.get("id"),
                    "name": pl.get("name"),
                    "tracks_total": (pl.get("tracks") or {}).get("total"),
                    "external_url": (pl.get("external_urls") or {}).get("spotify"),
                }
            )
        return {"playlists": playlists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playlists/{playlist_id}/tracks")
def get_playlist_tracks(playlist_id: str):
    try:
        data = sp_client.get_playlist_tracks(playlist_id, limit=100)
        items = data.get("items", []) if data else []
        tracks = []
        for it in items:
            tr = it.get("track") if it else None
            if not tr:
                continue
            artists = ", ".join(a.get("name", "") for a in (tr.get("artists") or []))
            tracks.append(
                {
                    "id": tr.get("id"),
                    "name": tr.get("name"),
                    "artists": artists,
                    "uri": tr.get("uri"),
                }
            )
        return {"tracks": tracks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playlists/play")
def play_playlist(req: PlaylistPlayRequest):
    try:
        sp_client.play_playlist(req.playlist_id, req.device_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playlists/{playlist_id}/add_track")
def add_track_to_playlist(playlist_id: str, req: TrackModifyRequest):
    try:
        sp_client.add_track_to_playlist(playlist_id, req.track_uri)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playlists/{playlist_id}/remove_track")
def remove_track_from_playlist(playlist_id: str, req: TrackModifyRequest):
    try:
        sp_client.remove_track_from_playlist(playlist_id, req.track_uri)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Queue ----------

@app.get("/queue")
def get_queue():
    try:
        data = sp_client.get_queue()
        if not data:
            return {"queue": []}

        queue_items = data.get("queue", []) or []
        tracks = []
        for tr in queue_items:
            if not tr:
                continue
            artists = ", ".join(a.get("name", "") for a in (tr.get("artists") or []))
            tracks.append(
                {
                    "id": tr.get("id"),
                    "name": tr.get("name"),
                    "artists": artists,
                    "uri": tr.get("uri"),
                }
            )
        return {"queue": tracks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queue/clear")
def clear_queue():
    """
    This will just return an error saying it's not supported,
    because Spotify doesn't expose a clear-queue endpoint.
    """
    try:
        sp_client.clear_queue()
        return {"status": "ok"}
    except Exception as e:
        # 400 = client-side limitation, not server crash
        raise HTTPException(status_code=400, detail=str(e))

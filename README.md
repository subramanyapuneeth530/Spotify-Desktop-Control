# Spotify Desktop Control (FastAPI + PySide6)

A **work-in-progress desktop controller for Spotify**.

This project is split into:
- a **FastAPI backend** that authenticates with Spotify and exposes simple HTTP endpoints, and
- a **PySide6 desktop GUI** that calls those endpoints to control playback, devices, playlists, and queue.

> ⚠️ **Project status:** not final — expected to change and grow. The README is written to stay useful even as features are upgraded.

---

## What this project does

- Controls Spotify playback (play/pause/next/previous/seek/volume)
- Toggles shuffle + repeat
- Lists available Spotify devices and transfers playback to a selected device
- Lists your playlists and lets you play a playlist
- Shows playlist tracks and supports add/remove track operations
- Shows your current queue (note: clearing queue is limited by Spotify API)

---

## How it works (high level)

1. **Backend (`backend/`)** handles Spotify OAuth using **Spotipy** and keeps a token cache.
2. The backend exposes REST endpoints like `/playback/play`, `/devices`, `/playlists`, etc.
3. **GUI (`GUI/`)** uses an `api_client.py` module to call the backend and render controls in a PySide6 window.
4. Spotify actions affect your **currently active Spotify device** (desktop app/web player/mobile).

> If nothing is playing on Spotify, some actions may fail until you start playback on any device once.

---

## Repo structure (current)



<img width="799" height="749" alt="image" src="https://github.com/user-attachments/assets/94dc5418-9845-4f22-948d-bbadd8add803" />

preview video https://drive.google.com/file/d/1E66S_lMVRq_VChGsQv-voaRVJM5P58-x/view?usp=drive_link 

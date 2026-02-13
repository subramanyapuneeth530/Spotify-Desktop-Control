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
```
├── backend/
│ ├── main.py # FastAPI routes (HTTP API)
│ ├── spotify_client.py # Spotify OAuth + Spotipy wrapper
│ ├── .env # (local) Spotify credentials ❌ don't commit
│ └── .spotify_token_cache # (local) OAuth token cache ❌ don't commit
│
└── GUI/
├── player.py # PySide6 desktop UI
└── api_client.py # HTTP client for backend
```

## Requirements

- **Python 3.9+**
- A Spotify account
- A Spotify Developer App (Client ID / Client Secret)

Python packages (installed via pip):
- `fastapi`
- `uvicorn`
- `pydantic`
- `spotipy`
- `python-dotenv`
- `requests`
- `PySide6`

---

## Spotify Developer App setup

1. Go to the Spotify Developer Dashboard and create an app.
2. Copy your:
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
3. In the app settings, add a Redirect URI matching your `.env` value, for example:
   - `http://localhost:8888/callback`

> Redirect URI **must match exactly** or login will fail.

---

## Environment variables

Create a file at:

`backend/.env`

Example:

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

## Install & run

This project consists of **two parts** that must be running together:

1. A **FastAPI backend** (handles Spotify authentication and API calls)
2. A **PySide6 desktop GUI** (user interface)

Both are written in Python and can be run using the same virtual environment.

---

## Prerequisites

- **Python 3.9 or higher**
- A **Spotify account**
- A **Spotify Developer App** with:
  - Client ID
  - Client Secret
  - Redirect URI configured

---

## 1) Clone the repository

```
git clone https://github.com/your-username/spotify-desktop-control.git
cd spotify-desktop-control
```

## 2) (Recommended) Create a virtual environment

Using a virtual environment keeps project dependencies isolated and avoids conflicts with other Python projects.

From the project root:

```
python -m venv venv
```
Activate the virtual environment:
venv\Scripts\activate

## 3) Install dependencies
At this stage, the project uses a single Python environment for both the backend and the GUI.

Install all required packages:
```
pip install fastapi uvicorn pydantic spotipy python-dotenv requests PySide6

```

## 4) Run the application (backend + GUI)

You do **not** need to start the backend manually.

The FastAPI backend is **started automatically** when the GUI application (`player.py`) is launched.

From the project root (with your virtual environment activated):

```
cd GUI
python player.py
```
What happens when you run this command:
- The FastAPI backend is started programmatically in the background
- Spotify OAuth authentication is handled automatically
- The PySide6 desktop GUI window opens
- The GUI communicates with the backend internally over HTTP

## First run behavior

On the first run:
- A browser window may open asking you to log in to Spotify
- You will be asked to authorize the application
- A local Spotify token cache file will be created automatically
- This only needs to happen once unless the token expires or is deleted.

## Runtime notes

Spotify playback controls require an active Spotify device
- If nothing responds, open Spotify on any device and start playing a track once
The backend runs locally and is tied to the GUI lifecycle
- Closing the GUI will also stop the backend
No additional servers or terminals are required

## Stopping the application

- Simply close the GUI window to shut down the application completely
- No background processes will continue running

## Troubleshooting
Application opens but playback controls do not work
- Ensure Spotify is open on at least one device
- Start playback manually once before using the controls

Spotify login / authorization fails
- Verify your credentials in backend/.env
- Ensure SPOTIFY_REDIRECT_URI matches exactly in the Spotify Developer Dashboard

Application fails to start
- Confirm your virtual environment is activated
- Make sure all dependencies are installed
- Run the application from the GUI/ directory

## Project status

This project is a work in progress and is expected to evolve.

The current design prioritizes:
- ease of use (single command to run everything)
- simplicity over deployment complexity
- flexibility for future upgrades

Future improvements may include:
- better startup/shutdown handling
- background service mode
- executable builds for non-technical users
- improved error reporting


## preview of the GUI:
![screen_record_1 - frame at 0m0s](https://github.com/user-attachments/assets/3ec8589e-e508-4c99-857c-0e9705fbafbb)


## working demo:
[https://drive.google.com/file/d/1E66S_lMVRq_VChGsQv-voaRVJM5P58-x/view?usp=drive_link ](https://drive.google.com/file/d/1egOn4gKI-aruCqKEZ1JBpMtx4fNpxH3h/view?usp=sharing)

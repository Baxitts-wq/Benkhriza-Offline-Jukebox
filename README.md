# Mr. Benkriza Offline Jukebox

A professional YouTube MP3/MP4 downloader with playlist support, local browser cookie handling, and a modern desktop UI.

[![CI](https://github.com/Baxitts-wq/Benkhriza-Offline-Jukebox/actions/workflows/ci.yml/badge.svg)](https://github.com/Baxitts-wq/Benkhriza-Offline-Jukebox/actions/workflows/ci.yml)

## Overview

This repository contains:

- `youtube_mp3_gui.py` — a desktop Tkinter application for downloading YouTube audio and video.
- `web_app.py` — a Flask web server with a front-end served from `static/`.

The application uses `yt-dlp` and `ffmpeg` to download, convert, and tag media files.

## Features

- Download single videos or complete playlists.
- Export audio to MP3 or video to MP4.
- Use local browser cookies for private or age-restricted content.
- Web application output is sandboxed to the `downloads/` folder.
- Professional branding with app icon and in-app logo support.

## Requirements

- Python 3.11+
- `ffmpeg` installed and available in `PATH`
- `yt-dlp`
- `flask`
- `flask-cors`

## Install

```powershell
python -m pip install -r requirements.txt
```

## Run the desktop app

```powershell
python youtube_mp3_gui.py
```

## Run the web app

```powershell
python web_app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Build a Windows executable

```powershell
.uild_release.ps1
```

The executable is generated in `dist/MrBenkrizaDownloader.exe`.

## Custom branding

Replace the branding assets in `assets/` with:

- `assets/app_icon.ico` or `assets/app_icon.png`
- `assets/inapp_logo.png` or `assets/inapp_logo.ico`

The app will fall back to existing logo files if these are not provided.

## Repository structure

- `assets/` — GUI icons and branding assets.
- `static/` — web frontend files.
- `requirements.txt` — runtime dependencies.
- `requirements-dev.txt` — build dependencies.
- `build_release.ps1` — Windows packaging script.

## Security

Do not commit browser cookie files or downloaded media. This repository contains only source code, documentation, and branding assets.

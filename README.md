# Mr. Benkriza Offline Jukebox

Vintage YouTube MP3/MP4 downloader for long playlists, built around `yt-dlp` and `ffmpeg`.

## What changed

- Playlist downloads now use unique filenames with playlist number and video id, so repeated titles do not overwrite each other.
- Long playlists retry harder and do not stop the whole playlist after a few bad/private items.
- The progress bar now tracks the full playlist instead of only one song at a time.
- Cookies can be loaded from the user's own browser from the app. No shared or embedded cookies are shipped.
- Web/API output paths are restricted to the downloads folder for safer public use.
- Private cookie files, downloaded media, and build outputs are ignored for GitHub.

## Run the desktop app

```powershell
.\run_dev.ps1
```

Or manually:

```powershell
python -m pip install -r requirements.txt
python youtube_mp3_gui.py
```

## Run the web app

```powershell
python -m pip install -r requirements.txt
python web_app.py
```

Open `http://127.0.0.1:5000`.

## Build the release EXE

```powershell
.\build_release.ps1
```

The release spec does not include cookie files, downloads, or local environment files.

## Cookie safety

Do not publish `cookies.txt` or any `*_cookies.txt` file. Cookies are login/session data. The app supports browser-cookie loading so each user can use their own local browser session without searching for a cookies file or exposing someone else's account.

Use this app only for content you own, have permission to download, or are otherwise allowed to save offline.

## Replacing logos

To replace the app icon and in-app logo, place image files in the `assets/` folder with these names:

- `assets/app_icon.ico` or `assets/app_icon.png` — used for the window icon when possible.
- `assets/inapp_logo.png` or `assets/inapp_logo.ico` — used for the header/stage images inside the app.

The GUI will also fall back to `assets/Mr_Benkhriza_Logo.png` / `.ico` or `assets/logo.png` / `.ico`.

"""Shared yt-dlp download logic for MP3 / MP4 (used by Tk GUI and Flask web UI)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

ProgressCallback = Callable[[float, str], None]
SUPPORTED_COOKIE_BROWSERS = {
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "safari",
    "vivaldi",
    "whale",
}


@dataclass(frozen=True)
class DownloadResult:
    output_folder: Path
    downloaded_count: int
    return_code: int
    archive_path: Path
    playlist_title: str
    total_items: int | None
    error_count: int

    def __str__(self) -> str:
        return str(self.output_folder)


def sanitize_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip()
    return cleaned[:120] or "Single_Videos"


def is_supported_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host in {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


def mp4_format_string(quality: str) -> str:
    """Map UI quality key to yt-dlp format selector."""
    if quality == "best":
        return "bestvideo+bestaudio/best"
    height = int(quality)
    return (
        f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
    )


def mp3_quality_kbps(quality: str) -> str:
    if quality == "best":
        return "320"
    return quality


class DownloadLogger:
    def __init__(self, progress: ProgressCallback) -> None:
        self.progress = progress
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        self.warnings.append(message)
        self.progress(0.0, f"Warning: {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        self.progress(0.0, f"Error: {message}")


def _apply_cookie_options(
    opts: dict[str, Any],
    cookies_path: Optional[str],
    browser_cookies: Optional[str],
) -> None:
    if cookies_path:
        cookie_file = Path(cookies_path).expanduser()
        if not cookie_file.exists():
            raise FileNotFoundError(f"Cookies file not found: {cookie_file}")
        opts["cookiefile"] = str(cookie_file)

    browser = (browser_cookies or "").strip().lower()
    if browser and browser != "none":
        if browser not in SUPPORTED_COOKIE_BROWSERS:
            names = ", ".join(sorted(SUPPORTED_COOKIE_BROWSERS))
            raise ValueError(f"Unsupported browser for cookies: {browser}. Use one of: {names}")
        opts["cookiesfrombrowser"] = (browser,)


def _playlist_count(info: dict[str, Any] | None) -> int | None:
    if not info:
        return None
    count = info.get("playlist_count") or info.get("n_entries")
    if isinstance(count, int) and count > 0:
        return count
    entries = info.get("entries")
    if isinstance(entries, list):
        return len([entry for entry in entries if entry])
    return None


def _playlist_title(info: dict[str, Any] | None, playlist: bool) -> str:
    if not playlist:
        return "Single_Videos"
    if not info:
        return "Playlist"
    return info.get("title") or info.get("playlist_title") or "Playlist"


def run_download(
    url: str,
    output_root: Path,
    *,
    media: str,
    quality: str,
    playlist: bool,
    cookies_path: Optional[str],
    browser_cookies: Optional[str] = None,
    progress: ProgressCallback,
) -> DownloadResult:
    """
    Download from URL into output_root / <playlist or Single_Videos> / files.

    media: 'mp3' or 'mp4'
    quality: 'best' | '1080' | '720' | ... | '128' | '192' | '320'
    playlist: True to download full playlist when URL contains a list.
    Returns the subfolder used for outputs.
    """
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed")
    if not is_supported_youtube_url(url):
        raise ValueError("Only YouTube links are supported.")

    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    download_mode = "playlist" if playlist else "single"

    progress(0.0, "Reading link...")
    probe_opts: dict = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "extractor_retries": 10,
        "noplaylist": download_mode != "playlist",
    }
    if download_mode == "playlist":
        probe_opts["extract_flat"] = "in_playlist"
        probe_opts["playliststart"] = 1
        probe_opts["playlistend"] = None
        probe_opts["lazy_playlist"] = False
    _apply_cookie_options(probe_opts, cookies_path, browser_cookies)

    with yt_dlp.YoutubeDL(probe_opts) as ydl_probe:
        info = ydl_probe.extract_info(url, download=False)
    if not info:
        raise RuntimeError("Could not read this YouTube link.")

    playlist_name = _playlist_title(info, playlist)
    total_items = _playlist_count(info) if playlist else 1
    subfolder = output_root / sanitize_folder_name(playlist_name)
    subfolder.mkdir(parents=True, exist_ok=True)
    archive_path = subfolder / f".downloaded_{media}_{quality}.txt"
    outtmpl = (
        "%(playlist_autonumber)03d - %(title).180B [%(id)s].%(ext)s"
        if playlist
        else "%(title).180B [%(id)s].%(ext)s"
    )

    if playlist and total_items:
        progress(0.0, f"Found {total_items} playlist items. Starting download...")

    def hook(d: dict) -> None:
        status = d.get("status", "")
        info_dict = d.get("info_dict") or {}
        idx = info_dict.get("playlist_autonumber") or info_dict.get("playlist_index")
        total = info_dict.get("n_entries") or total_items
        item_prefix = ""
        if playlist and idx and total:
            item_prefix = f"Item {idx}/{total}: "

        if status == "downloading":
            raw = d.get("_percent_str", "0%").replace("%", "").strip()
            try:
                pct = float(raw)
            except ValueError:
                pct = 0.0
            display_pct = pct
            if playlist and idx and total:
                display_pct = ((float(idx) - 1.0) + (pct / 100.0)) / float(total) * 100.0
            speed = (d.get("_speed_str") or "").strip()
            eta = (d.get("_eta_str") or "").strip()
            msg = f"{item_prefix}Downloading... {pct:.1f}%"
            if speed:
                msg += f" | {speed}"
            if eta:
                msg += f" | ETA {eta}"
            progress(display_pct, msg)
        elif status == "finished":
            display_pct = 100.0
            if playlist and idx and total:
                display_pct = float(idx) / float(total) * 100.0
            progress(display_pct, f"{item_prefix}Muxing / processing...")

    logger = DownloadLogger(progress)

    common_opts: dict[str, Any] = {
        "outtmpl": str(subfolder / outtmpl),
        "overwrites": False,
        "continuedl": True,
        "noplaylist": download_mode != "playlist",
        "ignoreerrors": True if playlist else False,
        "skip_playlist_after_errors": None,
        "extractor_retries": 10,
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "sleep_interval_requests": 0.25 if playlist else 0,
        "download_archive": str(archive_path),
        "windowsfilenames": True,
        "logger": logger,
        "progress_hooks": [hook],
    }
    if playlist:
        common_opts.update(
            {
                "playliststart": 1,
                "playlistend": None,
                "lazy_playlist": False,
            }
        )

    if media == "mp3":
        q = mp3_quality_kbps(quality)
        ydl_opts: dict = {
            **common_opts,
            "format": "bestaudio/best",
            "writethumbnail": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": q,
                },
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
        }
    elif media == "mp4":
        ydl_opts = {
            **common_opts,
            "format": mp4_format_string(quality),
            "merge_output_format": "mp4",
            "writethumbnail": False,
            "postprocessors": [
                {"key": "FFmpegMetadata"},
            ],
        }
    else:
        raise ValueError(f"Unknown media type: {media}")

    _apply_cookie_options(ydl_opts, cookies_path, browser_cookies)

    progress(0.0, "Starting download...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        retcode = ydl.download([url])
        downloaded_count = getattr(ydl, "_num_downloads", 0)

    if playlist and total_items and downloaded_count < total_items:
        progress(
            100.0,
            f"Done with {downloaded_count}/{total_items} new downloads. Check logs for skipped/private items.",
        )
    else:
        progress(100.0, f"Done. Downloaded {downloaded_count} new file(s).")
    return DownloadResult(
        output_folder=subfolder,
        downloaded_count=downloaded_count,
        return_code=retcode,
        archive_path=archive_path,
        playlist_title=playlist_name,
        total_items=total_items,
        error_count=len(logger.errors),
    )

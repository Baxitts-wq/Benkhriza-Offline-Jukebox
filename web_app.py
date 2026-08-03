"""Flask server: serves the Benkhriza HTML UI and runs yt-dlp downloads.

For a Lovable-hosted UI, set CORS_ORIGINS to your Lovable preview/production URLs
and point the frontend at this API (see LOVABLE.txt).
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from downloader_core import is_supported_youtube_url, run_download

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "8")) * 1024 * 1024

# Comma-separated list, e.g. "https://your-app.lovable.app,https://www.yourdomain.com"
_default_origins = "http://127.0.0.1:5000,http://localhost:5000"
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",") if o.strip()]
_download_root = Path(os.environ.get("DOWNLOAD_ROOT", Path.cwd() / "downloads")).resolve()
CORS(
    app,
    resources={r"/api/*": {"origins": _cors_origins}},
    supports_credentials=True,
    allow_headers=["Content-Type"],
)

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _update_job(job_id: str, **kwargs) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _safe_output_root(requested: str) -> Path:
    """Keep web/API writes inside DOWNLOAD_ROOT."""
    requested = (requested or "").strip()
    if not requested:
        return _download_root

    candidate = Path(requested)
    if candidate.is_absolute():
        raise ValueError("For the web app, output folders must be relative to the downloads folder.")

    resolved = (_download_root / candidate).resolve()
    if resolved != _download_root and _download_root not in resolved.parents:
        raise ValueError("Output folder must stay inside the downloads folder.")
    return resolved


def _run_job(
    job_id: str,
    url: str,
    output_dir: Path,
    media: str,
    quality: str,
    playlist: bool,
    cookies_path: str | None,
    browser_cookies: str | None,
) -> None:
    def progress(pct: float, msg: str) -> None:
        _update_job(job_id, percent=min(100.0, max(0.0, pct)), message=msg, error=None)

    try:
        subfolder = run_download(
            url,
            output_dir,
            media=media,
            quality=quality,
            playlist=playlist,
            cookies_path=cookies_path,
            browser_cookies=browser_cookies,
            progress=progress,
        )
        message = "Done"
        if subfolder.total_items:
            message = f"Done. New downloads: {subfolder.downloaded_count}/{subfolder.total_items}"
        _update_job(
            job_id,
            done=True,
            success=True,
            percent=100.0,
            message=message,
            output_folder=str(subfolder.output_folder),
            downloaded_count=subfolder.downloaded_count,
            total_items=subfolder.total_items,
            error_count=subfolder.error_count,
        )
    except Exception as e:
        _update_job(job_id, done=True, success=False, error=str(e), message="Failed")
    finally:
        if cookies_path and cookies_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(cookies_path)
            except OSError:
                pass


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/download")
def api_download():
    if shutil.which("ffmpeg") is None:
        return jsonify({"error": "ffmpeg not found in PATH. Install ffmpeg and restart."}), 400

    url = (request.form.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    if not is_supported_youtube_url(url):
        return jsonify({"error": "Only YouTube and youtu.be links are supported."}), 400

    media = (request.form.get("format") or "mp3").lower()
    if media not in ("mp3", "mp4"):
        return jsonify({"error": "Invalid format"}), 400

    quality = (request.form.get("quality") or "best").lower()
    playlist = request.form.get("playlist") in ("true", "1", "on", "yes")

    out = (request.form.get("output_dir") or "").strip()
    try:
        output_root = _safe_output_root(out)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    browser_cookies = (request.form.get("browser_cookies") or "").strip().lower() or None

    cookies_path: str | None = None
    f = request.files.get("cookies")
    if f and f.filename:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.close()
        f.save(tmp.name)
        cookies_path = tmp.name

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "done": False,
            "success": False,
            "percent": 0.0,
            "message": "Queued...",
            "error": None,
            "output_folder": None,
            "downloaded_count": 0,
            "total_items": None,
            "error_count": 0,
        }

    t = threading.Thread(
        target=_run_job,
        args=(job_id, url, output_root, media, quality, playlist, cookies_path, browser_cookies),
        daemon=True,
    )
    t.start()
    return jsonify({"job_id": job_id})


@app.get("/api/job/<job_id>")
def api_job(job_id: str):
    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        return jsonify({"error": "Unknown job"}), 404
    return jsonify(j)


@app.get("/api/health")
def api_health():
    """Load balancers / PaaS health checks."""
    return jsonify({"ok": True, "ffmpeg": shutil.which("ffmpeg") is not None, "download_root": str(_download_root)})


def main() -> None:
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    # Bind 0.0.0.0 on a VPS so the API is reachable (use HTTPS via reverse proxy).
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()

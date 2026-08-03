import os
import queue
import shutil
import subprocess
import threading
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import yt_dlp
except ImportError:
    yt_dlp = None
from PIL import Image, ImageTk

from downloader_core import is_supported_youtube_url, run_download


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


class YoutubeMp3App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mr. Benkriza Vintage Downloader")
        self.root.geometry("860x640")
        self.root.minsize(780, 560)
        self.events: "queue.Queue[tuple[str, str | float]]" = queue.Queue()
        self.colors = {
            "ink": "#2b2118",
            "paper": "#f4ecd6",
            "panel": "#fff8e8",
            "line": "#8a6f45",
            "brass": "#b8872f",
            "red": "#8f2f24",
            "green": "#284a3a",
            "cream": "#fff4da",
            "muted": "#6f5c3b",
        }

        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.cwd() / "downloads"))
        self.cookies_var = tk.StringVar()
        self.browser_cookie_var = tk.StringVar(value="none")
        self.media_var = tk.StringVar(value="mp3")
        self.quality_var = tk.StringVar(value="192")
        self.download_mode_var = tk.StringVar(value="playlist")
        self.status_var = tk.StringVar(value="Idle")
        self.logo_photo = None
        self.logo_stage_photo = None
        self.logo_icon = None

        self._configure_style()
        self._build_ui()
        self._load_logo()
        self._discover_cookies()
        self.root.after(100, self.process_events)

    def _discover_cookies(self) -> None:
        # Look for common cookie filenames in the current working directory and prefill the cookies field.
        candidates = [
            Path.cwd() / "cookies.txt",
            Path.cwd() / "www.youtube.com_cookies.txt",
            Path.cwd() / "startpageshared_cookies.txt",
            Path.cwd() / "cookies" / "cookies.txt",
        ]
        for p in candidates:
            try:
                if p.exists() and p.is_file():
                    self.cookies_var.set(str(p))
                    self.log(f"Using local cookies file: {p}")
                    return
            except Exception:
                continue

    def _configure_style(self) -> None:
        self.root.configure(bg=self.colors["paper"])
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=self.colors["paper"], foreground=self.colors["ink"])
        style.configure("TFrame", background=self.colors["paper"])
        style.configure("Panel.TFrame", background=self.colors["panel"], relief="solid", borderwidth=1)
        style.configure("Header.TFrame", background=self.colors["green"])
        style.configure("Title.TLabel", background=self.colors["green"], foreground=self.colors["cream"], font=("Georgia", 22, "bold"))
        style.configure("Subtitle.TLabel", background=self.colors["green"], foreground="#dbc99b", font=("Segoe UI", 10))
        style.configure("Badge.TLabel", background=self.colors["red"], foreground=self.colors["cream"], font=("Segoe UI", 9, "bold"), padding=(8, 4))
        style.configure("LogoFrame.TFrame", background=self.colors["green"])
        style.configure("TLabel", background=self.colors["paper"], foreground=self.colors["ink"])
        style.configure("Panel.TLabel", background=self.colors["panel"], foreground=self.colors["ink"])
        style.configure("Hint.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground="#fffdf5", foreground=self.colors["ink"], bordercolor=self.colors["line"], lightcolor=self.colors["brass"], darkcolor=self.colors["line"], padding=6)
        style.configure("TCombobox", fieldbackground="#fffdf5", foreground=self.colors["ink"], arrowcolor=self.colors["ink"], bordercolor=self.colors["line"], padding=4)
        style.configure("TButton", background="#e7d7aa", foreground=self.colors["ink"], bordercolor=self.colors["line"], focusthickness=2, focuscolor=self.colors["brass"], padding=(10, 6))
        style.map("TButton", background=[("active", "#d6bf7a")])
        style.configure("Accent.TButton", background=self.colors["red"], foreground=self.colors["cream"], font=("Segoe UI", 11, "bold"), padding=(12, 9))
        style.map("Accent.TButton", background=[("active", "#a74336"), ("disabled", "#b8988f")])
        style.configure("TRadiobutton", background=self.colors["panel"], foreground=self.colors["ink"])
        style.map("TRadiobutton", background=[("active", self.colors["panel"])])
        style.configure("Horizontal.TProgressbar", troughcolor="#d9c79b", background=self.colors["brass"], bordercolor=self.colors["line"], lightcolor=self.colors["brass"], darkcolor=self.colors["brass"])

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        header = ttk.Frame(frame, style="Header.TFrame", padding=(18, 14))
        header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        self.logo_label = ttk.Label(header, style="LogoFrame.TFrame")
        self.logo_label.grid(row=0, column=0, rowspan=3, sticky="w", padx=(0, 18))
        ttk.Label(header, text="Mr. Benkriza", style="Title.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            header,
            text="Official logo-driven offline jukebox for playlists, MP3, and MP4",
            style="Subtitle.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Label(header, text="BENKHRIZA OFFICIAL", style="Badge.TLabel").grid(row=0, column=2, rowspan=2, sticky="e")
        header.columnconfigure(1, weight=1)

        panel = ttk.Frame(frame, style="Panel.TFrame", padding=16)
        panel.grid(row=1, column=0, columnspan=3, sticky="nsew")

        logo_stage = ttk.Frame(panel, style="Panel.TFrame")
        logo_stage.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        self.logo_stage_label = ttk.Label(logo_stage, style="Panel.TLabel")
        self.logo_stage_label.grid(row=0, column=0, sticky="ew")

        ttk.Label(panel, text="YouTube URL(s)", style="Panel.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.url_var).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        ttk.Label(panel, text="Enter one URL per line or separate with commas.", style="Hint.TLabel").grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(panel, text="Output folder", style="Panel.TLabel").grid(row=4, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.output_var).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        ttk.Button(panel, text="Browse", command=self.pick_output).grid(row=5, column=2, sticky="ew", padx=(8, 0))

        ttk.Label(panel, text="Cookie source", style="Panel.TLabel").grid(row=6, column=0, sticky="w")
        browser_box = ttk.Combobox(
            panel,
            textvariable=self.browser_cookie_var,
            values=("none", "edge", "chrome", "firefox", "brave", "opera", "vivaldi"),
            state="readonly",
            width=14,
        )
        browser_box.grid(row=6, column=0, sticky="ew", pady=(4, 4))
        ttk.Label(panel, text="Optional: use your own browser session for private or age-restricted videos.", style="Hint.TLabel").grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(panel, text="Cookies file override", style="Panel.TLabel").grid(row=8, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.cookies_var).grid(row=9, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        ttk.Button(panel, text="Browse", command=self.pick_cookies).grid(row=9, column=2, sticky="ew", padx=(8, 0))

        ttk.Label(panel, text="Media", style="Panel.TLabel").grid(row=10, column=0, sticky="w")
        media_box = ttk.Combobox(
            panel,
            textvariable=self.media_var,
            values=["mp3", "mp4"],
            state="readonly",
            width=8,
        )
        media_box.grid(row=11, column=0, sticky="w", pady=(4, 12))
        media_box.bind("<<ComboboxSelected>>", self._on_media_change)

        ttk.Label(panel, text="Quality", style="Panel.TLabel").grid(row=10, column=1, sticky="w", padx=(8, 0))
        self.quality_box = ttk.Combobox(panel, textvariable=self.quality_var, width=14, state="readonly")
        self.quality_box.grid(row=11, column=1, sticky="w", padx=(8, 0), pady=(4, 12))
        self._refresh_quality_choices()

        ttk.Label(panel, text="Mode", style="Panel.TLabel").grid(row=10, column=2, sticky="w")
        mode_container = ttk.Frame(panel, style="Panel.TFrame")
        mode_container.grid(row=11, column=2, sticky="w", pady=(4, 12))
        ttk.Radiobutton(mode_container, text="Single", value="single", variable=self.download_mode_var).pack(side="left")
        ttk.Radiobutton(mode_container, text="Playlist", value="playlist", variable=self.download_mode_var).pack(
            side="left", padx=(10, 0)
        )

        self.progress = ttk.Progressbar(panel, length=200, mode="determinate", maximum=100)
        self.progress.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(4, 10))

        self.status_label = ttk.Label(panel, textvariable=self.status_var, style="Panel.TLabel")
        self.status_label.grid(row=13, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self.start_button = ttk.Button(panel, text="Start the deck", command=self.start_download, style="Accent.TButton")
        self.start_button.grid(row=14, column=0, columnspan=2, sticky="ew")
        ttk.Button(panel, text="Open output", command=self.open_output_folder).grid(row=14, column=2, sticky="ew", padx=(8, 0))

        ttk.Button(panel, text="Clear log", command=self.clear_log).grid(row=15, column=2, sticky="ew", padx=(8, 0), pady=(12, 0))

        self.logs = tk.Text(
            panel,
            height=10,
            wrap="word",
            bg=self.colors["green"],
            fg=self.colors["cream"],
            insertbackground=self.colors["cream"],
            relief="flat",
            padx=10,
            pady=8,
            font=("Consolas", 10),
        )
        self.logs.grid(row=15, column=0, columnspan=3, sticky="nsew", pady=(12, 0))

        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)
        panel.columnconfigure(2, weight=0)
        panel.rowconfigure(15, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

    def _load_logo(self) -> None:
        # Try multiple possible logo files (explicit names first, PNG preferred, ICO fallback).
        candidates = [
            "assets/app_icon.png",
            "assets/app_icon.ico",
            "assets/inapp_logo.png",
            "assets/inapp_logo.ico",
            "assets/Mr_Benkhriza_Logo.png",
            "assets/Mr_Benkhriza_Logo.ico",
            "assets/logo.png",
            "assets/logo.ico",
        ]
        img = None
        for rel in candidates:
            logo_path = resource_path(rel)
            if logo_path.exists():
                try:
                    # PIL can open many formats including ICO; convert to RGBA for consistency
                    opened = Image.open(logo_path)
                    img = opened.convert("RGBA")
                    break
                except Exception:
                    continue

        if img is None:
            return

        header_img = img.copy()
        header_img.thumbnail((132, 132), Image.Resampling.LANCZOS)
        stage_img = img.copy()
        stage_img.thumbnail((320, 320), Image.Resampling.LANCZOS)
        icon_img = img.copy()
        icon_img.thumbnail((64, 64), Image.Resampling.LANCZOS)

        self.logo_photo = ImageTk.PhotoImage(header_img)
        self.logo_stage_photo = ImageTk.PhotoImage(stage_img)
        self.logo_icon = ImageTk.PhotoImage(icon_img)

        self.logo_label.configure(image=self.logo_photo)
        self.logo_stage_label.configure(image=self.logo_stage_photo)
        try:
            self.root.iconphoto(True, self.logo_icon)
        except Exception:
            # Some platforms may not support iconphoto; ignore if it fails
            pass

    def _on_media_change(self, _evt=None) -> None:
        self._refresh_quality_choices()

    def _refresh_quality_choices(self) -> None:
        if self.media_var.get() == "mp4":
            self.quality_box["values"] = ("best", "1080", "720", "480", "360")
            if self.quality_var.get() not in self.quality_box["values"]:
                self.quality_var.set("best")
        else:
            self.quality_box["values"] = ("best", "128", "192", "320")
            if self.quality_var.get() not in self.quality_box["values"]:
                self.quality_var.set("192")

    def pick_output(self) -> None:
        folder = filedialog.askdirectory(title="Choose output folder")
        if folder:
            self.output_var.set(folder)

    def pick_cookies(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Choose cookies file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if file_path:
            self.cookies_var.set(file_path)

    def open_output_folder(self) -> None:
        folder = self.output_var.get().strip()
        if folder and Path(folder).exists():
            try:
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.run(["open", folder], check=False)
                else:
                    subprocess.run(["xdg-open", folder], check=False)
            except Exception:
                messagebox.showerror("Open folder", "Unable to open the output folder.")

    def clear_log(self) -> None:
        self.logs.delete("1.0", "end")

    def log(self, text: str) -> None:
        self.logs.insert("end", text + "\n")
        self.logs.see("end")

    def start_download(self) -> None:
        raw_text = self.url_var.get().strip()
        output_folder = self.output_var.get().strip()

        urls = [part.strip() for part in raw_text.replace(",", "\n").splitlines() if part.strip()]
        if not urls:
            messagebox.showerror("Missing URL", "Please provide one or more YouTube URLs.")
            return
        if any(not is_supported_youtube_url(url) for url in urls):
            messagebox.showerror("Unsupported URL", "Please use valid YouTube or youtu.be links only.")
            return
        if not output_folder:
            messagebox.showerror("Missing output", "Please choose an output folder.")
            return
        if yt_dlp is None:
            messagebox.showerror("Missing dependency", "yt-dlp is not installed. Run: pip install yt-dlp")
            return
        if shutil.which("ffmpeg") is None:
            messagebox.showerror("Missing dependency", "ffmpeg was not found in PATH.")
            return

        self.urls = urls
        self.start_button.config(state="disabled")
        self.progress["value"] = 0
        self.status_var.set("Preparing download...")
        self.log(f"Starting download of {len(urls)} URL(s)...")

        worker = threading.Thread(target=self.download_worker, daemon=True)
        worker.start()

    def download_worker(self) -> None:
        urls = getattr(self, "urls", [])
        quality = self.quality_var.get().strip()
        download_mode = self.download_mode_var.get().strip()
        output_root = Path(self.output_var.get().strip())
        cookies = self.cookies_var.get().strip() or None
        browser_cookies = self.browser_cookie_var.get().strip() or None
        media = self.media_var.get().strip()
        playlist = download_mode == "playlist"

        if not urls:
            self.events.put(("status", "No URLs to download."))
            self.events.put(("finish", ""))
            return

        for index, url in enumerate(urls, start=1):
            self.events.put(("status", f"Downloading {index}/{len(urls)}"))
            self.events.put(("log", f"Downloading: {url}"))

            def progress_cb(pct: float, msg: str) -> None:
                self.events.put(("progress", pct))
                self.events.put(("status", f"[{index}/{len(urls)}] {msg}"))

            try:
                subfolder = run_download(
                    url,
                    output_root,
                    media=media,
                    quality=quality,
                    playlist=playlist,
                    cookies_path=cookies,
                    browser_cookies=browser_cookies,
                    progress=progress_cb,
                )
                self.events.put(("progress", 100.0))
                self.events.put(("status", f"Done {index}/{len(urls)}"))
                if subfolder.total_items:
                    self.events.put(("log", f"Finished: {subfolder.downloaded_count}/{subfolder.total_items} new downloads in {subfolder.output_folder}"))
                else:
                    self.events.put(("log", f"Finished: output {subfolder.output_folder}"))
                if subfolder.return_code:
                    self.events.put(("log", f"yt-dlp finished with warning code {subfolder.return_code}."))
                if subfolder.error_count:
                    self.events.put(("log", f"yt-dlp reported {subfolder.error_count} error(s); unavailable/private videos may be skipped."))
            except Exception as exc:
                self.events.put(("status", f"Failed {index}/{len(urls)}"))
                self.events.put(("log", f"Error: {exc}"))
                break

        self.events.put(("finish", ""))

    def process_events(self) -> None:
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == "progress":
                self.progress["value"] = float(value)
            elif kind == "status":
                self.status_var.set(str(value))
            elif kind == "log":
                self.log(str(value))
            elif kind == "finish":
                self.start_button.config(state="normal")
        self.root.after(100, self.process_events)


def main() -> None:
    root = tk.Tk()
    YoutubeMp3App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

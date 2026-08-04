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
            "ink": "#00FF41",
            "paper": "#000000",
            "panel": "#07070B",
            "line": "#222233",
            "brass": "#FF9900",
            "red": "#FF003C",
            "green": "#00FF41",
            "cream": "#FFFFFF",
            "muted": "#555566",
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
        self.music_proc = None
        self.music_var = tk.StringVar()

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
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", font=("Consolas", 10), background=self.colors["paper"], foreground=self.colors["ink"])
        style.configure("TFrame", background=self.colors["paper"])
        style.configure("Panel.TFrame", background=self.colors["panel"], relief="solid", borderwidth=1)
        style.configure("Header.TFrame", background=self.colors["green"])
        style.configure("Title.TLabel", background=self.colors["green"], foreground=self.colors["red"], font=("Consolas", 20, "bold"))
        style.configure("Subtitle.TLabel", background=self.colors["green"], foreground=self.colors["muted"], font=("Consolas", 10))
        style.configure("Badge.TLabel", background=self.colors["red"], foreground=self.colors["cream"], font=("Segoe UI", 9, "bold"), padding=(8, 4))
        style.configure("LogoFrame.TFrame", background=self.colors["panel"])
        style.configure("TLabel", background=self.colors["paper"], foreground=self.colors["ink"])
        style.configure("Panel.TLabel", background=self.colors["panel"], foreground=self.colors["ink"])
        style.configure("Hint.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=("Consolas", 9))
        style.configure("TEntry", fieldbackground="#fffdf5", foreground=self.colors["ink"], bordercolor=self.colors["line"], lightcolor=self.colors["brass"], darkcolor=self.colors["line"], padding=6)
        style.configure("TCombobox", fieldbackground="#fffdf5", foreground=self.colors["ink"], arrowcolor=self.colors["ink"], bordercolor=self.colors["line"], padding=4)
        style.configure("TButton", background="#111111", foreground=self.colors["green"], bordercolor=self.colors["green"], focusthickness=2, focuscolor=self.colors["green"], padding=(10, 6))
        style.configure("Hover.TButton", background="#002200", foreground=self.colors["green"], bordercolor=self.colors["green"], padding=(10, 6))
        style.configure("Pressed.TButton", background="#001100", foreground=self.colors["green"], bordercolor=self.colors["green"], padding=(10, 6))
        style.map("TButton", background=[("active", "#002200")])
        style.configure("Accent.TButton", background=self.colors["red"], foreground=self.colors["cream"], font=("Consolas", 11, "bold"), padding=(12, 9), bordercolor=self.colors["red"])
        style.configure("Accent.Hover.TButton", background="#66001e", foreground=self.colors["cream"], bordercolor=self.colors["red"], padding=(12, 9))
        style.map("Accent.TButton", background=[("active", "#66001e"), ("disabled", "#333333")])
        style.configure("Neon.TNotebook", background=self.colors["panel"], tabmargins=0)
        style.configure("Neon.TNotebook.Tab", background=self.colors["panel"], foreground=self.colors["green"], padding=(12, 8), font=("Consolas", 10, "bold"))
        style.map("Neon.TNotebook.Tab", background=[("selected", self.colors["line"]), ("active", "#002200")], foreground=[("selected", self.colors["cream"])])
        style.configure("TRadiobutton", background=self.colors["panel"], foreground=self.colors["ink"])
        style.map("TRadiobutton", background=[("active", self.colors["panel"])])
        style.configure("Horizontal.TProgressbar", troughcolor="#111111", background=self.colors["green"], bordercolor=self.colors["line"], lightcolor=self.colors["green"], darkcolor=self.colors["green"])
        style.configure("NeonPanel.TFrame", background=self.colors["panel"], relief="solid", borderwidth=1)
        style.configure("NeonLabel.TLabel", background=self.colors["panel"], foreground=self.colors["ink"], font=("Consolas", 10))

    def _bind_neon_hover(self, widget: ttk.Button, base_style: str, hover_style: str, pressed_style: str) -> None:
        widget.bind("<Enter>", lambda e: widget.configure(style=hover_style))
        widget.bind("<Leave>", lambda e: widget.configure(style=base_style))
        widget.bind("<ButtonPress-1>", lambda e: widget.configure(style=pressed_style))
        widget.bind("<ButtonRelease-1>", lambda e: widget.configure(style=hover_style))

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

        # Ambient music controls (reads songs from the external example folder; does not modify it)
        try:
            music_folder = Path(r"C:\Users\Imad Eddin\Desktop\TestMrbenhriza\Mr_Benkhriza_v2\Songs")
            music_files = [p.name for p in music_folder.iterdir() if p.suffix.lower() in ('.mp3', '.wav', '.ogg')] if music_folder.exists() else []
        except Exception:
            music_files = []
        music_frame = ttk.Frame(header)
        music_frame.grid(row=2, column=1, sticky="e")
        ttk.Label(music_frame, text="Ambient:", style="Subtitle.TLabel").pack(side="left", padx=(0, 8))
        self.music_box = ttk.Combobox(music_frame, textvariable=self.music_var, values=music_files, state="readonly", width=28)
        self.music_box.pack(side="left")
        ttk.Button(music_frame, text="Play/Pause", command=self.toggle_music).pack(side="left", padx=(8, 0))

        panel = ttk.Frame(frame, style="Panel.TFrame", padding=16)
        panel.grid(row=1, column=0, columnspan=3, sticky="nsew")

        logo_stage = ttk.Frame(panel, style="Panel.TFrame")
        logo_stage.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        # Canvas for circular emblem + pulsing neon ring
        self.logo_canvas = tk.Canvas(logo_stage, width=180, height=180, highlightthickness=0, bg=self.colors["panel"])
        self.logo_canvas.grid(row=0, column=0, sticky="w")
        self._pulse_ring_id = None
        self._pulse_state = 0

        notebook = ttk.Notebook(panel, style="Neon.TNotebook")
        notebook.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(0, 14))

        deck_tab = ttk.Frame(notebook, style="NeonPanel.TFrame")
        settings_tab = ttk.Frame(notebook, style="NeonPanel.TFrame")
        notebook.add(deck_tab, text="Deck")
        notebook.add(settings_tab, text="Settings")

        ttk.Label(deck_tab, text="YouTube URL(s)", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.url_text = tk.Text(deck_tab, height=6, wrap="word", bg="#0b0b12", fg=self.colors["green"], insertbackground=self.colors["green"], relief="flat", padx=10, pady=10, font=("Consolas", 10))
        self.url_text.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        ttk.Label(deck_tab, text="Enter one URL per line or separate with commas.", style="Hint.TLabel").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 12))

        self.start_button = ttk.Button(deck_tab, text="Start the deck", command=self.start_download, style="Accent.TButton")
        self.start_button.grid(row=3, column=0, columnspan=2, sticky="ew")
        self._bind_neon_hover(self.start_button, "Accent.TButton", "Accent.Hover.TButton", "Pressed.TButton")

        open_button = ttk.Button(deck_tab, text="Open output", command=self.open_output_folder, style="TButton")
        open_button.grid(row=3, column=2, sticky="ew", padx=(8, 0))
        self._bind_neon_hover(open_button, "TButton", "Hover.TButton", "Pressed.TButton")

        self.progress = ttk.Progressbar(deck_tab, length=200, mode="determinate", maximum=100)
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(12, 10))
        self.status_label = ttk.Label(deck_tab, textvariable=self.status_var, style="Panel.TLabel")
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 10))

        clear_button = ttk.Button(deck_tab, text="Clear log", command=self.clear_log, style="TButton")
        clear_button.grid(row=6, column=2, sticky="ew", padx=(8, 0), pady=(12, 0))
        self._bind_neon_hover(clear_button, "TButton", "Hover.TButton", "Pressed.TButton")

        logs_frame = ttk.Frame(deck_tab, style="NeonPanel.TFrame")
        logs_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(12, 0))

        self.logs = tk.Text(
            logs_frame,
            height=10,
            wrap="word",
            bg="#000000",
            fg=self.colors["green"],
            insertbackground=self.colors["green"],
            relief="flat",
            padx=10,
            pady=8,
            font=("Consolas", 10),
        )
        self.logs.grid(row=0, column=0, sticky="nsew")

        logs_scroll = ttk.Scrollbar(logs_frame, orient="vertical", command=self.logs.yview)
        logs_scroll.grid(row=0, column=1, sticky="ns")
        self.logs.configure(yscrollcommand=logs_scroll.set)

        # Mouse-wheel scrolling bindings (Windows and X11)
        def _on_mousewheel(event):
            try:
                self.logs.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _on_button4_5(event):
            if event.num == 4:
                self.logs.yview_scroll(-1, "units")
            elif event.num == 5:
                self.logs.yview_scroll(1, "units")

        self.logs.bind_all("<MouseWheel>", _on_mousewheel)
        self.logs.bind_all("<Button-4>", _on_button4_5)
        self.logs.bind_all("<Button-5>", _on_button4_5)

        ttk.Label(settings_tab, text="Output folder", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings_tab, textvariable=self.output_var, style="TEntry").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        browse_output_button = ttk.Button(settings_tab, text="Browse", command=self.pick_output, style="TButton")
        browse_output_button.grid(row=1, column=2, sticky="ew", padx=(8, 0))
        self._bind_neon_hover(browse_output_button, "TButton", "Hover.TButton", "Pressed.TButton")

        ttk.Label(settings_tab, text="Cookie source", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        browser_box = ttk.Combobox(
            settings_tab,
            textvariable=self.browser_cookie_var,
            values=("none", "edge", "chrome", "firefox", "brave", "opera", "vivaldi"),
            state="readonly",
            width=14,
        )
        browser_box.grid(row=3, column=0, sticky="ew", pady=(4, 4))
        ttk.Label(settings_tab, text="Optional: use your own browser session for private or age-restricted videos.", style="Hint.TLabel").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(settings_tab, text="Cookies file override", style="Panel.TLabel").grid(row=5, column=0, sticky="w")
        ttk.Entry(settings_tab, textvariable=self.cookies_var, style="TEntry").grid(row=6, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        browse_cookie_button = ttk.Button(settings_tab, text="Browse", command=self.pick_cookies, style="TButton")
        browse_cookie_button.grid(row=6, column=2, sticky="ew", padx=(8, 0))
        self._bind_neon_hover(browse_cookie_button, "TButton", "Hover.TButton", "Pressed.TButton")

        ttk.Label(settings_tab, text="Media", style="Panel.TLabel").grid(row=7, column=0, sticky="w")
        media_box = ttk.Combobox(
            settings_tab,
            textvariable=self.media_var,
            values=["mp3", "mp4"],
            state="readonly",
            width=8,
        )
        media_box.grid(row=8, column=0, sticky="w", pady=(4, 12))
        media_box.bind("<<ComboboxSelected>>", self._on_media_change)

        ttk.Label(settings_tab, text="Quality", style="Panel.TLabel").grid(row=7, column=1, sticky="w", padx=(8, 0))
        self.quality_box = ttk.Combobox(settings_tab, textvariable=self.quality_var, width=14, state="readonly")
        self.quality_box.grid(row=8, column=1, sticky="w", padx=(8, 0), pady=(4, 12))
        self._refresh_quality_choices()

        ttk.Label(settings_tab, text="Mode", style="Panel.TLabel").grid(row=7, column=2, sticky="w")
        mode_container = ttk.Frame(settings_tab, style="Panel.TFrame")
        mode_container.grid(row=8, column=2, sticky="w", pady=(4, 12))
        ttk.Radiobutton(mode_container, text="Single", value="single", variable=self.download_mode_var).pack(side="left")
        ttk.Radiobutton(mode_container, text="Playlist", value="playlist", variable=self.download_mode_var).pack(
            side="left", padx=(10, 0)
        )

        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)
        panel.columnconfigure(2, weight=0)
        panel.rowconfigure(1, weight=1)
        deck_tab.columnconfigure(0, weight=1)
        deck_tab.columnconfigure(1, weight=1)
        deck_tab.columnconfigure(2, weight=0)
        deck_tab.rowconfigure(7, weight=1)
        settings_tab.columnconfigure(0, weight=1)
        settings_tab.columnconfigure(1, weight=1)
        settings_tab.columnconfigure(2, weight=0)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

    def _load_logo(self) -> None:
        # Try multiple possible logo files (explicit names first, PNG preferred, ICO fallback).
        candidates = [
            # allow a user-provided replacement logo in the downloads folder to override built-in assets
            Path.cwd() / "downloads" / "replace_Nero_AI_Image_Upscaler_Standard_Face-removebg-preview.png",
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
        # If we have an image, prepare a circular cropped version for the canvas
        if img is not None:
            try:
                size = (160, 160)
                img = img.resize(size, Image.LANCZOS)
                # create circular mask
                mask = Image.new("L", size, 0)
                mask_draw = Image.new("L", size, 0)
                from PIL import ImageDraw

                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, size[0], size[1]), fill=255)
                circ = Image.new("RGBA", size, (0, 0, 0, 0))
                circ.paste(img, (0, 0), mask=mask)
                self.logo_stage_photo = ImageTk.PhotoImage(circ)
                # clear existing canvas items
                try:
                    self.logo_canvas.delete("all")
                except Exception:
                    pass
                # draw pulsing ring (initial)
                x0, y0 = 10, 10
                x1, y1 = 170, 170
                ring_color = self.colors.get("green", "#00FF41")
                self._pulse_ring_id = self.logo_canvas.create_oval(x0, y0, x1, y1, outline=ring_color, width=4)
                # place image centered
                self.logo_canvas.create_image(90, 90, image=self.logo_stage_photo)
                self._start_logo_pulse()
                return
            except Exception:
                pass

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

    def _start_logo_pulse(self) -> None:
        try:
            self._pulse_state = 0
            self._pulse_step()
        except Exception:
            pass

    def _pulse_step(self) -> None:
        try:
            if self._pulse_ring_id is None:
                return
            # cycle pulse state 0..20
            self._pulse_state = (self._pulse_state + 1) % 40
            # compute width and alpha-like effect via color brightness
            import math

            t = (math.sin(self._pulse_state / 40.0 * math.pi * 2) + 1) / 2  # 0..1
            base = self.colors.get("green", "#00FF41")
            # line width varies 2..8
            width = 2 + int(t * 6)
            try:
                self.logo_canvas.itemconfigure(self._pulse_ring_id, width=width)
            except Exception:
                pass
            # schedule next
            self.logo_canvas.after(120, self._pulse_step)
        except Exception:
            pass

    def toggle_music(self) -> None:
        """Play or stop the selected ambient track. Uses ffplay when available, falls back to opening the file."""
        track = self.music_var.get().strip()
        if not track:
            self.log("No ambient track selected.")
            return
        # locate the file in the example songs folder without modifying it
        music_path = Path(r"C:\Users\Imad Eddin\Desktop\TestMrbenhriza\Mr_Benkhriza_v2\Songs") / track
        if not music_path.exists():
            self.log(f"Ambient file not found: {music_path}")
            return

        # If already playing, stop it
        if getattr(self, "music_proc", None) is not None:
            try:
                proc = self.music_proc
                if proc and proc.poll() is None:
                    proc.terminate()
                    self.music_proc = None
                    self.log("Ambient audio stopped.")
                    return
            except Exception:
                self.music_proc = None

        # Try to play with ffplay (part of ffmpeg), otherwise open with default app
        if shutil.which("ffplay"):
            try:
                # launch ffplay quietly
                self.music_proc = subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(music_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log(f"Playing ambient: {track}")
            except Exception as e:
                self.log(f"Failed to play ambient with ffplay: {e}")
                try:
                    os.startfile(str(music_path))
                except Exception:
                    self.log("Unable to open ambient file.")
        else:
            try:
                os.startfile(str(music_path))
                self.log(f"Opened ambient file with default player: {track}")
            except Exception:
                self.log("Unable to open ambient file; install ffplay for built-in playback control.")

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
        raw_text = self.url_text.get("1.0", "end").strip()
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

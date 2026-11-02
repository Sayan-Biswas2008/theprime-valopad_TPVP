import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as mb
from tkinter import filedialog
import copy
import json
import os
import shutil
import subprocess
import sys
import time
import ctypes
from PIL import Image, ImageColor, ImageSequence

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "valo_pad_data.json")
LOGO_FILE = os.path.join(BASE_DIR, "logo.ico")

MAX_CARD_CHARS = 90        # long text is shortened on the card (full text is still copied)
MAX_GIF_FRAMES = 50
BG_MAX_SIZE = (1280, 720)  # background frames are scaled down to this to save RAM

THEMES = {
    "Default": {"bg": "#0c0f17", "main": "#141a27", "accent": "#00d2d3", "card": "#182030"},
    "Black": {"bg": "#000000", "main": "#050505", "accent": "#ffffff", "card": "#0f0f0f"},
    "Radiant": {"bg": "#120d14", "main": "#1a1525", "accent": "#ff4655", "card": "#241b2d"},
    "Icebox": {"bg": "#0a1014", "main": "#101820", "accent": "#00ffff", "card": "#15202b"},
    "Lotus": {"bg": "#1c101c", "main": "#251525", "accent": "#ff79c6", "card": "#301b30"},
    "Reaver": {"bg": "#0d0a14", "main": "#151020", "accent": "#a855f7", "card": "#1e152d"},
    "Prime": {"bg": "#14120a", "main": "#1a1810", "accent": "#fde047", "card": "#262215"},
    "Glitchpop": {"bg": "#100a1c", "main": "#151025", "accent": "#ec4899", "card": "#201535"},
    "Sovereign": {"bg": "#0a1414", "main": "#152020", "accent": "#fde047", "card": "#1a2a2a"},
}

FONTS = [
    "Segoe UI", "Bahnschrift", "Consolas", "Arial", "Trebuchet MS",
    "Verdana", "Tahoma", "Courier New", "Comic Sans MS", "Georgia",
]

EFFECTS = ["Glow", "Solid", "Minimal"]

IMAGE_TYPES = [("Image Files", ("*.png", "*.jpg", "*.jpeg", "*.gif"))]

DEFAULT_DATA = {
    "settings": {
        "font": "Segoe UI",
        "theme": "Reaver",
        "bg_image": "",
        "title_bg": "",
        "effect": "Glow",
    },
    "sections": [
        {
            "id": "sec_1",
            "title": "General",
            "notes": "MAJOR SAMAL\nImmoneninenineeight\n\nNOSFERIN\nEldllvx",
            "notes_grid": [
                "MAJOR SAMAL\nImmoneninenineeight\n\nNOSFERIN\nEldllvx", "", "", ""
            ],
            "crosshairs": [
                {"id": "c1", "label": "TENZ", "text": "0;s;1;P;c;5;h;0;m;1;0l;4;0o;2;0a;1;0f;0;1b;0"}
            ],
            "links": [],
            "snippets": [
                {"id": "s1", "label": "YT", "text": "Hi I am live on yt --> @Itz_PRiM3 . hope to see u there!"}
            ],
        }
    ],
}


def _normalize(data):
    """Make sure loaded data has every key the app needs (handles old/partial files)."""
    if isinstance(data, list):                       # very old format: just a list of sections
        data = {"sections": data}
    if not isinstance(data, dict):
        return copy.deepcopy(DEFAULT_DATA)

    settings = data.get("settings")
    if not isinstance(settings, dict):
        settings = {}
    for k, v in DEFAULT_DATA["settings"].items():
        settings.setdefault(k, v)
    data["settings"] = settings

    sections = data.get("sections")
    if not isinstance(sections, list):
        sections = []
    clean = []
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue
        sec.setdefault("id", f"sec_{int(time.time() * 1000)}_{i}")
        sec.setdefault("title", "Untitled")
        sec.setdefault("notes", "")
        grid = sec.get("notes_grid")
        if not isinstance(grid, list):
            grid = [sec["notes"], "", "", ""]
        grid = (list(grid) + [""] * 4)[:4]
        sec["notes_grid"] = [str(x) for x in grid]
        for key in ("crosshairs", "links", "snippets"):
            if not isinstance(sec.get(key), list):
                sec[key] = []
        clean.append(sec)
    if not clean:
        clean = copy.deepcopy(DEFAULT_DATA["sections"])
    data["sections"] = clean
    return data


def load_data():
    if not os.path.exists(DATA_FILE):
        return copy.deepcopy(DEFAULT_DATA)
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Keep the unreadable file so nothing is lost, then start fresh
        try:
            shutil.copy(DATA_FILE, DATA_FILE + ".bad")
        except Exception:
            pass
        return copy.deepcopy(DEFAULT_DATA)
    return _normalize(data)


def save_data(data):
    """Atomic write: a crash mid-save can no longer corrupt the real file."""
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        print("Save error:", e)


class ValoPadApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("THE PRIME - VALO PAD")
        self.geometry("1100x720")
        self.minsize(960, 640)

        # Pending after() jobs, so they can be cancelled on close/restart
        self._clock_job = None
        self._anim_job = None
        self._toast_job = None
        self._title_job = None
        self._notes_job = None
        self._header_job = None
        self._closing = False

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ThePrime.ValoPad.App")
        except Exception:
            pass
        # CTk resets the icon shortly after startup, so apply it a bit later
        self.after(250, self._set_icon)

        self.data = load_data()
        self.settings = self.data["settings"]          # same object as in self.data -> saves correctly

        self.active_section_id = self.data["sections"][0]["id"]
        self.current_tab = "snippets"
        self.viewing_settings = False

        self.bg_image_obj = None
        self.bg_frames = []
        self.bg_delays = []
        self.current_frame = 0
        self.animating = False

        self.title_bg_obj = None
        self.title_bg_src = None

        self.apply_theme_colors()
        self.build_ui()
        self.load_background()
        self.load_title_background()
        self.render_sidebar()
        self.switch_tab(self.current_tab)
        self.update_clock()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ helpers
    def _set_icon(self):
        try:
            if os.path.exists(LOGO_FILE):
                self.iconbitmap(LOGO_FILE)
        except Exception:
            pass

    def _cancel_jobs(self):
        for name in ("_clock_job", "_anim_job", "_toast_job", "_title_job", "_notes_job", "_header_job"):
            job = getattr(self, name, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                setattr(self, name, None)

    def on_close(self):
        self._closing = True
        self._flush_pending()
        self._cancel_jobs()
        self.destroy()

    def _flush_pending(self):
        """Commit any debounced edits before closing/restarting."""
        try:
            if self._title_job is not None:
                self._commit_title(render=False)
            if self._notes_job is not None:
                self._commit_notes()
        except Exception:
            pass
        save_data(self.data)

    def apply_theme_colors(self):
        theme_name = self.settings.get("theme", "Reaver")
        self.theme = THEMES.get(theme_name, THEMES["Reaver"])
        self.configure(fg_color=self.theme["bg"])
        self.font_family = self.settings.get("font", "Segoe UI")
        self.active_effect = self.settings.get("effect", "Glow")

    def get_font(self, size, weight="normal"):
        return ctk.CTkFont(family=self.font_family, size=size, weight=weight)

    def get_active_section(self):
        for sec in self.data["sections"]:
            if sec["id"] == self.active_section_id:
                return sec
        if self.data["sections"]:
            self.active_section_id = self.data["sections"][0]["id"]
            return self.data["sections"][0]
        return None

    def restart_app(self):
        self._closing = True
        self._flush_pending()
        self._cancel_jobs()
        self.destroy()
        if getattr(sys, "frozen", False):               # PyInstaller .exe
            cmd = [sys.executable]
        else:
            cmd = [sys.executable, os.path.abspath(sys.argv[0])]
        subprocess.Popen(cmd)

    def update_clock(self):
        if self._closing:
            return
        self.time_label.configure(text=time.strftime("%A, %d %b  |  %I:%M %p"))
        self._clock_job = self.after(1000, self.update_clock)

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        # 1. Base master layer
        self.bg_label = ctk.CTkLabel(self, text="")
        self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 2. Transparent overlay layer
        self.overlay_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.overlay_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.overlay_frame, fg_color=self.theme["bg"], height=70,
                                         corner_radius=0, border_width=2, border_color=self.theme["main"])
        self.header_frame.pack(side="top", fill="x")
        self.header_frame.pack_propagate(False)
        self.header_frame.bind("<Configure>", self._on_header_resize)

        self.header_bg_label = ctk.CTkLabel(self.header_frame, text="")
        self.header_bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        brand_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_frame.pack(side="left", padx=24, pady=12)

        ctk.CTkLabel(brand_frame, text="⟁", font=self.get_font(28, "bold"),
                     text_color=self.theme["accent"]).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(brand_frame, text="THE PRIME\nVALO PAD", font=self.get_font(16, "bold"),
                     text_color="#ffffff", justify="left").pack(side="left")

        self.time_label = ctk.CTkLabel(self.header_frame, text="", font=self.get_font(15, "bold"),
                                       text_color=self.theme["accent"])
        self.time_label.pack(side="right", padx=30, pady=20)

        self.body_frame = ctk.CTkFrame(self.overlay_frame, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(
            self.body_frame,
            fg_color=self.theme["bg"] if not self.settings.get("bg_image") else "transparent",
            width=330, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        sidebar_top = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        sidebar_top.pack(fill="x", padx=16, pady=(20, 10))

        self.sections_count_label = ctk.CTkLabel(sidebar_top, text="SECTIONS", font=self.get_font(13, "bold"),
                                                 text_color="#8b9bb4")
        self.sections_count_label.pack(side="left")

        self.btn_new_sec = ctk.CTkButton(
            sidebar_top, text="+ NEW SECTION", font=self.get_font(11, "bold"),
            fg_color="transparent", hover_color=self.theme["accent"], text_color=self.theme["accent"],
            border_color=self.theme["accent"], border_width=2, width=110, height=28, corner_radius=14,
            command=self.create_new_section)
        self.btn_new_sec.pack(side="right")

        self.sections_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.sections_scroll.pack(fill="both", expand=True, padx=12, pady=(10, 10))

        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame, text="⚙ SETTINGS", font=self.get_font(13, "bold"),
            fg_color=self.theme["card"], hover_color=self.theme["main"], text_color=self.theme["accent"],
            height=45, corner_radius=10, command=self.toggle_settings)
        self.btn_settings.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_restart = ctk.CTkButton(
            self.sidebar_frame, text="⟳ RESTART APP", font=self.get_font(13, "bold"),
            fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff",
            height=45, corner_radius=10, command=self.restart_app)
        self.btn_restart.pack(fill="x", padx=16, pady=(0, 20))

        # Main area
        self.main_frame = ctk.CTkFrame(self.body_frame, fg_color="transparent", corner_radius=0)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=(1, 0))

        self.panel_header = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=45)
        self.panel_header.pack(fill="x", padx=30, pady=(24, 16))

        self.active_sec_entry = ctk.CTkEntry(
            self.panel_header, font=self.get_font(28, "bold"), text_color=self.theme["accent"],
            fg_color="transparent", border_width=0, width=500)
        self.active_sec_entry.pack(side="left")
        self.active_sec_entry.bind("<KeyRelease>", self.save_section_title)

        self.subtabs_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=35)
        self.subtabs_bar.pack(fill="x", padx=30, pady=(0, 16))

        self.tabs_meta = [
            ("notes", "🗎 Notes"), ("crosshairs", "⌖ Crosshairs"),
            ("links", "🔗 Links"), ("snippets", "💬 Chat Snippets"),
        ]
        self.tab_buttons = {}
        for key, title in self.tabs_meta:
            btn = ctk.CTkButton(
                self.subtabs_bar, text=title, font=self.get_font(14, "bold"),
                fg_color="transparent", hover_color=self.theme["card"], text_color="#8b9bb4",
                width=120, height=34, corner_radius=8, command=lambda k=key: self.switch_tab(k))
            btn.pack(side="left", padx=(0, 12))
            self.tab_buttons[key] = btn

        self.dynamic_area = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.dynamic_area.pack(fill="both", expand=True, padx=30, pady=(0, 12))

        # Notes: 2x2 grid
        self.notes_grid_frame = ctk.CTkFrame(self.dynamic_area, fg_color="transparent")
        self.notes_grid_frame.columnconfigure((0, 1), weight=1)
        self.notes_grid_frame.rowconfigure((0, 1), weight=1)

        self.note_boxes = []
        for r in range(2):
            for c in range(2):
                tb = ctk.CTkTextbox(
                    self.notes_grid_frame, font=self.get_font(16), fg_color=self.theme["card"],
                    text_color="#e2e8f0", border_color=self.theme["main"], border_width=2, corner_radius=12)
                tb.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
                tb.bind("<KeyRelease>", self.save_notes_text)
                self.note_boxes.append(tb)

        self.stream_scroll = ctk.CTkScrollableFrame(self.dynamic_area, fg_color="transparent")
        self.settings_frame = ctk.CTkScrollableFrame(self.dynamic_area, fg_color="transparent")

        # Composer (packed with side="bottom" before dynamic_area so it never gets squeezed out)
        self.composer_frame = ctk.CTkFrame(self.main_frame, fg_color=self.theme["card"], corner_radius=14)
        self.composer_title = ctk.CTkLabel(self.composer_frame, text="💬 SAVE NEW ITEM",
                                           font=self.get_font(12, "bold"), text_color=self.theme["accent"])
        self.composer_title.pack(anchor="w", padx=20, pady=(14, 6))

        inputs_row = ctk.CTkFrame(self.composer_frame, fg_color="transparent")
        inputs_row.pack(fill="x", padx=20, pady=(0, 18))

        self.entry_badge = ctk.CTkEntry(inputs_row, placeholder_text="Label", fg_color=self.theme["bg"],
                                        border_color=self.theme["bg"], font=self.get_font(14),
                                        height=42, width=200, corner_radius=8)
        self.entry_badge.pack(side="left", padx=(0, 12))

        self.entry_content = ctk.CTkEntry(inputs_row, placeholder_text="Content...", fg_color=self.theme["bg"],
                                          border_color=self.theme["bg"], font=self.get_font(14),
                                          height=42, corner_radius=8)
        self.entry_content.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.entry_content.bind("<Return>", lambda e: self.save_current_item())
        self.entry_badge.bind("<Return>", lambda e: self.entry_content.focus_set())

        self.btn_save = ctk.CTkButton(
            inputs_row, text="SAVE", font=self.get_font(14, "bold"), fg_color=self.theme["accent"],
            text_color="#000000", height=42, width=140, corner_radius=8, command=self.save_current_item)
        self.btn_save.pack(side="right")

        self.toast_label = ctk.CTkLabel(self.overlay_frame, text="", font=self.get_font(13, "bold"),
                                        text_color="#000000", fg_color=self.theme["accent"],
                                        corner_radius=10, height=36, width=220)
        self.build_settings_tab()

    def build_settings_tab(self):
        ctk.CTkLabel(self.settings_frame, text="Appearance & Themes", font=self.get_font(22, "bold"),
                     text_color="#ffffff").pack(anchor="w", pady=(10, 20))

        # Typography
        f_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        f_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(f_frame, text="App Font Family:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 15))
        self.font_dropdown = ctk.CTkOptionMenu(f_frame, values=FONTS, font=self.get_font(13),
                                               command=self.change_font, fg_color=self.theme["card"],
                                               button_color=self.theme["accent"])
        self.font_dropdown.set(self.settings.get("font", "Segoe UI"))
        self.font_dropdown.pack(side="left")

        # Effects
        e_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        e_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(e_frame, text="Hover Effects:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 15))
        self.effect_dropdown = ctk.CTkOptionMenu(e_frame, values=EFFECTS, font=self.get_font(13),
                                                 command=self.change_effect, fg_color=self.theme["card"],
                                                 button_color=self.theme["accent"])
        self.effect_dropdown.set(self.settings.get("effect", "Glow"))
        self.effect_dropdown.pack(side="left")

        # Main background
        bg_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        bg_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(bg_frame, text="Main Background:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 15))
        ctk.CTkButton(bg_frame, text="Upload Image/GIF", font=self.get_font(13, "bold"),
                      fg_color=self.theme["card"], hover_color=self.theme["accent"],
                      command=self.upload_bg).pack(side="left")
        ctk.CTkButton(bg_frame, text="Clear", font=self.get_font(13, "bold"), fg_color="#331c24",
                      hover_color="#ef4444", command=self.clear_bg).pack(side="left", padx=10)

        current_bg = self.settings.get("bg_image", "")
        bg_text = f"Active: {os.path.basename(current_bg)}" if current_bg else "Active: None"
        self.bg_status_lbl = ctk.CTkLabel(bg_frame, text=bg_text, font=self.get_font(12),
                                          text_color=self.theme["accent"])
        self.bg_status_lbl.pack(side="left", padx=15)

        # Title bar background
        tbg_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        tbg_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(tbg_frame, text="Title Bar BG:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 31))
        ctk.CTkButton(tbg_frame, text="Upload Header BG", font=self.get_font(13, "bold"),
                      fg_color=self.theme["card"], hover_color=self.theme["accent"],
                      command=self.upload_title_bg).pack(side="left")
        ctk.CTkButton(tbg_frame, text="Clear", font=self.get_font(13, "bold"), fg_color="#331c24",
                      hover_color="#ef4444", command=self.clear_title_bg).pack(side="left", padx=10)

        current_tbg = self.settings.get("title_bg", "")
        tbg_text = f"Active: {os.path.basename(current_tbg)}" if current_tbg else "Active: None"
        self.tbg_status_lbl = ctk.CTkLabel(tbg_frame, text=tbg_text, font=self.get_font(12),
                                           text_color=self.theme["accent"])
        self.tbg_status_lbl.pack(side="left", padx=15)

        # Color themes grid
        ctk.CTkLabel(self.settings_frame, text="Color Theme", font=self.get_font(18, "bold"),
                     text_color=self.theme["accent"]).pack(anchor="w", pady=(35, 15))

        themes_grid = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        themes_grid.pack(fill="x")

        row, col = 0, 0
        for t_name, t_colors in THEMES.items():
            t_btn = ctk.CTkButton(
                themes_grid, text=t_name, font=self.get_font(14, "bold"),
                fg_color=t_colors["card"], hover_color=t_colors["main"],
                border_color=t_colors["accent"], border_width=2,
                text_color=t_colors["accent"], width=150, height=55,
                command=lambda n=t_name: self.change_theme(n))
            t_btn.grid(row=row, column=col, padx=12, pady=12)
            col += 1
            if col > 3:
                col = 0
                row += 1

    # ------------------------------------------------------------------ toast
    def show_toast(self, message):
        if self._closing:
            return
        if self._toast_job is not None:                 # cancel the previous hide timer
            try:
                self.after_cancel(self._toast_job)
            except Exception:
                pass
        self.toast_label.configure(text=f" {message} ")
        self.toast_label.place(relx=0.5, rely=0.08, anchor="center")
        self.toast_label.lift()
        self._toast_job = self.after(2500, self._hide_toast)

    def _hide_toast(self):
        self._toast_job = None
        try:
            self.toast_label.place_forget()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ backgrounds
    def _clear_bg_image(self):
        try:
            self.bg_label.configure(image=None)
        except Exception:
            pass

    def load_background(self):
        self.animating = False
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

        bg_path = self.settings.get("bg_image", "")
        if not bg_path or not os.path.exists(bg_path):
            self._clear_bg_image()
            if hasattr(self, "bg_status_lbl"):
                self.bg_status_lbl.configure(text="Active: None")
            return

        try:
            img = Image.open(bg_path)
            theme_color = ImageColor.getrgb(self.theme["bg"])
            self.bg_frames = []
            self.bg_delays = []

            if getattr(img, "is_animated", False):
                for i, frame in enumerate(ImageSequence.Iterator(img)):
                    if i >= MAX_GIF_FRAMES:
                        break
                    f = frame.convert("RGBA")
                    f.thumbnail(BG_MAX_SIZE, Image.Resampling.LANCZOS)
                    overlay = Image.new("RGBA", f.size, theme_color + (190,))
                    blended = Image.alpha_composite(f, overlay)
                    self.bg_frames.append(ctk.CTkImage(light_image=blended, dark_image=blended, size=f.size))
                    delay = frame.info.get("duration", 60) or 60
                    self.bg_delays.append(max(20, int(delay)))
                self.current_frame = 0
                self.animating = len(self.bg_frames) > 1
                if self.animating:
                    self.animate_bg()
                elif self.bg_frames:
                    self.bg_label.configure(image=self.bg_frames[0])
            else:
                img = img.convert("RGBA")
                img.thumbnail(BG_MAX_SIZE, Image.Resampling.LANCZOS)
                overlay = Image.new("RGBA", img.size, theme_color + (205,))
                blended = Image.alpha_composite(img, overlay)
                self.bg_image_obj = ctk.CTkImage(light_image=blended, dark_image=blended, size=img.size)
                self.bg_label.configure(image=self.bg_image_obj)

            if hasattr(self, "bg_status_lbl"):
                self.bg_status_lbl.configure(text=f"Active: {os.path.basename(bg_path)}")

        except Exception as e:
            mb.showerror("Background Load Error", f"Could not load the background image:\n\n{e}")
            self.settings["bg_image"] = ""
            save_data(self.data)
            self._clear_bg_image()
            if hasattr(self, "bg_status_lbl"):
                self.bg_status_lbl.configure(text="Active: None")

    def animate_bg(self):
        if self._closing or not (self.animating and self.bg_frames):
            return
        self.bg_label.configure(image=self.bg_frames[self.current_frame])
        delay = self.bg_delays[self.current_frame] if self.bg_delays else 60
        self.current_frame = (self.current_frame + 1) % len(self.bg_frames)
        self._anim_job = self.after(delay, self.animate_bg)

    def load_title_background(self):
        tbg_path = self.settings.get("title_bg", "")
        self.title_bg_src = None
        if not tbg_path or not os.path.exists(tbg_path):
            self._clear_header_image()
            if hasattr(self, "tbg_status_lbl"):
                self.tbg_status_lbl.configure(text="Active: None")
            return

        try:
            self.title_bg_src = Image.open(tbg_path).convert("RGBA")
            self.header_frame.configure(fg_color="transparent")
            self._render_header_image()
            if hasattr(self, "tbg_status_lbl"):
                self.tbg_status_lbl.configure(text=f"Active: {os.path.basename(tbg_path)}")
        except Exception as e:
            print("Title BG Error:", e)
            self.title_bg_src = None
            self._clear_header_image()

    def _clear_header_image(self):
        try:
            self.header_bg_label.configure(image=None)
        except Exception:
            pass
        self.header_frame.configure(fg_color=self.theme["bg"])

    def _render_header_image(self):
        if self.title_bg_src is None:
            return
        w = max(self.header_frame.winfo_width(), 1200)
        img = self.title_bg_src.resize((w, 70), Image.Resampling.LANCZOS)
        self.title_bg_obj = ctk.CTkImage(light_image=img, dark_image=img, size=(w, 70))
        self.header_bg_label.configure(image=self.title_bg_obj)

    def _on_header_resize(self, event=None):
        if self.title_bg_src is None or self._closing:
            return
        if self._header_job is not None:
            try:
                self.after_cancel(self._header_job)
            except Exception:
                pass
        self._header_job = self.after(200, self._header_resize_commit)

    def _header_resize_commit(self):
        self._header_job = None
        self._render_header_image()

    # ------------------------------------------------------------------ settings actions
    def upload_title_bg(self):
        path = filedialog.askopenfilename(filetypes=IMAGE_TYPES)
        if path:
            self.settings["title_bg"] = path
            save_data(self.data)
            self.show_toast("Title BG Loaded! Rebooting...")
            self.after(1000, self.restart_app)

    def clear_title_bg(self):
        self.settings["title_bg"] = ""
        save_data(self.data)
        self.show_toast("Title BG Cleared! Rebooting...")
        self.after(1000, self.restart_app)

    def upload_bg(self):
        path = filedialog.askopenfilename(filetypes=IMAGE_TYPES)
        if path:
            self.settings["bg_image"] = path
            save_data(self.data)
            self.show_toast("Background Loaded! Rebooting...")
            self.after(1000, self.restart_app)

    def clear_bg(self):
        self.settings["bg_image"] = ""
        save_data(self.data)
        self.show_toast("Cleared! Rebooting...")
        self.after(1000, self.restart_app)

    def change_theme(self, theme_name):
        self.settings["theme"] = theme_name
        save_data(self.data)
        self.show_toast("Theme Updated! Rebooting...")
        self.after(1000, self.restart_app)

    def change_font(self, font_name):
        self.settings["font"] = font_name
        save_data(self.data)
        self.show_toast("Font Saved! Rebooting...")
        self.after(1000, self.restart_app)

    def change_effect(self, effect_name):
        self.settings["effect"] = effect_name
        self.active_effect = effect_name
        save_data(self.data)
        self.show_toast(f"{effect_name} Effects Enabled!")

    # ------------------------------------------------------------------ navigation
    def toggle_settings(self):
        self._flush_pending()
        self.viewing_settings = True
        self.active_sec_entry.delete(0, "end")
        self.active_sec_entry.insert(0, "Settings")
        self.notes_grid_frame.pack_forget()
        self.stream_scroll.pack_forget()
        self.composer_frame.pack_forget()
        self.settings_frame.pack(fill="both", expand=True)
        for btn in self.tab_buttons.values():
            btn.configure(fg_color="transparent", text_color="#8b9bb4")
        self.render_sidebar()                           # un-highlight the active section

    def load_notes(self, sec):
        grid = (list(sec.get("notes_grid") or [sec.get("notes", "")]) + [""] * 4)[:4]
        for tb, txt in zip(self.note_boxes, grid):
            tb.delete("0.0", "end")
            tb.insert("0.0", txt)

    def switch_tab(self, tab_key):
        self._flush_pending()
        self.viewing_settings = False
        self.current_tab = tab_key

        self.settings_frame.pack_forget()
        for key, btn in self.tab_buttons.items():
            btn.configure(fg_color=self.theme["card"] if key == tab_key else "transparent",
                          text_color="#ffffff" if key == tab_key else "#8b9bb4")

        sec = self.get_active_section()
        if sec:
            self.active_sec_entry.delete(0, "end")
            self.active_sec_entry.insert(0, sec["title"])

        if tab_key == "notes":
            self.stream_scroll.pack_forget()
            self.composer_frame.pack_forget()
            self.notes_grid_frame.pack(fill="both", expand=True)
            if sec:
                self.load_notes(sec)
        else:
            self.notes_grid_frame.pack_forget()
            self.composer_frame.pack_forget()
            # Pack the composer first (bottom) so it always keeps its space
            self.composer_frame.pack(side="bottom", fill="x", padx=30, pady=(0, 24), before=self.dynamic_area)
            self.stream_scroll.pack(fill="both", expand=True)

            ph_map = {"crosshairs": "Crosshair Code...", "links": "URL...", "snippets": "Message Text..."}
            self.entry_content.configure(placeholder_text=ph_map.get(tab_key, "Value"))
            self.render_cards()

        self.render_sidebar()

    # ------------------------------------------------------------------ saving edits (debounced)
    def save_section_title(self, event=None):
        if self.viewing_settings:
            return
        if self._title_job is not None:
            try:
                self.after_cancel(self._title_job)
            except Exception:
                pass
        self._title_job = self.after(400, self._commit_title)

    def _commit_title(self, render=True):
        self._title_job = None
        if self.viewing_settings:
            return
        sec = self.get_active_section()
        if sec:
            sec["title"] = self.active_sec_entry.get()
            save_data(self.data)
            if render and not self._closing:
                self.render_sidebar()

    def save_notes_text(self, event=None):
        if self._notes_job is not None:
            try:
                self.after_cancel(self._notes_job)
            except Exception:
                pass
        self._notes_job = self.after(300, self._commit_notes)

    def _commit_notes(self):
        self._notes_job = None
        sec = self.get_active_section()
        if sec and self.current_tab == "notes" and not self.viewing_settings:
            grid = [tb.get("0.0", "end").strip() for tb in self.note_boxes]
            sec["notes_grid"] = grid
            sec["notes"] = grid[0]                      # keeps the old single-note format working
            save_data(self.data)

    # ------------------------------------------------------------------ sidebar
    def render_sidebar(self):
        for widget in self.sections_scroll.winfo_children():
            widget.destroy()

        self.sections_count_label.configure(text=f"SECTIONS ({len(self.data['sections'])})")

        for sec in self.data["sections"]:
            is_active = sec["id"] == self.active_section_id and not self.viewing_settings
            bg_col = self.theme["card"] if is_active else "transparent"
            border_col = self.theme["accent"] if is_active else "transparent"

            item_btn = ctk.CTkFrame(self.sections_scroll, fg_color=bg_col, border_color=border_col,
                                    border_width=2, corner_radius=10)
            item_btn.pack(fill="x", pady=5)

            t_lbl = ctk.CTkLabel(item_btn, text=sec["title"], font=self.get_font(15, "bold"),
                                 text_color=self.theme["accent"] if is_active else "#e2e8f0")
            t_lbl.pack(side="left", padx=16, pady=12)

            del_btn = ctk.CTkButton(
                item_btn, text="✖ DELETE", font=self.get_font(10, "bold"), width=60, height=28,
                fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff",
                command=lambda s_id=sec["id"]: self.delete_section(s_id))
            del_btn.pack(side="right", padx=10, pady=12)

            for w in (item_btn, t_lbl):
                w.bind("<Button-1>", lambda e, s_id=sec["id"]: self.select_section(s_id))

    def delete_section(self, sec_id):
        if len(self.data["sections"]) <= 1:
            self.show_toast("Cannot delete the last section!")
            return

        if mb.askyesno("Delete Section", "Are you sure you want to permanently delete this section?"):
            self.data["sections"] = [s for s in self.data["sections"] if s["id"] != sec_id]
            if self.active_section_id == sec_id:
                self.active_section_id = self.data["sections"][0]["id"]
            save_data(self.data)
            self.switch_tab("snippets" if self.viewing_settings else self.current_tab)
            self.show_toast("Section deleted!")

    def select_section(self, sec_id):
        self._flush_pending()                           # save edits made in the previous section first
        self.active_section_id = sec_id
        target = "snippets" if self.viewing_settings else self.current_tab
        self.switch_tab(target)

    def create_new_section(self):
        dialog = ctk.CTkInputDialog(text="Enter new section name:", title="New Section")
        name = dialog.get_input()
        if name and name.strip():
            self._flush_pending()
            new_id = f"sec_{int(time.time() * 1000)}"
            self.data["sections"].append({
                "id": new_id, "title": name.strip(), "notes": "", "notes_grid": ["", "", "", ""],
                "crosshairs": [], "links": [], "snippets": [],
            })
            self.active_section_id = new_id
            save_data(self.data)
            self.after(200, self._finalize_new_section)

    def _finalize_new_section(self):
        if not self._closing:
            self.switch_tab("snippets")

    # ------------------------------------------------------------------ cards
    def render_cards(self):
        for widget in self.stream_scroll.winfo_children():
            widget.destroy()

        sec = self.get_active_section()
        if not sec:
            return
        items = sec.get(self.current_tab, [])

        has_bg = bool(self.settings.get("bg_image"))
        card_bg = "transparent" if has_bg else self.theme["bg"]

        def create_enter_event(c):
            def enter(e):
                try:
                    if not c.winfo_exists():
                        return
                    if c.hover_id is not None:
                        c.after_cancel(c.hover_id)
                        c.hover_id = None
                    if self.active_effect == "Glow":
                        c.configure(border_color=self.theme["accent"], fg_color=self.theme["card"])
                    elif self.active_effect == "Solid":
                        c.configure(border_color=self.theme["accent"], fg_color=self.theme["main"])
                    else:
                        c.configure(border_color=self.theme["accent"])
                except tk.TclError:
                    pass
            return enter

        def create_leave_event(c):
            def leave(e):
                def apply_leave():
                    try:
                        if c.winfo_exists():
                            c.configure(border_color=self.theme["card"], fg_color=card_bg)
                            c.hover_id = None
                    except tk.TclError:
                        pass
                try:
                    c.hover_id = c.after(50, apply_leave)
                except tk.TclError:
                    pass
            return leave

        for idx, item in enumerate(items):
            card = ctk.CTkFrame(self.stream_scroll, fg_color=card_bg, border_color=self.theme["card"],
                                border_width=2, corner_radius=12, height=60)
            card.pack(fill="x", pady=6)
            card.pack_propagate(False)
            card.hover_id = None

            badge = ctk.CTkLabel(card, text=f" {item.get('label', 'TAG').upper()} ", font=self.get_font(11, "bold"),
                                 fg_color=self.theme["card"], text_color="#cbd5e1", corner_radius=6)
            badge.pack(side="left", padx=(14, 12))

            full_text = item.get("text", "")
            shown = full_text.replace("\n", " ")
            if len(shown) > MAX_CARD_CHARS:
                shown = shown[:MAX_CARD_CHARS - 1] + "…"

            content_label = ctk.CTkLabel(card, text=shown, font=self.get_font(17),
                                         text_color="#f1f5f9", anchor="w")
            try:                                        # 'cursor' is not a CTkLabel arg in all versions
                content_label._label.configure(cursor="hand2")
            except Exception:
                pass
            content_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
            content_label.bind("<Button-1>", lambda e, val=full_text: self.copy_content(val, "Item"))

            btn_copy = ctk.CTkButton(card, text="⧉", font=self.get_font(16, "bold"), width=36,
                                     fg_color="transparent", hover_color=self.theme["main"],
                                     text_color=self.theme["accent"],
                                     command=lambda val=full_text: self.copy_content(val, "Item"))
            btn_copy.pack(side="right", padx=(4, 8))

            btn_del = ctk.CTkButton(card, text="🗑", font=self.get_font(15), width=36,
                                    fg_color="transparent", hover_color="#3c1a24", text_color="#64748b",
                                    command=lambda i_idx=idx: self.delete_item(i_idx))
            btn_del.pack(side="right")

            for w in (card, badge, content_label):
                w.bind("<Enter>", create_enter_event(card))
                w.bind("<Leave>", create_leave_event(card))

    def copy_content(self, text, label):
        # Built-in Tk clipboard: no pyperclip dependency needed
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()                                   # keeps the text available after the app closes
        self.show_toast("Copied to clipboard!")

    def save_current_item(self):
        badge = self.entry_badge.get().strip()
        content = self.entry_content.get().strip()
        sec = self.get_active_section()
        if badge and content and sec and self.current_tab in ("crosshairs", "links", "snippets"):
            sec.setdefault(self.current_tab, []).append(
                {"id": f"item_{int(time.time() * 1000)}", "label": badge, "text": content})
            save_data(self.data)
            self.entry_badge.delete(0, "end")
            self.entry_content.delete(0, "end")
            self.render_cards()
            self.show_toast("Saved successfully!")

    def delete_item(self, idx):
        sec = self.get_active_section()
        if sec and self.current_tab in sec and 0 <= idx < len(sec[self.current_tab]):
            del sec[self.current_tab][idx]
            save_data(self.data)
            self.render_cards()


if __name__ == "__main__":
    app = ValoPadApp()
    app.mainloop()
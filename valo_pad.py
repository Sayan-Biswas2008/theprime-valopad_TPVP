import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import filedialog
import pyperclip
import json
import os
import sys
import time
import subprocess
import ctypes
from PIL import Image, ImageColor, ImageSequence

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "valo_pad_data.json")
LOGO_FILE = os.path.join(BASE_DIR, "logo.ico")

THEMES = {
    "Default": {"bg": "#0c0f17", "main": "#141a27", "accent": "#00d2d3", "card": "#182030"},
    "Black": {"bg": "#000000", "main": "#050505", "accent": "#ffffff", "card": "#0f0f0f"},
    "Radiant": {"bg": "#120d14", "main": "#1a1525", "accent": "#ff4655", "card": "#241b2d"},
    "Icebox": {"bg": "#0a1014", "main": "#101820", "accent": "#00ffff", "card": "#15202b"},
    "Lotus": {"bg": "#1c101c", "main": "#251525", "accent": "#ff79c6", "card": "#301b30"},
    "Reaver": {"bg": "#0d0a14", "main": "#151020", "accent": "#a855f7", "card": "#1e152d"},
    "Prime": {"bg": "#14120a", "main": "#1a1810", "accent": "#fde047", "card": "#262215"},
    "Glitchpop": {"bg": "#100a1c", "main": "#151025", "accent": "#ec4899", "card": "#201535"},
    "Sovereign": {"bg": "#0a1414", "main": "#152020", "accent": "#fde047", "card": "#1a2a2a"}
}

FONTS = [
    "Segoe UI", "Bahnschrift", "Consolas", "Arial", "Trebuchet MS", 
    "Verdana", "Tahoma", "Courier New", "Comic Sans MS", "Georgia"
]

EFFECTS = ["Glow", "Solid", "Minimal"]

DEFAULT_DATA = {
    "settings": {
        "font": "Segoe UI",
        "theme": "Reaver",
        "bg_image": "",
        "title_bg": "",
        "effect": "Glow"
    },
    "sections": [
        {
            "id": "sec_1",
            "title": "General",
            "accounts": [
                {
                    "ign": "MAJOR SAMAL",
                    "username": "Immoneninenineeight",
                    "password": "",
                    "is_available": True,
                    "is_banned": False,
                    "unban_time": 0,
                    "is_idp_changed": False
                }
            ],
            "notes": [],
            "crosshairs": [
                {"id": "c1", "label": "TENZ", "text": "0;s;1;P;c;5;h;0;m;1;0l;4;0o;2;0a;1;0f;0;1b;0"}
            ],
            "links": [],
            "snippets": [
                {"id": "s1", "label": "YT", "text": "Hi I am live on yt --> @Itz_PRiM3 . hope to see u there!"}
            ]
        }
    ]
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "settings" in data and "title_bg" not in data["settings"]:
                data["settings"]["title_bg"] = ""
            return data
    except Exception:
        return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class ValoPadApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("THE PRIME - VALO PAD")
        self.geometry("1250x760")
        self.minsize(1050, 640)
        
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ThePrime.ValoPad.App")
            self.iconbitmap(LOGO_FILE)
        except Exception:
            pass
        
        self.data = load_data()
        self.settings = self.data.get("settings", DEFAULT_DATA["settings"])
        if "sections" not in self.data:
            self.data = {"settings": self.settings, "sections": self.data if isinstance(self.data, list) else []}
            
        self.active_section_id = self.data["sections"][0]["id"] if self.data["sections"] else None
        self.current_tab = "accounts" 
        self.viewing_settings = False
        
        self.bg_image_obj = None
        self.bg_frames = []
        self.current_frame = 0
        self.animating = False

        self.title_bg_obj = None
        self.title_bg_frames = []
        self.current_title_frame = 0
        self.animating_title = False
        
        self.countdown_labels = []

        self.apply_theme_colors()
        self.build_ui()
        self.load_background()
        self.load_title_background()
        self.render_sidebar()
        self.switch_tab(self.current_tab)
        self.update_clock()
        self.update_countdowns()

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
        save_data(self.data)
        self.destroy()
        script_path = os.path.abspath(sys.argv[0])
        subprocess.Popen([sys.executable, script_path])

    def update_clock(self):
        time_str = time.strftime("%A, %d %b  |  %I:%M %p")
        self.time_label.configure(text=time_str)
        self.after(1000, self.update_clock)

    def update_countdowns(self):
        current_time = time.time()
        needs_rerender = False
        
        for item in list(self.countdown_labels):
            lbl = item["label"]
            unban_time = item["unban_time"]
            acc = item["acc"]
            
            if not lbl.winfo_exists():
                self.countdown_labels.remove(item)
                continue
                
            rem = unban_time - current_time
            if rem <= 0:
                acc["is_banned"] = False
                acc["is_available"] = True
                acc["unban_time"] = 0
                needs_rerender = True
            else:
                days = int(rem // 86400)
                hrs = int((rem % 86400) // 3600)
                mins = int((rem % 3600) // 60)
                secs = int(rem % 60)
                
                txt = ""
                if days > 0: txt += f"{days}d "
                txt += f"{hrs:02d}:{mins:02d}:{secs:02d}"
                lbl.configure(text=f"({txt})")
                
        if needs_rerender:
            save_data(self.data)
            self.render_accounts()
            
        self.after(1000, self.update_countdowns)

    def build_ui(self):
        self.bg_label = ctk.CTkLabel(self, text="")
        self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.overlay_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.overlay_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.header_frame = ctk.CTkFrame(self.overlay_frame, fg_color=self.theme["bg"], height=70, corner_radius=0, border_width=2, border_color=self.theme["main"])
        self.header_frame.pack(side="top", fill="x")
        self.header_frame.pack_propagate(False)

        self.header_bg_label = ctk.CTkLabel(self.header_frame, text="")
        self.header_bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        brand_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_frame.pack(side="left", padx=24, pady=12)

        icon_label = ctk.CTkLabel(brand_frame, text="⟁", font=self.get_font(28, "bold"), text_color=self.theme["accent"])
        icon_label.pack(side="left", padx=(0, 12))

        title_label = ctk.CTkLabel(brand_frame, text="THE PRIME\nVALO PAD", font=self.get_font(16, "bold"), text_color="#ffffff", justify="left")
        title_label.pack(side="left")

        self.time_label = ctk.CTkLabel(self.header_frame, text="", font=self.get_font(15, "bold"), text_color=self.theme["accent"])
        self.time_label.pack(side="right", padx=30, pady=20)

        self.body_frame = ctk.CTkFrame(self.overlay_frame, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        self.sidebar_frame = ctk.CTkFrame(self.body_frame, fg_color=self.theme["bg"] if not self.settings.get("bg_image") else "transparent", width=330, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        sidebar_top = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        sidebar_top.pack(fill="x", padx=16, pady=(20, 10))

        self.sections_count_label = ctk.CTkLabel(sidebar_top, text="SECTIONS", font=self.get_font(13, "bold"), text_color="#8b9bb4")
        self.sections_count_label.pack(side="left")

        self.btn_new_sec = ctk.CTkButton(
            sidebar_top, text="+ NEW SECTION", font=self.get_font(11, "bold"),
            fg_color="transparent", hover_color=self.theme["accent"], text_color=self.theme["accent"],
            border_color=self.theme["accent"], border_width=2, width=110, height=28, corner_radius=14,
            command=self.create_new_section
        )
        self.btn_new_sec.pack(side="right")

        self.sections_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.sections_scroll.pack(fill="both", expand=True, padx=12, pady=(10, 10))

        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame, text="⚙ SETTINGS", font=self.get_font(13, "bold"),
            fg_color=self.theme["card"], hover_color=self.theme["main"], text_color=self.theme["accent"],
            height=45, corner_radius=10, command=self.toggle_settings
        )
        self.btn_settings.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_restart = ctk.CTkButton(
            self.sidebar_frame, text="⟳ RESTART APP", font=self.get_font(13, "bold"),
            fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff",
            height=45, corner_radius=10, command=self.restart_app
        )
        self.btn_restart.pack(fill="x", padx=16, pady=(0, 20))

        self.main_frame = ctk.CTkFrame(self.body_frame, fg_color="transparent", corner_radius=0)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=(1, 0))

        self.panel_header = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=45)
        self.panel_header.pack(fill="x", padx=30, pady=(24, 16))

        self.active_sec_entry = ctk.CTkEntry(
            self.panel_header, font=self.get_font(28, "bold"), text_color=self.theme["accent"],
            fg_color="transparent", border_width=0, width=500
        )
        self.active_sec_entry.pack(side="left")
        self.active_sec_entry.bind("<KeyRelease>", self.save_section_title)

        self.subtabs_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=35)
        self.subtabs_bar.pack(fill="x", padx=30, pady=(0, 16))

        self.tabs_meta = [
            ("accounts", "👥 Accounts"), ("notes", "🗎 Notes"), ("crosshairs", "⌖ Crosshairs"),
            ("links", "🔗 Links"), ("snippets", "💬 Chat Snippets")
        ]
        self.tab_buttons = {}
        for key, title in self.tabs_meta:
            btn = ctk.CTkButton(
                self.subtabs_bar, text=title, font=self.get_font(14, "bold"),
                fg_color="transparent", hover_color=self.theme["card"], text_color="#8b9bb4",
                width=115, height=34, corner_radius=8, command=lambda k=key: self.switch_tab(k)
            )
            btn.pack(side="left", padx=(0, 8))
            self.tab_buttons[key] = btn

        self.dynamic_area = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.dynamic_area.pack(fill="both", expand=True, padx=30, pady=(0, 12))

        # --- MULTIPLE ACCOUNTS CONTAINER ---
        self.accounts_container = ctk.CTkFrame(self.dynamic_area, fg_color="transparent")
        
        acc_top = ctk.CTkFrame(self.accounts_container, fg_color="transparent")
        acc_top.pack(fill="x", pady=(0, 5))
        
        self.btn_add_acc = ctk.CTkButton(
            acc_top, text="+ ADD ACCOUNT", font=self.get_font(12, "bold"),
            fg_color=self.theme["card"], hover_color=self.theme["main"], text_color=self.theme["accent"],
            command=self.add_account
        )
        self.btn_add_acc.pack(side="left")
        
        self.filter_var = ctk.StringVar(value="All")
        self.opt_filter = ctk.CTkOptionMenu(
            acc_top, values=["All", "Available", "Banned", "IDP Changed"], variable=self.filter_var, 
            font=self.get_font(12, "bold"), text_color="#ffffff", 
            fg_color=self.theme["card"], button_color=self.theme["main"],
            command=lambda e: self.render_accounts()
        )
        self.opt_filter.pack(side="right", padx=10)
        
        ctk.CTkLabel(acc_top, text="Sort:", font=self.get_font(13, "bold"), text_color="#8b9bb4").pack(side="right")

        acc_sub = ctk.CTkFrame(self.accounts_container, fg_color="transparent")
        acc_sub.pack(fill="x", pady=(0, 10))

        self.lbl_total_ids = ctk.CTkLabel(acc_sub, text="Total IDs: 0", font=self.get_font(13, "bold"), text_color=self.theme["accent"])
        self.lbl_total_ids.pack(side="left")

        self.search_var = ctk.StringVar()
        self.entry_search = ctk.CTkEntry(acc_sub, textvariable=self.search_var, placeholder_text="Search by IGN...", font=self.get_font(13), height=32, width=220, border_color=self.theme["main"], fg_color=self.theme["card"])
        self.entry_search.pack(side="right", padx=10)
        self.entry_search.bind("<KeyRelease>", lambda e: self.render_accounts())
        
        self.accounts_scroll = ctk.CTkScrollableFrame(self.accounts_container, fg_color="transparent")
        self.accounts_scroll.pack(fill="both", expand=True)

        # Configure columns for standard grid distribution inside scrollframe
        self.accounts_scroll.grid_columnconfigure(0, weight=1)
        self.accounts_scroll.grid_columnconfigure(1, weight=1)

        self.stream_scroll = ctk.CTkScrollableFrame(self.dynamic_area, fg_color="transparent")
        self.settings_frame = ctk.CTkScrollableFrame(self.dynamic_area, fg_color="transparent")

        self.composer_frame = ctk.CTkFrame(self.main_frame, fg_color=self.theme["card"], corner_radius=14)
        self.composer_title = ctk.CTkLabel(self.composer_frame, text="💬 SAVE NEW ITEM", font=self.get_font(12, "bold"), text_color=self.theme["accent"])
        self.composer_title.pack(anchor="w", padx=20, pady=(14, 6))

        inputs_row = ctk.CTkFrame(self.composer_frame, fg_color="transparent")
        inputs_row.pack(fill="x", padx=20, pady=(0, 18))

        self.entry_badge = ctk.CTkEntry(inputs_row, placeholder_text="Label", fg_color=self.theme["bg"], border_color=self.theme["bg"], font=self.get_font(14), height=42, width=200, corner_radius=8)
        self.entry_badge.pack(side="left", padx=(0, 12))

        self.entry_content = ctk.CTkEntry(inputs_row, placeholder_text="Content...", fg_color=self.theme["bg"], border_color=self.theme["bg"], font=self.get_font(14), height=42, corner_radius=8)
        self.entry_content.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.btn_save = ctk.CTkButton(
            inputs_row, text="SAVE", font=self.get_font(14, "bold"), fg_color=self.theme["accent"], 
            text_color="#000000", height=42, width=140, corner_radius=8, command=self.save_current_item
        )
        self.btn_save.pack(side="right")

        self.toast_label = ctk.CTkLabel(self.overlay_frame, text="", font=self.get_font(13, "bold"), text_color="#000000", fg_color=self.theme["accent"], corner_radius=10, height=36, width=220)
        self.build_settings_tab()

    def build_settings_tab(self):
        lbl = ctk.CTkLabel(self.settings_frame, text="Appearance & Themes", font=self.get_font(22, "bold"), text_color="#ffffff")
        lbl.pack(anchor="w", pady=(10, 20))

        f_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        f_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(f_frame, text="App Font Family:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 15))
        self.font_dropdown = ctk.CTkOptionMenu(f_frame, values=FONTS, font=self.get_font(13), command=self.change_font, fg_color=self.theme["card"], button_color=self.theme["accent"])
        self.font_dropdown.set(self.settings.get("font", "Segoe UI"))
        self.font_dropdown.pack(side="left")

        e_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        e_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(e_frame, text="Hover Effects:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 15))
        self.effect_dropdown = ctk.CTkOptionMenu(e_frame, values=EFFECTS, font=self.get_font(13), command=self.change_effect, fg_color=self.theme["card"], button_color=self.theme["accent"])
        self.effect_dropdown.set(self.settings.get("effect", "Glow"))
        self.effect_dropdown.pack(side="left")

        bg_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        bg_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(bg_frame, text="Main Background:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 15))
        ctk.CTkButton(bg_frame, text="Upload Image/GIF", font=self.get_font(13, "bold"), fg_color=self.theme["card"], hover_color=self.theme["accent"], command=self.upload_bg).pack(side="left")
        ctk.CTkButton(bg_frame, text="Clear", font=self.get_font(13, "bold"), fg_color="#331c24", hover_color="#ef4444", command=self.clear_bg).pack(side="left", padx=10)

        current_bg = self.settings.get("bg_image", "")
        bg_text = f"Active: {os.path.basename(current_bg)}" if current_bg else "Active: None"
        self.bg_status_lbl = ctk.CTkLabel(bg_frame, text=bg_text, font=self.get_font(12), text_color=self.theme["accent"])
        self.bg_status_lbl.pack(side="left", padx=15)

        tbg_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        tbg_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(tbg_frame, text="Title Bar BG:", font=self.get_font(15, "bold")).pack(side="left", padx=(0, 31))
        ctk.CTkButton(tbg_frame, text="Upload Image/GIF", font=self.get_font(13, "bold"), fg_color=self.theme["card"], hover_color=self.theme["accent"], command=self.upload_title_bg).pack(side="left")
        ctk.CTkButton(tbg_frame, text="Clear", font=self.get_font(13, "bold"), fg_color="#331c24", hover_color="#ef4444", command=self.clear_title_bg).pack(side="left", padx=10)

        current_tbg = self.settings.get("title_bg", "")
        tbg_text = f"Active: {os.path.basename(current_tbg)}" if current_tbg else "Active: None"
        self.tbg_status_lbl = ctk.CTkLabel(tbg_frame, text=tbg_text, font=self.get_font(12), text_color=self.theme["accent"])
        self.tbg_status_lbl.pack(side="left", padx=15)

        ctk.CTkLabel(self.settings_frame, text="Color Theme", font=self.get_font(18, "bold"), text_color=self.theme["accent"]).pack(anchor="w", pady=(35, 15))
        
        themes_grid = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        themes_grid.pack(fill="x")
        
        row, col = 0, 0
        for t_name, t_colors in THEMES.items():
            t_btn = ctk.CTkButton(
                themes_grid, text=t_name, font=self.get_font(14, "bold"),
                fg_color=t_colors["card"], hover_color=t_colors["main"], 
                border_color=t_colors["accent"], border_width=2,
                text_color=t_colors["accent"], width=150, height=55,
                command=lambda n=t_name: self.change_theme(n)
            )
            t_btn.grid(row=row, column=col, padx=12, pady=12)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def show_toast(self, message):
        self.toast_label.configure(text=f" {message} ")
        self.toast_label.place(relx=0.5, rely=0.08, anchor="center")
        self.after(2500, self.toast_label.place_forget)

    def load_background(self):
        self.animating = False
        bg_path = self.settings.get("bg_image", "")
        
        if not bg_path or not os.path.exists(bg_path):
            self.bg_label.configure(image="")
            if hasattr(self, 'bg_status_lbl'):
                self.bg_status_lbl.configure(text="Active: None")
            return

        try:
            img = Image.open(bg_path)
            theme_color = ImageColor.getrgb(self.theme["bg"])
            self.bg_frames = []

            if getattr(img, "is_animated", False):
                self.animating = True
                for i, frame in enumerate(ImageSequence.Iterator(img)):
                    if i > 50: break
                    f = frame.convert("RGBA")
                    f.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                    overlay = Image.new("RGBA", f.size, theme_color + (190,))
                    blended = Image.alpha_composite(f, overlay)
                    self.bg_frames.append(ctk.CTkImage(light_image=blended, dark_image=blended, size=f.size))
                
                self.current_frame = 0
                self.animate_bg()
            else:
                img = img.convert("RGBA")
                img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                overlay = Image.new("RGBA", img.size, theme_color + (205,))
                blended = Image.alpha_composite(img, overlay)
                self.bg_image_obj = ctk.CTkImage(light_image=blended, dark_image=blended, size=img.size)
                self.bg_label.configure(image=self.bg_image_obj)

            if hasattr(self, 'bg_status_lbl'):
                self.bg_status_lbl.configure(text=f"Active: {os.path.basename(bg_path)}")
            
        except Exception as e:
            mb.showerror("Background Load Error", f"Could not load the background image:\n\n{e}")
            self.settings["bg_image"] = ""
            save_data(self.data)
            self.bg_label.configure(image="")
            if hasattr(self, 'bg_status_lbl'):
                self.bg_status_lbl.configure(text="Active: None")

    def animate_bg(self):
        if self.animating and self.bg_frames:
            self.bg_label.configure(image=self.bg_frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.bg_frames)
            self.after(60, self.animate_bg)

    def load_title_background(self):
        self.animating_title = False
        tbg_path = self.settings.get("title_bg", "")
        
        if not tbg_path or not os.path.exists(tbg_path):
            self.header_bg_label.configure(image="")
            self.header_frame.configure(fg_color=self.theme["bg"])
            if hasattr(self, 'tbg_status_lbl'):
                self.tbg_status_lbl.configure(text="Active: None")
            return

        try:
            img = Image.open(tbg_path)
            self.title_bg_frames = []

            if getattr(img, "is_animated", False):
                self.animating_title = True
                for i, frame in enumerate(ImageSequence.Iterator(img)):
                    if i > 50: break
                    f = frame.convert("RGBA")
                    f = f.resize((1200, 70), Image.Resampling.LANCZOS)
                    self.title_bg_frames.append(ctk.CTkImage(light_image=f, dark_image=f, size=(1200, 70)))
                
                self.current_title_frame = 0
                self.animate_title_bg()
            else:
                img = img.convert("RGBA")
                img = img.resize((1200, 70), Image.Resampling.LANCZOS)
                self.title_bg_obj = ctk.CTkImage(light_image=img, dark_image=img, size=(1200, 70))
                self.header_bg_label.configure(image=self.title_bg_obj)
                self.header_frame.configure(fg_color="transparent")
                
            if hasattr(self, 'tbg_status_lbl'):
                self.tbg_status_lbl.configure(text=f"Active: {os.path.basename(tbg_path)}")
                
        except Exception as e:
            print("Title BG Error:", e)
            self.header_bg_label.configure(image="")
            self.header_frame.configure(fg_color=self.theme["bg"])

    def animate_title_bg(self):
        if self.animating_title and self.title_bg_frames:
            self.header_bg_label.configure(image=self.title_bg_frames[self.current_title_frame])
            self.current_title_frame = (self.current_title_frame + 1) % len(self.title_bg_frames)
            self.after(60, self.animate_title_bg)

    def upload_title_bg(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
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
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
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

    def toggle_settings(self):
        self.viewing_settings = True
        self.active_sec_entry.delete(0, "end")
        self.active_sec_entry.insert(0, "Settings")
        self.accounts_container.pack_forget()
        self.stream_scroll.pack_forget()
        self.composer_frame.pack_forget()
        self.settings_frame.pack(fill="both", expand=True)
        for btn in self.tab_buttons.values():
            btn.configure(fg_color="transparent", text_color="#8b9bb4")

    def switch_tab(self, tab_key):
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

        if tab_key == "accounts":
            self.stream_scroll.pack_forget()
            self.composer_frame.pack_forget()
            self.accounts_container.pack(fill="both", expand=True, pady=(10, 0))
            self.render_accounts()
        else:
            self.accounts_container.pack_forget()
            self.stream_scroll.pack(fill="both", expand=True)
            self.composer_frame.pack(fill="x", padx=30, pady=(0, 24))
            
            ph_map = {"notes": "Note Text...", "crosshairs": "Crosshair Code...", "links": "URL...", "snippets": "Message Text..."}
            self.entry_content.configure(placeholder_text=ph_map.get(tab_key, "Value"))
            self.render_cards()

    def copy_val(self, var):
        val = var.get()
        if val:
            pyperclip.copy(val)
            self.show_toast("Copied to clipboard!")

    def save_section_title(self, event=None):
        if self.viewing_settings: return
        sec = self.get_active_section()
        if sec:
            sec["title"] = self.active_sec_entry.get()
            save_data(self.data)
            self.render_sidebar()

    def add_account(self):
        sec = self.get_active_section()
        if sec:
            if "accounts" not in sec:
                sec["accounts"] = []
            sec["accounts"].append({
                "ign": "", "username": "", "password": "", 
                "is_available": False, "is_banned": False, "unban_time": 0, "is_idp_changed": False
            })
            save_data(self.data)
            self.filter_var.set("All") 
            self.render_accounts()

    def delete_account_card(self, idx):
        sec = self.get_active_section()
        if sec and "accounts" in sec:
            del sec["accounts"][idx]
            save_data(self.data)
            self.render_accounts()

    def render_accounts(self):
        for widget in self.accounts_scroll.winfo_children():
            widget.destroy()

        self.countdown_labels.clear()
        sec = self.get_active_section()
        if not sec: return
        
        if "accounts" not in sec:
            sec["accounts"] = []

        total_ids = len(sec["accounts"])
        self.lbl_total_ids.configure(text=f"Total IDs: {total_ids}")

        show_filter = self.filter_var.get()
        search_q = self.search_var.get().lower().strip()

        row_idx = 0
        col_idx = 0

        for idx, acc in enumerate(sec["accounts"]):
            if show_filter == "Available" and not acc.get("is_available", False): continue
            if show_filter == "Banned" and not acc.get("is_banned", False): continue
            if show_filter == "IDP Changed" and not acc.get("is_idp_changed", False): continue
            
            if search_q and search_q not in acc.get("ign", "").lower():
                continue
            
            card = ctk.CTkFrame(self.accounts_scroll, fg_color=self.theme["card"], corner_radius=10, border_color=self.theme["main"], border_width=2)
            card.grid(row=row_idx, column=col_idx, sticky="nsew", padx=6, pady=8)

            col_idx += 1
            if col_idx > 1:
                col_idx = 0
                row_idx += 1

            left_col = ctk.CTkFrame(card, fg_color="transparent")
            left_col.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
            
            right_col = ctk.CTkFrame(card, fg_color="transparent")
            right_col.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

            card.ign_var = ctk.StringVar(value=acc.get("ign", ""))
            card.user_var = ctk.StringVar(value=acc.get("username", ""))
            card.pass_var = ctk.StringVar(value=acc.get("password", ""))
            card.chk_var = ctk.BooleanVar(value=acc.get("is_available", False))
            card.ban_var = ctk.BooleanVar(value=acc.get("is_banned", False))
            card.idp_var = ctk.BooleanVar(value=acc.get("is_idp_changed", False))

            def get_saver(i=idx, c=card):
                def saver(event=None):
                    sec["accounts"][i]["ign"] = c.ign_var.get()
                    sec["accounts"][i]["username"] = c.user_var.get()
                    sec["accounts"][i]["password"] = c.pass_var.get()
                    sec["accounts"][i]["is_available"] = c.chk_var.get()
                    sec["accounts"][i]["is_idp_changed"] = c.idp_var.get()
                    save_data(self.data)
                return saver

            saver = get_saver(idx, card)

            def get_ban_toggler(i=idx, c=card):
                def toggler():
                    if c.ban_var.get():
                        dialog = ctk.CTkInputDialog(text="Enter Ban Duration (in days):", title="Account Banned")
                        val = dialog.get_input()
                        try:
                            days = float(val)
                            sec["accounts"][i]["is_banned"] = True
                            sec["accounts"][i]["is_available"] = False
                            sec["accounts"][i]["unban_time"] = time.time() + (days * 86400)
                            c.chk_var.set(False)
                        except (ValueError, TypeError):
                            c.ban_var.set(False)
                            sec["accounts"][i]["is_banned"] = False
                    else:
                        sec["accounts"][i]["is_banned"] = False
                        sec["accounts"][i]["unban_time"] = 0
                    save_data(self.data)
                    self.render_accounts()
                return toggler

            r1 = ctk.CTkFrame(left_col, fg_color="transparent")
            r1.pack(fill="x", pady=(0, 5))
            ctk.CTkLabel(r1, text="🎮 IGN", font=self.get_font(13, "bold"), text_color=self.theme["accent"], width=50, anchor="w").pack(side="left")
            ign_e = ctk.CTkEntry(r1, textvariable=card.ign_var, height=32, font=self.get_font(14))
            ign_e.pack(side="left", fill="x", expand=True, padx=(10, 10))
            ign_e.bind("<KeyRelease>", saver)

            r2 = ctk.CTkFrame(left_col, fg_color="transparent")
            r2.pack(fill="x", pady=5)
            ctk.CTkLabel(r2, text="👤 User", font=self.get_font(13, "bold"), text_color=self.theme["accent"], width=50, anchor="w").pack(side="left")
            usr_e = ctk.CTkEntry(r2, textvariable=card.user_var, height=32, font=self.get_font(14))
            usr_e.pack(side="left", fill="x", expand=True, padx=(10, 5))
            usr_e.bind("<KeyRelease>", saver)
            ctk.CTkButton(r2, text="⧉", font=self.get_font(16, "bold"), width=32, height=32, fg_color="transparent", text_color=self.theme["accent"], hover_color=self.theme["main"], command=lambda v=card.user_var: self.copy_val(v)).pack(side="left", padx=(0, 10))

            r3 = ctk.CTkFrame(left_col, fg_color="transparent")
            r3.pack(fill="x", pady=5)
            ctk.CTkLabel(r3, text="🔑 Pass", font=self.get_font(13, "bold"), text_color=self.theme["accent"], width=50, anchor="w").pack(side="left")
            pas_e = ctk.CTkEntry(r3, textvariable=card.pass_var, height=32, font=self.get_font(14))
            pas_e.pack(side="left", fill="x", expand=True, padx=(10, 5))
            pas_e.bind("<KeyRelease>", saver)
            ctk.CTkButton(r3, text="⧉", font=self.get_font(16, "bold"), width=32, height=32, fg_color="transparent", text_color=self.theme["accent"], hover_color=self.theme["main"], command=lambda v=card.pass_var: self.copy_val(v)).pack(side="left", padx=(0, 10))

            ctk.CTkButton(right_col, text="✖ DEL", font=self.get_font(11, "bold"), width=50, height=26, fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff", command=lambda i=idx: self.delete_account_card(i)).pack(anchor="e", pady=(0, 10))
            
            ctk.CTkCheckBox(right_col, text="Available to Play", variable=card.chk_var, font=self.get_font(12, "bold"), text_color="#cbd5e1", command=saver).pack(anchor="w", pady=4)
            ctk.CTkCheckBox(right_col, text="IDP Changed", variable=card.idp_var, font=self.get_font(12, "bold"), text_color="#cbd5e1", command=saver).pack(anchor="w", pady=4)
            
            ban_f = ctk.CTkFrame(right_col, fg_color="transparent")
            ban_f.pack(fill="x", pady=4)
            ctk.CTkCheckBox(ban_f, text="BANNED", variable=card.ban_var, font=self.get_font(12, "bold"), text_color="#ef4444", command=get_ban_toggler(idx, card)).pack(side="left")
            
            if acc.get("is_banned") and acc.get("unban_time", 0) > 0:
                card.countdown_lbl = ctk.CTkLabel(ban_f, text="", font=self.get_font(13, "bold"), text_color="#ffb7b7", width=110, anchor="w")
                card.countdown_lbl.pack(side="left", padx=(8, 0))
                self.countdown_labels.append({"label": card.countdown_lbl, "unban_time": acc["unban_time"], "acc": acc})

    def render_sidebar(self):
        for widget in self.sections_scroll.winfo_children():
            widget.pack_forget()
            widget.destroy()

        self.sections_scroll.update_idletasks()
        self.sections_count_label.configure(text=f"SECTIONS ({len(self.data['sections'])})")

        for sec in self.data["sections"]:
            is_active = sec["id"] == self.active_section_id and not self.viewing_settings
            bg_col = self.theme["card"] if is_active else "transparent"
            border_col = self.theme["accent"] if is_active else self.theme["bg"]
            b_width = 2 if is_active else 0

            item_btn = ctk.CTkFrame(self.sections_scroll, fg_color=bg_col, border_color=border_col, border_width=b_width, corner_radius=10)
            item_btn.pack(fill="x", pady=5)

            t_lbl = ctk.CTkLabel(item_btn, text=sec["title"], font=self.get_font(15, "bold"), text_color=self.theme["accent"] if is_active else "#e2e8f0")
            t_lbl.pack(side="left", padx=16, pady=12)

            del_btn = ctk.CTkButton(
                item_btn, text="✖ DELETE", font=self.get_font(10, "bold"), width=60, height=28,
                fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff",
                command=lambda s_id=sec["id"]: self.delete_section(s_id)
            )
            del_btn.pack(side="right", padx=10, pady=12)

            for w in [item_btn, t_lbl]:
                w.bind("<Button-1>", lambda e, s_id=sec["id"]: self.select_section(s_id))

        self.sections_scroll.update_idletasks()

    def delete_section(self, sec_id):
        if len(self.data["sections"]) <= 1:
            self.show_toast("Cannot delete the last section!")
            return
            
        confirm = mb.askyesno("Delete Section", "Are you sure you want to permanently delete this section?")
        if confirm:
            self.data["sections"] = [s for s in self.data["sections"] if s["id"] != sec_id]
            if self.active_section_id == sec_id:
                self.active_section_id = self.data["sections"][0]["id"]
            save_data(self.data)
            self.render_sidebar()
            self.switch_tab("accounts" if self.viewing_settings else self.current_tab)
            self.show_toast("Section deleted!")

    def select_section(self, sec_id):
        self.active_section_id = sec_id
        if self.viewing_settings:
            self.switch_tab("accounts")
        self.render_sidebar()
        self.switch_tab(self.current_tab)

    def render_cards(self):
        for widget in self.stream_scroll.winfo_children():
            widget.pack_forget()
            widget.destroy()

        self.stream_scroll.update_idletasks()
        sec = self.get_active_section()
        if not sec: return
        
        items = sec.get(self.current_tab, [])
        if isinstance(items, str):
            items = [{"id": f"item_{int(time.time()*1000)}", "label": "NOTE", "text": items}] if items else []
            sec[self.current_tab] = items
            save_data(self.data)

        has_bg = bool(self.settings.get("bg_image"))
        card_bg = "transparent" if has_bg else self.theme["bg"]

        def create_enter_event(c):
            def enter(e):
                if c.hover_id is not None:
                    c.after_cancel(c.hover_id)
                    c.hover_id = None
                if self.active_effect == "Glow":
                    c.configure(border_color=self.theme["accent"], fg_color=self.theme["card"])
                elif self.active_effect == "Solid":
                    c.configure(border_color=self.theme["accent"], fg_color=self.theme["main"])
                else:
                    c.configure(border_color=self.theme["accent"])
            return enter

        def create_leave_event(c):
            def leave(e):
                def apply_leave():
                    c.configure(border_color=self.theme["card"], fg_color=card_bg)
                    c.hover_id = None
                c.hover_id = c.after(50, apply_leave)
            return leave

        for idx, item in enumerate(items):
            card = ctk.CTkFrame(self.stream_scroll, fg_color=card_bg, border_color=self.theme["card"], border_width=2, corner_radius=12, height=60)
            card.pack(fill="x", pady=6)
            card.pack_propagate(False)
            card.hover_id = None
            
            badge = ctk.CTkLabel(card, text=f" {item.get('label', 'TAG').upper()} ", font=self.get_font(11, "bold"), fg_color=self.theme["card"], text_color="#cbd5e1", corner_radius=6)
            badge.pack(side="left", padx=(14, 12))

            content_text = item.get("text", "")
            content_label = ctk.CTkLabel(card, text=content_text, font=self.get_font(17), text_color="#f1f5f9", anchor="w", cursor="hand2")
            content_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
            content_label.bind("<Button-1>", lambda e, val=content_text: self.copy_content(val, "Item"))

            btn_copy = ctk.CTkButton(card, text="⧉", font=self.get_font(16, "bold"), width=36, fg_color="transparent", hover_color=self.theme["main"], text_color=self.theme["accent"], command=lambda val=content_text: self.copy_content(val, "Item"))
            btn_copy.pack(side="right", padx=(4, 8))

            btn_del = ctk.CTkButton(card, text="🗑", font=self.get_font(15), width=36, fg_color="transparent", hover_color="#3c1a24", text_color="#64748b", command=lambda i_idx=idx: self.delete_item(i_idx))
            btn_del.pack(side="right")

            for w in [card, badge, content_label]:
                w.bind("<Enter>", create_enter_event(card))
                w.bind("<Leave>", create_leave_event(card))

    def copy_content(self, text, label):
        pyperclip.copy(text)
        self.show_toast("Copied to clipboard!")

    def save_current_item(self):
        badge = self.entry_badge.get().strip()
        content = self.entry_content.get().strip()
        sec = self.get_active_section()
        if badge and content and sec:
            if self.current_tab not in sec: sec[self.current_tab] = []
            sec[self.current_tab].append({"id": f"item_{int(time.time()*1000)}", "label": badge, "text": content})
            save_data(self.data)
            self.entry_badge.delete(0, "end")
            self.entry_content.delete(0, "end")
            self.render_cards()
            self.show_toast("Saved successfully!")

    def delete_item(self, idx):
        sec = self.get_active_section()
        if sec and self.current_tab in sec:
            del sec[self.current_tab][idx]
            save_data(self.data)
            self.render_cards()

    def create_new_section(self):
        dialog = ctk.CTkInputDialog(text="Enter new section name:", title="New Section")
        name = dialog.get_input()
        if name and name.strip():
            new_id = f"sec_{int(time.time()*1000)}"
            self.data["sections"].append({"id": new_id, "title": name.strip(), "accounts": [], "notes": [], "crosshairs": [], "links": [], "snippets": []})
            self.active_section_id = new_id
            save_data(self.data)
            self.after(200, self._finalize_new_section)
            
    def _finalize_new_section(self):
        self.render_sidebar()
        self.switch_tab("accounts")

if __name__ == "__main__":
    app = ValoPadApp()
    app.mainloop()
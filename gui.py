"""
WhatsApp Sales Automation Engine — Desktop GUI (tkinter, stdlib only).

Run with:  python gui.py

A windowed console around the dispatch engine. The data pipeline (pipeline.py),
dashboard export, and WhatsApp dispatcher are reused unchanged; only the interactive
questionary prompts are replaced by native dialogs, and dispatch progress streams into
a live log pane via a background thread + thread-safe queue.
"""

import json
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from config import (
    WAIT_TIME, TAB_CLOSE, CLOSE_TIME, COOL_DOWN, MAX_RETRIES, FOCUS_TIMEOUT,
    TEST_MODE, TEST_LIMIT, SALES_FILE_PREFIX, SALES_FILE_EXTENSION,
    COL_DEPOT, COL_VENDOR, COL_PARTY, COL_PRIORITY,
)
import pipeline
import dashboard
import dispatcher
from main import load_settings, save_settings

# ---------------------------------------------------------------------------
# Palette & fonts
# ---------------------------------------------------------------------------
BG         = "#0f172a"   # window background (dark slate)
PANEL      = "#16233a"   # panel background
PANEL2     = "#1e2c45"   # raised panel / input background
FG         = "#e2e8f0"   # default text
MUTED      = "#8ba3c7"   # secondary text
ACCENT     = "#25d366"   # whatsapp green
ACCENT_HI  = "#43e07a"   # hover
ACCENT_TXT = "#04250f"   # text on accent
DANGER     = "#ef4444"
BORDER     = "#2b3b58"

UI_FONT    = ("Segoe UI", 10)
BOLD_FONT  = ("Segoe UI", 10, "bold")
TITLE_FONT = ("Segoe UI", 15, "bold")
MONO_FONT  = ("Consolas", 10)

DAILY_REPORT   = "Daily Sales Progress Report (Invoiced / Balance)"
MONTHLY_REPORT = "Start-of-Month Target Announcement"

FILTER_ALL      = "all"
FILTER_PRIORITY = "priority"
FILTER_GROUPS   = "groups"
FILTER_CUSTOM   = "custom"

CUSTOM_GROUPS_FILE = "custom_groups.json"


# ---------------------------------------------------------------------------
# Small reusable dialogs
# ---------------------------------------------------------------------------
def _center_over(parent, win, w, h):
    """Centers `win` over `parent`, clamped to the screen so large dialogs never clip."""
    parent.update_idletasks()
    screen_w = parent.winfo_screenwidth()
    screen_h = parent.winfo_screenheight()
    w = min(w, screen_w - 40)
    h = min(h, screen_h - 80)
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
    x = max(0, min(x, screen_w - w))
    y = max(0, min(y, screen_h - h))
    win.geometry(f"{w}x{h}+{x}+{y}")


def multi_select_dialog(parent, title, options, preselect=None):
    """
    Scrollable checklist dialog.
    Returns the list of selected options, or None when cancelled.
    """
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=PANEL)
    dlg.transient(parent)
    _center_over(parent, dlg, 440, min(560, 120 + len(options) * 28))
    result = {"value": None}
    preselect = set(preselect or [])

    top = tk.Frame(dlg, bg=PANEL)
    top.pack(fill="both", expand=True, padx=10, pady=10)
    canvas = tk.Canvas(top, bg=PANEL, highlightthickness=0)
    scroll = ttk.Scrollbar(top, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=PANEL)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    vars_ = {}
    for opt in options:
        var = tk.IntVar(value=1 if opt in preselect else 0)
        cb = tk.Checkbutton(inner, text=opt, variable=var, bg=PANEL, fg=FG,
                            activebackground=PANEL, activeforeground=FG,
                            selectcolor=PANEL2, anchor="w", font=UI_FONT)
        cb.pack(fill="x", padx=8, pady=2)
        vars_[opt] = var

    btns = tk.Frame(dlg, bg=PANEL)
    btns.pack(fill="x", padx=10, pady=(0, 10))

    def ok():
        result["value"] = [o for o, v in vars_.items() if v.get()]
        dlg.destroy()

    ttk.Button(btns, text="  OK  ", style="Accent.TButton", command=ok).pack(side="right", padx=4)
    ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)

    dlg.grab_set()
    dlg.wait_window()
    return result["value"]


def message_preview_dialog(parent, items):
    """
    Pre-dispatch review dialog. Left: the queued accounts. Right: the exact WhatsApp
    message (already rendered by templates.py via the pipeline) for the selected
    account. Returns True to proceed with dispatch, False to cancel.
    """
    dlg = tk.Toplevel(parent)
    dlg.title("Message Preview — verify before dispatch")
    dlg.configure(bg=PANEL)
    dlg.transient(parent)
    _center_over(parent, dlg, 940, 680)
    result = {"value": False}

    top = tk.Frame(dlg, bg=PANEL)
    top.pack(fill="both", expand=True, padx=12, pady=(12, 8))

    # ---- left: queued accounts ----
    left = tk.Frame(top, bg=PANEL2)
    left.pack(side="left", fill="y")
    tk.Label(left, text="ACCOUNTS IN QUEUE", bg=PANEL2, fg=ACCENT, font=BOLD_FONT).pack(anchor="w", padx=8, pady=(6, 2))
    list_frame = tk.Frame(left, bg=PANEL2)
    list_frame.pack(fill="both", expand=True, padx=4, pady=4)
    listbox = tk.Listbox(list_frame, bg=PANEL2, fg=FG, relief="flat", selectbackground=ACCENT,
                         selectforeground=ACCENT_TXT, font=UI_FONT, highlightthickness=0, width=34)
    scroll = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
    listbox.configure(yscrollcommand=scroll.set)
    listbox.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    for it in items:
        label = it["party"] if not it.get("phone") else f"{it['party']}   ·   {it['phone']}"
        listbox.insert("end", label)

    # ---- right: exact message ----
    right = tk.Frame(top, bg=PANEL2)
    right.pack(side="left", fill="both", expand=True, padx=(10, 0))
    tk.Label(right, text="EXACT WHATSAPP MESSAGE", bg=PANEL2, fg=ACCENT, font=BOLD_FONT).pack(anchor="w", padx=8, pady=(6, 2))
    text = scrolledtext.ScrolledText(right, wrap="word", bg=PANEL2, fg=FG, insertbackground=FG,
                                     font=MONO_FONT, relief="flat", padx=12, pady=10,
                                     state="disabled", highlightthickness=0)
    text.pack(fill="both", expand=True, padx=(4, 8), pady=(0, 8))

    def show(_event=None):
        sel = listbox.curselection()
        if not sel:
            return
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("1.0", items[sel[0]]["message"])
        text.configure(state="disabled")

    listbox.bind("<<ListboxSelect>>", show)
    if items:
        listbox.selection_set(0)
        show()

    # ---- bottom actions ----
    btns = tk.Frame(dlg, bg=PANEL)
    btns.pack(fill="x", padx=12, pady=(0, 12))
    tk.Label(btns, text="WhatsApp Desktop must be open & logged in before continuing.",
             bg=PANEL, fg=MUTED, font=UI_FONT).pack(side="left")

    def proceed():
        result["value"] = True
        dlg.destroy()

    ttk.Button(btns, text="  Continue Dispatch →  ", style="Accent.TButton", command=proceed).pack(side="right", padx=4)
    ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)
    dlg.bind("<Escape>", lambda _e: dlg.destroy())

    dlg.grab_set()
    dlg.wait_window()
    return result["value"]


def brand_dialog(parent, current):
    """
    Add/edit brand dialog (code, name, target column, actual column).
    Returns (code, name, target_col, actual_col) or None when cancelled.
    """
    dlg = tk.Toplevel(parent)
    dlg.title("Edit Brand" if current else "Add New Brand")
    dlg.configure(bg=PANEL)
    dlg.transient(parent)
    _center_over(parent, dlg, 400, 300)
    result = {"value": None}

    cur_code = current[0] if current else ""
    rows = [
        ("Short Code (e.g. OCW)", cur_code),
        ("Display Name", current[1] if current else ""),
        ("Master Target Column", current[2] if current else ""),
        ("Sales Actual Column", current[3] if current else ""),
    ]
    entries = {}
    body = tk.Frame(dlg, bg=PANEL)
    body.pack(fill="both", expand=True, padx=16, pady=16)
    for i, (label, value) in enumerate(rows):
        tk.Label(body, text=label, bg=PANEL, fg=MUTED, font=UI_FONT).grid(row=i, column=0, sticky="w", pady=6)
        var = tk.StringVar(value=value)
        entry = tk.Entry(body, textvariable=var, bg=PANEL2, fg=FG, insertbackground=FG,
                         relief="flat", font=UI_FONT)
        entry.grid(row=i, column=1, sticky="ew", pady=6, padx=(10, 0))
        entries[["code", "name", "target_col", "actual_col"][i]] = var
    body.columnconfigure(1, weight=1)

    btns = tk.Frame(dlg, bg=PANEL)
    btns.pack(fill="x", padx=16, pady=(0, 14))

    def ok():
        code = entries["code"].get().strip().upper()
        if not code:
            messagebox.showwarning("Code required", "Brand short code cannot be empty.", parent=dlg)
            return
        result["value"] = (
            code,
            entries["name"].get().strip() or code,
            entries["target_col"].get().strip() or f"{code}_TARGET",
            entries["actual_col"].get().strip() or f"{code}.1",
        )
        dlg.destroy()

    ttk.Button(btns, text="  Save  ", style="Accent.TButton", command=ok).pack(side="right", padx=4)
    ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)

    dlg.grab_set()
    dlg.wait_window()
    return result["value"]


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WhatsApp Sales Automation Engine")
        self.geometry("1280x800")
        self.minsize(1120, 700)
        self.configure(bg=BG)

        self.settings = load_settings()
        self.sales_file = None
        self.df_sales = None
        self.df_master = None
        self.master_parties = []
        self.depot_vars = {}
        self.groups_selection = []
        self.custom_recipient = None
        self.custom_outlets = None
        self.log_q = queue.Queue()
        self.busy = False

        self._setup_style()
        self._build_ui()
        self._refresh_brand_list()
        self._refresh_file_list()
        self.after(100, self._pump_log)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL2, foreground=MUTED, padding=(16, 9), font=UI_FONT)
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", ACCENT_TXT)])
        style.configure("TButton", background=PANEL2, foreground=FG, font=UI_FONT, padding=(10, 6), borderwidth=0)
        style.map("TButton", background=[("active", "#2a3b5c"), ("disabled", "#131c2e")],
                  foreground=[("disabled", "#5c6f8f")])
        style.configure("Accent.TButton", background=ACCENT, foreground=ACCENT_TXT,
                        font=BOLD_FONT, padding=(14, 9), borderwidth=0)
        style.map("Accent.TButton", background=[("active", ACCENT_HI)])
        style.configure("Vertical.TScrollbar", background=PANEL2, troughcolor=PANEL, borderwidth=0)
        # ttk widgets reject font= directly — fonts must live in a style.
        style.configure("UI.TCombobox", font=UI_FONT, fieldbackground=PANEL2, background=PANEL2,
                        foreground=FG, arrowcolor=FG)
        style.map("UI.TCombobox", fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", FG)])
        self.option_add("*TCombobox*Listbox.background", PANEL2)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", ACCENT_TXT)

    def _build_ui(self):
        # ---- header banner ----
        header = tk.Frame(self, bg=ACCENT, padx=20, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="🚀 WHATSAPP SALES AUTOMATION ENGINE", bg=ACCENT, fg=ACCENT_TXT,
                 font=TITLE_FONT).pack(anchor="w")
        tk.Label(header, text="Territory Sales Dispatch — Desktop Console", bg=ACCENT, fg=ACCENT_TXT,
                 font=UI_FONT).pack(anchor="w")

        # ---- main split: left setup / right log ----
        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(paned, width=440)
        right = ttk.Frame(paned)
        paned.add(left, weight=0)
        paned.add(right, weight=1)

        notebook = ttk.Notebook(left)
        notebook.pack(fill="both", expand=True)
        notebook.add(self._build_run_tab(notebook), text="  ▶ Run  ")
        notebook.add(self._build_profile_tab(notebook), text="  👤 Profile  ")
        notebook.add(self._build_brands_tab(notebook), text="  🍾 Brands  ")

        self._build_log_panel(right)

        # ---- status bar ----
        self.status_bar = tk.Label(self, text="Ready", bg=PANEL2, fg=MUTED, anchor="w",
                                   padx=12, font=UI_FONT)
        self.status_bar.pack(fill="x")

    # ------------------------------------------------------ Run tab
    def _build_run_tab(self, parent):
        tab = tk.Frame(parent, bg=PANEL, padx=14, pady=12)

        # Sales file
        tk.Label(tab, text="SALES FILE", bg=PANEL, fg=ACCENT, font=BOLD_FONT).pack(anchor="w")
        file_row = tk.Frame(tab, bg=PANEL)
        file_row.pack(fill="x", pady=(4, 2))
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(file_row, textvariable=self.file_var, style="UI.TCombobox")
        self.file_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text="Browse…", command=self._browse_file).pack(side="left", padx=(6, 0))
        btn_row = tk.Frame(tab, bg=PANEL)
        btn_row.pack(fill="x", pady=(0, 10))
        ttk.Button(btn_row, text="Load File", command=self._load_file).pack(side="left")
        ttk.Button(btn_row, text="Refresh List", command=self._refresh_file_list).pack(side="left", padx=(6, 0))
        self.file_status = tk.Label(tab, text="No file loaded", bg=PANEL, fg=MUTED, font=UI_FONT)
        self.file_status.pack(anchor="w", pady=(0, 12))

        # Report type
        tk.Label(tab, text="REPORT TYPE", bg=PANEL, fg=ACCENT, font=BOLD_FONT).pack(anchor="w")
        self.report_var = tk.StringVar(value=DAILY_REPORT)
        tk.Radiobutton(tab, text="Daily Sales Progress Report (Invoiced / Balance)", variable=self.report_var,
                       value=DAILY_REPORT, bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=FG,
                       selectcolor=PANEL2, anchor="w", font=UI_FONT).pack(fill="x", anchor="w")
        tk.Radiobutton(tab, text="Start-of-Month Target Announcement", variable=self.report_var,
                       value=MONTHLY_REPORT, bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=FG,
                       selectcolor=PANEL2, anchor="w", font=UI_FONT).pack(fill="x", anchor="w", pady=(0, 12))

        # Depots
        tk.Label(tab, text="DEPOTS TO PROCESS", bg=PANEL, fg=ACCENT, font=BOLD_FONT).pack(anchor="w")
        depot_head = tk.Frame(tab, bg=PANEL)
        depot_head.pack(fill="x")
        self.depot_count = tk.Label(depot_head, text="0 depots", bg=PANEL, fg=MUTED, font=UI_FONT)
        self.depot_count.pack(side="left")
        ttk.Button(depot_head, text="Select All", command=lambda: self._set_all_depots(1)).pack(side="right", padx=2)
        ttk.Button(depot_head, text="Clear", command=lambda: self._set_all_depots(0)).pack(side="right", padx=2)
        depot_body = tk.Frame(tab, bg=PANEL2)
        depot_body.pack(fill="x", pady=(4, 2))
        depot_canvas = tk.Canvas(depot_body, bg=PANEL2, highlightthickness=0, height=150)
        depot_scroll = ttk.Scrollbar(depot_body, orient="vertical", command=depot_canvas.yview)
        self.depot_inner = tk.Frame(depot_canvas, bg=PANEL2)
        self.depot_window_id = depot_canvas.create_window((0, 0), window=self.depot_inner, anchor="nw")
        self.depot_inner.bind("<Configure>", lambda e: depot_canvas.configure(scrollregion=depot_canvas.bbox("all")))
        depot_canvas.configure(yscrollcommand=depot_scroll.set)
        depot_canvas.pack(side="left", fill="both", expand=True)
        depot_scroll.pack(side="right", fill="y")
        depot_canvas.bind("<Configure>",
                          lambda e: depot_canvas.itemconfigure(self.depot_window_id, width=e.width))

        # Filter mode
        tk.Label(tab, text="FILTER STRATEGY", bg=PANEL, fg=ACCENT, font=BOLD_FONT).pack(anchor="w", pady=(10, 0))
        self.filter_var = tk.StringVar(value=FILTER_ALL)
        for key, label in [
            (FILTER_ALL, "All Eligible Accounts (Standard Pacing Rules)"),
            (FILTER_PRIORITY, "Filter by Specific Priority Slab (A / B / C)"),
            (FILTER_GROUPS, "Select Individual Groups / Syndicates / Outlets"),
            (FILTER_CUSTOM, "Custom Consolidation (Cross-Syndicate Outlets)"),
        ]:
            tk.Radiobutton(tab, text=label, variable=self.filter_var, value=key,
                           bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=FG,
                           selectcolor=PANEL2, anchor="w", font=UI_FONT,
                           command=self._toggle_filter_mode).pack(fill="x", anchor="w")

        # filter sub-widgets — all inside a fixed sub-frame so toggling modes never
        # reorders the tab layout (pack_forget/pack on the rows themselves would push
        # the active row below the Start button).
        self.filter_extras = tk.Frame(tab, bg=PANEL)

        self.priority_row = tk.Frame(self.filter_extras, bg=PANEL)
        tk.Label(self.priority_row, text="Priority tier:", bg=PANEL, fg=FG, font=UI_FONT).pack(side="left")
        self.priority_var = tk.StringVar(value="A")
        ttk.Combobox(self.priority_row, textvariable=self.priority_var, values=["A", "B", "C"],
                     state="readonly", width=6, style="UI.TCombobox").pack(side="left", padx=6)

        self.groups_row = tk.Frame(self.filter_extras, bg=PANEL)
        ttk.Button(self.groups_row, text="Choose Groups…", command=self._choose_groups).pack(side="left")
        self.groups_status = tk.Label(self.groups_row, text="none selected", bg=PANEL, fg=MUTED, font=UI_FONT)
        self.groups_status.pack(side="left", padx=8)

        self.custom_row = tk.Frame(self.filter_extras, bg=PANEL)
        tk.Label(self.custom_row, text="Recipient:", bg=PANEL, fg=FG, font=UI_FONT).pack(side="left")
        self.party_combo = ttk.Combobox(self.custom_row, state="readonly", width=22, style="UI.TCombobox")
        self.party_combo.pack(side="left", padx=6)
        ttk.Button(self.custom_row, text="Choose Outlets…", command=self._choose_custom_outlets).pack(side="left", padx=(6, 0))
        self.custom_status = tk.Label(self.filter_extras, text="", bg=PANEL, fg=MUTED, font=UI_FONT)

        self.filter_extras.pack(fill="x", pady=(6, 2))
        self._toggle_filter_mode()

        # Start button
        self.start_btn = ttk.Button(tab, text="▶ START DISPATCH", style="Accent.TButton",
                                    command=self._start_dispatch)
        self.start_btn.pack(fill="x", pady=(16, 4))
        tk.Label(tab, text="Dispatch requires WhatsApp Desktop (Windows) open & logged in.",
                 bg=PANEL, fg=MUTED, font=UI_FONT, justify="left", wraplength=380).pack(anchor="w")
        return tab

    def _toggle_filter_mode(self):
        mode = self.filter_var.get()
        for row in (self.priority_row, self.groups_row, self.custom_row, self.custom_status):
            row.pack_forget()
        if mode == FILTER_PRIORITY:
            self.priority_row.pack(fill="x", pady=(2, 0))
        elif mode == FILTER_GROUPS:
            self.groups_row.pack(fill="x", pady=(2, 0))
        elif mode == FILTER_CUSTOM:
            self.custom_row.pack(fill="x", pady=(2, 0))
            self.custom_status.pack(anchor="w", pady=(2, 2))

    # --------------------------------------------------- Profile tab
    def _build_profile_tab(self, parent):
        tab = tk.Frame(parent, bg=PANEL, padx=18, pady=16)
        tk.Label(tab, text="USER PROFILE", bg=PANEL, fg=ACCENT, font=BOLD_FONT).pack(anchor="w", pady=(0, 12))
        profile = self.settings.get("profile", {})
        self.profile_name = tk.StringVar(value=profile.get("name", ""))
        self.profile_designation = tk.StringVar(value=profile.get("designation", ""))
        self.profile_agency = tk.StringVar(value=profile.get("agency", ""))
        for label, var in [
            ("Executive Name", self.profile_name),
            ("Designation", self.profile_designation),
            ("Agency / Distributor", self.profile_agency),
        ]:
            tk.Label(tab, text=label, bg=PANEL, fg=MUTED, font=UI_FONT).pack(anchor="w", pady=(8, 2))
            tk.Entry(tab, textvariable=var, bg=PANEL2, fg=FG, insertbackground=FG,
                     relief="flat", font=UI_FONT).pack(fill="x", ipady=5)
        ttk.Button(tab, text="Save Profile", style="Accent.TButton",
                   command=self._save_profile).pack(anchor="w", pady=(18, 0))
        tk.Label(tab, text="The profile is used in the message header & signature.",
                 bg=PANEL, fg=MUTED, font=UI_FONT, justify="left", wraplength=360).pack(anchor="w", pady=(10, 0))
        return tab

    # --------------------------------------------------- Brands tab
    def _build_brands_tab(self, parent):
        tab = tk.Frame(parent, bg=PANEL, padx=14, pady=12)
        tk.Label(tab, text="BRAND PORTFOLIO & COLUMN MAPPING", bg=PANEL, fg=ACCENT,
                 font=BOLD_FONT).pack(anchor="w", pady=(0, 8))
        list_frame = tk.Frame(tab, bg=PANEL2)
        list_frame.pack(fill="both", expand=True)
        self.brand_list = tk.Listbox(list_frame, bg=PANEL2, fg=FG, relief="flat",
                                     selectbackground=ACCENT, selectforeground=ACCENT_TXT,
                                     font=UI_FONT, highlightthickness=0)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.brand_list.yview)
        self.brand_list.configure(yscrollcommand=scroll.set)
        self.brand_list.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        scroll.pack(side="right", fill="y", pady=4)
        btns = tk.Frame(tab, bg=PANEL)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="➕ Add", command=self._add_brand).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="✏️ Edit", command=self._edit_brand).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="❌ Remove", command=self._remove_brand).pack(side="left")
        return tab

    # ---------------------------------------------------- Log panel
    def _build_log_panel(self, parent):
        tk.Label(parent, text="LIVE DISPATCH LOG", bg=BG, fg=ACCENT, font=BOLD_FONT).pack(anchor="w", padx=4)
        self.log_pane = scrolledtext.ScrolledText(parent, wrap="word", bg=PANEL2, fg=FG,
                                                  insertbackground=FG, font=MONO_FONT,
                                                  relief="flat", padx=12, pady=10,
                                                  state="disabled", highlightthickness=0)
        self.log_pane.pack(fill="both", expand=True, pady=(6, 8))

        summary = tk.Frame(parent, bg=PANEL2, padx=14, pady=10)
        summary.pack(fill="x")
        tk.Label(summary, text="RUN SUMMARY", bg=PANEL2, fg=ACCENT, font=BOLD_FONT).pack(side="left", padx=(0, 18))
        self.summary_success = tk.StringVar(value="0")
        self.summary_failed = tk.StringVar(value="0")
        self.summary_skipped = tk.StringVar(value="0")
        for label, var, color in [
            ("Success", self.summary_success, ACCENT),
            ("Failed", self.summary_failed, DANGER),
            ("Skipped", self.summary_skipped, MUTED),
        ]:
            box = tk.Frame(summary, bg=PANEL2)
            box.pack(side="left", padx=10)
            tk.Label(box, text=label.upper(), bg=PANEL2, fg=MUTED, font=("Segoe UI", 8)).pack()
            tk.Label(box, textvariable=var, bg=PANEL2, fg=color, font=("Segoe UI", 16, "bold")).pack()

    # --------------------------------------------------------- actions
    def _refresh_file_list(self):
        files = [f for f in os.listdir(".") if f.startswith(SALES_FILE_PREFIX) and f.endswith(SALES_FILE_EXTENSION)]
        files.sort(reverse=True)
        self.file_combo["values"] = files
        if files and not self.file_var.get():
            self.file_var.set(files[0])

    def _browse_file(self):
        path = filedialog.askopenfilename(
            parent=self, title="Select sales dump",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialdir=os.getcwd())
        if path:
            self.file_var.set(path)  # keep the full path so existence checks pass for any folder
            self._load_file()

    def _load_file(self):
        name = self.file_var.get().strip()
        if not name or not os.path.exists(name):
            messagebox.showerror("File not found",
                                 f"'{name}' does not exist in the project folder.\n\n"
                                 "Pick a file with Browse… or Refresh List.", parent=self)
            return
        try:
            df_sales, df_master = pipeline.load_dataframes(name)
        except Exception as e:
            messagebox.showerror("Load failed", f"Could not read '{name}':\n{e}", parent=self)
            return
        depots = sorted([d for d in df_sales[COL_DEPOT].unique() if d])
        if not depots:
            messagebox.showerror("No depots", "No valid depots found in the sales file.", parent=self)
            return

        # Only commit state once the file has been validated.
        self.sales_file = name
        self.df_sales, self.df_master = df_sales, df_master

        for w in self.depot_inner.winfo_children():
            w.destroy()
        self.depot_vars = {}
        for d in depots:
            var = tk.IntVar(value=1)
            tk.Checkbutton(self.depot_inner, text=d, variable=var, bg=PANEL2, fg=FG,
                           activebackground=PANEL2, activeforeground=FG, selectcolor=PANEL2,
                           anchor="w", font=UI_FONT).pack(fill="x", padx=6, pady=1)
            self.depot_vars[d] = var
        self.depot_count.config(text=f"{len(depots)} depots found")

        self.master_parties = sorted([p for p in df_master[COL_PARTY].unique() if p])
        self.party_combo["values"] = self.master_parties

        self.file_status.config(text=f"Loaded: {name}  ·  {len(depots)} depots  ·  {len(self.master_parties)} accounts",
                                fg=ACCENT)
        self._log(f"✅ Loaded '{name}' — {len(depots)} depots, {len(self.master_parties)} master accounts.")

    def _set_all_depots(self, value):
        for var in self.depot_vars.values():
            var.set(value)

    def _choose_groups(self):
        if not self.master_parties:
            messagebox.showwarning("No file", "Load a sales file first.", parent=self)
            return
        selected = multi_select_dialog(self, "Select groups / syndicates to broadcast to",
                                       self.master_parties, preselect=self.groups_selection)
        if selected is None:
            return
        self.groups_selection = selected
        self.groups_status.config(text=f"{len(selected)} selected", fg=ACCENT if selected else MUTED)

    def _load_custom_groups(self):
        if os.path.exists(CUSTOM_GROUPS_FILE):
            try:
                with open(CUSTOM_GROUPS_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _choose_custom_outlets(self):
        recipient = self.party_combo.get().strip()
        if not recipient:
            messagebox.showwarning("Recipient", "Choose the target recipient from the dropdown first.", parent=self)
            return
        if self.df_sales is None:
            messagebox.showwarning("No file", "Load a sales file first.", parent=self)
            return
        outlets = sorted([o for o in self.df_sales[COL_VENDOR].unique() if o])
        saved = self._load_custom_groups()
        preselect = None
        if recipient in saved:
            if messagebox.askyesno("Saved preset",
                                   f"Use the saved {len(saved[recipient])}-outlet group for '{recipient}'?",
                                   parent=self):
                preselect = saved[recipient]
        selected = multi_select_dialog(self, f"Outlets to consolidate for '{recipient}'",
                                       outlets, preselect=preselect)
        if selected is None:
            return
        if not selected:
            messagebox.showwarning("No outlets", "Select at least one outlet.", parent=self)
            return
        if messagebox.askyesno("Save preset",
                               f"Save this {len(selected)}-outlet group for '{recipient}' for future runs?",
                               parent=self):
            saved[recipient] = selected
            with open(CUSTOM_GROUPS_FILE, "w") as f:
                json.dump(saved, f, indent=4)
            self._log(f"💾 Saved custom group for '{recipient}' ({len(selected)} outlets).")
        self.custom_recipient = recipient
        self.custom_outlets = selected
        self.custom_status.config(text=f"{recipient} ← {len(selected)} outlets", fg=ACCENT)

    # ----------------------------------------------------- dispatch flow
    def _start_dispatch(self):
        if self.busy:
            return
        if not self.settings.get("brands"):
            messagebox.showerror("Empty portfolio", "Add at least one brand in the Brands tab first.", parent=self)
            return
        name = self.file_var.get().strip()
        if not name or not os.path.exists(name):
            messagebox.showerror("No sales file", "Choose and load an Outlet_Wise_Sales_*.xlsx file first.", parent=self)
            return
        selected_depots = [d for d, var in self.depot_vars.items() if var.get()]
        if not selected_depots:
            messagebox.showerror("No depots", "Select at least one depot to process.", parent=self)
            return

        self._set_busy(True)
        self._log(f"🔄 Preparing run with '{name}' …")
        try:
            if self.df_sales is None:
                self.df_sales, self.df_master = pipeline.load_dataframes(name)
            report_date, file_date_str, remaining_days = pipeline.compute_run_dates(name)

            df_sales = self.df_sales[self.df_sales[COL_DEPOT].isin(selected_depots)].copy()
            if df_sales.empty:
                raise ValueError("No transactions found for the selected depot(s).")
            df_master = self.df_master

            brand_map, sales_brands, target_cols, market_names = pipeline.build_brand_map(self.settings)
            pipeline.cast_sales_columns(df_sales, sales_brands)
            pipeline.cast_target_columns(df_master, target_cols)

            mode = self.filter_var.get()
            allowed_parties = None
            custom_run_config = None
            if mode == FILTER_PRIORITY:
                tier = self.priority_var.get()
                allowed_parties = set(df_master[df_master[COL_PRIORITY].str.upper() == tier][COL_PARTY])
                if not allowed_parties:
                    raise ValueError(f"No master accounts found with priority '{tier}'.")
            elif mode == FILTER_GROUPS:
                if not self.groups_selection:
                    raise ValueError("No groups selected — click 'Choose Groups…' first.")
                allowed_parties = set(self.groups_selection)
            elif mode == FILTER_CUSTOM:
                if not self.custom_recipient or not self.custom_outlets:
                    raise ValueError("Custom consolidation needs a recipient and at least one outlet "
                                     "(choose them above).")
                custom_run_config = {"recipient": self.custom_recipient, "outlets": self.custom_outlets}

            actual_perf, brand_level_outlets = pipeline.aggregate_actuals(df_sales, sales_brands)
            user_profile = self.settings["profile"]
            report_type = self.report_var.get()

            if custom_run_config:
                unordered_queue = [pipeline.build_custom_item(
                    df_master, df_sales, brand_map, market_names, user_profile,
                    report_type, report_date, remaining_days, custom_run_config)]
                dashboard_rows, missing_contacts = [], []
            else:
                def drill_down_resolver(party, outlets):
                    opts = [o["vendor_name"] for o in outlets]
                    return multi_select_dialog(self, f"Isolate outlets of '{party}'", opts)

                unordered_queue, dashboard_rows, missing_contacts = pipeline.build_regular_items(
                    df_master, actual_perf, brand_level_outlets, brand_map, sales_brands,
                    market_names, user_profile, report_type, report_date, remaining_days,
                    allowed_parties=allowed_parties, drill_down_resolver=drill_down_resolver)

            if not custom_run_config and dashboard_rows:
                dashboard.export_territory_dashboard(dashboard_rows, file_date_str, brand_map.keys())
                self._log(f"📊 Dashboard exported: exports/territory_intelligence_dashboard_{file_date_str}.xlsx")
            pipeline.export_missing_contacts(missing_contacts, file_date_str)
            if missing_contacts:
                self._log(f"📝 {len(missing_contacts)} missing accounts written to logs/.")

            dispatch_queue = pipeline.build_dispatch_queue(unordered_queue)
            if TEST_MODE:
                dispatch_queue = dispatch_queue[:TEST_LIMIT]
                self._log(f"🧪 TEST_MODE is ON — queue capped at {TEST_LIMIT} item(s).")
            if not dispatch_queue:
                raise ValueError("No accounts qualified for dispatch (all on track). "
                                 "Try a filtered mode or lower thresholds.")
        except Exception as e:
            messagebox.showerror("Run preparation failed", str(e), parent=self)
            self._set_busy(False)
            return

        # Let the operator eyeball every queued message before anything is sent.
        if not message_preview_dialog(self, dispatch_queue):
            self._log("👁️ Preview cancelled — no messages were sent.")
            self._set_busy(False)
            return

        self._log(f"🚀 Dispatching to {len(dispatch_queue)} contact(s) — do not touch keyboard/mouse …")
        threading.Thread(target=self._run_dispatch_thread, args=(dispatch_queue,), daemon=True).start()

    def _run_dispatch_thread(self, dispatch_queue):
        try:
            success, failed, skipped = dispatcher.process_dispatch_queue(
                dispatch_queue, WAIT_TIME, TAB_CLOSE, CLOSE_TIME, COOL_DOWN,
                MAX_RETRIES, FOCUS_TIMEOUT,
                log=lambda line: self.log_q.put(line),
                confirm_ready=lambda: True)
            self.log_q.put(("DONE", success, failed, skipped))
        except Exception as e:
            self.log_q.put(("ERROR", str(e)))

    def _pump_log(self):
        try:
            while True:
                item = self.log_q.get_nowait()
                if isinstance(item, tuple) and item and item[0] in ("DONE", "ERROR"):
                    if item[0] == "DONE":
                        _, success, failed, skipped = item
                        self.summary_success.set(str(success))
                        self.summary_failed.set(str(failed))
                        self.summary_skipped.set(str(skipped))
                        self._log(f"\n🏁 Run Completed Cleanly — Success: {success} | Failed: {failed} | "
                                  f"Skipped: {skipped}")
                    else:
                        self._log(f"\n❌ Dispatch error: {item[1]}")
                    self._set_busy(False)
                else:
                    self._log(str(item))
        except queue.Empty:
            pass
        self.after(100, self._pump_log)

    def _log(self, line):
        self.log_pane.configure(state="normal")
        self.log_pane.insert("end", line + "\n")
        self.log_pane.see("end")
        self.log_pane.configure(state="disabled")

    def _set_busy(self, busy):
        self.busy = busy
        self.start_btn.configure(state="disabled" if busy else "normal")
        self.config(cursor="watch" if busy else "")
        self.status_bar.config(text="Dispatch running… do not touch keyboard/mouse" if busy else "Ready")

    # ------------------------------------------------------- settings tabs
    def _save_profile(self):
        self.settings["profile"] = {
            "name": self.profile_name.get().strip(),
            "designation": self.profile_designation.get().strip(),
            "agency": self.profile_agency.get().strip(),
        }
        save_settings(self.settings)
        self._log("👤 Profile updated.")
        messagebox.showinfo("Saved", "Profile saved.", parent=self)

    def _refresh_brand_list(self):
        self.brand_list.delete(0, "end")
        for code, data in self.settings.get("brands", {}).items():
            self.brand_list.insert(
                "end",
                f"{code} — {data.get('name', code)}   (target: {data.get('target_col', code + '_TARGET')} | "
                f"actual: {data.get('actual_col', code + '.1')})")

    def _add_brand(self):
        result = brand_dialog(self, None)
        if result is None:
            return
        code, name, tgt, act = result
        if code in self.settings["brands"]:
            messagebox.showerror("Duplicate", f"Brand '{code}' already exists.", parent=self)
            return
        self.settings["brands"][code] = {"name": name, "target_col": tgt, "actual_col": act}
        save_settings(self.settings)
        self._refresh_brand_list()
        self._log(f"🍾 Added brand {code} — {name}.")

    def _edit_brand(self):
        sel = self.brand_list.curselection()
        if not sel:
            messagebox.showinfo("Select first", "Select a brand in the list to edit.", parent=self)
            return
        code = list(self.settings["brands"].keys())[sel[0]]
        data = self.settings["brands"][code]
        result = brand_dialog(self, (code, data.get("name", code),
                                     data.get("target_col", code + "_TARGET"),
                                     data.get("actual_col", code + ".1")))
        if result is None:
            return
        new_code, name, tgt, act = result
        del self.settings["brands"][code]
        self.settings["brands"][new_code] = {"name": name, "target_col": tgt, "actual_col": act}
        save_settings(self.settings)
        self._refresh_brand_list()
        self._log(f"🍾 Updated brand {new_code}.")

    def _remove_brand(self):
        sel = self.brand_list.curselection()
        if not sel:
            messagebox.showinfo("Select first", "Select a brand in the list to remove.", parent=self)
            return
        code = list(self.settings["brands"].keys())[sel[0]]
        if messagebox.askyesno("Remove brand", f"Remove '{code}' from the portfolio?", parent=self):
            del self.settings["brands"][code]
            save_settings(self.settings)
            self._refresh_brand_list()
            self._log(f"🗑️ Removed brand {code}.")

    # -------------------------------------------------------------- misc
    def _on_close(self):
        if self.busy:
            if not messagebox.askyesno("Dispatch running",
                                       "A dispatch is still in progress. Quit anyway?",
                                       parent=self):
                return
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

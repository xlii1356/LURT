import json
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter import font as tkfont
from pathlib import Path
import re
import sys, os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CSV_PATH = resource_path("lancer/lancer_reactions.csv")

# --------------------------
# Constants & Themes
# --------------------------
DEFAULT_REACTIONS = [
    {
        "ID": "brace",
        "Rank": "-",
        "Name": "Brace",
        "Trigger": "You are hit by an attack and damage has been rolled.",
        "Frequency": "1/round",
        "Detail": "You count as having RESISTANCE to all damage, burn, and heat from the triggering attack, and until the end of your next turn, all other attacks against you are made at +1 difficulty. Due to the stress of bracing, you cannot take reactions until the end of your next turn and on that turn, you can only take one quick action, you cannot OVERCHARGE, move normally, take full actions, or take free actions."
    },
    {
        "ID": "overwatch",
        "Rank": "-",
        "Name": "Overwatch",
        "Trigger": "A hostile character starts any movement (including BOOST and other actions) inside one of your weapons THREAT.",
        "Frequency": "1/round",
        "Detail": "Trigger OVERWATCH, immediately using that weapon to SKIRMISH against that character as a reaction, before they move."
    }
]

THEMES = {
    "GMS": {
        "bg": "#f4f4f4", "fg": "#dbdbdb", "frame_bg": "#991E2A",
        "label_fg": "#dbdbdb", "button_bg": "#991E2A", "button_fg": "#f4f4f4",
        "used_fg": "#555555", "unlimited_fg": "#FFAB00",
    },
    "Horus": {
        "bg": "#2b2b2b", "fg": "#00d900", "frame_bg": "#126127",
        "label_fg": "#00d900", "button_bg": "#005500", "button_fg": "#00d900",
        "used_fg": "#444444", "unlimited_fg": "#FFAB00",
    },
    "MSMC": {
        "bg": "#263237", "fg": "#dbdbdb", "frame_bg": "#146464",
        "label_fg": "#dbdbdb", "button_bg": "#146464", "button_fg": "#dbdbdb",
        "used_fg": "#555555", "unlimited_fg": "#FFAB00",
    },
    "Harrison Armory": {
        "bg": "#2b2b2b", "fg": "#dbdbdb", "frame_bg": "#771675",
        "label_fg": "#dbdbdb", "button_bg": "#771675", "button_fg": "#dbdbdb",
        "used_fg": "#5b5160", "unlimited_fg": "#FFAB00",
    }
}

# --------------------------
# Helpers
# --------------------------
def normalize(s: str) -> str:
    if s is None:
        return ""
    return "".join(c.lower() for c in str(s) if c.isalnum())

def load_csv_rows(csv_path=CSV_PATH):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    rows = []
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            mr = r.get("min_talent_rank") or r.get("Min Talent Rank")
            try:
                r["_min_rank"] = int(float(str(mr))) if mr and str(mr).strip() else 1
            except ValueError:
                m = re.search(r"(\d+)", str(mr) or "")
                r["_min_rank"] = int(m.group(1)) if m else 1
            rows.append(r)
    return rows

def extract_ids(obj, collected):
    if isinstance(obj, dict):
        if "id" in obj:
            cid = obj["id"]
            rank = obj.get("rank")
            if not isinstance(rank, int):
                if isinstance(obj.get("ranks"), list):
                    rank = max((r.get("tier", 0) for r in obj["ranks"]), default=1)
                else:
                    rank = 1
            collected.append({"id": cid, "rank": rank, "raw": obj})
        for v in obj.values():
            extract_ids(v, collected)
    elif isinstance(obj, list):
        for i in obj:
            extract_ids(i, collected)

def load_all_components(json_path: Path):
    with json_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    
    # --- Extract Callsign for Window Title ---
    callsign = data.get("callsign")
    if not callsign and "pilot" in data and isinstance(data["pilot"], dict):
        callsign = data["pilot"].get("callsign")
        if not callsign:
            callsign = data["pilot"].get("name")
    if not callsign:
        callsign = data.get("name", "")
    
    collected = []
    
    # --- 1. Scan Pilot Data (Talents, Traits, Core Bonuses) ---
    pilot_keys = ["talents", "traits", "core_bonuses"]
    
    for key in pilot_keys:
        if key in data:
            extract_ids(data[key], collected)
            
    if "pilot" in data and isinstance(data["pilot"], dict):
        for key in pilot_keys:
            if key in data["pilot"]:
                extract_ids(data["pilot"][key], collected)
    
    active_mech_name = ""

    try:
        active_id = data.get("state", {}).get("active_mech_id")
        mechs = data.get("mechs") or []
        active_mech = None
        
        if isinstance(mechs, dict) and active_id in mechs:
            active_mech = mechs[active_id]
        elif isinstance(mechs, list):
            active_mech = next((m for m in mechs if str(m.get("id")) == str(active_id)), None)

        if isinstance(active_mech, dict):
            active_mech_name = active_mech.get("name", "")
            
            # A. Frame ID
            f = active_mech.get("frame")
            if isinstance(f, str):
                collected.append({"id": f, "rank": 3, "raw": {}})
            elif isinstance(f, dict):
                fid = f.get("id")
                if fid: collected.append({"id": fid, "rank": 3, "raw": {}})
            
            # B. Loadouts (Systems & Weapons)
            loadouts = active_mech.get("loadouts") or []
            if isinstance(loadouts, dict): loadouts = list(loadouts.values())
            
            for ld in loadouts:
                if not isinstance(ld, dict): continue
                
                # 1. Systems
                systems = ld.get("systems") or []
                if isinstance(systems, dict): systems = list(systems.values())
                for s in systems:
                    sid = s.get("id") if isinstance(s, dict) else s if isinstance(s, str) else None
                    if sid: collected.append({"id": sid, "rank": 3, "raw": {}})

                # 2. Mounts & Slots (Deep Parsing)
                # We combine all sources of mounts into one list to iterate
                all_mounts = []
                
                # Standard Mounts
                m_standard = ld.get("mounts") or []
                if isinstance(m_standard, dict): m_standard = list(m_standard.values())
                all_mounts.extend(m_standard)
                
                # Integrated Mounts
                m_integrated = ld.get("integratedMounts") or []
                if isinstance(m_integrated, dict): m_integrated = list(m_integrated.values())
                all_mounts.extend(m_integrated)
                
                # Process all mounts found
                for mount in all_mounts:
                    if not isinstance(mount, dict): continue
                    
                    # Check both 'slots' and 'extra' lists
                    slots_to_check = []
                    
                    # Add regular slots
                    s_list = mount.get("slots") or []
                    if isinstance(s_list, dict): s_list = list(s_list.values())
                    slots_to_check.extend(s_list)
                    
                    # Add extra slots (for Aux/Aux, etc)
                    e_list = mount.get("extra") or []
                    if isinstance(e_list, dict): e_list = list(e_list.values())
                    slots_to_check.extend(e_list)
                    
                    for slot in slots_to_check:
                        if not isinstance(slot, dict): continue
                        
                        # Look for weapon data in various fields
                        # Case 1: "weapon": { "id": "mw_vorpal_gun" ... } (Object)
                        w_obj = slot.get("weapon")
                        if isinstance(w_obj, dict):
                            wid = w_obj.get("id")
                            if wid:
                                collected.append({"id": wid, "rank": 3, "raw": w_obj})
                                continue # Found it, move to next slot
                        
                        # Case 2: "weapon": "mw_vorpal_gun" (String ID)
                        if isinstance(w_obj, str) and w_obj.strip():
                            collected.append({"id": w_obj, "rank": 3, "raw": {}})
                            continue

                        # Case 3: Fallback keys directly on the slot
                        for k in ("item", "id", "weapon_id"):
                            val = slot.get(k)
                            if isinstance(val, str) and val.strip():
                                collected.append({"id": val, "rank": 3, "raw": {}})
                                break
            
    except Exception:
        pass

    merged = {}
    for it in collected:
        key = normalize(it.get("id"))
        if not key: continue
        
        if key not in merged:
            merged[key] = {"id": it.get("id"), "rank": 0, "count": 0}
            
        merged[key]["rank"] = max(merged[key]["rank"], int(it.get("rank") or 1))
        merged[key]["count"] += 1  
        
    return list(merged.values()), str(callsign).strip(), str(active_mech_name).strip()

def match_components(components, csv_rows):
    results = []
    by_pid = {}
    for r in csv_rows:
        pid = normalize(r.get("Parent_ID") or r.get("ParentID") or r.get("Parent_Id") or "")
        by_pid.setdefault(pid, []).append(r)
        
    for comp in components:
        pid = normalize(comp.get("id"))
        if not pid: continue
        candidates = by_pid.get(pid, [])
        for r in candidates:
            if comp.get("rank", 1) >= int(r.get("_min_rank", 1)):
                
                # --- FREQUENCY SCALING LOGIC ---
                freq_str = (r.get("Frequency") or "").strip()
                count = comp.get("count", 1)
                
                if count > 1 and freq_str and "unlimited" not in freq_str.lower():
                    m = re.match(r"^(\d+)(.*)", freq_str)
                    if m:
                        try:
                            base_uses = int(m.group(1))
                            new_uses = base_uses + (count - 1)
                            freq_str = f"{new_uses}{m.group(2)}"
                        except:
                            pass 
                
                results.append({
                    "ID": comp["id"],
                    "Rank": comp.get("rank", 1),
                    "Name": (r.get("Name") or "").strip(),
                    "Trigger": (r.get("Trigger") or "").strip(),
                    "Frequency": freq_str,
                    "Detail": (r.get("Detail") or "").strip(),
                })
    return results

# --------------------------
# GUI
# --------------------------
class ReactionGUI(tk.Tk):
    def __init__(self, matches=None):
        super().__init__()
        self.title("Lancer Ultimate Reaction Tracker")
        self.geometry("820x720")
        self.drag_overlay_tag = "drag_overlay"
        self.text_size = 12 

        # Style setup
        self.style = ttk.Style(self)
        try: self.style.theme_use("clam")
        except Exception: pass
        
        self.matches = matches or []
        self.inject_default_reactions() 
        
        # State Variables
        self.mini_mode_var = tk.BooleanVar(value=False)
        self.always_on_top_var = tk.BooleanVar(value=False)

        # Theme state
        self.current_theme = "GMS"
        self.current_theme_data = THEMES[self.current_theme]

        # Top controls
        self.topframe = tk.Frame(self)
        self.topframe.pack(fill="x", padx=6, pady=6)

        tk.Label(self.topframe, text="Theme:").pack(side="left", padx=(4, 6))
        self.theme_var = tk.StringVar(value=self.current_theme)
        ttk.OptionMenu(self.topframe, self.theme_var, self.current_theme, *THEMES.keys(), command=self.on_theme_change).pack(side="left")
        ttk.Button(self.topframe, text="Open JSON", command=self.open_json, style="Reaction.TButton").pack(side="left", padx=6)

        # Text Size group
        textsize_frame = tk.LabelFrame(self.topframe, text="Text Size", labelanchor="n")
        textsize_frame.pack(side="left", padx=6)
        ttk.Button(textsize_frame, text="+", width=3, command=self.increase_text_size).pack(side="left", padx=2)
        ttk.Button(textsize_frame, text="-", width=3, command=self.decrease_text_size).pack(side="left", padx=2)

        # Mini Mode & Always On Top
        ttk.Checkbutton(self.topframe, text="Top", variable=self.always_on_top_var, command=self.toggle_always_on_top).pack(side="left", padx=5)
        ttk.Checkbutton(self.topframe, text="Mini", variable=self.mini_mode_var, command=self.toggle_mini_mode).pack(side="left", padx=2)

        # Next Round button - Created with 'self' as master so we can repack it outside topframe easily
        self.next_round_btn = ttk.Button(self, text="Next Round", command=self.reset_round, style="Reaction.TButton")
        self.next_round_btn.pack(in_=self.topframe, side="right", padx=6)

        # Scroll area
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scroll_frame = tk.Frame(self.canvas, bg=self.current_theme_data["bg"])
        
        self.canvas_frame_id = self.canvas.create_window(0, 0, anchor="nw", window=self.scroll_frame)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.scroll_frame.bind("<Configure>", self._on_scroll_frame_configure)

        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        # Drag state & Context Menu
        self.drag_data = {"widget": None, "proxy": None, "placeholder": None}
        self.entry_frames = []
        
        # Context Menu Creation
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Edit", command=self.edit_current_entry)
        self.context_menu.add_command(label="Reset", command=self.reset_current_entry)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_current_entry)
        
        self.current_context_frame = None

        self.populate_entries()
        self.apply_theme()

    def inject_default_reactions(self):
        """Helper to ensure brace/overwatch are present."""
        current_ids = {m["ID"] for m in self.matches} if self.matches else set()
        to_insert = [r for r in DEFAULT_REACTIONS if r["ID"] not in current_ids]
        self.matches = to_insert + list(self.matches)
        
    # --------------------------
    # Mini-Mode / Top Helpers
    # --------------------------
    def toggle_always_on_top(self):
        self.attributes("-topmost", self.always_on_top_var.get())

    def toggle_mini_mode(self):
        is_mini = self.mini_mode_var.get()
        
        # Repack Next Round Button
        self.next_round_btn.pack_forget()
        if is_mini:
            # Move button to its own row below the controls, but above the scroll/canvas
            self.next_round_btn.pack(side="top", fill="x", padx=6, pady=(0, 6), before=self.vscroll)
        else:
            # Put it back in the topbar
            self.next_round_btn.pack(in_=self.topframe, side="right", padx=6)

        for frame in self.entry_frames:
            self._apply_mini_mode_to_frame(frame, is_mini)
        self._repack_entries() 

    def _apply_mini_mode_to_frame(self, frame, is_mini):
        # Adjust visibility of label and position of button
        if is_mini:
            if hasattr(frame, "_label"):
                frame._label.grid_remove()
            if hasattr(frame, "_btn_frame"):
                frame._btn_frame.grid(rowspan=1, pady=2)
        else:
            if hasattr(frame, "_label"):
                frame._label.grid()
            if hasattr(frame, "_btn_frame"):
                frame._btn_frame.grid(rowspan=2, pady=6)

    def open_json(self):
        path = filedialog.askopenfilename(title="Select Pilot JSON", filetypes=[("JSON files","*.json"), ("All files","*.*")])
        if not path: return
        try:
            comps, callsign, mech_name = load_all_components(Path(path))
            csv_rows = load_csv_rows()
            matches = match_components(comps, csv_rows)
            self.matches = sorted(matches, key=lambda x: (x.get("Name",""), x.get("ID","")))
            
            # Update Window Title with Callsign and Mech Name
            base_title = "Lancer Ultimate Reaction Tracker"
            
            if callsign and mech_name:
                new_title = f"{base_title} - {callsign}://:{mech_name}"
            elif callsign:
                new_title = f"{base_title} - {callsign}"
            elif mech_name:
                new_title = f"{base_title} - {mech_name}"
            else:
                new_title = base_title
                
            self.title(new_title)
            
            self.inject_default_reactions() 
            self.populate_entries()
            self.apply_theme()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON or match: {e}")

    def reload_csv(self):
        try:
            csv_rows = load_csv_rows()
            comps = [{"id": m["ID"], "rank": m.get("Rank",1)} for m in self.matches]
            self.matches = match_components(comps, csv_rows)
            self.populate_entries()
            self.apply_theme()
        except Exception as e:
            messagebox.showerror("Error reloading CSV", str(e))

    def parse_frequency(self, freq):
        if not freq: return (1, True)
        s = str(freq).strip().lower()
        if s.startswith("unlimited"): return (float("inf"), True)
        m = re.match(r"(\d+)\s*/\s*round", s)
        if m: return (int(m.group(1)), True)
        if s.startswith("1/scene") or s.startswith("1/mission"): return (1, False)
        return (1, True)

    def populate_entries(self):
        for f in list(self.entry_frames):
            try: f.destroy()
            except: pass
        self.entry_frames.clear()

        for match in self.matches:
            frame = tk.Frame(self.scroll_frame, bd=1, relief="solid", pady=4)
            
            frame._match = match
            max_uses, resets = self.parse_frequency(match.get("Frequency"))
            frame._max_uses = max_uses
            frame._resets_each_round = resets
            frame._uses = 0
            frame._is_exhausted = False

            # Name Label
            name_font = tkfont.Font(family="TkDefaultFont", size=self.text_size + 2, weight="bold")
            name_lbl = tk.Label(frame, text=match.get("Name", ""), font=name_font, bg=frame.cget("bg"), anchor="w", padx=6, pady=2)
            name_lbl.grid(row=0, column=0, sticky="w", padx=6, pady=2)
            frame._name_font = name_font
            frame._name_label = name_lbl

            frame.grid_columnconfigure(0, weight=1)
            frame.grid_columnconfigure(1, weight=0)

            # Details Label
            details = f"Trigger: {match.get('Trigger','')}\nFrequency: {match.get('Frequency','')}\nDetail: {match.get('Detail','')}"
            detail_font = tkfont.Font(family="TkDefaultFont", size=self.text_size)
            detail_lbl = tk.Label(frame, text=details, justify="left", anchor="w", padx=6, pady=4, font=detail_font, bg=frame.cget("bg"))
            detail_lbl.grid(row=1, column=0, sticky="ew", padx=6, pady=4)
            frame._label = detail_lbl
            frame._label_font = detail_font

            # Button
            btn_frame = tk.Frame(frame, width=80)
            btn_frame.grid(row=0, column=1, rowspan=2, sticky="ne", padx=6, pady=6)
            btn_frame.grid_propagate(False)
            frame._btn_frame = btn_frame # SAVE REFERENCE for mini-mode toggling

            use_btn = ttk.Button(btn_frame, text="Use", width=6, style="Reaction.TButton")
            use_btn.pack(fill="x", pady=2)
            use_btn.configure(command=lambda f=frame, b=use_btn: self.use_entry(f, b))
            frame._button = use_btn

            # Wrapping logic
            frame.update_idletasks()
            col0_width = frame.grid_bbox(0, 0)[2]
            detail_lbl.config(wraplength=max(200, col0_width - 20))
            frame.bind("<Configure>", lambda e, l=detail_lbl, f=frame: l.config(wraplength=max(200, f.grid_bbox(0, 0)[2] - 20)))

            # Drag bindings
            # EXCLUDE use_btn from drag, but add Right-Click to ALL widgets in the frame
            for w in (frame, detail_lbl, name_lbl):
                w.bind("<ButtonPress-1>", self.on_drag_start)
                w.bind("<B1-Motion>", self.on_drag_motion)
                w.bind("<ButtonRelease-1>", self.on_drag_release)
            
            # Right Click Bindings (Frame and all children)
            for w in (frame, detail_lbl, name_lbl, use_btn):
                if sys.platform == "darwin":
                    w.bind("<Button-2>", lambda e, f=frame: self.show_context_menu(e, f))
                    w.bind("<Control-1>", lambda e, f=frame: self.show_context_menu(e, f))
                else:
                    w.bind("<Button-3>", lambda e, f=frame: self.show_context_menu(e, f))
            
            # Apply current mini-mode state immediately
            self._apply_mini_mode_to_frame(frame, self.mini_mode_var.get())

            self.entry_frames.append(frame)

        # Initial pack
        self._repack_entries()
        self.update_idletasks()
        self.apply_theme()

    # --------------------------
    # Context Menu Handlers
    # --------------------------
    def show_context_menu(self, event, frame):
        self.current_context_frame = frame
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def edit_current_entry(self):
        if not self.current_context_frame: return
        
        frame = self.current_context_frame
        match = frame._match
        
        # Create Edit Window
        edit_win = tk.Toplevel(self)
        edit_win.title("Edit Reaction")
        edit_win.geometry("600x550")
        edit_win.transient(self)
        edit_win.grab_set()
        
        # Padding for internal elements
        pad_opts = {'padx': 10, 'pady': 5, 'sticky': 'ew'}
        edit_win.columnconfigure(1, weight=1)
        
        # 1. Title (Name)
        tk.Label(edit_win, text="Title (Name):", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(10,0), sticky="w")
        name_var = tk.StringVar(value=match.get("Name", ""))
        tk.Entry(edit_win, textvariable=name_var).grid(row=1, column=0, columnspan=2, **pad_opts)
        
        # 2. Frequency (Details)
        tk.Label(edit_win, text="Frequency (e.g. 1/round):", font=("TkDefaultFont", 10, "bold")).grid(row=2, column=0, columnspan=2, padx=10, pady=(10,0), sticky="w")
        freq_var = tk.StringVar(value=match.get("Frequency", ""))
        tk.Entry(edit_win, textvariable=freq_var).grid(row=3, column=0, columnspan=2, **pad_opts)
        
        # 3. Trigger
        tk.Label(edit_win, text="Trigger:", font=("TkDefaultFont", 10, "bold")).grid(row=4, column=0, columnspan=2, padx=10, pady=(10,0), sticky="w")
        trigger_txt = tk.Text(edit_win, height=4, wrap="word")
        trigger_txt.insert("1.0", match.get("Trigger", ""))
        trigger_txt.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        # 4. Effect (Detail)
        tk.Label(edit_win, text="Effect / Details:", font=("TkDefaultFont", 10, "bold")).grid(row=6, column=0, columnspan=2, padx=10, pady=(10,0), sticky="w")
        effect_txt = tk.Text(edit_win, height=6, wrap="word")
        effect_txt.insert("1.0", match.get("Detail", ""))
        effect_txt.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        edit_win.rowconfigure(5, weight=1)
        edit_win.rowconfigure(7, weight=2)
        
        # Buttons
        btn_frame = tk.Frame(edit_win)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=15)
        
        def save_changes():
            new_name = name_var.get()
            new_freq = freq_var.get()
            new_trigger = trigger_txt.get("1.0", "end-1c").strip()
            new_detail = effect_txt.get("1.0", "end-1c").strip()
            
            # Update Data
            match["Name"] = new_name
            match["Frequency"] = new_freq
            match["Trigger"] = new_trigger
            match["Detail"] = new_detail
            
            # Update Max Uses based on new frequency
            max_uses, resets = self.parse_frequency(new_freq)
            frame._max_uses = max_uses
            frame._resets_each_round = resets
            
            # Reset usage count if frequency logic changed significantly or user wants reset
            # For simplicity, we just re-evaluate limits but keep current usage unless it exceeds new limit
            if frame._uses >= max_uses and max_uses != float("inf"):
                frame._is_exhausted = True
            elif max_uses == float("inf"):
                 frame._is_exhausted = False
                 
            # Update UI Text
            if hasattr(frame, "_name_label"):
                frame._name_label.configure(text=new_name)
                
            if hasattr(frame, "_label"):
                updated_text = f"Trigger: {new_trigger}\nFrequency: {new_freq}\nDetail: {new_detail}"
                frame._label.configure(text=updated_text)
                
            # Re-color button text in case limits changed
            if frame._max_uses == float("inf"):
                 frame._button.configure(text="Use" if frame._uses==0 else "Used")
            elif frame._max_uses > 1:
                 frame._button.configure(text=f"Use ({frame._uses}/{int(frame._max_uses)})")
            else:
                 frame._button.configure(text="Used" if frame._is_exhausted else "Use")
                 
            self.apply_theme() # Refresh colors
            edit_win.destroy()
            
        ttk.Button(btn_frame, text="Save", command=save_changes).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=edit_win.destroy).pack(side="left", padx=10)

    def delete_current_entry(self):
        if not self.current_context_frame: return
        if messagebox.askyesno("Delete", "Are you sure you want to delete this reaction?"):
            frame = self.current_context_frame
            
            # Remove from visual list
            if frame in self.entry_frames:
                self.entry_frames.remove(frame)
            
            # Remove from data list
            if frame._match in self.matches:
                self.matches.remove(frame._match)
                
            frame.destroy()
            self._repack_entries()

    def reset_current_entry(self):
        if not self.current_context_frame: return
        frame = self.current_context_frame
        
        frame._uses = 0
        frame._is_exhausted = False
        frame._button.configure(state="normal", text="Use")
        
        if hasattr(frame, "_label"):
            frame._label.configure(fg=self.current_theme_data["label_fg"])
        
        if hasattr(frame, "_name_font"):
            current_weight = frame._name_font.actual().get("weight", "bold")
            frame._name_font.configure(overstrike=0, weight=current_weight)

    # --------------------------
    # Existing Logic
    # --------------------------

    def _repack_entries(self):
        """Helper to repack all frames in order."""
        for f in self.entry_frames:
            if f == self.drag_data.get("placeholder"):
                widget = self.drag_data.get("widget")
                if widget:
                    f.configure(height=widget.winfo_height(), width=widget.winfo_width())
                f.pack(in_=self.scroll_frame, fill="x", pady=5, padx=6)
                f.pack_propagate(False)
            else:
                f.pack(in_=self.scroll_frame, fill="x", pady=5, padx=6)

    def use_entry(self, frame, button):
        frame._uses += 1
        
        # UNLIMITED LOGIC
        if frame._max_uses == float("inf"):
            if hasattr(frame, "_label"):
                frame._label.configure(fg=self.current_theme_data["unlimited_fg"])
            button.configure(text="Used")
            self.after(800, lambda: button.configure(text="Use"))
            return

        # LIMITED LOGIC
        if frame._max_uses > 1:
            button.configure(text=f"Use ({frame._uses}/{int(frame._max_uses)})")

        if frame._uses >= frame._max_uses:
            frame._is_exhausted = True
            if hasattr(frame, "_name_font"): 
                current_weight = frame._name_font.actual().get("weight", "bold")
                frame._name_font.configure(overstrike=1, weight=current_weight)
            
            button.configure(text="Used", state="disabled")
            if hasattr(frame, "_label"):
                frame._label.configure(fg=self.current_theme_data["used_fg"])

    def increase_text_size(self):
        self.text_size += 2
        self.update_text_size()

    def decrease_text_size(self):
        self.text_size = max(8, self.text_size - 2)
        self.update_text_size()

    def update_text_size(self):
        for frame in getattr(self, "entry_frames", []):
            if hasattr(frame, "_name_font"):
                current_weight = frame._name_font.actual().get("weight", "bold")
                current_overstrike = frame._name_font.actual().get("overstrike", 0)
                frame._name_font.configure(size=self.text_size + 2, weight=current_weight, overstrike=current_overstrike)
                if hasattr(frame, "_name_label"):
                    frame._name_label.configure(font=frame._name_font)

            if hasattr(frame, "_label_font"):
                frame._label_font.configure(size=self.text_size)
                if hasattr(frame, "_label"):
                    frame._label.configure(font=frame._label_font)

    def reset_round(self):
        for frame in self.entry_frames:
            if getattr(frame, "_resets_each_round", True):
                frame._uses = 0
                frame._is_exhausted = False
                frame._button.configure(state="normal", text="Use")
                if hasattr(frame, "_label"):
                    frame._label.configure(fg=self.current_theme_data["label_fg"])
                if hasattr(frame, "_name_font"):
                    current_weight = frame._name_font.actual().get("weight", "bold")
                    frame._name_font.configure(overstrike=0, weight=current_weight)
        self.apply_theme()

    def on_theme_change(self, *args):
        sel = self.theme_var.get()
        if sel in THEMES:
            self.current_theme = sel
            self.current_theme_data = THEMES[sel]
            self.apply_theme()

    def apply_theme(self):
        t = self.current_theme_data
        self.configure(bg=t["bg"])
        self.canvas.configure(bg=t["bg"])
        self.scroll_frame.configure(bg=t["bg"])

        if self.drag_data.get("placeholder"):
             self.drag_data["placeholder"].configure(bg=t["used_fg"])

        try:
            self.style.configure("Reaction.TButton", background=t["button_bg"], foreground=t["button_fg"], relief="raised", padding=6)
            self.style.map("Reaction.TButton",
                           foreground=[('disabled', t["used_fg"]), ('!disabled', t["button_fg"])],
                           background=[('active', t["button_bg"]), ('!disabled', t["button_bg"])])
        except Exception: pass

        for frame in self.entry_frames:
            if frame == self.drag_data.get("placeholder"):
                continue

            frame.configure(bg=t["frame_bg"], highlightbackground=t["frame_bg"])
            
            is_unlimited_used = (frame._max_uses == float("inf") and frame._uses > 0)
            
            if getattr(frame, "_is_exhausted", False):
                fg_color = t["used_fg"]
            elif is_unlimited_used:
                fg_color = t["unlimited_fg"]
            else:
                fg_color = t["label_fg"]
                
            frame._label.configure(bg=t["frame_bg"], fg=fg_color)
            try: frame._button.configure(style="Reaction.TButton")
            except Exception: pass
        self.update_idletasks()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame_id, width=event.width)
        self.canvas.coords(self.canvas_frame_id, 0, 0)

    def _on_scroll_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_drag_start(self, event):
        widget = event.widget
        while widget is not None and widget not in self.entry_frames:
            widget = widget.master
        if widget is None: return

        self.drag_data["widget"] = widget
        self.drag_data["start_index"] = self.entry_frames.index(widget)
        
        bg_color = widget.cget("bg")
        width = widget.winfo_width()
        height = widget.winfo_height()
        
        proxy = tk.Toplevel(self)
        proxy.overrideredirect(True)
        proxy.attributes("-topmost", True)
        proxy.attributes("-alpha", 0.85)
        proxy.configure(bg=bg_color, relief="solid", bd=1)
        
        if hasattr(widget, "_name_label"):
            name_txt = widget._name_label.cget("text")
            name_font = widget._name_font
            tk.Label(proxy, text=name_txt, bg=bg_color, fg=self.current_theme_data["label_fg"], 
                     font=name_font, anchor="w", padx=6, pady=2).pack(fill="x")

        # Respect Mini-mode for drag proxy
        if hasattr(widget, "_label") and not self.mini_mode_var.get():
            detail_txt = widget._label.cget("text")
            detail_font = widget._label_font
            detail_lbl = tk.Label(proxy, text=detail_txt, bg=bg_color, fg=self.current_theme_data["label_fg"],
                     font=detail_font, justify="left", anchor="w", padx=6, pady=4)
            detail_lbl.pack(fill="x")
            detail_lbl.configure(wraplength=width - 20)

        self.drag_data["proxy"] = proxy
        
        x, y = self.winfo_pointerx() - 10, self.winfo_pointery() - 10
        proxy.geometry(f"{width}x{height}+{x}+{y}")

        placeholder = tk.Frame(self.scroll_frame, bg=self.current_theme_data["used_fg"], height=height, relief="sunken", bd=1)
        self.drag_data["placeholder"] = placeholder
        
        idx = self.drag_data["start_index"]
        self.entry_frames[idx] = placeholder
        
        widget.pack_forget()
        self._repack_entries()


    def on_drag_motion(self, event):
        if not self.drag_data.get("widget"): return
        
        x, y = self.winfo_pointerx() - 10, self.winfo_pointery() - 10
        self.drag_data["proxy"].geometry(f"+{x}+{y}")
        
        pointer_y = self.canvas.winfo_pointery()
        ph_idx = self.entry_frames.index(self.drag_data["placeholder"])
        
        if ph_idx > 0:
            prev = self.entry_frames[ph_idx - 1]
            prev_center = prev.winfo_rooty() + (prev.winfo_height() / 2)
            if pointer_y < prev_center:
                self.entry_frames[ph_idx], self.entry_frames[ph_idx-1] = self.entry_frames[ph_idx-1], self.entry_frames[ph_idx]
                self._repack_entries()
                return

        if ph_idx < len(self.entry_frames) - 1:
            next_item = self.entry_frames[ph_idx + 1]
            next_center = next_item.winfo_rooty() + (next_item.winfo_height() / 2)
            if pointer_y > next_center:
                self.entry_frames[ph_idx], self.entry_frames[ph_idx+1] = self.entry_frames[ph_idx+1], self.entry_frames[ph_idx]
                self._repack_entries()
                return

    def on_drag_release(self, event):
        if not self.drag_data.get("widget"): return
        
        if self.drag_data.get("proxy"):
            self.drag_data["proxy"].destroy()
            
        ph = self.drag_data["placeholder"]
        final_idx = self.entry_frames.index(ph)
        ph.destroy()
        
        self.entry_frames[final_idx] = self.drag_data["widget"]
        self._repack_entries()
        
        self.drag_data = {"widget": None, "proxy": None, "placeholder": None}
        self.apply_theme()

    def _on_mousewheel(self, event):
        system = self.tk.call("tk", "windowingsystem")
        if system == "aqua":
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            if delta: self.canvas.yview_scroll(delta, "units")

def main():
    root_matches = []
    app = ReactionGUI(root_matches)
    app.mainloop()

if __name__ == "__main__":
    main()
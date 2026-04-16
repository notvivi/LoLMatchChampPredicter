import customtkinter as ctk
from PIL import Image
import requests
from io import BytesIO
import joblib
import numpy as np

ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"]
ALLY_ROLES = {r: [x for x in ROLES if x != r] for r in ROLES}

DDR_BASE = "https://ddragon.leagueoflegends.com"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Solo/Duo Champ Predictor")
        self.geometry("1420x940")
        self.minsize(1180, 760)

        self.model = self.role_list = None
        self.champ_icons = {}
        self._load_champ_data()
        self._load_model()
        self._build_ui()
        self._refresh()

    # ── data loading ──────────────────────────────────────────────────────────

    def _load_model(self):
        try:
            self.model = joblib.load("champ_model.pkl")
            self.role_list = joblib.load("role_model.pkl")
            if not isinstance(self.role_list, list) or not self.role_list:
                self.role_list = ROLES.copy()
        except Exception:
            self.model = None

    def _load_champ_data(self):
        try:
            ver = requests.get(f"{DDR_BASE}/api/versions.json", timeout=10).json()[0]
            data = requests.get(f"{DDR_BASE}/cdn/{ver}/data/en_US/champion.json", timeout=10).json()["data"]
            self.ver = ver
            self.name_to_id = {n: int(d["key"]) for n, d in data.items()}
            self.id_to_name = {int(d["key"]): n for n, d in data.items()}
            self.id_to_tags = {int(d["key"]): d["tags"] for n, d in data.items()}
            self.champ_names = sorted(self.name_to_id)
            self.champ_lower = {n.lower(): n for n in self.champ_names}
        except Exception:
            self.ver = "14.7.1"
            self.name_to_id = {"Garen": 86, "Ashe": 22}
            self.id_to_name = {86: "Garen", 22: "Ashe"}
            self.id_to_tags = {86: ["Fighter", "Tank"], 22: ["Marksman"]}
            self.champ_names = ["Garen", "Ashe"]
            self.champ_lower = {n.lower(): n for n in self.champ_names}

    def get_icon(self, name, size=(28, 28)):
        key = (name, size)
        if key not in self.champ_icons:
            try:
                r = requests.get(f"{DDR_BASE}/cdn/{self.ver}/img/champion/{name}.png", timeout=3)
                r.raise_for_status()
                img = Image.open(BytesIO(r.content))
                self.champ_icons[key] = ctk.CTkImage(img, img, size)
            except Exception:
                self.champ_icons[key] = None
        return self.champ_icons[key]

    # ── ui building ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # top bar
        top = ctk.CTkFrame(self, height=64)
        top.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 4), sticky="ew")
        top.grid_propagate(False)

        ctk.CTkLabel(top, text="Your role:", font=("Arial", 12, "bold")).pack(side="left", padx=(12, 8))
        self.role_cb = ctk.CTkComboBox(top, values=ROLES, width=140, command=self._on_role_changed)
        self.role_cb.pack(side="left")
        self.role_cb.set("MIDDLE")

        stats = ctk.CTkFrame(top, fg_color="transparent")
        stats.pack(side="right", padx=12)
        self.tank_bar = self._stat_bar(stats, "Tank", "#555555")
        self.ap_bar   = self._stat_bar(stats, "AP",   "#a335ee")
        self.ad_bar   = self._stat_bar(stats, "AD",   "#ff8000")

        # team panels
        self.ally_slots, self.ally_selectors   = self._team_panel(0, "ALLY TEAM",  "#3b8ed0")
        self.enemy_slots, self.enemy_selectors = self._team_panel(1, "ENEMY TEAM", "#db4437")

        # bottom bar
        bot = ctk.CTkFrame(self)
        bot.grid(row=2, column=0, columnspan=2, padx=10, pady=(4, 10), sticky="ew")

        ctk.CTkButton(bot, text="PREDICT", height=42, width=240,
                      font=("Arial", 14, "bold"), command=self._predict,
                      fg_color="#28a745", hover_color="#218838").pack(side="left", padx=12, pady=12)

        self.res_box = ctk.CTkTextbox(bot, height=110, width=800, font=("Consolas", 13))
        self.res_box.pack(side="right", padx=12, pady=12, fill="x", expand=True)
        self.res_box.insert("0.0", "Write down champ and then press Enter.")

    def _stat_bar(self, parent, label, color):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=8)
        ctk.CTkLabel(f, text=label, font=("Arial", 10)).pack()
        bar = ctk.CTkProgressBar(f, width=90, progress_color=color)
        bar.set(0)
        bar.pack(pady=(2, 0))
        return bar

    def _team_panel(self, col, title, color):
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=col, padx=(10 if col == 0 else 5, 5 if col == 0 else 10), pady=4, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=("Arial", 14, "bold"), text_color=color).pack(pady=(8, 4))
        slots = ctk.CTkFrame(frame, fg_color="transparent")
        slots.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        roles = ALLY_ROLES.get(self.role_cb.get(), ROLES) if col == 0 else ROLES
        selectors = [ChampSlot(self, slots, r) for r in roles]
        for s in selectors:
            s.pack(fill="x", pady=3)
        return slots, selectors

    # ── logic ─────────────────────────────────────────────────────────────────

    def _refresh(self):
        my_role = self.role_cb.get().upper()
        ally_roles = ALLY_ROLES.get(my_role, ROLES)
        for sel, role in zip(self.ally_selectors, ally_roles):
            sel.set_role(role)
        for sel, role in zip(self.enemy_selectors, ROLES):
            sel.set_role(role)
        self._update_stats()

    def _on_role_changed(self, choice):
        old = {s.role_name: s.selected_champ for s in self.ally_selectors}
        for sel, role in zip(self.ally_selectors, ALLY_ROLES.get(choice, ROLES)):
            sel.set_role(role)
            prev = old.get(role)
            if prev and not self.is_taken(prev, sel):
                sel.set_selected(prev)
            else:
                sel.clear(silent=True)
        self._update_stats()

    def all_selectors(self):
        return self.ally_selectors + self.enemy_selectors

    def is_taken(self, name, exclude=None):
        return any(s.selected_champ == name for s in self.all_selectors() if s is not exclude)

    def normalize(self, text):
        q = text.strip().lower()
        if not q: return None
        if q in self.champ_lower: return self.champ_lower[q]
        matches = [n for n in self.champ_names if n.lower().startswith(q)]
        if len(matches) == 1: return matches[0]
        matches = [n for n in self.champ_names if q in n.lower()]
        return matches[0] if len(matches) == 1 else None

    def _tags(self, names):
        tags = []
        for n in names:
            cid = self.name_to_id.get(n)
            if cid: tags.extend(self.id_to_tags.get(cid, []))
        return tags

    def _tag_vec(self, tags):
        return [
            tags.count("Tank"),
            tags.count("Mage") + tags.count("Support"),
            tags.count("Marksman") + tags.count("Assassin"),
            tags.count("Tank") + tags.count("Support"),
            tags.count("Fighter"),
            tags.count("Assassin"),
        ]

    def _update_stats(self):
        ally_names = [s.selected_champ for s in self.ally_selectors if s.selected_champ]
        tags = self._tags(ally_names)
        d = max(len(ally_names), 1)
        self.tank_bar.set(min(tags.count("Tank") / d, 1))
        self.ap_bar.set(min((tags.count("Mage") + tags.count("Support")) / d, 1))
        self.ad_bar.set(min((tags.count("Marksman") + tags.count("Assassin")) / d, 1))

    def _build_features(self):
        ally  = self._tag_vec(self._tags([s.selected_champ for s in self.ally_selectors  if s.selected_champ]))
        enemy = self._tag_vec(self._tags([s.selected_champ for s in self.enemy_selectors if s.selected_champ]))
        delta = [ally[i] - enemy[i] for i in range(4)]
        extra = [int(enemy[1] >= 3), int(enemy[2] >= 3), int(enemy[0] >= 2), int(ally[0] == 0)]
        role_vec = [1 if r == self.role_cb.get().upper() else 0 for r in self.role_list]
        return np.array(role_vec + ally + enemy + delta + extra, dtype=np.float32).reshape(1, -1)

    def _predict(self):
        if not self.model:
            return self._show("ERROR: Model did not load.")

        selected = [s.selected_champ for s in self.all_selectors() if s.selected_champ]
        if not selected:
            return self._show("ERROR: Enter at least one champ.")
        if len(selected) != len(set(selected)):
            return self._show("ERROR: The same champ cannot be chosen more than once.")

        try:
            X = self._build_features()
            exp = getattr(self.model, "n_features_in_", None)
            if exp and exp != X.shape[1]:
                return self._show(f"ERROR: Model expects {exp} features, got {X.shape[1]}.")

            probs = self.model.predict_proba(X)[0]
            taken = set(selected)
            top3 = sorted(
                [(probs[i], self.id_to_name[cid]) for i, cid in enumerate(self.model.classes_)
                 if self.id_to_name.get(cid) not in taken],
                reverse=True
            )[:3]

            ally_c  = sum(1 for s in self.ally_selectors  if s.selected_champ)
            enemy_c = sum(1 for s in self.enemy_selectors if s.selected_champ)
            lines = [f"Role: {self.role_cb.get().upper()}  |  Draft: {ally_c}/4 ally  {enemy_c}/5 enemy\n"]
            lines += [f"{i}. {n.ljust(18)} {p*100:6.2f}%" for i, (p, n) in enumerate(top3, 1)]
            self._show("\n".join(lines))
        except Exception as e:
            self._show(f"ERROR: {e}")

    def _show(self, text):
        self.res_box.delete("0.0", "end")
        self.res_box.insert("0.0", text)


class ChampSlot(ctk.CTkFrame):
    def __init__(self, app, master, role_name):
        super().__init__(master)
        self.app = app
        self.role_name = role_name
        self.selected_champ = None

        self.grid_columnconfigure(2, weight=1)

        self.icon_lbl  = ctk.CTkLabel(self, text="", width=34)
        self.icon_lbl.grid(row=0, column=0, padx=(6, 4), pady=6)

        self.role_lbl = ctk.CTkLabel(self, text=role_name, width=78, anchor="w", font=("Arial", 12, "bold"))
        self.role_lbl.grid(row=0, column=1, padx=(0, 6), sticky="w")

        self.entry = ctk.CTkEntry(self, placeholder_text="Champ name + Enter", height=30)
        self.entry.grid(row=0, column=2, padx=(0, 6), pady=6, sticky="ew")
        self.entry.bind("<Return>", lambda e: self._confirm())
        self.entry.bind("<FocusOut>", lambda e: self._confirm())

        ctk.CTkButton(self, text="X", width=30, height=30, command=self.clear,
                      fg_color="#8b1e1e", hover_color="#a62424").grid(row=0, column=3, padx=(0, 6), pady=6)

        self.status = ctk.CTkLabel(self, text="", width=120, anchor="w", font=("Arial", 10))
        self.status.grid(row=0, column=4, padx=(0, 6), sticky="w")

    def set_role(self, role):
        self.role_name = role
        self.role_lbl.configure(text=role)

    def set_selected(self, name):
        if not name:
            return self.clear(silent=True)
        self.selected_champ = name
        self.entry.delete(0, "end")
        self.entry.insert(0, name)
        self.entry.configure(state="disabled")
        icon = self.app.get_icon(name)
        self.icon_lbl.configure(image=icon if icon else None, text="" if icon else "?")
        self.status.configure(text="Chosen", text_color="#cfcfcf")

    def _confirm(self):
        if self.selected_champ: return
        raw = self.entry.get().strip()
        if not raw:
            return self.status.configure(text="", text_color="gray70")
        name = self.app.normalize(raw)
        if not name:
            return self.status.configure(text="Invalid", text_color="#ff6b6b")
        if self.app.is_taken(name, self):
            return self.status.configure(text="Already chosen", text_color="#ff6b6b")
        self.set_selected(name)
        self.app._update_stats()

    def clear(self, silent=False):
        self.selected_champ = None
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.icon_lbl.configure(image=None, text="")
        self.status.configure(text="", text_color="gray70")
        if not silent:
            self.app._update_stats()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
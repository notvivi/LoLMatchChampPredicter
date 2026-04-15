import customtkinter as ctk
from PIL import Image
import requests
from io import BytesIO
import joblib
import numpy as np


VALID_ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"]

ALLY_ROLES_BY_MY_ROLE = {
    "TOP": ["JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"],
    "JUNGLE": ["TOP", "MIDDLE", "BOTTOM", "SUPPORT"],
    "MIDDLE": ["TOP", "JUNGLE", "BOTTOM", "SUPPORT"],
    "BOTTOM": ["TOP", "JUNGLE", "MIDDLE", "SUPPORT"],
    "SUPPORT": ["TOP", "JUNGLE", "MIDDLE", "BOTTOM"],
}


class LoLModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Solo/Duo Champ Predictor")
        self.geometry("1420x940")
        self.minsize(1180, 760)

        self.model = None
        self.roles_list = VALID_ROLES.copy()

        self.get_champion_data()
        self.load_model()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.top_panel = ctk.CTkFrame(self, height=64)
        self.top_panel.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 4), sticky="ew")
        self.top_panel.grid_propagate(False)

        ctk.CTkLabel(self.top_panel, text="Your role:", font=("Arial", 12, "bold")).pack(side="left", padx=(12, 8))

        self.my_role_cb = ctk.CTkComboBox(
            self.top_panel,
            values=VALID_ROLES,
            width=140,
            command=self.on_my_role_changed
        )
        self.my_role_cb.pack(side="left", padx=(0, 8))
        self.my_role_cb.set("MIDDLE")

        self.stats_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.stats_frame.pack(side="right", padx=12)

        self.tank_bar = self.create_stat_bar("Tank", "#555555")
        self.ap_bar = self.create_stat_bar("AP", "#a335ee")
        self.ad_bar = self.create_stat_bar("AD", "#ff8000")

        self.setup_ui()

        self.bottom_panel = ctk.CTkFrame(self)
        self.bottom_panel.grid(row=2, column=0, columnspan=2, padx=10, pady=(4, 10), sticky="ew")

        self.btn_predict = ctk.CTkButton(
            self.bottom_panel,
            text="PREDICT",
            height=42,
            width=240,
            font=("Arial", 14, "bold"),
            command=self.run_prediction,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.btn_predict.pack(side="left", padx=12, pady=12)

        self.res_box = ctk.CTkTextbox(self.bottom_panel, height=110, width=800, font=("Consolas", 13))
        self.res_box.pack(side="right", padx=12, pady=12, fill="x", expand=True)
        self.res_box.insert("0.0", "Write down champ and then press Enter.")

        self.refresh_role_labels()
        self.update_all_stats()

    def load_model(self):
        try:
            self.model = joblib.load("champ_model.pkl")
            self.roles_list = joblib.load("role_model.pkl")
            if not isinstance(self.roles_list, list) or not self.roles_list:
                self.roles_list = VALID_ROLES.copy()
        except Exception as e:
            self.model = None

    def get_champion_data(self):
        try:
            ver = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10).json()[0]
            data = requests.get(
                f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json",
                timeout=10
            ).json()["data"]

            self.current_version = ver
            self.name_to_id = {n: int(d["key"]) for n, d in data.items()}
            self.id_to_name = {int(d["key"]): n for n, d in data.items()}
            self.id_to_tags = {int(d["key"]): d["tags"] for n, d in data.items()}
            self.champ_names = sorted(self.name_to_id.keys())
            self.champ_names_lower = {name.lower(): name for name in self.champ_names}
            self.champ_icons = {}
        except Exception as e:
            self.current_version = "14.7.1"
            self.champ_names = ["Garen", "Ashe"]
            self.champ_names_lower = {"garen": "Garen", "ashe": "Ashe"}
            self.name_to_id = {"Garen": 86, "Ashe": 22}
            self.id_to_name = {86: "Garen", 22: "Ashe"}
            self.id_to_tags = {86: ["Fighter", "Tank"], 22: ["Marksman"]}
            self.champ_icons = {}

    def get_champion_icon(self, champ_name, size=(28, 28)):
        key = (champ_name, size)
        if key in self.champ_icons:
            return self.champ_icons[key]
        try:
            url = f"https://ddragon.leagueoflegends.com/cdn/{self.current_version}/img/champion/{champ_name}.png"
            r = requests.get(url, timeout=3)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content))
            out = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self.champ_icons[key] = out
            return out
        except Exception:
            return None

    def create_stat_bar(self, label, color):
        f = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        f.pack(side="left", padx=8)
        ctk.CTkLabel(f, text=label, font=("Arial", 10)).pack()
        bar = ctk.CTkProgressBar(f, width=90, progress_color=color)
        bar.set(0)
        bar.pack(pady=(2, 0))
        return bar

    def setup_ui(self):
        self.ally_selectors = []
        self.enemy_selectors = []

        self.ally_frame = ctk.CTkFrame(self)
        self.ally_frame.grid(row=1, column=0, padx=(10, 5), pady=4, sticky="nsew")

        self.enemy_frame = ctk.CTkFrame(self)
        self.enemy_frame.grid(row=1, column=1, padx=(5, 10), pady=4, sticky="nsew")

        ctk.CTkLabel(self.ally_frame, text="ALLY TEAM", font=("Arial", 14, "bold"), text_color="#3b8ed0").pack(pady=(8, 4))
        ctk.CTkLabel(self.enemy_frame, text="ENEMY TEAM", font=("Arial", 14, "bold"), text_color="#db4437").pack(pady=(8, 4))

        self.ally_slots = ctk.CTkFrame(self.ally_frame, fg_color="transparent")
        self.ally_slots.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.enemy_slots = ctk.CTkFrame(self.enemy_frame, fg_color="transparent")
        self.enemy_slots.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        ally_roles = ALLY_ROLES_BY_MY_ROLE.get(self.my_role_cb.get().strip().upper(), ["TOP", "JUNGLE", "BOTTOM", "SUPPORT"])
        for role_name in ally_roles:
            sel = ChampSlot(self, self.ally_slots, role_name)
            sel.pack(fill="x", pady=3)
            self.ally_selectors.append(sel)

        for role_name in VALID_ROLES:
            sel = ChampSlot(self, self.enemy_slots, role_name)
            sel.pack(fill="x", pady=3)
            self.enemy_selectors.append(sel)

    def refresh_role_labels(self):
        my_role = self.my_role_cb.get().strip().upper()
        ally_roles = ALLY_ROLES_BY_MY_ROLE.get(my_role, ["TOP", "JUNGLE", "BOTTOM", "SUPPORT"])
        for sel, role_name in zip(self.ally_selectors, ally_roles):
            sel.set_role(role_name)
        for sel, role_name in zip(self.enemy_selectors, VALID_ROLES):
            sel.set_role(role_name)

    def on_my_role_changed(self, choice):
        old_selected = {sel.role_name: sel.selected_champ for sel in self.ally_selectors}
        ally_roles = ALLY_ROLES_BY_MY_ROLE.get(choice, ["TOP", "JUNGLE", "BOTTOM", "SUPPORT"])

        for sel, role_name in zip(self.ally_selectors, ally_roles):
            sel.set_role(role_name)
            prev = old_selected.get(role_name)
            if prev and not self.is_champ_taken(prev, sel):
                sel.set_selected(prev)
            else:
                sel.clear(silent=True)

        self.on_selector_updated()

    def all_selectors(self):
        return self.ally_selectors + self.enemy_selectors

    def get_all_selected_champs(self):
        return [s.selected_champ for s in self.all_selectors() if s.selected_champ]

    def get_taken_champs_except(self, current_selector=None):
        taken = set()
        for s in self.all_selectors():
            if s is not current_selector and s.selected_champ:
                taken.add(s.selected_champ)
        return taken

    def is_champ_taken(self, champ_name, current_selector=None):
        return champ_name in self.get_taken_champs_except(current_selector)

    def normalize_champ_name(self, text):
        q = text.strip().lower()
        if not q:
            return None
        if q in self.champ_names_lower:
            return self.champ_names_lower[q]

        matches = [name for name in self.champ_names if name.lower().startswith(q)]
        if len(matches) == 1:
            return matches[0]

        matches = [name for name in self.champ_names if q in name.lower()]
        if len(matches) == 1:
            return matches[0]

        return None

    def on_selector_updated(self):
        self.update_all_stats()

    def get_tags_from_selected_names(self, names):
        tags = []
        for name in names:
            cid = self.name_to_id.get(name)
            if cid:
                tags.extend(self.id_to_tags.get(cid, []))
        return tags

    def compute_stats_from_tags(self, tags):
        return [
            tags.count("Tank"),
            tags.count("Mage") + tags.count("Support"),
            tags.count("Marksman") + tags.count("Assassin"),
            tags.count("Tank") + tags.count("Support"),
            tags.count("Fighter"),
            tags.count("Assassin"),
        ]

    def update_all_stats(self):
        ally_names = [s.selected_champ for s in self.ally_selectors if s.selected_champ]
        ally_tags = self.get_tags_from_selected_names(ally_names)
        divisor = max(len(ally_names), 1)

        self.tank_bar.set(min(ally_tags.count("Tank") / divisor, 1))
        self.ap_bar.set(min((ally_tags.count("Mage") + ally_tags.count("Support")) / divisor, 1))
        self.ad_bar.set(min((ally_tags.count("Marksman") + ally_tags.count("Assassin")) / divisor, 1))

    def build_feature_vector(self):
        ally_names = [s.selected_champ for s in self.ally_selectors if s.selected_champ]
        enemy_names = [s.selected_champ for s in self.enemy_selectors if s.selected_champ]

        ally_vec = self.compute_stats_from_tags(self.get_tags_from_selected_names(ally_names))
        enemy_vec = self.compute_stats_from_tags(self.get_tags_from_selected_names(enemy_names))

        delta_vec = [
            ally_vec[0] - enemy_vec[0],
            ally_vec[1] - enemy_vec[1],
            ally_vec[2] - enemy_vec[2],
            ally_vec[3] - enemy_vec[3],
        ]

        extra_vec = [
            1 if enemy_vec[1] >= 3 else 0,
            1 if enemy_vec[2] >= 3 else 0,
            1 if enemy_vec[0] >= 2 else 0,
            1 if ally_vec[0] == 0 else 0,
        ]

        selected_role = self.my_role_cb.get().strip().upper()
        role_vec = [1 if r == selected_role else 0 for r in self.roles_list]

        return np.array(role_vec + ally_vec + enemy_vec + delta_vec + extra_vec, dtype=np.float32).reshape(1, -1)

    def validate_inputs(self):
        if self.my_role_cb.get().strip().upper() not in VALID_ROLES:
            return False, "Choose your role."

        all_selected = [s.selected_champ for s in self.all_selectors() if s.selected_champ]
        if not all_selected:
            return False, "Enter at least one champ."
        if len(all_selected) != len(set(all_selected)):
            return False, "The same champ cannot be chosen more than once."
        return True, ""

    def run_prediction(self):
        if not self.model:
            self.res_box.delete("0.0", "end")
            self.res_box.insert("0.0", "ERROR: Model did not load.")
            return

        ok, msg = self.validate_inputs()
        if not ok:
            self.res_box.delete("0.0", "end")
            self.res_box.insert("0.0", f"ERROR: {msg}")
            return

        try:
            ally_count = sum(1 for s in self.ally_selectors if s.selected_champ)
            enemy_count = sum(1 for s in self.enemy_selectors if s.selected_champ)
            X_input = self.build_feature_vector()

            expected = getattr(self.model, "n_features_in_", None)
            actual = X_input.shape[1]
            if expected is not None and expected != actual:
                self.res_box.delete("0.0", "end")
                self.res_box.insert("0.0", f"ERROR: Model expects {expected} feature, but UI created {actual}.")
                return

            probs = self.model.predict_proba(X_input)[0]
            taken = set(self.get_all_selected_champs())

            candidates = []
            for idx, champ_id in enumerate(self.model.classes_):
                name = self.id_to_name.get(champ_id)
                if name and name not in taken:
                    candidates.append((probs[idx], name))

            candidates.sort(reverse=True)
            top_picks = candidates[:3]

            self.res_box.delete("0.0", "end")
            self.res_box.insert(
                "0.0",
                f"Your role: {self.my_role_cb.get().strip().upper()}\n"
                f"Draft: {ally_count}/4 ally | {enemy_count}/5 enemy\n\n"
            )

            for i, (prob, name) in enumerate(top_picks, start=1):
                self.res_box.insert("end", f"{i}. {name.ljust(18)} {prob * 100:6.2f}%\n")

        except Exception as e:
            self.res_box.delete("0.0", "end")
            self.res_box.insert("0.0", f"ERROR with prediction:\n{e}")


class ChampSlot(ctk.CTkFrame):
    def __init__(self, app, master, role_name):
        super().__init__(master)
        self.app = app
        self.role_name = role_name
        self.selected_champ = None

        self.grid_columnconfigure(2, weight=1)

        self.icon_label = ctk.CTkLabel(self, text="", width=34)
        self.icon_label.grid(row=0, column=0, padx=(6, 4), pady=6)

        self.role_label = ctk.CTkLabel(self, text=role_name, width=78, anchor="w", font=("Arial", 12, "bold"))
        self.role_label.grid(row=0, column=1, padx=(0, 6), pady=6, sticky="w")

        self.entry = ctk.CTkEntry(self, placeholder_text="Champ name + Enter", height=30)
        self.entry.grid(row=0, column=2, padx=(0, 6), pady=6, sticky="ew")
        self.entry.bind("<Return>", self.on_confirm)
        self.entry.bind("<FocusOut>", self.on_focus_out)

        self.clear_btn = ctk.CTkButton(
            self,
            text="X",
            width=30,
            height=30,
            command=self.clear,
            fg_color="#8b1e1e",
            hover_color="#a62424"
        )
        self.clear_btn.grid(row=0, column=3, padx=(0, 6), pady=6)

        self.status_label = ctk.CTkLabel(self, text="", width=120, anchor="w", font=("Arial", 10))
        self.status_label.grid(row=0, column=4, padx=(0, 6), pady=6, sticky="w")

    def set_role(self, role_name):
        self.role_name = role_name
        self.role_label.configure(text=role_name)

    def set_selected(self, champ_name):
        if not champ_name:
            self.clear(silent=True)
            return
        self.selected_champ = champ_name
        self.entry.delete(0, "end")
        self.entry.insert(0, champ_name)
        self.entry.configure(state="disabled")

        icon = self.app.get_champion_icon(champ_name, size=(28, 28))
        if icon:
            self.icon_label.configure(image=icon, text="")
        else:
            self.icon_label.configure(image=None, text="?")

        self.status_label.configure(text="Chosen", text_color="#cfcfcf")

    def try_select_from_entry(self):
        if self.selected_champ:
            return

        raw = self.entry.get().strip()
        if not raw:
            self.status_label.configure(text="", text_color="gray70")
            return

        champ_name = self.app.normalize_champ_name(raw)
        if not champ_name:
            self.status_label.configure(text="Invalid", text_color="#ff6b6b")
            return

        if self.app.is_champ_taken(champ_name, self):
            self.status_label.configure(text="Already chosen", text_color="#ff6b6b")
            return

        self.set_selected(champ_name)
        self.app.on_selector_updated()

    def on_confirm(self, event=None):
        self.try_select_from_entry()

    def on_focus_out(self, event=None):
        if not self.selected_champ:
            self.try_select_from_entry()

    def clear(self, silent=False):
        self.selected_champ = None
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.icon_label.configure(image=None, text="")
        self.status_label.configure(text="", text_color="gray70")
        if not silent:
            self.app.on_selector_updated()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = LoLModernApp()
    app.mainloop()
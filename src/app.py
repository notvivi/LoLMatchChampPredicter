import customtkinter as ctk
from PIL import Image
import requests
from io import BytesIO
import json, numpy as np, torch, torch.nn as nn
import sys, os

ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"]
ALLY_ROLES = {r: [x for x in ROLES if x != r] for r in ROLES}
DDR = "https://ddragon.leagueoflegends.com"


class SimpleScaler:
    """
    Lightweight replacement for sklearn StandardScaler.
    Loaded from scaler_params.json — no sklearn dependency at runtime.
    :param mean (list): Feature means from training.
    :param scale (list): Feature standard deviations from training.
    :param n_features (int): Number of input features.
    """
    def __init__(self, mean, scale, n_features):
        self.mean_          = np.array(mean,  dtype=np.float32)
        self.scale_         = np.array(scale, dtype=np.float32)
        self.n_features_in_ = n_features

    def transform(self, X):
        """
        Applies standard scaling: (X - mean) / scale.
        :param X (np.ndarray): Raw feature array.
        :return: np.ndarray — scaled features.
        """
        return ((X - self.mean_) / self.scale_).astype(np.float32)


class SimpleEncoder:
    """
    Lightweight replacement for sklearn LabelEncoder.
    Loaded from le_classes.json — no sklearn dependency at runtime.
    :param classes (list): Ordered list of champion IDs from training.
    """
    def __init__(self, classes):
        self.classes_ = np.array(classes)

    def inverse_transform(self, indices):
        """
        Maps class indices back to champion IDs.
        :param indices (list[int]): Model output indices.
        :return: np.ndarray — champion IDs.
        """
        return self.classes_[indices]


class DraftNet(nn.Module):
    """
    Feed-forward neural network for champion recommendation.
    :param input_size (int): Number of input features.
    :param num_classes (int): Number of output classes (champions).
    """
    def __init__(self, input_size, num_classes):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 128), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(128, 256),        nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        return self.network(x)


class ChampSlot(ctk.CTkFrame):
    """
    Single row widget for selecting a champion for a given role.
    Contains: champion icon, role label, name entry, clear button, status label.
    :param app: Reference to the main App instance.
    :param master: Parent widget.
    :param role (str): Role name displayed in this slot (e.g. "TOP").
    """
    def __init__(self, app, master, role):
        super().__init__(master)
        self.app, self.role_name, self.selected_champ = app, role, None
        self.grid_columnconfigure(2, weight=1)

        self.icon_lbl = ctk.CTkLabel(self, text="", width=60)
        self.icon_lbl.grid(row=0, column=0, padx=(6, 4), pady=8)

        self.role_lbl = ctk.CTkLabel(self, text=role, width=94, anchor="w", font=("Arial", 14, "bold"))
        self.role_lbl.grid(row=0, column=1, padx=(0, 6), sticky="w")

        self.entry = ctk.CTkEntry(self, placeholder_text="Champ name", height=42, font=("Arial", 13))
        self.entry.grid(row=0, column=2, padx=(0, 6), pady=8, sticky="ew")
        self.entry.bind("<Return>",     lambda e: self._confirm())
        self.entry.bind("<FocusOut>",   lambda e: self._confirm())
        self.entry.bind("<KeyRelease>", lambda e: self._on_text_change())

        ctk.CTkButton(self, text="X", width=42, height=42, command=self.clear,
                      fg_color="#8b1e1e", hover_color="#a62424", font=("Arial", 13, "bold")).grid(row=0, column=3, padx=(0, 6), pady=8)

        self.status = ctk.CTkLabel(self, text="", width=130, anchor="w", font=("Arial", 12))
        self.status.grid(row=0, column=4, padx=(0, 6), sticky="w")

    def set_role(self, role):
        """
        Updates the displayed role label.
        :param role (str): New role name.
        """
        self.role_name = role
        self.role_lbl.configure(text=role)

    def _set_icon(self, name=None):
        """
        Loads and displays the champion icon, or clears it if name is None.
        :param name (str|None): Champion name to fetch icon for.
        """
        icon = self.app.get_icon(name) if name else None
        self.icon_lbl.configure(image=icon or "", text="" if icon else ("?" if name else ""))
        self.icon_lbl.image = icon  # prevent garbage collection

    def set_selected(self, name):
        """
        Marks a champion as selected: fills entry, shows icon, updates status.
        :param name (str): Canonical champion name.
        """
        self.selected_champ = name
        self.entry.delete(0, "end")
        self.entry.insert(0, name)
        self._set_icon(name)
        self.status.configure(text="Chosen", text_color="#cfcfcf")

    def _on_text_change(self):
        """Resets selection state when the user edits the entry manually."""
        raw = self.entry.get().strip()
        if not raw or (self.selected_champ and raw.lower() != self.selected_champ.lower()):
            self.selected_champ = None
            self._set_icon()
            self.status.configure(text="", text_color="gray70")

    def _confirm(self):
        """
        Validates the typed champion name on Enter/FocusOut.
        Shows error status if the name is invalid or already taken.
        """
        raw = self.entry.get().strip()
        if not raw:
            return self.clear()
        name = self.app.normalize(raw)
        if not name:
            self.selected_champ = None
            self._set_icon()
            return self.status.configure(text="Invalid", text_color="#ff6b6b")
        if self.app.is_taken(name, self):
            return self.status.configure(text="Already chosen", text_color="#ff6b6b")
        self.set_selected(name)

    def clear(self):
        """Resets the slot to its empty state."""
        self.selected_champ = None
        self.entry.delete(0, "end")
        self._set_icon()
        self.status.configure(text="", text_color="gray70")


class App(ctk.CTk):
    """
    Main application window.
    Loads champion data from Riot Data Dragon, loads the trained model,
    and renders the draft UI with ally/enemy team panels.
    """
    def __init__(self):
        super().__init__()
        self.title("Solo/Duo Champ Predictor")
        self.geometry("1000x700")
        self.minsize(860, 580)
        self.model = self.scaler = self.label_encoder = None
        self.device = torch.device("cpu")
        self.champ_icons = {}  # icon cache: (name, size) -> CTkImage
        self._load_champ_data()
        self._load_model()
        self._build_ui()
        self._refresh()

    def _load_model(self):
        """
        Loads scaler params and label encoder classes from JSON,
        then loads DraftNet weights from draftnet_model.pth.
        All three files must be in the same folder as the exe/script.
        Silently disables prediction if any file is missing or invalid.
        """
        base = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
        try:
            with open(os.path.join(base, "scaler_params.json")) as f:
                sp = json.load(f)
            self.scaler = SimpleScaler(sp["mean"], sp["scale"], sp["n_features"])

            with open(os.path.join(base, "le_classes.json")) as f:
                classes = json.load(f)
            self.label_encoder = SimpleEncoder(classes)

            model_path = os.path.join(base, "draftnet_model.pth")
            self.model = DraftNet(self.scaler.n_features_in_, len(self.label_encoder.classes_))
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()
            print("Model loaded OK")
        except Exception as e:
            print(f"Model load error: {e}")

    def _load_champ_data(self):
        """
        Fetches champion data from the latest Data Dragon version.
        Falls back to a minimal hardcoded dataset if the request fails.
        """
        try:
            ver = requests.get(f"{DDR}/api/versions.json", timeout=10).json()[0]
            data = requests.get(f"{DDR}/cdn/{ver}/data/en_US/champion.json", timeout=10).json()["data"]
            self.ver = ver
            self.name_to_id = {n: int(d["key"]) for n, d in data.items()}
            self.id_to_name  = {int(d["key"]): n for n, d in data.items()}
            self.id_to_tags  = {int(d["key"]): d["tags"] for n, d in data.items()}
        except Exception:
            self.ver = "14.7.1"
            self.name_to_id = {"Garen": 86, "Ashe": 22}
            self.id_to_name  = {86: "Garen", 22: "Ashe"}
            self.id_to_tags  = {86: ["Fighter", "Tank"], 22: ["Marksman"]}
        self.champ_names = sorted(self.name_to_id)
        self.champ_lower = {n.lower(): n for n in self.champ_names}  # for case-insensitive lookup

    def get_icon(self, name, size=(56, 56)):
        """
        Returns a CTkImage for the given champion, fetched from Data Dragon.
        Results are cached; returns None on network/decode failure.
        :param name (str): Champion name.
        :param size (tuple): Icon dimensions in pixels.
        :return: CTkImage or None.
        """
        key = (name, size)
        if key not in self.champ_icons:
            try:
                r = requests.get(f"{DDR}/cdn/{self.ver}/img/champion/{name}.png", timeout=3)
                r.raise_for_status()
                img = Image.open(BytesIO(r.content))
                self.champ_icons[key] = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            except Exception:
                self.champ_icons[key] = None
        return self.champ_icons[key]

    def _build_ui(self):
        """Builds the top bar, ally/enemy panels, and bottom predict bar."""
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, height=72)
        top.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 4), sticky="ew")
        top.grid_propagate(False)
        ctk.CTkLabel(top, text="Your role:", font=("Arial", 14, "bold")).pack(side="left", padx=(14, 8))
        self.role_cb = ctk.CTkComboBox(top, values=ROLES, width=160, font=("Arial", 13), command=self._on_role_changed)
        self.role_cb.pack(side="left")
        self.role_cb.set("MIDDLE")

        self.ally_slots, self.ally_selectors   = self._team_panel(0, "ALLY TEAM",  "#3b8ed0")
        self.enemy_slots, self.enemy_selectors = self._team_panel(1, "ENEMY TEAM", "#db4437")

        bot = ctk.CTkFrame(self)
        bot.grid(row=2, column=0, columnspan=2, padx=10, pady=(4, 10), sticky="ew")
        ctk.CTkButton(bot, text="PREDICT", height=50, width=200, font=("Arial", 16, "bold"),
                      command=self._predict, fg_color="#28a745", hover_color="#218838").pack(side="left", padx=12, pady=12)
        self.res_box = ctk.CTkTextbox(bot, height=120, font=("Consolas", 14))
        self.res_box.pack(side="right", padx=12, pady=12, fill="x", expand=True)
        self.res_box.insert("0.0", "Write down champ and then press Enter.")

    def _team_panel(self, col, title, color):
        """
        Creates a team panel (ally or enemy) with one ChampSlot per role.
        :param col (int): Grid column index (0 = ally, 1 = enemy).
        :param title (str): Panel header text.
        :param color (str): Header text color.
        :return: tuple(slots_frame, list[ChampSlot])
        """
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=col,
                   padx=(10 if col == 0 else 5, 5 if col == 0 else 10), pady=4, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=("Arial", 16, "bold"), text_color=color).pack(pady=(10, 4))
        slots = ctk.CTkFrame(frame, fg_color="transparent")
        slots.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        roles = ALLY_ROLES.get(self.role_cb.get(), ROLES) if col == 0 else ROLES
        selectors = [ChampSlot(self, slots, r) for r in roles]
        for s in selectors:
            s.pack(fill="x", pady=3)
        return slots, selectors

    def _refresh(self):
        """Syncs role labels in all slots to match the currently selected role."""
        for sel, role in zip(self.ally_selectors, ALLY_ROLES.get(self.role_cb.get().upper(), ROLES)):
            sel.set_role(role)
        for sel, role in zip(self.enemy_selectors, ROLES):
            sel.set_role(role)

    def _on_role_changed(self, choice):
        """
        Re-assigns ally slots when the user changes their role.
        Preserves previously selected champions where the role still exists.
        :param choice (str): Newly selected role.
        """
        old = {s.role_name: s.selected_champ for s in self.ally_selectors}
        for sel, role in zip(self.ally_selectors, ALLY_ROLES.get(choice, ROLES)):
            sel.set_role(role)
            prev = old.get(role)
            sel.set_selected(prev) if prev and not self.is_taken(prev, sel) else sel.clear()

    def all_selectors(self):
        """:return: list[ChampSlot] — all ally and enemy slots combined."""
        return self.ally_selectors + self.enemy_selectors

    def is_taken(self, name, exclude=None):
        """
        Checks whether a champion is already selected in any other slot.
        :param name (str): Champion name to check.
        :param exclude (ChampSlot|None): Slot to ignore in the check.
        :return: bool
        """
        return any(s.selected_champ == name for s in self.all_selectors() if s is not exclude)

    def normalize(self, text):
        """
        Resolves a user-typed string to a canonical champion name.
        Tries exact match, then prefix match, then substring match.
        :param text (str): Raw user input.
        :return: str or None if no unambiguous match found.
        """
        q = text.strip().lower()
        if not q:
            return None
        if q in self.champ_lower:
            return self.champ_lower[q]
        for candidates in (
            [n for n in self.champ_names if n.lower().startswith(q)],
            [n for n in self.champ_names if q in n.lower()],
        ):
            if len(candidates) == 1:
                return candidates[0]
        return None

    def _comp_stats(self, names):
        """
        Counts champion type tags for a list of champion names.
        :param names (list[str]): Champion names.
        :return: list[int] — [tanks, mages+supports, marksmen+assassins, fighters]
        """
        tags = [t for n in names for t in self.id_to_tags.get(self.name_to_id.get(n), [])]
        return [
            tags.count("Tank"),
            tags.count("Mage") + tags.count("Support"),
            tags.count("Marksman") + tags.count("Assassin"),
            tags.count("Fighter"),
        ]

    def _build_features(self):
        """
        Builds and scales the feature vector for model inference.
        Features: one-hot role + ally comp stats + enemy comp stats + two delta stats.
        :return: np.ndarray of shape (1, n_features), scaled.
        """
        ally  = [s.selected_champ for s in self.ally_selectors  if s.selected_champ]
        enemy = [s.selected_champ for s in self.enemy_selectors if s.selected_champ]
        role_vec = [1 if r == self.role_cb.get().upper() else 0 for r in ROLES]
        a, e = self._comp_stats(ally), self._comp_stats(enemy)
        features = [*role_vec, *a, *e, a[0] - e[0], a[1] - e[1]]
        X = np.array(features, dtype=np.float32).reshape(1, -1)
        return self.scaler.transform(X).astype(np.float32)

    def _predict(self):
        """
        Runs inference and displays the top 3 recommended champions.
        Validates input, builds features, runs the model, filters already-taken champions.
        """
        if not all([self.model, self.scaler, self.label_encoder]):
            return self._show("ERROR: Neural model did not load.")
        selected = [s.selected_champ for s in self.all_selectors() if s.selected_champ]
        if not selected:
            return self._show("ERROR: Enter at least one champ.")
        if len(selected) != len(set(selected)):
            return self._show("ERROR: The same champ cannot be chosen more than once.")
        try:
            X = self._build_features()
            if X.shape[1] != self.scaler.n_features_in_:
                return self._show(f"ERROR: Model expects {self.scaler.n_features_in_} features, got {X.shape[1]}.")
            with torch.no_grad():
                probs = torch.softmax(self.model(torch.tensor(X)), dim=1).cpu().numpy()[0]

            taken = set(selected)
            top3 = sorted(
                [(p, self.id_to_name.get(int(self.label_encoder.inverse_transform([i])[0])))
                 for i, p in enumerate(probs)
                 if self.id_to_name.get(int(self.label_encoder.inverse_transform([i])[0])) not in taken],
                reverse=True
            )[:3]

            ally_c  = sum(1 for s in self.ally_selectors  if s.selected_champ)
            enemy_c = sum(1 for s in self.enemy_selectors if s.selected_champ)
            lines = [f"Role: {self.role_cb.get().upper()}  |  Draft: {ally_c}/4 ally  {enemy_c}/5 enemy\n"]
            lines += [f"{i}. {n.ljust(18)} {p*100:6.2f}%" for i, (p, n) in enumerate(top3, 1)] or ["No available recommendations."]
            self._show("\n".join(lines))
        except Exception as e:
            self._show(f"ERROR: {e}")

    def _show(self, text):
        """
        Replaces the result box content with the given text.
        :param text (str): Text to display.
        """
        self.res_box.delete("0.0", "end")
        self.res_box.insert("0.0", text)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
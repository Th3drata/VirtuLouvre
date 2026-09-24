"""Constantes, réglages du joueur (config/settings.json) et petits outils de calcul."""

import json
import math
import os

import numpy as np
import pygame

DOSSIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chemin(*morceaux):
    """Chemin absolu d'un fichier du projet : le jeu se lance depuis n'importe quel dossier."""
    return os.path.join(DOSSIER, *morceaux)


VERSION = "3.0"
FICHIER_CONFIG = chemin("config", "settings.json")

# --- Le joueur (unités du jeu : 1 unité ≈ 1,15 m) ---
EYE = 1.5  # hauteur des yeux debout
CROUCH_EYE = 0.95  # accroupi
BODY = 1.75  # taille (pour les lasers)
CROUCH_BODY = 1.15
RADIUS = 0.3  # « épaisseur » du joueur pour les collisions
STEP = 0.45  # hauteur de marche franchissable
CELL = 0.25  # taille d'une case des cartes de collision

# --- Les touches ---
ACTIONS = [  # (identifiant, libellé, touches par défaut)
    ("forward", "Avancer", ["z", "w"]),  # Z et W : ZQSD (AZERTY) et WASD (QWERTY) marchent tous les deux
    ("back", "Reculer", ["s"]),
    ("left", "Aller à gauche", ["q", "a"]),
    ("right", "Aller à droite", ["d"]),
    ("sprint", "Courir", ["left shift"]),
    ("jump", "Sauter / monter", ["space"]),
    ("crouch", "S'accroupir / descendre", ["c"]),
    ("interact", "Examiner / agir", ["e"]),
    ("torch", "Lampe torche", ["f"]),
    ("fly", "Voler (visite libre)", ["g"]),
]
ARROWS = {"forward": pygame.K_UP, "back": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT}
KEY_LABELS = {
    "space": "ESPACE", "left shift": "MAJ", "right shift": "MAJ DROITE", "left ctrl": "CTRL",
    "right ctrl": "CTRL DROITE", "left alt": "ALT", "right alt": "ALT GR", "return": "ENTRÉE",
    "backspace": "EFFACER", "tab": "TAB", "up": "HAUT", "down": "BAS", "left": "GAUCHE",
    "right": "DROITE", "left meta": "CMD", "right meta": "CMD DROITE",
}

# --- L'interface ---
GOLD = (214, 178, 94)
IVORY = (242, 236, 222)
DIM = (150, 142, 128)
RED = (235, 90, 75)
BLUE = (120, 175, 255)
GREEN = (110, 210, 140)
RESOLUTIONS = [(854, 480), (960, 540), (1280, 720), (1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160)]
SERIF_FONT = next((p for p in (  # police à empattements pour les titres, selon le système
    "/System/Library/Fonts/Supplemental/Georgia.ttf",  # macOS
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "georgia.ttf"),  # Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",  # Linux (Debian, Ubuntu)
    "/usr/share/fonts/dejavu-serif-fonts/DejaVuSerif.ttf",  # Linux (Fedora)
    "/usr/share/fonts/TTF/DejaVuSerif.ttf",  # Linux (Arch)
    "/usr/share/fonts/noto/NotoSerif-Regular.ttf",  # Linux (Arch, avec Noto)
) if os.path.exists(p)), None)  # None : police par défaut de pygame

# --- Les œuvres accrochées aux murs (src/tableaux, domaine public) ---
TABLEAUX = {
    "joconde": ("La Joconde", "Léonard de Vinci", "vers 1503-1519"),
    "noces_de_cana": ("Les Noces de Cana", "Véronèse", "1562-1563"),
    "concert_champetre": ("Le Concert champêtre", "Titien", "vers 1509"),
    "femme_au_miroir": ("La Femme au miroir", "Titien", "vers 1515"),
    "homme_au_gant": ("L'Homme au gant", "Titien", "vers 1520"),
    "belle_nani": ("La Belle Nani", "Véronèse", "vers 1560"),
    "vierge_aux_rochers": ("La Vierge aux rochers", "Léonard de Vinci", "1483-1486"),
    "belle_ferronniere": ("La Belle Ferronnière", "Léonard de Vinci", "vers 1490-1497"),
    "saint_jean_baptiste": ("Saint Jean-Baptiste", "Léonard de Vinci", "vers 1513-1516"),
    "sainte_anne": ("La Vierge à l'Enfant avec sainte Anne", "Léonard de Vinci", "vers 1503-1519"),
    "castiglione": ("Portrait de Baldassare Castiglione", "Raphaël", "vers 1514-1515"),
    "mort_de_la_vierge": ("La Mort de la Vierge", "Caravage", "1601-1606"),
    "dentelliere": ("La Dentellière", "Johannes Vermeer", "vers 1669-1670"),
    "tricheur": ("Le Tricheur à l'as de carreau", "Georges de La Tour", "vers 1635"),
    "liberte": ("La Liberté guidant le peuple", "Eugène Delacroix", "1830"),
    "radeau_meduse": ("Le Radeau de la Méduse", "Théodore Géricault", "1818-1819"),
    "sacre_napoleon": ("Le Sacre de Napoléon", "Jacques-Louis David", "1805-1807"),
    "serment_horaces": ("Le Serment des Horaces", "Jacques-Louis David", "1784"),
    "grande_odalisque": ("La Grande Odalisque", "Jean-Auguste-Dominique Ingres", "1814"),
    "madame_recamier": ("Madame Récamier", "Jacques-Louis David", "1800"),
}


# ---------------------------------------------------------------------------
# Réglages du joueur
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "volume": 0.8,
    "musique": 0.5,
    "fov": 75,
    "sensitivity": 0.12,
    "resolution": None,
    "fullscreen": False,
    "controls": {action: touches for action, _, touches in ACTIONS},
    "progress": {},  # {mission : {"stars": 0-3, "best": secondes}}
}


def key_code(nom):
    """Code pygame d'une touche à partir de son nom ("z", "space"...), ou None si inconnu."""
    try:
        return pygame.key.key_code(nom)
    except (ValueError, TypeError, pygame.error):
        return None


def nombre(valeur, positif=True):
    """Vrai si la valeur lue dans le JSON est un nombre fini (et positif si demandé)."""
    return type(valeur) in (int, float) and math.isfinite(valeur) and (valeur > 0 if positif else valeur >= 0)


def load_settings():
    """Charge les réglages ; toute valeur absente, invalide ou d'une ancienne version reprend sa valeur par défaut."""
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))  # copie indépendante des valeurs par défaut
    try:
        with open(FICHIER_CONFIG, encoding="utf-8") as fichier:
            data = json.load(fichier)
    except (OSError, ValueError):
        return settings
    if not isinstance(data, dict):
        return settings
    for cle in ("fov", "sensitivity"):
        if nombre(data.get(cle)):
            settings[cle] = data[cle]
    for cle in ("volume", "musique"):
        if nombre(data.get(cle), positif=False):
            settings[cle] = data[cle]
    if type(data.get("fullscreen")) is bool:
        settings["fullscreen"] = data["fullscreen"]
    resolution = data.get("resolution")
    if isinstance(resolution, list) and len(resolution) == 2 and all(type(n) is int for n in resolution):
        settings["resolution"] = resolution
    controles = data.get("controls")
    if isinstance(controles, dict):  # (la toute première version stockait une liste : on l'ignore)
        for action, touches in controles.items():
            if action in settings["controls"] and isinstance(touches, list) and all(
                isinstance(t, str) and key_code(t) for t in touches
            ):
                settings["controls"][action] = touches
    progression = data.get("progress")
    if isinstance(progression, dict):
        for mission, info in progression.items():
            if isinstance(info, dict) and type(info.get("stars")) is int and 0 <= info["stars"] <= 3:
                entree = {"stars": info["stars"]}
                if nombre(info.get("best")):
                    entree["best"] = float(info["best"])
                settings["progress"][str(mission)] = entree
    ancien = data.get("best_time")  # version 2 : un seul record, celui de la mission des joyaux
    if "apollon" not in settings["progress"] and nombre(ancien):
        settings["progress"]["apollon"] = {"stars": 3 if ancien <= 90 else 2 if ancien <= 150 else 1, "best": float(ancien)}
    settings["volume"] = min(1.0, settings["volume"])
    settings["musique"] = min(1.0, settings["musique"])
    settings["fov"] = int(min(100, max(50, settings["fov"])))
    settings["sensitivity"] = min(0.36, max(0.03, settings["sensitivity"]))
    return settings


def save_settings(settings):
    """Enregistre les réglages (sans planter si le dossier est en lecture seule)."""
    try:
        os.makedirs(os.path.dirname(FICHIER_CONFIG), exist_ok=True)
        with open(FICHIER_CONFIG, "w", encoding="utf-8") as fichier:
            json.dump(settings, fichier, indent=4, ensure_ascii=False)
    except OSError as erreur:
        print("Impossible d'enregistrer les réglages :", erreur)


# ---------------------------------------------------------------------------
# Petits outils
# ---------------------------------------------------------------------------


def fmt_time(secondes):
    """125.3 -> "2:05" """
    s = max(0, int(secondes))
    return f"{s // 60}:{s % 60:02d}"


def clamp(x, a, b):
    return a if x < a else b if x > b else x


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def angle_vers(dx, dz):
    """Lacet (en degrés) qui regarde dans la direction (dx, dz) — même convention que la caméra."""
    return math.degrees(math.atan2(dz, dx))


def ecart_angle(a, b):
    """Écart entre deux angles en degrés, entre -180 et 180."""
    return (b - a + 180) % 360 - 180


def seg_seg_distance(p1, q1, p2, q2):
    """Distance minimale entre les segments [p1 q1] et [p2 q2] (en 3D) — sert aux lasers."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = float(d1 @ d1), float(d2 @ d2), float(d2 @ r)
    if a < 1e-9 and e < 1e-9:
        return float(np.linalg.norm(r))
    if a < 1e-9:
        s, t = 0.0, clamp(f / e, 0.0, 1.0)
    else:
        c = float(d1 @ r)
        if e < 1e-9:
            s, t = clamp(-c / a, 0.0, 1.0), 0.0
        else:
            b = float(d1 @ d2)
            denominateur = a * e - b * b
            s = clamp((b * f - c * e) / denominateur, 0.0, 1.0) if denominateur > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0:
                s, t = clamp(-c / a, 0.0, 1.0), 0.0
            elif t > 1:
                s, t = clamp((b - c) / a, 0.0, 1.0), 1.0
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


def wrap(texte, largeur_max, mesure):
    """Coupe un texte en lignes qui tiennent dans `largeur_max` (mesure(ligne) -> largeur)."""
    lignes = []
    for paragraphe in texte.split("\n"):
        ligne = ""
        for mot in paragraphe.split(" "):
            essai = (ligne + " " + mot).strip()
            if ligne and mesure(essai) > largeur_max:
                lignes.append(ligne)
                ligne = mot
            else:
                ligne = essai
        lignes.append(ligne)
    return lignes

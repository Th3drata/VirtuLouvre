# Projet : VirtuLouvre
# Auteurs : Albert Oscar, Moors Michel, Rinckenbach Yann
"""VirtuLouvre : la galerie d'Apollon du musée du Louvre en 3D.

Deux modes de jeu :
  - Mission : la galerie est plongée dans le noir ; retrouve à la lampe torche les huit
    joyaux de la Couronne avant la fermeture du musée ;
  - Visite libre : promène-toi (ou vole) dans la galerie éclairée.

Fonctionne sous Windows, macOS et Linux (Python 3.9+, pygame-ce, PyOpenGL, NumPy).
Lancer le jeu : python main.py        Auto-test sans fenêtre : python main.py --test
"""

import ctypes
import json
import math
import os
import random
import sys
import tempfile
import time
from collections import deque

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # pas de message de pygame dans la console

import numpy as np
import OpenGL
import pygame

if not getattr(pygame, "IS_CE", False):  # pygame « classique » et pygame-ce s'installent au même endroit
    sys.exit("VirtuLouvre a besoin de pygame-ce (et pas de pygame) : pip uninstall pygame pygame-ce, "
             "puis pip install -r requirements.txt")
OpenGL.ERROR_CHECKING = False  # plus rapide, et un pilote graphique capricieux ne fait pas planter le jeu
from OpenGL.GL import *  # (doit venir après le réglage ci-dessus ; pas de GLU : absent de beaucoup de Linux)

DOSSIER = os.path.dirname(os.path.abspath(__file__))


def chemin(*morceaux):
    """Chemin absolu d'un fichier du projet : le jeu se lance depuis n'importe quel dossier."""
    return os.path.join(DOSSIER, *morceaux)


VERSION = "2.0"
FICHIER_CONFIG = chemin("config", "settings.json")
MODELE = chemin("src", "models", "untitled.obj")  # en minuscules : Linux distingue les majuscules

# --- La galerie (unités du modèle 3D : 1 unité ≈ 1,15 m) ---
FLOOR_Y = -1.5  # hauteur du sol
EYE_HEIGHT = 1.5  # hauteur des yeux au-dessus du sol
RADIUS = 0.3  # « épaisseur » du joueur pour les collisions
START = (0.2, 18.2)  # point de départ (x, z), au bout de la galerie
CELL = 0.25  # taille d'une case de la carte des collisions
GRID_X = (-3.75, 5.25)  # emprise de la carte des collisions
GRID_Z = (-22.6, 20.3)
VITRINES = [(0.2, 10.0, False), (0.2, 0.0, True), (0.2, -10.0, False)]  # (x, z, brisée ?)
VITRINE_SIZE = (0.45, 0.85, 0.85)  # demi-largeur, demi-longueur, hauteur du socle
PICK_RADIUS = 1.2  # distance à laquelle on ramasse un joyau

# --- La mission ---
MISSION_TIME = 180  # secondes avant la fermeture du musée
JEWELS = [  # les huit joyaux volés dans la galerie d'Apollon le 19 octobre 2025
    ("Diadème de saphirs de Marie-Amélie et Hortense", (70, 110, 255)),
    ("Collier de saphirs de Marie-Amélie et Hortense", (50, 90, 235)),
    ("Boucle d'oreille de saphirs", (110, 150, 255)),
    ("Collier d'émeraudes de Marie-Louise", (40, 205, 110)),
    ("Boucles d'oreilles d'émeraudes de Marie-Louise", (80, 225, 150)),
    ("Broche reliquaire", (225, 240, 255)),
    ("Diadème de l'impératrice Eugénie", (255, 232, 240)),
    ("Grand nœud de corsage de l'impératrice Eugénie", (215, 230, 255)),
]

# --- Les touches ---
ACTIONS = [  # (identifiant, libellé, touches par défaut)
    ("forward", "Avancer", ["z", "w"]),  # Z et W : ZQSD (AZERTY) et WASD (QWERTY) marchent tous les deux
    ("back", "Reculer", ["s"]),
    ("left", "Aller à gauche", ["q", "a"]),
    ("right", "Aller à droite", ["d"]),
    ("sprint", "Courir", ["left shift"]),
    ("jump", "Sauter / monter", ["space"]),
    ("down", "Descendre (vol)", ["c"]),
    ("fly", "Voler / atterrir (visite libre)", ["g"]),
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
RESOLUTIONS = [(854, 480), (960, 540), (1280, 720), (1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160)]
WINDOW_FLAGS = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
SERIF_FONT = next((p for p in (  # police à empattements pour les titres, selon le système
    "/System/Library/Fonts/Supplemental/Georgia.ttf",  # macOS
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "georgia.ttf"),  # Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",  # Linux (Debian, Ubuntu)
    "/usr/share/fonts/dejavu-serif-fonts/DejaVuSerif.ttf",  # Linux (Fedora)
    "/usr/share/fonts/TTF/DejaVuSerif.ttf",  # Linux (Arch)
) if os.path.exists(p)), None)  # None : police par défaut de pygame


# ---------------------------------------------------------------------------
# Paramètres (config/settings.json)
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "volume": 0.8,
    "fov": 75,
    "sensitivity": 0.12,
    "resolution": None,
    "fullscreen": False,
    "best_time": None,
    "controls": {action: touches for action, _, touches in ACTIONS},
}


def key_code(nom):
    """Code pygame d'une touche à partir de son nom ("z", "space"...), ou None si inconnu."""
    try:
        return pygame.key.key_code(nom)
    except (ValueError, TypeError, pygame.error):
        return None


def load_settings():
    """Charge les paramètres ; toute valeur absente, invalide ou d'une ancienne version reprend sa valeur par défaut."""
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))  # copie indépendante des valeurs par défaut
    try:
        with open(FICHIER_CONFIG, encoding="utf-8") as fichier:
            data = json.load(fichier)
    except (OSError, ValueError):
        return settings
    if not isinstance(data, dict):
        return settings
    for cle in ("volume", "fov", "sensitivity", "best_time"):
        valeur = data.get(cle)
        if type(valeur) in (int, float) and math.isfinite(valeur) and (valeur >= 0 if cle == "volume" else valeur > 0):
            settings[cle] = valeur
    if type(data.get("fullscreen")) is bool:
        settings["fullscreen"] = data["fullscreen"]
    resolution = data.get("resolution")
    if isinstance(resolution, list) and len(resolution) == 2 and all(type(n) is int for n in resolution):
        settings["resolution"] = resolution
    controles = data.get("controls")
    if isinstance(controles, dict):  # (l'ancienne version stockait une liste : on l'ignore)
        for action, touches in controles.items():
            if action in settings["controls"] and isinstance(touches, list) and all(
                isinstance(t, str) and key_code(t) for t in touches
            ):
                settings["controls"][action] = touches
    settings["volume"] = min(1.0, settings["volume"])
    settings["fov"] = int(min(100, max(50, settings["fov"])))
    settings["sensitivity"] = min(0.36, max(0.03, settings["sensitivity"]))
    return settings


def save_settings(settings):
    """Enregistre les paramètres (sans planter si le dossier est en lecture seule)."""
    try:
        os.makedirs(os.path.dirname(FICHIER_CONFIG), exist_ok=True)
        with open(FICHIER_CONFIG, "w", encoding="utf-8") as fichier:
            json.dump(settings, fichier, indent=4, ensure_ascii=False)
    except OSError as erreur:
        print("Impossible d'enregistrer les paramètres :", erreur)


def fmt_time(secondes):
    """125.3 -> "2:05" """
    s = max(0, int(secondes))
    return f"{s // 60}:{s % 60:02d}"


# ---------------------------------------------------------------------------
# Modèle 3D et carte des collisions
# ---------------------------------------------------------------------------


def load_model(fichier_obj):
    """Lit un fichier .obj et renvoie trois tableaux (positions, UV, normales) avec un sommet
    par coin de triangle, prêts à être envoyés à la carte graphique.
    Gère les polygones (découpés en triangles), les indices négatifs et les UV/normales absents."""
    v, vt, vn, coins = [["0", "0", "0"]], [["0", "0"]], [["0", "1", "0"]], []  # indice 0 = valeur par défaut
    with open(fichier_obj, encoding="utf-8", errors="replace") as fichier:
        for ligne in fichier:
            m = ligne.split()
            if not m:
                continue
            if m[0] == "v":
                v.append(m[1:4])
            elif m[0] == "vt":
                vt.append(m[1:3])
            elif m[0] == "vn":
                vn.append(m[1:4])
            elif m[0] == "f":
                c = m[1:]
                for k in range(1, len(c) - 1):  # polygone -> triangles en éventail
                    coins += (c[0], c[k], c[k + 1])
    # "12/5/7", "12//7", "12/5" ou "12" -> [12, 5, 7] (0 quand une partie manque)
    indices = np.array([(c.replace("//", "/0/") + "/0/0").split("/")[:3] for c in coins], dtype=np.int64)
    tableaux = []
    for colonne, valeurs in enumerate((v, vt, vn)):
        tableau = np.array(valeurs, dtype=np.float32)
        negatifs = indices[:, colonne] < 0  # indice -1 = dernier élément lu
        indices[negatifs, colonne] += len(tableau)
        tableaux.append(tableau[indices[:, colonne]])
    return tableaux


def cell_of(x, z):
    """Case (ligne, colonne) de la carte des collisions qui contient le point (x, z)."""
    return int((z - GRID_Z[0]) // CELL), int((x - GRID_X[0]) // CELL)


def dilate(carte, rayon):
    """Étend les cases vraies d'une carte booléenne de `rayon` cases dans toutes les directions."""
    resultat = carte.copy()
    for di in range(-rayon, rayon + 1):
        for dj in range(-rayon, rayon + 1):
            resultat |= np.roll(carte, (di, dj), axis=(0, 1))
    return resultat


class Gallery:
    """La galerie d'Apollon : le modèle 3D, les vitrines et la carte des collisions."""

    def __init__(self, positions, uvs, normals):
        self.positions, self.uvs, self.normals = positions, uvs, normals
        self.grid, self.reach = self.build_grid()
        self.spots = self.find_spots()
        x, z = next((x, z) for x, z, brisee in VITRINES if brisee)
        self.vitrine_spot = (x, FLOOR_Y + VITRINE_SIZE[2] + 0.17, z)  # sur le velours de la vitrine brisée
        hasard = random.Random(7)
        self.shards = []  # éclats de verre au pied de la vitrine brisée
        while len(self.shards) < 40:
            cx, cz = x + hasard.uniform(-1.2, 1.2), z + hasard.uniform(-1.5, 1.5)
            if abs(cx - x) > VITRINE_SIZE[0] or abs(cz - z) > VITRINE_SIZE[1]:
                self.shards.append(
                    [(cx + hasard.uniform(-0.08, 0.08), FLOOR_Y + 0.01, cz + hasard.uniform(-0.08, 0.08)) for _ in range(3)]
                )

    def build_grid(self):
        """Carte des collisions vue de dessus : une case est un obstacle si le modèle 3D y a de la
        matière à hauteur du corps (murs, cheminées, portes...) ou si elle est hors d'atteinte."""
        p = self.positions
        tri = p.reshape(-1, 3, 3)
        # sommets + centres + milieux des arêtes : assez de points pour ne rater aucun mur
        points = np.concatenate([p, tri.mean(axis=1), (tri[:, 0] + tri[:, 1]) / 2,
                                 (tri[:, 1] + tri[:, 2]) / 2, (tri[:, 2] + tri[:, 0]) / 2])
        corps = points[(points[:, 1] > FLOOR_Y + 0.3) & (points[:, 1] < FLOOR_Y + 1.9)]
        nz = int(round((GRID_Z[1] - GRID_Z[0]) / CELL))
        nx = int(round((GRID_X[1] - GRID_X[0]) / CELL))
        i = np.floor((corps[:, 2] - GRID_Z[0]) / CELL).astype(int)
        j = np.floor((corps[:, 0] - GRID_X[0]) / CELL).astype(int)
        dedans = (i >= 0) & (i < nz) & (j >= 0) & (j < nx)
        compte = np.zeros((nz, nx), dtype=np.int32)
        np.add.at(compte, (i[dedans], j[dedans]), 1)
        grid = compte > 3  # quelques points isolés ne font pas un mur
        grid[[0, -1], :] = True  # bords de la carte
        grid[:, [0, -1]] = True
        hx, hz, _ = VITRINE_SIZE
        for x, z, _ in VITRINES:  # les vitrines sont des obstacles
            (i0, j0), (i1, j1) = cell_of(x - hx, z - hz), cell_of(x + hx, z + hz)
            grid[i0:i1 + 1, j0:j1 + 1] = True
        # Cases où le joueur tient debout (la case et ses 8 voisines sont libres), puis
        # parcours en largeur depuis le départ : tout ce qui est inaccessible devient un mur.
        # Ça bouche les trous du scan 3D par lesquels on pourrait sortir de la galerie.
        tient = ~dilate(grid, 1)
        depart = cell_of(*START)
        reach = np.zeros_like(grid)
        reach[depart] = True
        file = deque([depart])
        while file:
            i0, j0 = file.popleft()
            for a, b in ((i0 + 1, j0), (i0 - 1, j0), (i0, j0 + 1), (i0, j0 - 1)):
                if tient[a, b] and not reach[a, b]:
                    reach[a, b] = True
                    file.append((a, b))
        return ~dilate(reach, 1), reach

    def find_spots(self):
        """Cachettes possibles pour les joyaux : cases accessibles, un peu à l'écart des murs."""
        loin_des_murs = ~dilate(~self.reach, 2)
        spots = []
        for i, j in zip(*np.nonzero(loin_des_murs)):
            x, z = GRID_X[0] + (j + 0.5) * CELL, GRID_Z[0] + (i + 0.5) * CELL
            if math.hypot(x - START[0], z - START[1]) > 3.5:
                spots.append((float(x), FLOOR_Y + 0.25, float(z)))
        return spots

    def blocked(self, x, z):
        """Le corps du joueur (un carré de côté 2 × RADIUS centré en x, z) touche-t-il un obstacle ?"""
        g = self.grid
        for px, pz in ((x - RADIUS, z - RADIUS), (x + RADIUS, z - RADIUS), (x - RADIUS, z + RADIUS), (x + RADIUS, z + RADIUS)):
            i, j = cell_of(px, pz)
            if not (0 <= i < g.shape[0] and 0 <= j < g.shape[1]) or g[i, j]:
                return True
        return False

    def place_jewels(self, hasard):
        """Choisit une cachette par tronçon de galerie : les joyaux sont répartis sur toute la longueur."""
        n = len(JEWELS)
        bornes = np.linspace(GRID_Z[0], GRID_Z[1], n + 1)
        choix = []
        for a, b in zip(bornes, bornes[1:]):
            options = [s for s in self.spots if a <= s[2] < b and s not in choix]
            choix.append(hasard.choice(options or [s for s in self.spots if s not in choix]))
        if hasard.random() < 0.6:  # souvent, un joyau est resté dans la vitrine brisée
            k = min(range(n), key=lambda i: abs(choix[i][2] - self.vitrine_spot[2]))
            choix[k] = self.vitrine_spot
        return choix

    # --- Dessin (nécessite OpenGL) ---

    def upload(self):
        """Envoie le modèle 3D à la carte graphique (un seul tampon : positions, puis UV, puis normales)."""
        donnees = np.concatenate([self.positions.ravel(), self.uvs.ravel(), self.normals.ravel()])
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, donnees.nbytes, donnees, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.count = len(self.positions)
        self.offsets = (self.positions.nbytes, self.positions.nbytes + self.uvs.nbytes)

    def draw_model(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glTexCoordPointer(2, GL_FLOAT, 0, ctypes.c_void_p(self.offsets[0]))
        glNormalPointer(GL_FLOAT, 0, ctypes.c_void_p(self.offsets[1]))
        glDrawArrays(GL_TRIANGLES, 0, self.count)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def draw_vitrines(self):
        """Socles en bois, velours et cadres dorés des vitrines (parties opaques)."""
        hx, hz, h = VITRINE_SIZE
        for x, z, brisee in VITRINES:
            draw_box(x - hx, FLOOR_Y, z - hz, x + hx, FLOOR_Y + h - 0.04, z + hz, (0.34, 0.19, 0.11))
            draw_box(x - hx - 0.02, FLOOR_Y + h - 0.04, z - hz - 0.02, x + hx + 0.02, FLOOR_Y + h, z + hz + 0.02, (0.78, 0.62, 0.3))
            draw_box(x - hx + 0.04, FLOOR_Y + h, z - hz + 0.04, x + hx - 0.04, FLOOR_Y + h + 0.02, z + hz - 0.04, (0.12, 0.1, 0.32))
            # arêtes de la cloche de verre (chaque coin a sa normale, sinon la lampe les laisse noires)
            y0, y1 = FLOOR_Y + h, FLOOR_Y + h + 0.5
            coins = ((x - hx, z - hz), (x + hx, z - hz), (x + hx, z + hz), (x - hx, z + hz))
            normales = ((-0.71, 0, -0.71), (0.71, 0, -0.71), (0.71, 0, 0.71), (-0.71, 0, 0.71))
            glColor3f(0.8, 0.65, 0.32)
            glLineWidth(2.0)
            glBegin(GL_LINES)
            for k in range(4):
                (ax, az), (bx, bz) = coins[k], coins[(k + 1) % 4]
                glNormal3f(*normales[k])
                glVertex3f(ax, y0, az)
                glVertex3f(ax, y1, az)
                glVertex3f(ax, y1, az)
                glNormal3f(*normales[(k + 1) % 4])
                glVertex3f(bx, y1, bz)
            glEnd()

    def draw_glass(self, lum):
        """Vitres et éclats de verre (transparents : à dessiner après les objets opaques)."""
        hx, hz, h = VITRINE_SIZE
        y0, y1 = FLOOR_Y + h, FLOOR_Y + h + 0.5
        glColor4f(0.65 * lum, 0.8 * lum, 0.95 * lum, 0.16)
        glBegin(GL_QUADS)
        for x, z, brisee in VITRINES:
            x0, x1, z0, z1 = x - hx, x + hx, z - hz, z + hz
            faces = [((x0, z0), (x1, z0)), ((x1, z1), (x0, z1))] if brisee else [
                ((x0, z0), (x1, z0)), ((x1, z0), (x1, z1)), ((x1, z1), (x0, z1)), ((x0, z1), (x0, z0))]
            for (ax, az), (bx, bz) in faces:
                for px, py, pz in ((ax, y0, az), (bx, y0, bz), (bx, y1, bz), (ax, y1, az)):
                    glVertex3f(px, py, pz)
            if not brisee:  # couvercle
                for px, pz in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
                    glVertex3f(px, y1, pz)
        glEnd()
        glColor4f(0.85 * lum, 0.92 * lum, 1.0 * lum, 0.45)
        glBegin(GL_TRIANGLES)
        for eclat in self.shards:
            for point in eclat:
                glVertex3f(*point)
        glEnd()


# ---------------------------------------------------------------------------
# Le joueur
# ---------------------------------------------------------------------------


class Player:
    """Le visiteur : caméra à la première personne, déplacements, saut, vol et collisions."""

    WALK, RUN, FLY = 2.6, 5.0, 4.5  # vitesses en unités par seconde
    GRAVITY, JUMP = 15.0, 4.8

    def __init__(self, x, z, yaw=-90.0, pitch=0.0):
        self.pos = np.array([x, FLOOR_Y + EYE_HEIGHT, z], dtype=float)
        self.vel = np.zeros(3)
        self.yaw, self.pitch = yaw, pitch
        self.flying = False
        self.on_ground = True
        self.walking = False  # (pour le bruit de pas)
        self.want_jump = False
        self.bob = 0.0  # balancement de la tête en marchant

    def front(self):
        lacet, tangage = math.radians(self.yaw), math.radians(self.pitch)
        return np.array([math.cos(lacet) * math.cos(tangage), math.sin(tangage), math.sin(lacet) * math.cos(tangage)])

    def eye(self):
        return self.pos + (0.0, math.sin(self.bob) * 0.035, 0.0)

    def look(self, dx, dy, sensibilite):
        self.yaw = (self.yaw + dx * sensibilite) % 360
        self.pitch = max(-89.0, min(89.0, self.pitch - dy * sensibilite))

    def update(self, dt, held, gallery, can_fly):
        """Avance le joueur de `dt` secondes ; `held(action)` dit si une touche est enfoncée."""
        if not can_fly:
            self.flying = False
        lacet = math.radians(self.yaw)
        fx, fz = math.cos(lacet), math.sin(lacet)
        avant, cote = held("forward") - held("back"), held("right") - held("left")
        dx, dz = avant * fx - cote * fz, avant * fz + cote * fx
        n = math.hypot(dx, dz)
        vitesse = (self.RUN if held("sprint") else self.WALK) * (1.8 if self.flying else 1.0)
        cible = (dx / n * vitesse, dz / n * vitesse) if n else (0.0, 0.0)
        douceur = min(1.0, dt * 12)  # accélération progressive
        self.vel[0] += (cible[0] - self.vel[0]) * douceur
        self.vel[2] += (cible[1] - self.vel[2]) * douceur
        x, z = self.pos[0], self.pos[2]
        mx, mz = self.vel[0] * dt, self.vel[2] * dt
        if self.flying or gallery.blocked(x, z):  # en vol (ou coincé) : on passe partout
            x, z = x + mx, z + mz
        else:  # un axe après l'autre : on glisse le long des murs au lieu de s'y coller
            if not gallery.blocked(x + mx, z):
                x += mx
            if not gallery.blocked(x, z + mz):
                z += mz
        self.pos[0], self.pos[2] = x, z

        sol = FLOOR_Y + EYE_HEIGHT
        if self.flying:
            self.pos[1] = max(sol, self.pos[1] + (held("jump") - held("down")) * self.FLY * dt)
        else:
            if self.want_jump and self.on_ground:
                self.vel[1] = self.JUMP
            self.vel[1] -= self.GRAVITY * dt
            self.pos[1] += self.vel[1] * dt
            self.on_ground = self.pos[1] <= sol
            if self.on_ground:
                self.pos[1], self.vel[1] = sol, 0.0
        self.want_jump = False
        self.walking = self.on_ground and not self.flying and n > 0
        if self.walking:
            self.bob += dt * vitesse * 3.2

    def apply(self, fov, aspect):
        """Place la caméra OpenGL à la place des yeux du joueur (comme gluPerspective + gluLookAt)."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        pres = 0.05
        haut = pres * math.tan(math.radians(fov) / 2)
        glFrustum(-haut * aspect, haut * aspect, -haut, haut, pres, 400.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        avant = self.front()
        droite = np.cross(avant, (0.0, 1.0, 0.0))
        droite /= np.linalg.norm(droite)
        vue = np.identity(4)
        vue[0, :3], vue[1, :3], vue[2, :3] = droite, np.cross(droite, avant), -avant
        glMultMatrixd(vue.T)  # OpenGL lit les matrices colonne par colonne
        glTranslated(*-self.eye())


# ---------------------------------------------------------------------------
# Sons
# ---------------------------------------------------------------------------


class Audio:
    """Sons du jeu : fabriqués avec NumPy (pas de fichiers), plus les bruits de pas.
    Sans carte son (machine virtuelle, serveur...), le jeu tourne quand même, en silence."""

    def __init__(self, volume):
        self.sounds, self.walk, self.channel = {}, None, None
        if not pygame.mixer.get_init():
            print("Pas de son disponible : le jeu continue sans audio.")
            return
        frequence = pygame.mixer.get_init()[0]

        def notes(hauteurs, duree, amortissement=6.0):
            t = np.arange(int(frequence * duree)) / frequence
            enveloppe = np.exp(-amortissement * t) * (1 - np.exp(-t * 400))  # attaque douce, puis extinction
            onde = np.concatenate([np.sin(2 * np.pi * f * t) * enveloppe for f in hauteurs])
            onde = (onde * 32767 * 0.8).astype(np.int16)
            return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([onde, onde])))

        self.sounds = {  # nom : (son, volume relatif)
            "beep_near": (notes([1480], 0.07, 25), 0.35),
            "beep_mid": (notes([1175], 0.07, 25), 0.3),
            "beep_far": (notes([880], 0.07, 25), 0.25),
            "pickup": (notes([1047, 1319, 1568, 2093], 0.09, 9), 0.5),
            "win": (notes([523, 659, 784, 1047, 784, 1047, 1319], 0.13, 5), 0.5),
            "lose": (notes([392, 349, 294, 196], 0.24, 4), 0.5),
            "tick": (notes([1250], 0.035, 30), 0.3),
            "click": (notes([720], 0.03, 40), 0.25),
        }
        try:
            self.walk = pygame.mixer.Sound(chemin("src", "media", "walk.mp3"))
            pygame.mixer.set_reserved(1)  # un canal réservé aux pas
            self.channel = pygame.mixer.Channel(0)
        except pygame.error as erreur:
            print("Bruits de pas indisponibles :", erreur)
        self.set_volume(volume)

    def set_volume(self, volume):
        for son, relatif in self.sounds.values():
            son.set_volume(volume * relatif)
        if self.walk:
            self.walk.set_volume(volume * 0.6)

    def play(self, nom):
        if nom in self.sounds:
            self.sounds[nom][0].play()

    def walking(self, en_marche):
        """Le fichier de pas dure 24 s : on le joue en boucle et on le met en pause à l'arrêt."""
        if not self.channel:
            return
        if not en_marche:
            self.channel.pause()
        elif self.channel.get_busy():
            self.channel.unpause()
        else:
            self.channel.play(self.walk, loops=-1)


# ---------------------------------------------------------------------------
# Petits outils OpenGL
# ---------------------------------------------------------------------------


def load_texture(fichier):
    """Envoie une image à la carte graphique, réduite si elle dépasse la taille maximale supportée."""
    image = pygame.image.load(fichier)
    limite = int(glGetIntegerv(GL_MAX_TEXTURE_SIZE))
    if max(image.get_size()) > limite:  # vieilles cartes graphiques : 4096 px maximum
        k = limite / max(image.get_size())
        image = pygame.transform.smoothscale(image, (int(image.get_width() * k), int(image.get_height() * k)))
    largeur, hauteur = image.get_size()
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, largeur, hauteur, 0, GL_RGB, GL_UNSIGNED_BYTE,
                 pygame.image.tobytes(image, "RGB", True))
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    try:
        glGenerateMipmap(GL_TEXTURE_2D)  # versions réduites de l'image : pas de scintillement au loin
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    except Exception:  # OpenGL trop ancien : texture simple
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    if b"GL_EXT_texture_filter_anisotropic" in (glGetString(GL_EXTENSIONS) or b""):
        glTexParameterf(GL_TEXTURE_2D, 0x84FE, min(8.0, float(glGetFloatv(0x84FF))))  # sol net en biais
    return texture


def make_glow_texture(taille=64):
    """Halo lumineux en étoile, calculé avec NumPy, pour faire briller les joyaux."""
    y, x = np.mgrid[-1:1:taille * 1j, -1:1:taille * 1j]
    rond = np.clip(1 - np.hypot(x, y), 0, 1) ** 2.2
    branches = np.clip(1 - np.abs(x) * 14, 0, 1) * np.clip(1 - np.abs(y), 0, 1) ** 2
    alpha = np.maximum(rond, 0.8 * np.maximum(branches, branches.T))
    rgba = np.dstack([np.full(alpha.shape, 255, np.uint8)] * 3 + [(alpha * 255).astype(np.uint8)])
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, taille, taille, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba.tobytes())
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return texture


def draw_box(x0, y0, z0, x1, y1, z1, couleur):
    """Pavé plein ; chaque face a sa normale (pour la lampe torche) et sa nuance (relief sans lampe)."""
    glBegin(GL_QUADS)
    for normale, nuance, coins in (
        ((0, 1, 0), 1.0, ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))),
        ((0, -1, 0), 0.4, ((x0, y0, z0), (x0, y0, z1), (x1, y0, z1), (x1, y0, z0))),
        ((1, 0, 0), 0.75, ((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0))),
        ((-1, 0, 0), 0.75, ((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1))),
        ((0, 0, 1), 0.6, ((x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1))),
        ((0, 0, -1), 0.6, ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))),
    ):
        glNormal3f(*normale)
        glColor3f(*(c * nuance for c in couleur))
        for coin in coins:
            glVertex3f(*coin)
    glEnd()


def gem_triangles(facettes=8):
    """Une pierre précieuse taillée : une couronne en haut, un pavillon pointu en bas."""
    haut, bas = np.array([0.0, 0.55, 0.0]), np.array([0.0, -0.95, 0.0])
    tour = [np.array([math.cos(a), 0.0, math.sin(a)]) for a in np.linspace(0, 2 * math.pi, facettes, endpoint=False)]
    triangles = []
    for k in range(facettes):
        a, b = tour[k], tour[(k + 1) % facettes]
        for tri in ((haut, b, a), (bas, a, b)):
            n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            triangles.append((n / np.linalg.norm(n), tri))
    return triangles


GEM = gem_triangles()


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
# Interface 2D
# ---------------------------------------------------------------------------


class UI:
    """Interface dessinée avec pygame sur une surface, plaquée en texture par-dessus la 3D.

    Les coordonnées sont « virtuelles » : 720 de haut, la largeur suit le format de la fenêtre.
    Tout est mis à l'échelle au moment de dessiner, donc le texte reste net à toute résolution.
    C'est une interface « immédiate » : button() dessine le bouton ET dit s'il vient d'être cliqué."""

    H = 720

    def __init__(self):
        self.texture = glGenTextures(1)
        self.fonts, self.cache, self.icons = {}, {}, {}
        self.window = None
        self.click = None  # position du clic de cette image, None sinon
        self.active = None  # curseur en cours de glissement
        self.clicked = False  # un bouton a été cliqué (pour le son)

    def resize(self, largeur, hauteur):
        surface_h = min(hauteur, 1080)  # ponytail: surface plafonnée à 1080 lignes, l'envoi au GPU reste rapide en 4K
        self.k = surface_h / self.H
        self.W = largeur / hauteur * self.H
        self.surface = pygame.Surface((round(largeur * surface_h / hauteur), surface_h), pygame.SRCALPHA)
        self.window = (largeur, hauteur)
        self.fonts.clear()
        self.cache.clear()
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, *self.surface.get_size(), 0, GL_RGBA, GL_UNSIGNED_BYTE, None)

    def mouse(self):
        mx, my = pygame.mouse.get_pos()
        return mx * self.W / self.window[0], my * self.H / self.window[1]

    def to_virtual(self, pos):
        return pos[0] * self.W / self.window[0], pos[1] * self.H / self.window[1]

    def px(self, r):
        return pygame.Rect(round(r[0] * self.k), round(r[1] * self.k), round(r[2] * self.k), round(r[3] * self.k))

    def font(self, taille, serif=False):
        if (taille, serif) not in self.fonts:
            self.fonts[taille, serif] = pygame.font.Font(SERIF_FONT if serif else None, max(8, round(taille * self.k)))
        return self.fonts[taille, serif]

    def text(self, texte, taille, pos, couleur=IVORY, ancre="center", serif=False, alpha=255):
        image = self.font(taille, serif).render(texte, True, couleur)
        if alpha < 255:
            image.set_alpha(alpha)
        r = image.get_rect(**{ancre: (round(pos[0] * self.k), round(pos[1] * self.k))})
        self.surface.blit(image, r)
        return pygame.FRect(r.x / self.k, r.y / self.k, r.w / self.k, r.h / self.k)

    def rect(self, couleur, r, rayon=0, epaisseur=0):
        pr = self.px(r)
        epaisseur = max(1, round(epaisseur * self.k)) if epaisseur else 0
        if len(couleur) == 4:  # semi-transparent : on passe par une surface pour mélanger les couleurs
            calque = pygame.Surface(pr.size, pygame.SRCALPHA)
            pygame.draw.rect(calque, couleur, calque.get_rect(), epaisseur, round(rayon * self.k))
            self.surface.blit(calque, pr)
        else:
            pygame.draw.rect(self.surface, couleur, pr, epaisseur, round(rayon * self.k))

    def line(self, couleur, a, b, epaisseur=1):
        pygame.draw.line(self.surface, couleur, (round(a[0] * self.k), round(a[1] * self.k)),
                         (round(b[0] * self.k), round(b[1] * self.k)), max(1, round(epaisseur * self.k)))

    def diamond(self, centre, r, couleur, plein=True):
        x, y, r = centre[0] * self.k, centre[1] * self.k, r * self.k
        pygame.draw.polygon(self.surface, couleur, [(x, y - r), (x + r * 0.8, y), (x, y + r), (x - r * 0.8, y)],
                            0 if plein else max(1, round(self.k * 1.5)))

    def hit(self, r):
        """Vrai si le clic de cette image tombe dans le rectangle (le clic est alors consommé)."""
        if self.click and pygame.FRect(r).collidepoint(self.click):
            self.click, self.clicked = None, True
            return True
        return False

    def button(self, texte, pos, taille=30, ancre="center", couleur=IVORY, serif=False):
        """Bouton texte : surligné au survol, renvoie True s'il vient d'être cliqué."""
        w, h = self.font(taille, serif).size(texte)
        r = pygame.FRect(0, 0, w / self.k + 28, h / self.k + 14)
        setattr(r, ancre, pos)
        survol = r.collidepoint(self.mouse())
        if survol:
            self.rect((255, 255, 255, 20), r, rayon=8)
            self.rect(GOLD, (r.x, r.y + 6, 3, r.h - 12))
        self.text(texte, taille, r.center, GOLD if survol else couleur, serif=serif)
        return self.hit(r)

    def icon(self, nom, r, teinte=None):
        """Icône de src/icons (teintée si besoin) ; renvoie True si elle vient d'être cliquée."""
        cle = (nom, teinte, r[2], r[3])
        if cle not in self.cache:
            if nom not in self.icons:
                brute = pygame.image.load(chemin("src", "icons", nom + ".png"))
                self.icons[nom] = pygame.Surface(brute.get_size(), pygame.SRCALPHA)
                self.icons[nom].blit(brute, (0, 0))  # conversion en 32 bits (certaines icônes ont une palette)
            image = pygame.transform.smoothscale(self.icons[nom], self.px(r).size)
            if teinte:  # icônes noires -> couleur voulue (la transparence est conservée)
                image.fill(teinte, special_flags=pygame.BLEND_RGB_MAX)
            self.cache[cle] = image
        image = self.cache[cle].copy()
        if not pygame.FRect(r).collidepoint(self.mouse()):
            image.set_alpha(190)
        self.surface.blit(image, self.px(r))
        return self.hit(r)

    def slider(self, cle, r, valeur, mini, maxi):
        """Barre réglable à la souris ; renvoie la nouvelle valeur."""
        r = pygame.FRect(r)
        if self.click and r.inflate(16, 24).collidepoint(self.click):
            self.active, self.click = cle, None
        if self.active == cle:
            if pygame.mouse.get_pressed()[0]:
                valeur = mini + (maxi - mini) * min(1.0, max(0.0, (self.mouse()[0] - r.x) / r.w))
            else:
                self.active = None
        t = (valeur - mini) / (maxi - mini)
        self.rect((255, 255, 255, 45), r, rayon=r.h / 2)
        self.rect(GOLD, (r.x, r.y, max(r.h, r.w * t), r.h), rayon=r.h / 2)
        pygame.draw.circle(self.surface, IVORY, (round((r.x + r.w * t) * self.k), round(r.centery * self.k)), round(8 * self.k))
        return valeur

    def overlay(self, sorte):
        """Grands dégradés calculés une fois par taille de fenêtre (fond du menu, vignette du jeu)."""
        if sorte not in self.cache:
            w, h = self.surface.get_size()
            if sorte == "menu":  # sombre à gauche (sous le texte) et en bas, plus clair ailleurs
                x, y = np.linspace(0, 1, w)[:, None], np.linspace(0, 1, h)[None, :]
                alpha = np.maximum(np.clip(1.1 - x * 1.5, 0.15, 0.9), np.clip((y - 0.8) * 3.5, 0, 0.7))
            else:  # vignette : coins assombris
                x, y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h), indexing="ij")
                alpha = np.clip((np.hypot(x, y) - 0.6) * 1.2, 0, 0.8)
            calque = pygame.Surface((w, h), pygame.SRCALPHA)
            calque.fill((0, 0, 0, 255))
            pygame.surfarray.pixels_alpha(calque)[:] = (alpha * 255).astype(np.uint8)
            self.cache[sorte] = calque
        self.surface.blit(self.cache[sorte], (0, 0))

    def draw(self):
        """Envoie la surface à la carte graphique et la plaque sur tout l'écran."""
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, *self.surface.get_size(), GL_RGBA, GL_UNSIGNED_BYTE,
                        pygame.image.tobytes(self.surface, "RGBA"))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, 1, 1, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        for x, y in ((0, 0), (1, 0), (1, 1), (0, 1)):
            glTexCoord2f(x, y)
            glVertex2f(x, y)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)


# ---------------------------------------------------------------------------
# Le jeu
# ---------------------------------------------------------------------------


class App:
    """Une seule fenêtre OpenGL pour tout le jeu : menus, mission et visite libre.
    Le menu s'affiche par-dessus un survol de la galerie en 3D."""

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512, allowedchanges=0)  # format fixe pour les sons NumPy
        pygame.init()
        pygame.key.stop_text_input()  # pas de saisie de texte : évite les fenêtres d'accents / IME en appui long
        self.settings = load_settings()
        self.refresh_codes()
        pygame.display.set_caption("VirtuLouvre")
        pygame.display.set_icon(pygame.image.load(chemin("src", "icons", "icon.png")))
        self.create_window(self.pick_resolution())
        self.check_opengl()
        self.ui = UI()
        self.ui.resize(*pygame.display.get_window_size())
        self.audio = Audio(self.settings["volume"])

        self.loading(0.05, "Lecture du modèle 3D...")
        self.gallery = Gallery(*load_model(MODELE))
        self.loading(0.45, "Envoi de la galerie à la carte graphique...")
        self.gallery.upload()
        self.loading(0.6, "Textures...")
        self.tex_model = load_texture(chemin("src", "textures", "texture.png"))
        self.loading(0.85, "Textures...")
        self.tex_floor = load_texture(chemin("src", "textures", "sol.png"))
        self.tex_sky = load_texture(chemin("src", "textures", "sky.png"))
        self.tex_glow = make_glow_texture()
        self.floor_list = self.build_floor()
        self.sky_list = self.build_sky()
        self.loading(1.0, "C'est prêt !")
        if self.settings["fullscreen"]:
            pygame.display.toggle_fullscreen()

        self.clock = pygame.time.Clock()
        self.running = True
        self.t = 0.0
        self.menu_cam = Player(0.2, 10.0)
        self.player = Player(*START)
        self.mode = None  # None (menus), "mission" ou "explore"
        self.state = "menu"
        self.tab = "Vidéo"
        self.settings_back = "menu"
        self.waiting_key = None
        self.skip_motion = False
        self.want_screenshot = False
        self.jewels, self.particles = [], []
        self.notice = self.toast = None  # (texte, heure d'affichage) : joyau retrouvé / capture d'écran
        self.keys = pygame.key.get_pressed()

    # --- Fenêtre ---

    def pick_resolution(self):
        """Résolutions 16:9 qui tiennent sur l'écran ; par défaut la plus grande qui laisse de la marge."""
        largeur, hauteur = pygame.display.get_desktop_sizes()[0]
        self.resolutions = [r for r in RESOLUTIONS if r[0] <= largeur and r[1] <= hauteur] or RESOLUTIONS[:1]
        sauvee = tuple(self.settings["resolution"] or ())
        if sauvee in self.resolutions:
            return sauvee
        return ([r for r in self.resolutions if r[0] <= largeur * 0.9 and r[1] <= hauteur * 0.9] or self.resolutions)[-1]

    def create_window(self, taille):
        """Fenêtre OpenGL avec anticrénelage si possible (absent de certains pilotes et machines virtuelles)."""
        for echantillons in (4, 0):
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1 if echantillons else 0)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, echantillons)
            pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
            try:
                return pygame.display.set_mode(taille, WINDOW_FLAGS)
            except pygame.error:
                pass
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 16)  # dernier recours : réglages minimaux
        return pygame.display.set_mode(taille, WINDOW_FLAGS)

    def check_opengl(self):
        """OpenGL 2.0 minimum. Sans pilote graphique (machine virtuelle sans 3D, « Carte graphique de base
        Microsoft »...), on n'a que l'OpenGL 1.1 logiciel : on le dit clairement au lieu d'un écran blanc."""
        version = (glGetString(GL_VERSION) or b"0").decode("ascii", "replace")
        try:
            trop_ancien = tuple(int(n) for n in version.split()[0].split(".")[:2]) < (2, 0)
        except ValueError:
            trop_ancien = False
        if trop_ancien or not bool(glGenBuffers):
            rendu = (glGetString(GL_RENDERER) or b"?").decode("ascii", "replace")
            pygame.display.message_box(
                "VirtuLouvre", f"OpenGL 2.0 minimum est nécessaire (trouvé : {version}, {rendu}).\n"
                "Installe le pilote de ta carte graphique, ou active l'accélération 3D de la machine virtuelle.", "error")
            pygame.quit()
            sys.exit(1)

    def change_resolution(self, pas):
        taille = pygame.display.get_window_size()
        actuelle = min(range(len(self.resolutions)), key=lambda i: abs(self.resolutions[i][0] - taille[0]))
        nouvelle = self.resolutions[(actuelle + pas) % len(self.resolutions)]
        pygame.display.set_mode(nouvelle, WINDOW_FLAGS)  # (pygame-ce garde le contexte OpenGL et les textures)
        self.settings["resolution"] = list(nouvelle)

    def toggle_fullscreen(self):
        pygame.display.toggle_fullscreen()
        self.settings["fullscreen"] = pygame.display.is_fullscreen()
        save_settings(self.settings)

    def screenshot(self, fichier=None):
        """Capture d'écran (F12) dans le dossier captures/."""
        largeur, hauteur = pygame.display.get_window_size()
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        pixels = glReadPixels(0, 0, largeur, hauteur, GL_RGB, GL_UNSIGNED_BYTE)
        image = pygame.image.frombytes(bytes(pixels), (largeur, hauteur), "RGB", True)
        if fichier is None:
            os.makedirs(chemin("captures"), exist_ok=True)
            fichier = chemin("captures", time.strftime("VirtuLouvre_%Y-%m-%d_%H-%M-%S.png"))
        pygame.image.save(image, fichier)
        return fichier

    # --- Touches ---

    def refresh_codes(self):
        """Traduit les noms de touches des paramètres en codes pygame (+ les flèches, toujours actives)."""
        self.codes = {}
        for action, _, _ in ACTIONS:
            codes = [key_code(nom) for nom in self.settings["controls"][action]]
            self.codes[action] = [c for c in codes if c] + ([ARROWS[action]] if action in ARROWS else [])

    def held(self, action):
        return any(self.keys[code] for code in self.codes[action])

    def key_text(self, action):
        noms = self.settings["controls"][action]
        return " / ".join(KEY_LABELS.get(nom, nom.upper()) for nom in noms) if noms else "—"

    def move_text(self):
        """Touches de déplacement : "ZQSD / WASD" avec les réglages par défaut."""
        listes = [self.settings["controls"][a] or ["?"] for a in ("forward", "left", "back", "right")]
        jeux = []
        for k in range(max(map(len, listes))):
            touches = [KEY_LABELS.get(l[min(k, len(l) - 1)], l[min(k, len(l) - 1)].upper()) for l in listes]
            jeux.append(("" if all(len(t) == 1 for t in touches) else "/").join(touches))
        return " / ".join(jeux)

    # --- Changements d'écran ---

    def set_state(self, etat):
        self.state = etat
        en_jeu = etat == "play"
        pygame.mouse.set_relative_mode(en_jeu)  # souris capturée et cachée pendant le jeu
        if en_jeu:
            pygame.mouse.get_rel()
            self.skip_motion = True  # le premier mouvement après capture peut être un grand saut
        else:
            self.audio.walking(False)

    def new_mission(self):
        self.mode = "mission"
        self.player = Player(*START)
        cachettes = self.gallery.place_jewels(random)
        self.jewels = [{"name": nom, "color": couleur, "pos": np.array(pos), "found": False}
                       for (nom, couleur), pos in zip(JEWELS, cachettes)]
        self.time_left = float(MISSION_TIME)
        self.elapsed = 0.0
        self.signal = 0.0
        self.beep_timer, self.beep_flash = 1.0, 0.0
        self.notice = None
        self.particles = []
        self.set_state("briefing")

    def new_visit(self):
        self.mode = "explore"
        self.player = Player(*START)
        self.jewels, self.particles = [], []
        self.visit_start = self.t
        self.set_state("play")

    def to_menu(self):
        self.mode = None
        self.jewels, self.particles = [], []
        self.set_state("menu")

    def open_settings(self, retour):
        self.settings_back = retour
        self.waiting_key = None
        self.set_state("settings")

    def close_settings(self):
        self.waiting_key = None  # sinon la touche suivante serait avalée, dans n'importe quel écran
        save_settings(self.settings)
        self.set_state(self.settings_back)

    def end_mission(self, gagne):
        self.win = gagne
        self.new_record = False
        if gagne:
            record = self.settings["best_time"]
            if record is None or self.elapsed < record:
                self.settings["best_time"] = round(self.elapsed, 2)
                self.new_record = True
                save_settings(self.settings)
        self.audio.play("win" if gagne else "lose")
        self.set_state("end")

    # --- Boucle principale ---

    def run(self):
        while self.running:
            dt = min(self.clock.tick(120) / 1000.0, 0.05)
            self.frame(pygame.event.get(), dt)
            pygame.display.flip()
        save_settings(self.settings)
        pygame.quit()

    def frame(self, evenements, dt):
        """Une image du jeu : événements, mise à jour, dessin."""
        taille = pygame.display.get_window_size()
        if taille != self.ui.window and min(taille) > 0:
            self.ui.resize(*taille)
        self.ui.click = None
        for e in evenements:
            self.handle_event(e)
        self.keys = pygame.key.get_pressed()
        self.t += dt
        if self.state == "play":
            self.update_play(dt)
        self.update_particles(dt)
        self.render()
        if self.ui.clicked:
            self.audio.play("click")
            self.ui.clicked = False
        if self.want_screenshot:
            self.want_screenshot = False
            try:
                self.toast = ("Capture enregistrée : " + os.path.relpath(self.screenshot(), DOSSIER), self.t)
            except (OSError, pygame.error) as erreur:  # dossier du jeu en lecture seule (réseau du lycée...)
                self.toast = (f"Capture impossible : {erreur}", self.t)

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.WINDOWFOCUSLOST and self.state == "play":
            self.set_state("pause")  # on change de fenêtre (Alt+Tab, Cmd+Tab) : pause automatique
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.ui.click = self.ui.to_virtual(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.ui.active = None
        elif e.type == pygame.MOUSEMOTION and self.state == "play":
            if self.skip_motion:
                self.skip_motion = False
            else:
                self.player.look(*e.rel, self.settings["sensitivity"])
        elif e.type == pygame.KEYDOWN:
            self.handle_key(e)

    def handle_key(self, e):
        if self.waiting_key:  # changement de touche dans les paramètres
            nom = pygame.key.name(e.key) or pygame.key.name(e.key, use_compat=False)  # (ù, ², é... en AZERTY)
            reservees = (pygame.K_ESCAPE, pygame.K_F11, pygame.K_F12, *ARROWS.values())  # les flèches déplacent toujours
            if e.key not in reservees and key_code(nom):
                controles = self.settings["controls"]
                for action in controles:  # une touche ne sert qu'à une action
                    controles[action] = [t for t in controles[action] if t != nom]
                controles[self.waiting_key] = [nom]
                self.refresh_codes()
            self.waiting_key = None
            return
        entree = e.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
        if e.key == pygame.K_F11 or (entree and e.mod & pygame.KMOD_ALT):  # (sur Mac, F11 règle le volume)
            self.toggle_fullscreen()
        elif e.key == pygame.K_F12:
            self.want_screenshot = True
        elif e.key == pygame.K_ESCAPE:
            retour = {"play": "pause", "pause": "play", "briefing": "menu", "credits": "menu", "end": "menu"}
            if self.state == "settings":
                self.close_settings()
            elif retour.get(self.state) == "menu":
                self.to_menu()
            elif self.state in retour:
                self.set_state(retour[self.state])
        elif entree and self.state == "briefing":
            self.set_state("play")
        elif entree and self.state == "end":
            self.new_mission()
        elif self.state == "play":
            joueur = self.player
            if e.key in self.codes["jump"]:
                joueur.want_jump = True
            elif e.key in self.codes["fly"] and self.mode == "explore":
                if joueur.flying and self.gallery.blocked(joueur.pos[0], joueur.pos[2]):
                    self.toast = ("Impossible d'atterrir ici", self.t)  # sinon on se poserait dans un mur
                else:
                    joueur.flying = not joueur.flying
                    joueur.vel[1] = 0.0

    # --- Mise à jour ---

    def update_play(self, dt):
        joueur = self.player
        joueur.update(dt, self.held, self.gallery, can_fly=self.mode == "explore")
        self.audio.walking(joueur.walking)
        if self.mode != "mission":
            return
        self.elapsed += dt
        avant = math.ceil(self.time_left)
        self.time_left -= dt
        if math.ceil(self.time_left) < avant <= 10:
            self.audio.play("tick")  # les dix dernières secondes
        for joyau in self.jewels:
            d = joyau["pos"] - joueur.pos
            if not joyau["found"] and math.hypot(d[0], d[2]) < PICK_RADIUS and abs(d[1]) < 2.0:
                joyau["found"] = True
                self.notice = (joyau["name"], self.t)
                self.audio.play("pickup")
                self.burst(joyau["pos"], joyau["color"])
        restants = [j for j in self.jewels if not j["found"]]
        if not restants:
            self.end_mission(True)
        elif self.time_left <= 0:
            self.end_mission(False)
        else:  # détecteur : bipe de plus en plus vite près du joyau le plus proche
            distance = min(float(np.linalg.norm(j["pos"] - joueur.pos)) for j in restants)
            self.signal = max(0.0, 1.0 - distance / 20.0)
            self.beep_timer -= dt
            self.beep_flash = max(0.0, self.beep_flash - dt * 4)
            if self.beep_timer <= 0:
                self.audio.play("beep_near" if distance < 4 else "beep_mid" if distance < 10 else "beep_far")
                self.beep_timer = min(1.6, 0.12 + 0.07 * distance)
                self.beep_flash = 1.0

    def burst(self, pos, couleur):
        """Gerbe d'étincelles quand on ramasse un joyau."""
        for _ in range(40):
            direction = np.random.normal(size=3)
            direction /= np.linalg.norm(direction)
            vie = random.uniform(0.6, 1.1)
            self.particles.append([np.array(pos, dtype=float), direction * random.uniform(0.8, 2.6) + (0, 1.2, 0),
                                   vie, vie, couleur])

    def update_particles(self, dt):
        for p in self.particles:
            p[1][1] -= 3.0 * dt  # gravité
            p[0] += p[1] * dt
            p[2] -= dt
        self.particles = [p for p in self.particles if p[2] > 0]

    def update_menu_camera(self):
        """Lent survol de la galerie derrière le menu."""
        t, cam = self.t, self.menu_cam
        cam.pos[:] = (0.2 + 0.9 * math.sin(t * 0.11), 0.9 + 0.5 * math.sin(t * 0.07), -1.5 + 16 * math.sin(t * 0.04))
        cam.yaw = -90 + 28 * math.sin(t * 0.05)
        cam.pitch = 10 + 8 * math.sin(t * 0.09)

    # --- Dessin 3D ---

    def render(self):
        if self.mode is None:
            self.update_menu_camera()
        self.draw_scene(self.player if self.mode else self.menu_cam, self.mode == "mission")
        ui = self.ui
        ui.surface.fill((0, 0, 0, 0))
        if self.state in ("play", "pause"):
            self.screen_hud()
        {
            "menu": self.screen_menu, "settings": self.screen_settings, "credits": self.screen_credits,
            "briefing": self.screen_briefing, "play": lambda: None, "pause": self.screen_pause, "end": self.screen_end,
        }[self.state]()
        if self.toast and self.t - self.toast[1] < 2.5:
            ui.text(self.toast[0], 20, (ui.W / 2, ui.H - 110), IVORY)
        ui.draw()

    def draw_scene(self, cam, sombre):
        largeur, hauteur = self.ui.window
        glViewport(0, 0, largeur, hauteur)
        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        cam.apply(self.settings["fov"], largeur / hauteur)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glDisable(GL_CULL_FACE)  # le scan 3D se voit des deux côtés
        glEnable(GL_TEXTURE_2D)

        # Ciel : une sphère centrée sur la caméra, dessinée sans profondeur (toujours au fond)
        glDepthMask(GL_FALSE)
        glColor3f(*((0.06, 0.07, 0.12) if sombre else (1, 1, 1)))
        glBindTexture(GL_TEXTURE_2D, self.tex_sky)
        glPushMatrix()
        glTranslatef(*cam.eye())
        glCallList(self.sky_list)
        glPopMatrix()
        glDepthMask(GL_TRUE)

        if sombre:
            self.torch_on()
        glColor3f(1, 1, 1)
        glBindTexture(GL_TEXTURE_2D, self.tex_floor)
        glCallList(self.floor_list)
        # La galerie (éclairée des deux côtés : les normales du scan ne sont pas toutes dans le bon sens)
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        glBindTexture(GL_TEXTURE_2D, self.tex_model)
        self.gallery.draw_model()
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)
        glDisable(GL_TEXTURE_2D)
        self.gallery.draw_vitrines()
        glDisable(GL_LIGHTING)

        oeil, avant = cam.eye(), cam.front()
        droite = np.cross(avant, (0.0, 1.0, 0.0))
        droite /= np.linalg.norm(droite) or 1.0
        haut = np.cross(droite, avant)
        halos = []
        for i, joyau in enumerate(self.jewels):
            if joyau["found"]:
                continue
            pos = joyau["pos"] + (0.0, 0.05 * math.sin(self.t * 2 + i), 0.0)
            vers = pos - oeil
            distance = float(np.linalg.norm(vers)) or 1.0
            eclaire = 1.0
            if sombre:  # la lampe torche fait briller les pierres qu'elle touche
                eclaire = smoothstep(0.85, 0.97, float(vers @ avant) / distance) * max(0.0, 1 - distance / 16)
            self.draw_gem(pos, joyau["color"], self.t * 70 + i * 45, 0.25 + 0.75 * eclaire, -vers / distance)
            scintille = 0.5 + 0.5 * math.sin(self.t * 5 + i * 1.7)
            taille = 0.25 + 0.5 * eclaire
            # halo avancé vers l'œil : sinon sa moitié basse passe sous le parquet et il est coupé net
            halos.append((pos - vers / distance * min(taille, distance / 2), taille, joyau["color"],
                          0.08 + 0.1 * scintille + 0.8 * eclaire))

        # Transparents : vitres, puis halos et étincelles (en « addition » de lumière)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        self.gallery.draw_glass(0.35 if sombre else 1.0)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.tex_glow)
        for p in self.particles:
            halos.append((p[0], 0.07, p[4], p[2] / p[3]))
        glBegin(GL_QUADS)
        for pos, taille, couleur, alpha in halos:
            glColor4f(couleur[0] / 255, couleur[1] / 255, couleur[2] / 255, min(1.0, alpha))
            for (u, v), (a, b) in zip(((0, 0), (1, 0), (1, 1), (0, 1)), ((-1, -1), (1, -1), (1, 1), (-1, 1))):
                glTexCoord2f(u, v)
                glVertex3f(*(pos + (droite * a + haut * b) * taille))
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)

    def build_floor(self):
        """Parquet (le scan 3D n'a pas de sol) : une grille fine dans la galerie, car la lampe éclaire
        sommet par sommet et un seul grand carré resterait noir ; puis un grand carré dehors, plus bas.
        Le tout est compilé une fois pour toutes dans une « display list »."""
        liste = glGenLists(1)
        glNewList(liste, GL_COMPILE)
        glNormal3f(0, 1, 0)
        glBegin(GL_QUADS)
        pas = 0.25
        for x in np.arange(-4.0, 6.0, pas):
            for z in np.arange(-24.0, 22.0, pas):
                for dx, dz in ((0, 0), (pas, 0), (pas, pas), (0, pas)):
                    glTexCoord2f((x + dx) * 2, (z + dz) * 2)
                    glVertex3f(x + dx, FLOOR_Y - 0.02, z + dz)
        for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            glTexCoord2f(x * 400, z * 400)
            glVertex3f(x * 200, FLOOR_Y - 0.05, z * 200)
        glEnd()
        glEndList()
        return liste

    def build_sky(self, rayon=150.0, tranches=24, quartiers=48):
        """Sphère texturée pour le ciel (remplace gluSphere), compilée une fois pour toutes."""
        liste = glGenLists(1)
        glNewList(liste, GL_COMPILE)
        for i in range(tranches):
            glBegin(GL_QUAD_STRIP)
            for j in range(quartiers + 1):
                longitude = 2 * math.pi * j / quartiers
                for k in (i, i + 1):
                    latitude = math.pi * (k / tranches - 0.5)
                    glTexCoord2f(j / quartiers, k / tranches)
                    glVertex3f(rayon * math.cos(latitude) * math.cos(longitude), rayon * math.sin(latitude),
                               rayon * math.cos(latitude) * math.sin(longitude))
            glEnd()
        glEndList()
        return liste

    def torch_on(self):
        """Galerie dans le noir, éclairée par une lampe torche fixée à la caméra."""
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.07, 0.07, 0.1, 1.0))
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glPushMatrix()
        glLoadIdentity()  # position donnée dans le repère de l'œil : la lampe suit le regard
        glLightfv(GL_LIGHT0, GL_POSITION, (0.15, -0.1, 0.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, (0.0, 0.0, -1.0))
        glPopMatrix()
        glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 30.0)
        glLightf(GL_LIGHT0, GL_SPOT_EXPONENT, 10.0)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.6, 1.5, 1.3, 1.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
        glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION, 0.6)
        glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.12)

    def draw_gem(self, pos, couleur, angle, lumiere, vers_oeil):
        """Une pierre qui tourne ; chaque facette s'allume quand elle fait face au joueur."""
        ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        r, g, b = (c / 255 for c in couleur)
        glPushMatrix()
        glTranslatef(*pos)
        glRotatef(angle, 0, 1, 0)
        glScalef(0.13, 0.13, 0.13)
        glBegin(GL_TRIANGLES)
        for n, tri in GEM:
            # normale de la facette une fois la pierre tournée, comparée à la direction de l'œil
            d = (n[0] * ca + n[2] * sa) * vers_oeil[0] + n[1] * vers_oeil[1] + (n[2] * ca - n[0] * sa) * vers_oeil[2]
            nuance = (0.3 + 0.7 * max(0.0, d)) * lumiere
            reflet = 0.7 * lumiere if d > 0.9 else 0.0
            glColor3f(min(1.0, r * nuance + reflet), min(1.0, g * nuance + reflet), min(1.0, b * nuance + reflet))
            for sommet in tri:
                glVertex3f(*sommet)
        glEnd()
        glPopMatrix()

    # --- Écrans ---

    def loading(self, avancement, texte):
        """Écran de chargement (appelé entre deux étapes de chargement)."""
        pygame.event.pump()
        ui = self.ui
        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        ui.surface.fill((8, 8, 12, 255))
        ui.text("VirtuLouvre", 72, (ui.W / 2, ui.H / 2 - 70), GOLD, serif=True)
        largeur = ui.W * 0.5
        x, y = (ui.W - largeur) / 2, ui.H / 2 + 10
        ui.rect((255, 255, 255, 40), (x, y, largeur, 10), rayon=5)
        ui.rect(GOLD, (x, y, max(10, largeur * avancement), 10), rayon=5)
        ui.text(texte, 22, (ui.W / 2, y + 44), DIM)
        ui.draw()
        pygame.display.flip()

    def back_button(self):
        ui = self.ui
        clic = ui.icon("back_arrow", (34, 30, 30, 30))
        return ui.button("Retour", (66, 45), 24, "midleft") or clic

    def screen_menu(self):
        ui = self.ui
        ui.overlay("menu")
        ui.icon("icon", (74, 128, 60, 60))
        ui.text("VirtuLouvre", 84, (146, 160), GOLD, "midleft", serif=True)
        ui.text("La galerie d'Apollon · musée du Louvre", 24, (80, 222), IVORY, "midleft")
        y = 300
        for texte, action in (
            ("Mission : les joyaux de la Couronne", self.new_mission),
            ("Visite libre", self.new_visit),
            ("Paramètres", lambda: self.open_settings("menu")),
            ("Crédits", lambda: self.set_state("credits")),
            ("Quitter", lambda: setattr(self, "running", False)),
        ):
            if ui.button(texte, (66, y), 30, "midleft"):
                action()
            y += 56
        record = self.settings["best_time"]
        ui.text(f"Record de la mission : {fmt_time(record)}" if record else "Pas encore de record : à toi de jouer !",
                20, (80, ui.H - 52), DIM, "midleft")
        ui.text(f"v{VERSION}  ·  F11 ou Alt+Entrée : plein écran", 18, (ui.W - 24, ui.H - 24), DIM, "bottomright")

    def row(self, libelle, y):
        """Ligne de réglage : fond, libellé à gauche ; renvoie l'abscisse du bord droit."""
        ui = self.ui
        x0 = ui.W / 2 - 330
        ui.rect((255, 255, 255, 14), (x0, y - 22, 660, 44), rayon=10)
        ui.text(libelle, 24, (x0 + 22, y), IVORY, "midleft")
        return x0 + 638

    def screen_settings(self):
        ui, s = self.ui, self.settings
        ui.rect((8, 8, 12, 225), (0, 0, ui.W, ui.H))
        if self.back_button():
            self.close_settings()
            return
        ui.text("Paramètres", 52, (ui.W / 2, 72), GOLD, serif=True)
        for k, onglet in enumerate(("Vidéo", "Audio", "Touches")):
            if ui.button(onglet, (ui.W / 2 + (k - 1) * 160, 138), 28, couleur=GOLD if onglet == self.tab else DIM):
                self.tab, self.waiting_key = onglet, None
        ui.line(GOLD, (ui.W / 2 - 330, 164), (ui.W / 2 + 330, 164))

        if self.tab == "Vidéo":
            xd = self.row("Résolution", 210)
            if pygame.display.is_fullscreen():
                ui.text("plein écran", 24, (xd, 210), DIM, "midright")
            else:
                largeur, hauteur = pygame.display.get_window_size()
                if ui.icon("arrow_right", (xd - 22, 199, 22, 22), IVORY):
                    self.change_resolution(+1)
                ui.text(f"{largeur} × {hauteur}", 24, (xd - 95, 210), IVORY)
                if ui.icon("arrow_left", (xd - 190, 199, 22, 22), IVORY):
                    self.change_resolution(-1)
            xd = self.row("Plein écran", 266)
            if ui.button("Oui" if pygame.display.is_fullscreen() else "Non", (xd + 14, 266), 24, "midright", BLUE):
                self.toggle_fullscreen()
            xd = self.row("Champ de vision", 322)
            s["fov"] = round(ui.slider("fov", (xd - 290, 318, 220, 8), s["fov"], 50, 100))
            ui.text(f"{s['fov']}°", 24, (xd, 322), IVORY, "midright")
            xd = self.row("Sensibilité de la souris", 378)
            s["sensitivity"] = ui.slider("sensi", (xd - 290, 374, 220, 8), s["sensitivity"], 0.03, 0.36)
            ui.text(f"{round(s['sensitivity'] / 0.12 * 100)} %", 24, (xd, 378), IVORY, "midright")

        elif self.tab == "Audio":
            xd = self.row("Volume général", 210)
            volume = ui.slider("volume", (xd - 290, 206, 220, 8), s["volume"], 0.0, 1.0)
            if volume != s["volume"]:
                s["volume"] = volume
                self.audio.set_volume(volume)
            ui.text(f"{round(volume * 100)} %", 24, (xd, 210), IVORY, "midright")
            if ui.button("Tester le son", (ui.W / 2, 280), 24, couleur=BLUE):
                self.audio.play("pickup")

        else:
            y = 196
            for action, libelle, _ in ACTIONS:
                xd = self.row(libelle, y)
                attente = self.waiting_key == action
                texte = "appuie sur une touche..." if attente else self.key_text(action)
                if ui.button(texte, (xd + 14, y), 24, "midright", GOLD if attente else BLUE):
                    self.waiting_key = action
                y += 50
            if ui.button("Touches par défaut", (ui.W / 2, y + 6), 24, couleur=BLUE):
                s["controls"] = {action: list(touches) for action, _, touches in ACTIONS}
                self.refresh_codes()
            ui.text("Les flèches marchent toujours  ·  Échap : pause  ·  F11 ou Alt+Entrée : plein écran  ·  F12 : capture",
                    18, (ui.W / 2, y + 48), DIM)

    def screen_credits(self):
        ui = self.ui
        ui.rect((8, 8, 12, 225), (0, 0, ui.W, ui.H))
        if self.back_button():
            self.set_state("menu")
            return
        gauche, droite = ui.W * 0.28, ui.W * 0.68
        ui.text("Crédits", 48, (gauche, 110), GOLD, serif=True)
        y = 170
        for titre, lignes in (
            ("Développé par", ["Albert Oscar", "Moors Michel", "Rinckenbach Yann"]),
            ("Projet de NSI", ["Trophées NSI"]),
            ("Modèle 3D", ["Galerie d'Apollon, musée du Louvre"]),
            ("Ciel", ["Freepik"]),
            ("Réalisé avec", ["Python · pygame-ce · PyOpenGL · NumPy"]),
        ):
            ui.text(titre, 20, (gauche, y), GOLD)
            y += 28
            for ligne in lignes:
                ui.text(ligne, 24, (gauche, y))
                y += 28
            y += 12
        ui.text("Merci d'avoir joué !", 30, (gauche, y + 20), IVORY, serif=True)

        ui.text("Comment jouer", 48, (droite, 110), GOLD, serif=True)
        y = 170
        for ligne in (
            ("Mission", GOLD),
            ("Le 19 octobre 2025, huit joyaux de la Couronne", IVORY),
            ("ont été volés dans la galerie d'Apollon.", IVORY),
            ("Dans ce jeu, ils sont cachés dans la galerie :", IVORY),
            (f"retrouve-les en moins de {MISSION_TIME // 60} minutes.", IVORY),
            ("", IVORY),
            ("Visite libre", GOLD),
            ("Promène-toi, ou vole jusqu'au plafond peint", IVORY),
            ("par Delacroix (Apollon vainqueur du serpent Python).", IVORY),
            ("", IVORY),
            ("Commandes", GOLD),
            (f"{self.move_text()} ou flèches : se déplacer", IVORY),
            (f"{self.key_text('sprint')} : courir   ·   {self.key_text('jump')} : sauter", IVORY),
            (f"{self.key_text('fly')} : voler   ·   {self.key_text('down')} : descendre", IVORY),
            ("Souris : regarder   ·   Échap : pause", IVORY),
        ):
            ui.text(ligne[0], 20 if ligne[1] == GOLD else 21, (droite, y), ligne[1])
            y += 28 if ligne[0] else 12

    def screen_briefing(self):
        ui = self.ui
        ui.rect((0, 0, 0, 140), (0, 0, ui.W, ui.H))
        panneau = pygame.FRect(0, 0, 800, 470)
        panneau.center = (ui.W / 2, ui.H / 2)
        ui.rect((10, 10, 16, 230), panneau, rayon=18)
        ui.rect(GOLD, panneau, rayon=18, epaisseur=1)
        cx, y = panneau.centerx, panneau.y
        ui.text("MISSION", 20, (cx, y + 50), GOLD)
        ui.text("Les joyaux de la Couronne", 46, (cx, y + 95), IVORY, serif=True)
        for k, ligne in enumerate((
            "Musée du Louvre, galerie d'Apollon. Les joyaux de la Couronne",
            "ont été dérobés ! Dans leur fuite, les voleurs ont semé leur butin",
            "dans la galerie, plongée dans le noir.",
        )):
            ui.text(ligne, 24, (cx, y + 160 + k * 30), IVORY)
        ui.text(f"Retrouve les {len(JEWELS)} joyaux en moins de {MISSION_TIME // 60} minutes.", 26, (cx, y + 270), GOLD)
        ui.text("Ta lampe fait scintiller les pierres. Le détecteur bipe plus vite quand tu t'approches.",
                20, (cx, y + 310), DIM)
        deplacement = self.move_text()
        ui.text(f"{deplacement} : avancer  ·  {self.key_text('sprint')} : courir  ·  Souris : regarder",
                20, (cx, y + 338), DIM)
        if ui.button("Commencer (Entrée)", (cx + 110, y + 410), 28, couleur=GOLD):
            self.set_state("play")
        elif ui.button("Retour", (cx - 150, y + 410), 28):
            self.to_menu()

    def screen_hud(self):
        ui = self.ui
        ui.overlay("vignette")
        cx, cy = ui.W / 2, ui.H / 2
        if self.state == "play":  # viseur (pas sous le menu pause)
            for a, b in (((-7, 0), (-2, 0)), ((2, 0), (7, 0)), ((0, -7), (0, -2)), ((0, 2), (0, 7))):
                ui.line((255, 255, 255), (cx + a[0], cy + a[1]), (cx + b[0], cy + b[1]))

        if self.mode == "explore":
            depuis = self.t - self.visit_start
            if depuis < 10:
                deplacement = self.move_text()
                ui.text(f"{deplacement} : se déplacer  ·  {self.key_text('fly')} : voler  ·  {self.key_text('jump')} / "
                        f"{self.key_text('down')} : monter / descendre  ·  Échap : menu",
                        20, (cx, ui.H - 40), IVORY, alpha=int(255 * min(1.0, 10 - depuis)))
            if self.player.flying:
                ui.text("MODE VOL", 20, (cx, 36), GOLD)
            return

        trouves = sum(j["found"] for j in self.jewels)
        ui.text("JOYAUX", 18, (40, 34), GOLD, "topleft")
        ui.text(f"{trouves} / {len(self.jewels)}", 44, (40, 54), IVORY, "topleft", serif=True)
        for i, joyau in enumerate(self.jewels):
            ui.diamond((48 + i * 22, 118), 8, joyau["color"] if joyau["found"] else DIM, joyau["found"])
        reste = math.ceil(self.time_left)
        urgent = reste <= 30
        ui.text("TEMPS RESTANT", 18, (ui.W - 40, 34), GOLD, "topright")
        ui.text(fmt_time(reste), 48, (ui.W - 40, 54), RED if urgent else IVORY, "topright", serif=True,
                alpha=int(255 * (0.6 + 0.4 * abs(math.sin(self.t * 4)))) if urgent else 255)
        # détecteur
        ui.text("DÉTECTEUR", 16, (cx, ui.H - 76), GOLD)
        allumes = round(self.signal * 16)
        for k in range(16):
            t = k / 15
            couleur = tuple(int(BLUE[c] + (RED[c] - BLUE[c]) * t) for c in range(3))
            if k >= allumes:
                couleur = (60, 60, 70)
            elif self.beep_flash > 0:
                couleur = tuple(min(255, int(c + (255 - c) * self.beep_flash * 0.6)) for c in couleur)
            ui.rect(couleur, (cx - 175 + k * 22, ui.H - 58, 18, 12), rayon=3)
        if self.notice and self.t - self.notice[1] < 3:
            alpha = int(255 * min(1.0, 3 - (self.t - self.notice[1])))
            ui.text(self.notice[0], 30, (cx, 150), GOLD, serif=True, alpha=alpha)
            ui.text("retrouvé !", 22, (cx, 184), IVORY, alpha=alpha)

    def screen_pause(self):
        ui = self.ui
        ui.rect((0, 0, 0, 160), (0, 0, ui.W, ui.H))
        ui.text("Pause", 60, (ui.W / 2, 170), GOLD, serif=True)
        choix = [("Reprendre", lambda: self.set_state("play")),
                 ("Paramètres", lambda: self.open_settings("pause"))]
        if self.mode == "mission":
            choix.append(("Recommencer la mission", self.new_mission))
        choix += [("Menu principal", self.to_menu), ("Quitter le jeu", lambda: setattr(self, "running", False))]
        for k, (texte, action) in enumerate(choix):
            if ui.button(texte, (ui.W / 2, 270 + k * 56), 30):
                action()

    def screen_end(self):
        ui = self.ui
        ui.rect((0, 0, 0, 175), (0, 0, ui.W, ui.H))
        cx = ui.W / 2
        trouves = sum(j["found"] for j in self.jewels)
        if self.win:
            ui.text("Mission accomplie !", 58, (cx, 110), GOLD, serif=True)
            ui.text(f"Les {len(JEWELS)} joyaux de la Couronne sont retrouvés en {fmt_time(self.elapsed)}.", 26, (cx, 168))
            if self.new_record:
                ui.text("Nouveau record !", 26, (cx, 204), GOLD, alpha=int(255 * (0.6 + 0.4 * abs(math.sin(self.t * 3)))))
            else:
                ui.text(f"Record : {fmt_time(self.settings['best_time'])}", 24, (cx, 204), DIM)
        else:
            ui.text("Le musée ferme...", 58, (cx, 110), RED, serif=True)
            ui.text(f"Tu as retrouvé {trouves} joyau{'x' if trouves > 1 else ''} sur {len(JEWELS)}.", 26, (cx, 168))
        for k, joyau in enumerate(self.jewels):
            y = 262 + k * 32
            ui.diamond((cx - 290, y), 7, joyau["color"] if joyau["found"] else DIM, joyau["found"])
            ui.text(joyau["name"], 22, (cx - 270, y), IVORY if joyau["found"] else DIM, "midleft")
        if ui.button("Rejouer (Entrée)", (cx + 130, ui.H - 70), 30, couleur=GOLD):
            self.new_mission()
        elif ui.button("Menu principal", (cx - 130, ui.H - 70), 30):
            self.to_menu()


# ---------------------------------------------------------------------------
# Auto-test (sans fenêtre ni carte graphique) : python main.py --test
# ---------------------------------------------------------------------------


def self_test():
    positions, uvs, normals = load_model(MODELE)
    assert len(positions) % 3 == 0 and len(positions) == len(uvs) == len(normals)
    galerie = Gallery(positions, uvs, normals)
    assert not galerie.blocked(*START), "le départ doit être libre"
    assert galerie.blocked(-3.2, 0.0), "le mur de gauche doit bloquer"
    assert galerie.blocked(0.2, 0.0), "les vitrines doivent bloquer"
    accessibles = np.argwhere(galerie.reach)
    centres = np.column_stack([GRID_X[0] + (accessibles[:, 1] + 0.5) * CELL, GRID_Z[0] + (accessibles[:, 0] + 0.5) * CELL])
    hasard = random.Random(1)
    for _ in range(200):
        cachettes = galerie.place_jewels(hasard)
        assert len(cachettes) == len(JEWELS) == len(set(cachettes)), "8 cachettes différentes"
        for x, _, z in cachettes:  # chaque joyau peut être ramassé depuis une case accessible
            assert np.hypot(centres[:, 0] - x, centres[:, 1] - z).min() < PICK_RADIUS - 0.1, (x, z)
    joueur = Player(*START, yaw=180.0)  # face au mur de gauche
    for _ in range(300):
        joueur.update(1 / 60, lambda action: action == "forward", galerie, can_fly=False)
    assert -3.0 < joueur.pos[0] < START[0] - 2, "on avance, mais on ne traverse pas le mur"
    assert abs(joueur.pos[1] - (FLOOR_Y + EYE_HEIGHT)) < 1e-9, "on reste au sol"
    global FICHIER_CONFIG  # réglages d'une ancienne version ou modifiés à la main
    ancien, FICHIER_CONFIG = FICHIER_CONFIG, os.path.join(tempfile.gettempdir(), "virtulouvre_test_settings.json")
    try:
        with open(FICHIER_CONFIG, "w", encoding="utf-8") as fichier:
            fichier.write('{"volume": 0.0, "best_time": 1e999, "fov": 500, "controls": [["Z", "Avancer"]]}')
        reglages = load_settings()
    finally:
        os.remove(FICHIER_CONFIG)
        FICHIER_CONFIG = ancien
    assert reglages["volume"] == 0.0 and reglages["best_time"] is None and reglages["fov"] == 100
    assert reglages["controls"] == DEFAULT_SETTINGS["controls"]
    assert fmt_time(125.3) == "2:05"
    print("Auto-test OK :", len(positions) // 3, "triangles,", len(galerie.spots), "cachettes possibles")


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        App().run()

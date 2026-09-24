"""Outils OpenGL : textures (fichiers et textures procédurales), maillages, éclairage, effets lumineux."""

import ctypes
import math

import numpy as np
import pygame
from OpenGL.GL import *

from .base import chemin

# ---------------------------------------------------------------------------
# Textures
# ---------------------------------------------------------------------------

_TEXTURES = {}  # nom -> identifiant OpenGL (créées une seule fois)


def texture_depuis_surface(image, repeter=True):
    """Envoie une image pygame à la carte graphique (réduite si elle dépasse la taille maximale supportée)."""
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
    enveloppe = GL_REPEAT if repeter else GL_CLAMP_TO_EDGE
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, enveloppe)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, enveloppe)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    try:
        glGenerateMipmap(GL_TEXTURE_2D)  # versions réduites de l'image : pas de scintillement au loin
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    except Exception:  # OpenGL trop ancien : texture simple
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    if b"GL_EXT_texture_filter_anisotropic" in (glGetString(GL_EXTENSIONS) or b""):
        glTexParameterf(GL_TEXTURE_2D, 0x84FE, min(8.0, float(glGetFloatv(0x84FF))))  # sols nets en biais
    return texture


def texture(nom):
    """Texture par son nom : "tableau:joconde", "fichier:src/textures/sol.png" ou une texture procédurale."""
    if nom not in _TEXTURES:
        if nom.startswith("tableau:"):
            image = pygame.image.load(chemin("src", "tableaux", nom[8:] + ".jpg"))
            _TEXTURES[nom] = texture_depuis_surface(image, repeter=False)
        elif nom.startswith("fichier:"):
            _TEXTURES[nom] = texture_depuis_surface(pygame.image.load(chemin(*nom[8:].split("/"))))
        else:
            pixels = PROCEDURALES[nom]()
            image = pygame.surfarray.make_surface(np.ascontiguousarray(pixels.swapaxes(0, 1)))
            _TEXTURES[nom] = texture_depuis_surface(image, repeter=nom != "sortie")
    return _TEXTURES[nom]


# --- Textures procédurales (tableaux NumPy lignes × colonnes × RVB) ---

N = 256  # taille des textures procédurales


def bruit(fmax=8, composantes=40, graine=0, n=N):
    """Bruit lisse entre 0 et 1, périodique (la texture se répète sans raccord visible) :
    une somme de sinusoïdes de fréquences entières, plus faibles quand la fréquence monte."""
    hasard = np.random.default_rng(graine)
    u = np.arange(n) / n
    y, x = np.meshgrid(u, u, indexing="ij")
    total = np.zeros((n, n))
    for _ in range(composantes):
        fx, fy = hasard.integers(-fmax, fmax + 1, 2)
        f = math.hypot(fx, fy)
        if f:
            total += np.sin(2 * np.pi * (fx * x + fy * y) + hasard.uniform(0, 2 * np.pi)) / f
    total -= total.min()
    return total / max(total.max(), 1e-9)


def _grille(n=N):
    u = np.arange(n) / n
    return np.meshgrid(u, u, indexing="ij")  # (y, x)


def _couleur(valeur, *couleurs):
    """Mélange de couleurs selon une valeur entre 0 et 1 (0 -> première couleur, 1 -> dernière)."""
    couleurs = np.array(couleurs, dtype=float)
    position = np.clip(valeur, 0, 1) * (len(couleurs) - 1)
    i = np.minimum(position.astype(int), len(couleurs) - 2)
    t = (position - i)[..., None]
    return couleurs[i] * (1 - t) + couleurs[i + 1] * t


def _octet(rgb):
    return np.clip(rgb, 0, 255).astype(np.uint8)


def tex_marbre(base=(236, 232, 224), veine=(120, 115, 110), graine=1):
    y, x = _grille()
    turbulence = bruit(6, 50, graine)
    veines = (1 - np.abs(np.sin(2 * np.pi * (2 * x + y) + turbulence * 9))) ** 10
    fond = _couleur(0.85 + 0.15 * bruit(12, 40, graine + 7), (0, 0, 0), base)
    return _octet(fond * (1 - veines[..., None] * 0.7) + np.array(veine) * veines[..., None] * 0.7)


def tex_damier():
    """Dallage de marbre blanc et gris, 2 × 2 dalles par répétition."""
    y, x = _grille()
    blanc, gris = tex_marbre(), tex_marbre((150, 148, 146), (60, 58, 56), graine=5)
    case = ((x * 2).astype(int) + (y * 2).astype(int)) % 2
    pixels = np.where(case[..., None] == 0, blanc, gris).astype(float)
    joint = (np.minimum((x * 2) % 1, (y * 2) % 1) < 0.012)
    pixels[joint] *= 0.45
    return _octet(pixels)


def tex_pierre(couleur=(196, 184, 160), graine=2):
    """Pierre de taille : 4 rangées de blocs décalés, joints clairs, légères variations par bloc."""
    y, x = _grille()
    rangee = (y * 4).astype(int)
    xx = x * 2 + (rangee % 2) * 0.5
    bloc = (xx.astype(int) % 2) + rangee * 2
    variation = 0.9 + 0.1 * np.sin(bloc * 12.9898) ** 2
    fond = np.array(couleur) * (variation * (0.88 + 0.12 * bruit(10, 40, graine)))[..., None]
    joint = ((y * 4) % 1 < 0.025) | ((xx % 1) < 0.012)
    fond[joint] = np.array(couleur) * 1.08
    return _octet(fond)


def tex_dalles(couleur=(170, 160, 145)):
    y, x = _grille()
    fond = np.array(couleur) * (0.82 + 0.18 * bruit(9, 40, 11))[..., None]
    fond *= (0.95 + 0.05 * np.sin(((x * 2).astype(int) * 3 + (y * 2).astype(int) * 7) * 1.7))[..., None]
    fond[np.minimum((x * 2) % 1, (y * 2) % 1) < 0.01] *= 0.55
    return _octet(fond)


def tex_platre(couleur, graine=3):
    return _octet(np.array(couleur) * (0.9 + 0.1 * bruit(5, 30, graine))[..., None])


def tex_bois(couleur=(92, 56, 34)):
    y, x = _grille()
    fibres = 0.75 + 0.25 * np.sin(2 * np.pi * (y * 24 + bruit(4, 20, 9) * 3)) ** 2
    return _octet(np.array(couleur) * fibres[..., None])


def tex_velours(couleur=(130, 20, 30)):
    return _octet(np.array(couleur) * (0.8 + 0.2 * bruit(16, 60, 13))[..., None])


def tex_dorure():
    y, x = _grille()
    motif = 0.75 + 0.25 * np.sin(2 * np.pi * 8 * x) * np.sin(2 * np.pi * 8 * y) + 0.15 * bruit(12, 40, 4)
    return _octet(_couleur(np.clip(motif, 0, 1), (110, 75, 25), (215, 170, 70), (255, 230, 150)))


def tex_caissons():
    """Plafond à caissons : cadres clairs, fond creux plus sombre, rosace dorée au centre."""
    y, x = _grille()
    u, v = (x * 3) % 1, (y * 3) % 1
    bord = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    fond = np.array((214, 204, 184)) * (0.93 + 0.07 * bruit(6, 30, 21))[..., None]
    fond[bord > 0.08] *= 0.78
    fond[(bord > 0.06) & (bord < 0.09)] = (235, 226, 205)
    rosace = np.hypot(u - 0.5, v - 0.5) < 0.12
    fond[rosace] = (200, 160, 70)
    return _octet(fond)


def tex_verriere():
    y, x = _grille()
    ciel = _couleur(y, (20, 30, 60), (45, 60, 100))
    ciel[((x * 4) % 1 < 0.04) | ((y * 4) % 1 < 0.04)] = (25, 25, 30)
    return _octet(ciel)


def tex_granit():
    hasard = np.random.default_rng(17)
    fond = np.array((176, 118, 110)) * (0.85 + 0.15 * bruit(10, 30, 17))[..., None]
    taches = hasard.random((N, N))
    fond[taches < 0.08] *= 0.45
    fond[taches > 0.95] = (225, 200, 190)
    return _octet(fond)


def tex_hieroglyphes():
    """Grès gravé de colonnes de hiéroglyphes (dessinés avec pygame)."""
    image = pygame.surfarray.make_surface(np.ascontiguousarray(tex_platre((200, 172, 128), 23).swapaxes(0, 1)))
    trait = (120, 88, 56)
    hasard = np.random.default_rng(3)
    for colonne in range(4):
        x0 = colonne * 64
        pygame.draw.line(image, trait, (x0 + 1, 0), (x0 + 1, N), 2)
        for ligne in range(6):
            cx, cy = x0 + 32, ligne * 42 + 22
            forme = hasard.integers(0, 6)
            if forme == 0:  # ankh
                pygame.draw.ellipse(image, trait, (cx - 7, cy - 16, 14, 14), 3)
                pygame.draw.line(image, trait, (cx, cy - 2), (cx, cy + 16), 3)
                pygame.draw.line(image, trait, (cx - 10, cy + 2), (cx + 10, cy + 2), 3)
            elif forme == 1:  # œil
                pygame.draw.ellipse(image, trait, (cx - 14, cy - 6, 28, 12), 3)
                pygame.draw.circle(image, trait, (cx, cy), 4)
                pygame.draw.line(image, trait, (cx - 4, cy + 6), (cx - 8, cy + 16), 3)
            elif forme == 2:  # eau
                pygame.draw.lines(image, trait, False, [(cx - 16 + 4 * k, cy + (4 if k % 2 else -4)) for k in range(9)], 3)
            elif forme == 3:  # oiseau
                pygame.draw.polygon(image, trait, [(cx - 12, cy + 12), (cx - 4, cy - 4), (cx + 4, cy - 12), (cx + 8, cy - 8),
                                                   (cx + 4, cy - 2), (cx + 12, cy + 12)], 3)
            elif forme == 4:  # soleil
                pygame.draw.circle(image, trait, (cx, cy), 10, 3)
                pygame.draw.circle(image, trait, (cx, cy), 2)
            else:  # roseau
                pygame.draw.line(image, trait, (cx, cy - 14), (cx, cy + 14), 3)
                pygame.draw.polygon(image, trait, [(cx, cy - 14), (cx + 9, cy - 4), (cx, cy)], 0)
    return pygame.surfarray.array3d(image).swapaxes(0, 1)


def tex_sortie():
    image = pygame.Surface((256, 128))
    image.fill((20, 150, 70))
    police = pygame.font.Font(None, 72)
    texte = police.render("SORTIE", True, (240, 255, 240))
    image.blit(texte, texte.get_rect(center=(150, 64)))
    pygame.draw.polygon(image, (240, 255, 240), [(20, 64), (50, 40), (50, 54), (72, 54), (72, 74), (50, 74), (50, 88)])
    return pygame.surfarray.array3d(image).swapaxes(0, 1)


PROCEDURALES = {
    "marbre": tex_marbre,
    "damier": tex_damier,
    "pierre": tex_pierre,
    "pierre_sombre": lambda: tex_pierre((150, 138, 118), 8),
    "dalles": tex_dalles,
    "mur_bleu": lambda: tex_platre((38, 52, 78)),
    "mur_beige": lambda: tex_platre((196, 182, 158)),
    "mur_rouge": lambda: tex_platre((120, 36, 34)),
    "plafond": lambda: tex_platre((226, 220, 206), 9),
    "bois": tex_bois,
    "velours": tex_velours,
    "dorure": tex_dorure,
    "caissons": tex_caissons,
    "verriere": tex_verriere,
    "granit": tex_granit,
    "hieroglyphes": tex_hieroglyphes,
    "sortie": tex_sortie,
}


def make_glow_texture(taille=64):
    """Halo lumineux en étoile (pour les joyaux, étincelles, lasers, flammes)."""
    if "halo" not in _TEXTURES:
        y, x = np.mgrid[-1:1:taille * 1j, -1:1:taille * 1j]
        rond = np.clip(1 - np.hypot(x, y), 0, 1) ** 2.2
        branches = np.clip(1 - np.abs(x) * 14, 0, 1) * np.clip(1 - np.abs(y), 0, 1) ** 2
        alpha = np.maximum(rond, 0.8 * np.maximum(branches, branches.T))
        rgba = np.dstack([np.full(alpha.shape, 255, np.uint8)] * 3 + [(alpha * 255).astype(np.uint8)])
        halo = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, halo)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, taille, taille, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba.tobytes())
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        _TEXTURES["halo"] = halo
    return _TEXTURES["halo"]


# ---------------------------------------------------------------------------
# Maillages
# ---------------------------------------------------------------------------


class Mesh:
    """Géométrie envoyée une fois à la carte graphique (VBO) : positions, normales, UV et couleurs."""

    def __init__(self, positions, normales, uvs, couleurs=None):
        self.count = len(positions)
        if couleurs is None:
            couleurs = np.ones((self.count, 3), np.float32)
        morceaux = [np.ascontiguousarray(a, dtype=np.float32) for a in (positions, normales, uvs, couleurs)]
        self.offsets, total = [], 0
        for m in morceaux:
            self.offsets.append(total)
            total += m.nbytes
        donnees = np.concatenate([m.ravel() for m in morceaux])
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, donnees.nbytes, donnees, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def draw(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        for etat in (GL_VERTEX_ARRAY, GL_NORMAL_ARRAY, GL_TEXTURE_COORD_ARRAY, GL_COLOR_ARRAY):
            glEnableClientState(etat)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glNormalPointer(GL_FLOAT, 0, ctypes.c_void_p(self.offsets[1]))
        glTexCoordPointer(2, GL_FLOAT, 0, ctypes.c_void_p(self.offsets[2]))
        glColorPointer(3, GL_FLOAT, 0, ctypes.c_void_p(self.offsets[3]))
        glDrawArrays(GL_TRIANGLES, 0, self.count)
        for etat in (GL_COLOR_ARRAY, GL_TEXTURE_COORD_ARRAY, GL_NORMAL_ARRAY, GL_VERTEX_ARRAY):
            glDisableClientState(etat)
        glBindBuffer(GL_ARRAY_BUFFER, 0)


# ---------------------------------------------------------------------------
# Caméra et éclairage
# ---------------------------------------------------------------------------


def camera(oeil, avant, fov, aspect, loin=400.0):
    """Place la caméra OpenGL (comme gluPerspective + gluLookAt, sans dépendre de GLU)."""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    pres = 0.05
    haut = pres * math.tan(math.radians(fov) / 2)
    glFrustum(-haut * aspect, haut * aspect, -haut, haut, pres, loin)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    droite = np.cross(avant, (0.0, 1.0, 0.0))
    droite /= np.linalg.norm(droite)
    vue = np.identity(4)
    vue[0, :3], vue[1, :3], vue[2, :3] = droite, np.cross(droite, avant), -avant
    glMultMatrixd(vue.T)  # OpenGL lit les matrices colonne par colonne
    glTranslated(*-np.asarray(oeil))


def eclairage(ambiante, torche=None, points=(), spots=()):
    """Allume les lumières de la scène (juste après camera(), pour que les positions soient dans le monde).

    torche : None, ou (couleur, portée) — la lampe torche du joueur, attachée à la caméra (GL_LIGHT0) ;
    points : jusqu'à 5 lumières ponctuelles [(position, couleur, portée)] (GL_LIGHT1 à 5) ;
    spots : jusqu'à 2 lampes de personnages [(position, direction, couleur, portée)] (GL_LIGHT6 et 7)."""
    glEnable(GL_LIGHTING)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (*ambiante, 1.0))
    glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)
    if torche:
        couleur, portee = torche
        glPushMatrix()
        glLoadIdentity()  # position donnée dans le repère de l'œil : la lampe suit le regard
        glLightfv(GL_LIGHT0, GL_POSITION, (0.15, -0.1, 0.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, (0.0, 0.0, -1.0))
        glPopMatrix()
        _regler(GL_LIGHT0, couleur, portee, angle=30.0, exposant=10.0)
        glEnable(GL_LIGHT0)
    else:
        glDisable(GL_LIGHT0)
    for k in range(5):
        lumiere = GL_LIGHT1 + k
        if k < len(points):
            position, couleur, portee = points[k]
            glLightfv(lumiere, GL_POSITION, (*position, 1.0))
            _regler(lumiere, couleur, portee)
            glEnable(lumiere)
        else:
            glDisable(lumiere)
    for k in range(2):
        lumiere = GL_LIGHT6 + k
        if k < len(spots):
            # ponctuelle, placée dans le faisceau : un vrai « spot » tourné vers la caméra rend toute la scène
            # noire avec le pilote OpenGL de macOS (le cône visible est dessiné à part, en effet lumineux)
            position, direction, couleur, portee = spots[k]
            glLightfv(lumiere, GL_POSITION, (*(np.asarray(position) + np.asarray(direction) * 2.0), 1.0))
            _regler(lumiere, couleur, portee * 0.5)
            glEnable(lumiere)
        else:
            glDisable(lumiere)


def _regler(lumiere, couleur, portee, angle=180.0, exposant=0.0):
    glLightfv(lumiere, GL_DIFFUSE, (*couleur, 1.0))
    glLightfv(lumiere, GL_SPECULAR, (*couleur, 1.0))
    glLightfv(lumiere, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
    glLightf(lumiere, GL_SPOT_CUTOFF, angle)
    glLightf(lumiere, GL_SPOT_EXPONENT, exposant)
    glLightf(lumiere, GL_CONSTANT_ATTENUATION, 1.0)
    glLightf(lumiere, GL_LINEAR_ATTENUATION, 0.0)
    glLightf(lumiere, GL_QUADRATIC_ATTENUATION, 4.0 / (portee * portee))  # 20 % de la lumière à `portee`


def brouillard(couleur, densite):
    """Brume légère : les lointains se fondent dans la couleur de fond (profondeur, ambiance)."""
    if densite <= 0:
        glDisable(GL_FOG)
        return
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_EXP2)
    glFogfv(GL_FOG_COLOR, (*couleur, 1.0))
    glFogf(GL_FOG_DENSITY, densite)


# ---------------------------------------------------------------------------
# Effets lumineux (dessinés en « addition » de lumière, sans écrire la profondeur)
# ---------------------------------------------------------------------------


def debut_additif():
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glDepthMask(GL_FALSE)


def fin_additif():
    glDepthMask(GL_TRUE)
    glDisable(GL_BLEND)
    glDisable(GL_TEXTURE_2D)


def halos(liste, droite, haut):
    """Petits soleils face à la caméra : liste de (position, taille, couleur 0-255, opacité)."""
    if not liste:
        return
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, make_glow_texture())
    glBegin(GL_QUADS)
    for pos, taille, couleur, alpha in liste:
        glColor4f(couleur[0] / 255, couleur[1] / 255, couleur[2] / 255, min(1.0, alpha))
        for (u, v), (a, b) in zip(((0, 0), (1, 0), (1, 1), (0, 1)), ((-1, -1), (1, -1), (1, 1), (-1, 1))):
            glTexCoord2f(u, v)
            glVertex3f(*(pos + (droite * a + haut * b) * taille))
    glEnd()
    glDisable(GL_TEXTURE_2D)


def faisceau(a, b, oeil, largeur, couleur, alpha):
    """Rayon lumineux entre a et b (un ruban toujours tourné vers la caméra), pour les lasers."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    cote = np.cross(b - a, oeil - (a + b) / 2)
    n = np.linalg.norm(cote)
    if n < 1e-9:
        return
    cote *= largeur / n
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, make_glow_texture())
    glColor4f(couleur[0] / 255, couleur[1] / 255, couleur[2] / 255, alpha)
    glBegin(GL_QUADS)
    for u, p in ((0.0, a - cote), (1.0, a + cote), (1.0, b + cote), (0.0, b - cote)):
        glTexCoord2f(u, 0.5)  # coupe au milieu du halo : brillant au centre, transparent sur les bords
        glVertex3f(*p)
    glEnd()
    glDisable(GL_TEXTURE_2D)


def cone_lumineux(sommet, direction, longueur, angle, couleur, alpha, cotes=20):
    """Cône de lumière d'une lampe (visible dans la pénombre), qui s'efface vers le bout."""
    direction = np.asarray(direction, float) / np.linalg.norm(direction)
    aide = np.array((0.0, 1.0, 0.0)) if abs(direction[1]) < 0.9 else np.array((1.0, 0.0, 0.0))
    u = np.cross(direction, aide)
    u /= np.linalg.norm(u)
    v = np.cross(direction, u)
    rayon = longueur * math.tan(math.radians(angle))
    base = np.asarray(sommet) + direction * longueur
    r, g, b = (c / 255 for c in couleur)
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(r, g, b, alpha)
    glVertex3f(*sommet)
    glColor4f(r, g, b, 0.0)
    for k in range(cotes + 1):
        a = 2 * math.pi * k / cotes
        glVertex3f(*(base + (u * math.cos(a) + v * math.sin(a)) * rayon))
    glEnd()


def draw_box(x0, y0, z0, x1, y1, z1, couleur):
    """Pavé plein ; chaque face a sa normale (pour l'éclairage) et sa nuance (relief sans éclairage)."""
    glBegin(GL_QUADS)
    for normale, nuance, coins in (
        ((0, 1, 0), 1.0, ((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0))),
        ((0, -1, 0), 0.4, ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))),
        ((1, 0, 0), 0.75, ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))),
        ((-1, 0, 0), 0.75, ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))),
        ((0, 0, 1), 0.6, ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))),
        ((0, 0, -1), 0.6, ((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))),
    ):
        glNormal3f(*normale)
        glColor3f(*(c * nuance for c in couleur))
        for coin in coins:
            glVertex3f(*coin)
    glEnd()


def build_sky(rayon=150.0, tranches=24, quartiers=48):
    """Sphère texturée pour le ciel, compilée une fois pour toutes (display list)."""
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

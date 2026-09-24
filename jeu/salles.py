"""Les salles du musée : géométrie, cartes de collision (murs, sol, obstacles), lumières et œuvres.

Chaque salle est d'abord construite « sur le papier » (tableaux NumPy, sans carte graphique : c'est ce que
teste `python main.py --test`), puis envoyée à la carte graphique au premier affichage (upload)."""

import math
from collections import deque

import numpy as np
import pygame
from OpenGL.GL import *

from . import rendu
from .base import CELL, RADIUS, STEP, TABLEAUX, chemin
from .modeles import SYMBOLES, modele

MATERIAUX_SALLE = {  # nom : (texture, unités par répétition (None = image étirée), reflet, émission)
    "parquet": ("fichier:src/textures/sol.png", 1.0, 0.12, None),
    "marbre": ("marbre", 2.5, 0.35, None),
    "damier": ("damier", 2.5, 0.3, None),
    "pierre": ("pierre", 3.0, 0.0, None),
    "pierre_sombre": ("pierre_sombre", 3.0, 0.0, None),
    "dalles": ("dalles", 2.5, 0.1, None),
    "mur_bleu": ("mur_bleu", 3.0, 0.0, None),
    "mur_beige": ("mur_beige", 3.0, 0.0, None),
    "mur_rouge": ("mur_rouge", 3.0, 0.0, None),
    "plafond": ("plafond", 3.0, 0.0, None),
    "caissons": ("caissons", 3.0, 0.0, None),
    "verriere": ("verriere", 4.0, 0.0, (0.22, 0.27, 0.4)),
    "hieroglyphes": ("hieroglyphes", 2.4, 0.0, None),
    "bois": ("bois", 1.5, 0.15, None),
    "dorure": ("dorure", 1.0, 0.7, None),
    "velours": ("velours", 1.0, 0.0, None),
    "sortie": ("sortie", None, 0.0, (0.3, 0.95, 0.5)),
    "scan": ("fichier:src/textures/texture.png", None, 0.0, None),
}


class Salle:
    """Une salle prête à jouer : géométrie par matériau, objets, lumières, cartes de collision."""

    def __init__(self, nom, x0, z0, x1, z1):
        self.nom = nom
        self.x0, self.z0 = x0, z0
        self.nz, self.nx = int(math.ceil((z1 - z0) / CELL)), int(math.ceil((x1 - x0) / CELL))
        self.bloque = np.ones((self.nz, self.nx), bool)  # tout est plein tant qu'on n'a pas posé de sol
        self.opaque = np.full((self.nz, self.nx), 99.0)  # hauteur des obstacles qui cachent la vue
        self.sol = np.zeros((self.nz, self.nx), np.float32)
        self.seaux = {}  # matériau -> [positions, normales, uv, couleurs]
        self.objets = []  # (modèle, position, lacet, échelle)
        self.lumieres = []  # (position, couleur, portée)
        self.oeuvres = []  # (centre, normale, largeur, hauteur, titre, artiste, date)
        self.cartels = []  # (position, titre, texte) : statues et objets remarquables
        self.vitres = []  # (4 coins, couleur rgba) : vitres transparentes
        self.depart = (0.0, 0.0, 0.0, -90.0)  # x, y, z, lacet
        self.ambiante_nuit = (0.08, 0.08, 0.11)
        self.ambiante_visite = (0.5, 0.48, 0.45)
        self.brume = 0.0
        self.fond = (0.0, 0.0, 0.0)
        self.ciel = False
        self.meshes = None
        # Figurants de la visite libre : nombre de visiteurs, points de vue en plus des tableaux (x, z, point regardé),
        # chaise du gardien (x, z, lacet), guide et son groupe (x, z, lacet, point regardé), attroupement (cible, positions)
        self.visiteurs, self.points_vue, self.chaise, self.groupe, self.attroupement = 8, [], None, None, None
        self.sol_son = "pierre"  # bruit des pas : "parquet", "marbre" ou "pierre"

    # --- Cartes de collision ---

    def reset(self):
        """Retour aux cartes d'origine (une mission a pu poser des caisses ou renverser des chariots)."""
        self.bloque, self.opaque, self.sol = (g.copy() for g in self.grilles0)

    def cellule(self, x, z):
        return int((z - self.z0) // CELL), int((x - self.x0) // CELL)

    def centres(self):
        """Coordonnées (X, Z) des centres de toutes les cases."""
        return np.meshgrid(self.x0 + (np.arange(self.nx) + 0.5) * CELL, self.z0 + (np.arange(self.nz) + 0.5) * CELL)

    def bloquer_si(self, masque, hauteur=99.0):
        """Rend infranchissables les cases du masque ; `hauteur` : jusqu'où elles cachent la vue."""
        self.bloque |= masque
        self.opaque[masque] = np.maximum(self.opaque[masque], hauteur) if hauteur < 99 else 99.0

    def bloquer_rect(self, x0, z0, x1, z1, hauteur=99.0):
        X, Z = self.centres()
        m = (X > min(x0, x1) - RADIUS * 0.3) & (X < max(x0, x1) + RADIUS * 0.3) & \
            (Z > min(z0, z1) - RADIUS * 0.3) & (Z < max(z0, z1) + RADIUS * 0.3)
        self.bloquer_si(m, hauteur)

    def bloquer_disque(self, x, z, r, hauteur=99.0):
        X, Z = self.centres()
        self.bloquer_si(np.hypot(X - x, Z - z) < r, hauteur)

    def _dans(self, i, j):
        return 0 <= i < self.nz and 0 <= j < self.nx

    def libre(self, x, z, pied):
        """Le joueur (carré de côté 2 × RADIUS) peut-il se tenir en (x, z) avec les pieds à la hauteur `pied` ?"""
        for px, pz in ((x - RADIUS, z - RADIUS), (x + RADIUS, z - RADIUS), (x - RADIUS, z + RADIUS), (x + RADIUS, z + RADIUS)):
            i, j = self.cellule(px, pz)
            if not self._dans(i, j) or self.bloque[i, j] or self.sol[i, j] > pied + STEP:
                return False
        return True

    def sol_sous(self, x, z):
        """Hauteur du sol sous le joueur (la plus haute des cases touchées)."""
        hauteur = -99.0
        for px, pz in ((x - RADIUS, z - RADIUS), (x + RADIUS, z - RADIUS), (x - RADIUS, z + RADIUS), (x + RADIUS, z + RADIUS), (x, z)):
            i, j = self.cellule(px, pz)
            if self._dans(i, j) and not self.bloque[i, j]:
                hauteur = max(hauteur, float(self.sol[i, j]))
        return 0.0 if hauteur == -99.0 else hauteur

    def vue_libre(self, a, b, marge=0.0):
        """Rien d'opaque entre les points a et b ? (murs, statues, caisses assez hautes pour cacher).
        `marge` : on ignore les derniers centimètres avant b (un objet posé contre un mur reste visible)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        longueur = float(np.hypot(b[0] - a[0], b[2] - a[2]))
        n = max(2, int(longueur / (CELL * 0.5)))
        for t in np.linspace(0, 1, n)[1:-1]:
            if longueur * (1 - t) < marge:
                break
            p = a + (b - a) * t
            i, j = self.cellule(p[0], p[2])
            if not self._dans(i, j) or p[1] < self.opaque[i, j]:
                return False
        return True

    # --- Construction de la géométrie ---

    def quad(self, a, b, d, mat, pas=0.5, uv=None, ombre=True):
        """Parallélogramme de coin a, de côtés a->b et a->d (normale = (b-a) × (d-a)), découpé en petits
        carreaux (l'éclairage OpenGL est calculé aux sommets : une grande face resterait uniforme)."""
        a, b, d = (np.asarray(p, float) for p in (a, b, d))
        u, v = b - a, d - a
        nu = max(1, int(math.ceil(np.linalg.norm(u) / pas)))
        nv = max(1, int(math.ceil(np.linalg.norm(v) / pas)))
        i = np.linspace(0, 1, nu + 1)[:, None, None]
        j = np.linspace(0, 1, nv + 1)[None, :, None]
        P = a + u * i + v * j
        n = np.cross(u, v)
        n /= np.linalg.norm(n)
        echelle = MATERIAUX_SALLE.get(mat, (None, None))[1] if not mat.startswith("tableau:") else None
        if uv is not None:  # plage de coordonnées imposée (s0, s1, t0, t1)
            s0, s1, t0, t1 = uv
            UV = np.concatenate([np.broadcast_to(s0 + (s1 - s0) * i, P.shape[:2] + (1,)),
                                 np.broadcast_to(t0 + (t1 - t0) * j, P.shape[:2] + (1,))], -1)
        elif echelle is None:  # image étirée (tableaux, panneaux)
            UV = np.concatenate([np.broadcast_to(i, P.shape[:2] + (1,)), np.broadcast_to(j, P.shape[:2] + (1,))], -1)
        elif abs(n[1]) > 0.7:
            UV = P[..., [0, 2]] / echelle
        elif abs(n[0]) > abs(n[2]):
            UV = P[..., [2, 1]] / echelle
        else:
            UV = P[..., [0, 1]] / echelle
        couleur = np.ones(P.shape[:2] + (1,))
        if ombre and abs(n[1]) < 0.5:  # pied des murs un peu plus sombre (occlusion ambiante)
            ii = np.clip(((P[..., 2] - self.z0) // CELL).astype(int), 0, self.nz - 1)
            jj = np.clip(((P[..., 0] - self.x0) // CELL).astype(int), 0, self.nx - 1)
            hauteur = P[..., 1] - self.sol[ii, jj]
            couleur = (0.6 + 0.4 * np.clip(hauteur / 1.6, 0, 1) ** 0.7)[..., None]
        seau = self.seaux.setdefault(mat, [[], [], [], []])
        for champ, source in ((0, P), (2, UV), (3, np.broadcast_to(couleur, P.shape[:2] + (1,)))):
            triangles = [np.stack([source[:-1, :-1], source[1:, :-1], source[1:, 1:]], -2),
                         np.stack([source[:-1, :-1], source[1:, 1:], source[:-1, 1:]], -2)]
            morceau = np.concatenate([t.reshape(-1, t.shape[-1]) for t in triangles])
            seau[champ].append(np.repeat(morceau, 3, axis=1) if champ == 3 else morceau)
        seau[1].append(np.tile(n, (len(seau[0][-1]), 1)))

    def boite(self, x0, y0, z0, x1, y1, z1, mat, bloquer=True, dessous=False, pas=0.5):
        """Pavé vu de l'extérieur (socles, masses de maçonnerie, cimaise...)."""
        faces = [((x0, y1, z1), (x1, y1, z1), (x0, y1, z0)), ((x0, y0, z1), (x1, y0, z1), (x0, y1, z1)),
                 ((x1, y0, z0), (x0, y0, z0), (x1, y1, z0)), ((x1, y0, z1), (x1, y0, z0), (x1, y1, z1)),
                 ((x0, y0, z0), (x0, y0, z1), (x0, y1, z0))]
        if dessous:
            faces.append(((x0, y0, z0), (x1, y0, z0), (x0, y0, z1)))
        for a, b, d in faces:
            self.quad(a, b, d, mat, pas)
        if bloquer:
            self.bloquer_rect(x0, z0, x1, z1, y1)

    def plancher(self, x0, z0, x1, z1, y, mat, pas=0.5):
        """Sol praticable (normale vers le haut) : les cases deviennent libres, à la hauteur y."""
        self.quad((x0, y, z1), (x1, y, z1), (x0, y, z0), mat, pas)
        X, Z = self.centres()
        m = (X > x0) & (X < x1) & (Z > z0) & (Z < z1)
        self.bloque[m] = False
        self.opaque[m] = y
        self.sol[m] = y

    def plafond(self, x0, z0, x1, z1, y, mat, pas=1.0):
        self.quad((x0, y, z0), (x1, y, z0), (x0, y, z1), mat, pas)

    def mur(self, a, b, y0, y1, mat, interieur, portes=(), pas=0.5, epaisseur=0.25):
        """Paroi verticale de a à b (points (x, z)), face tournée vers le point `interieur`.
        portes : [(début, fin, hauteur)] le long du mur, en unités depuis a (portes fermées, infranchissables)."""
        a, b = np.array(a, float), np.array(b, float)
        u = b - a
        normale = np.array((-u[1], u[0]))
        if normale @ (np.asarray(interieur, float) - a) < 0:
            a, b = b, a
            u = -u
            portes = [(np.linalg.norm(u) - f, np.linalg.norm(u) - d, h) for d, f, h in portes]
        longueur = np.linalg.norm(u)
        direction = u / longueur
        coupes = sorted(portes)
        debut = 0.0
        for d, f, h in coupes + [(longueur, longueur, 0)]:
            if d > debut:
                p, q = a + direction * debut, a + direction * d
                self.quad((p[0], y0, p[1]), (q[0], y0, q[1]), (p[0], y1, p[1]), mat, pas)
            if f > d:
                p, q = a + direction * d, a + direction * f
                if y0 + h < y1:
                    self.quad((p[0], y0 + h, p[1]), (q[0], y0 + h, q[1]), (p[0], y1, p[1]), mat, pas)  # linteau
                self.porte(p, q, y0, y0 + h, np.array((-direction[1], direction[0])))
            debut = f
        # collision : une bande de cases le long du mur
        X, Z = self.centres()
        t = (X - a[0]) * direction[0] + (Z - a[1]) * direction[1]
        ecart = np.abs((X - a[0]) * direction[1] - (Z - a[1]) * direction[0])
        self.bloquer_si((t > -epaisseur) & (t < longueur + epaisseur) & (ecart < epaisseur))

    def porte(self, p, q, y0, y1, normale):
        """Porte fermée en retrait dans une ouverture (deux vantaux en bois, encadrement doré)."""
        retrait = -normale * 0.2
        p3, q3 = np.array((p[0], 0, p[1])) + np.array((retrait[0], 0, retrait[1])), np.array((q[0], 0, q[1])) + np.array((retrait[0], 0, retrait[1]))
        self.quad((p3[0], y0, p3[2]), (q3[0], y0, q3[2]), (p3[0], y1, p3[2]), "bois", 0.5)
        milieu = (p3 + q3) / 2 + np.array((normale[0], 0, normale[1])) * 0.01
        sens = (q3 - p3) / np.linalg.norm(q3 - p3)
        self.quad(milieu - sens * 0.04 + (0, y0, 0), milieu + sens * 0.04 + (0, y0, 0), milieu - sens * 0.04 + (0, y1, 0),
                  "dorure", 0.5, ombre=False)  # filet doré entre les deux vantaux
        for bord in (p, q):  # tableaux de la porte (épaisseur du mur)
            b0 = np.array((bord[0], bord[1]))
            self.quad((b0[0], y0, b0[1]), (b0[0] + retrait[0], y0, b0[1] + retrait[1]), (b0[0], y1, b0[1]), "dorure", 0.5, ombre=False)
            self.quad((b0[0] + retrait[0], y0, b0[1] + retrait[1]), (b0[0], y0, b0[1]), (b0[0] + retrait[0], y1, b0[1] + retrait[1]),
                      "dorure", 0.5, ombre=False)

    def eventail(self, centre, points, mat, normale):
        """Surface plane en éventail (triangles depuis `centre`), tournée vers `normale`."""
        c, n = np.asarray(centre, float), np.asarray(normale, float)
        echelle = MATERIAUX_SALLE[mat][1] or 1.0
        axes = [0, 2] if abs(n[1]) > 0.7 else [2, 1] if abs(n[0]) > abs(n[2]) else [0, 1]
        seau = self.seaux.setdefault(mat, [[], [], [], []])
        for p, q in zip(points, points[1:]):
            tri = np.array([c, p, q], float)
            if np.cross(tri[1] - tri[0], tri[2] - tri[0]) @ n < 0:
                tri = tri[[0, 2, 1]]
            seau[0].append(tri)
            seau[1].append(np.tile(n, (3, 1)))
            seau[2].append(tri[:, axes] / echelle)
            seau[3].append(np.ones((3, 3)))

    def voute(self, x0, x1, z0, z1, y, fleche, mat, segments=18, pas=1.0, fermer=False):
        """Voûte en berceau le long de z, entre les murs x0 et x1, qui démarre à la hauteur y
        (fermer : on bouche les deux demi-cercles du bout par des tympans)."""
        xc, demi = (x0 + x1) / 2, (x1 - x0) / 2
        arc = [(xc - demi * math.cos(t), y + fleche * math.sin(t)) for t in np.linspace(0, math.pi, segments + 1)]
        longueurs = np.concatenate([[0], np.cumsum([math.dist(arc[k], arc[k + 1]) for k in range(segments)])])
        echelle = MATERIAUX_SALLE[mat][1]
        for k in range(segments):
            (xa, ya), (xb, yb) = arc[k], arc[k + 1]
            self.quad((xa, ya, z0), (xb, yb, z0), (xa, ya, z1), mat, pas,
                      uv=(longueurs[k] / echelle, longueurs[k + 1] / echelle, z0 / echelle, z1 / echelle))
        if fermer:
            for z, n in ((z0, (0, 0, 1)), (z1, (0, 0, -1))):
                self.eventail((xc, y, z), [(xa, ya, z) for xa, ya in arc], mat, n)

    def colonne(self, x, z, r, y0, y1, mat="marbre", cotes=16):
        """Colonne cannelée avec base et chapiteau carrés."""
        for k in range(cotes):
            a0, a1 = 2 * math.pi * k / cotes, 2 * math.pi * (k + 1) / cotes
            p0 = (x + r * math.cos(a0), z + r * math.sin(a0))
            p1 = (x + r * math.cos(a1), z + r * math.sin(a1))
            self.quad((p1[0], y0 + 0.3, p1[1]), (p0[0], y0 + 0.3, p0[1]), (p1[0], y1 - 0.4, p1[1]), mat, 1.0)
        self.boite(x - r * 1.3, y0, z - r * 1.3, x + r * 1.3, y0 + 0.3, z + r * 1.3, mat, bloquer=False)
        self.boite(x - r * 1.35, y1 - 0.4, z - r * 1.35, x + r * 1.35, y1, z + r * 1.35, mat, bloquer=False, dessous=True)
        self.bloquer_disque(x, z, r * 1.3)

    def marches(self, x0, x1, z_bas, z_haut, y_bas, y_haut, n, mat):
        """Escalier droit qui monte de z_bas vers z_haut (le sol des cases suit les marches)."""
        sens = 1 if z_haut > z_bas else -1
        profondeur, hauteur = (z_haut - z_bas) / n, (y_haut - y_bas) / n
        for k in range(n):
            za, zb, y = z_bas + k * profondeur, z_bas + (k + 1) * profondeur, y_bas + (k + 1) * hauteur
            self.quad((x0, y, max(za, zb)), (x1, y, max(za, zb)), (x0, y, min(za, zb)), mat, 0.5)
            if sens < 0:  # contremarche tournée vers le bas de l'escalier
                self.quad((x0, y - hauteur, za), (x1, y - hauteur, za), (x0, y, za), mat, 0.5)
            else:
                self.quad((x1, y - hauteur, za), (x0, y - hauteur, za), (x1, y, za), mat, 0.5)
        X, Z = self.centres()
        t = (Z - z_bas) / (z_haut - z_bas)
        m = (X > x0) & (X < x1) & (t >= 0) & (t < 1)
        self.bloque[m] = False
        self.sol[m] = y_bas + (np.floor(t[m] * n) + 1) * hauteur
        self.opaque[m] = self.sol[m]

    def tableau(self, nom, centre, normale, hauteur, cadre=0.12):
        """Accroche une œuvre de src/tableaux (largeur déduite des proportions de l'image)."""
        largeur_px, hauteur_px = pygame.image.load(chemin("src", "tableaux", nom + ".jpg")).get_size()
        largeur = hauteur * largeur_px / hauteur_px
        n = np.asarray(normale, float)
        droite = np.cross((0.0, 1.0, 0.0), n)
        c = np.asarray(centre, float) + n * 0.06
        bas_gauche = c - droite * largeur / 2 - np.array((0, hauteur / 2, 0))
        self.quad(bas_gauche, bas_gauche + droite * largeur, bas_gauche + np.array((0, hauteur, 0)), "tableau:" + nom,
                  pas=0.4, ombre=False)
        for (x0, y0), (x1, y1) in (((-largeur / 2 - cadre, -hauteur / 2 - cadre), (largeur / 2 + cadre, -hauteur / 2)),
                                   ((-largeur / 2 - cadre, hauteur / 2), (largeur / 2 + cadre, hauteur / 2 + cadre)),
                                   ((-largeur / 2 - cadre, -hauteur / 2), (-largeur / 2, hauteur / 2)),
                                   ((largeur / 2, -hauteur / 2), (largeur / 2 + cadre, hauteur / 2))):
            coins = [np.asarray(centre, float) + droite * x + np.array((0, y, 0)) for x in (x0, x1) for y in (y0, y1)]
            lo = np.min([np.minimum(p, p + n * 0.1) for p in coins], axis=0)
            hi = np.max([np.maximum(p, p + n * 0.1) for p in coins], axis=0)
            self.boite(*lo, *hi, "dorure", bloquer=False, pas=0.5)
        titre, artiste, date = TABLEAUX[nom]
        self.oeuvres.append((c, n, largeur, hauteur, titre, artiste, date))

    def panneau(self, centre, normale, largeur, hauteur, mat):
        n = np.asarray(normale, float)
        droite = np.cross((0.0, 1.0, 0.0), n)
        bas_gauche = np.asarray(centre, float) + n * 0.03 - droite * largeur / 2 - np.array((0, hauteur / 2, 0))
        self.quad(bas_gauche, bas_gauche + droite * largeur, bas_gauche + np.array((0, hauteur, 0)), mat, 1.0, ombre=False)

    def objet(self, nom, position, lacet=0.0, echelle=1.0, rayon=None, rect=None, hauteur=99.0):
        """Pose un modèle ; rayon ou rect (demi-largeurs x, z) : zone infranchissable autour."""
        x, y, z = position
        self.objets.append((modele(nom), np.array(position, float), lacet, echelle))
        if rayon:
            self.bloquer_disque(x, z, rayon, hauteur)
        if rect:
            self.bloquer_rect(x - rect[0], z - rect[1], x + rect[0], z + rect[1], hauteur)

    def lumiere(self, position, couleur=(1.0, 0.86, 0.66), portee=9.0):
        self.lumieres.append((np.array(position, float), couleur, portee))

    # --- Affichage ---

    def upload(self):
        self.meshes = []
        for mat, (P, N, UV, C) in self.seaux.items():
            if P:
                self.meshes.append((mat, rendu.Mesh(np.concatenate(P), np.concatenate(N), np.concatenate(UV), np.concatenate(C))))

    def lumieres_proches(self, point, n=5):
        return sorted(self.lumieres, key=lambda l: float(np.sum((l[0] - point) ** 2)))[:n]

    def draw(self):
        if self.meshes is None:
            self.upload()
        glEnable(GL_TEXTURE_2D)
        glColor3f(1, 1, 1)
        for mat, mesh in self.meshes:
            nom_texture, _, reflet, emission = MATERIAUX_SALLE.get(mat, (mat, None, 0.05, None))
            glBindTexture(GL_TEXTURE_2D, rendu.texture(nom_texture))
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (reflet * 0.4,) * 3 + (1.0,))
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 30.0)
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (*(emission or (0, 0, 0)), 1.0))
            mesh.draw()
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
        glDisable(GL_TEXTURE_2D)
        for m, position, lacet, echelle in self.objets:
            dessiner_modele(m, position, lacet, echelle)

    def draw_transparent(self):
        if not self.vitres:
            return
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        glDisable(GL_LIGHTING)
        glBegin(GL_QUADS)
        for coins, couleur in self.vitres:
            glColor4f(*couleur)
            for p in coins:
                glVertex3f(*p)
        glEnd()
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)


def dessiner_modele(m, position, lacet=0.0, echelle=1.0, partie="corps"):
    """Dessine un modèle tourné de `lacet` degrés (0 : le modèle regarde vers +z)."""
    glPushMatrix()
    glTranslatef(*position)
    glRotatef(lacet, 0, 1, 0)
    if echelle != 1.0:
        glScalef(echelle, echelle, echelle)
    m.draw(partie)
    glPopMatrix()


def vitre_boite(salle, x0, y0, z0, x1, y1, z1, couleur=(0.7, 0.85, 1.0, 0.13)):
    """Cloche de verre (5 faces transparentes)."""
    for coins in (((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)), ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
                  ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)), ((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)),
                  ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))):
        salle.vitres.append((coins, couleur))


# ---------------------------------------------------------------------------
# La galerie d'Apollon (scan 3D)
# ---------------------------------------------------------------------------

VITRINES_APOLLON = [(0.2, 10.0, False), (0.2, 0.0, True), (0.2, -10.0, False)]  # (x, z, brisée ?)
VITRINE_SIZE = (0.45, 0.85, 0.85)  # demi-largeur, demi-longueur, hauteur du socle


def load_model(fichier_obj):
    """Lit un fichier .obj et renvoie trois tableaux (positions, UV, normales) avec un sommet
    par coin de triangle. Gère les polygones, les indices négatifs et les UV/normales absents."""
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
    indices = np.array([(c.replace("//", "/0/") + "/0/0").split("/")[:3] for c in coins], dtype=np.int64)
    tableaux = []
    for colonne, valeurs in enumerate((v, vt, vn)):
        tableau = np.array(valeurs, dtype=np.float32)
        negatifs = indices[:, colonne] < 0  # indice -1 = dernier élément lu
        indices[negatifs, colonne] += len(tableau)
        tableaux.append(tableau[indices[:, colonne]])
    return tableaux


def dilate(carte, rayon):
    resultat = carte.copy()
    for di in range(-rayon, rayon + 1):
        for dj in range(-rayon, rayon + 1):
            resultat |= np.roll(carte, (di, dj), axis=(0, 1))
    return resultat


class SalleApollon(Salle):
    """Le scan est dessiné à part : sa texture porte déjà la lumière, et ses normales ne sont pas fiables."""

    def upload(self):
        super().upload()
        positions, normales, uvs = self.scan
        self.mesh_scan = rendu.Mesh(positions, normales, uvs)
        self.sky_list = rendu.build_sky()

    def draw(self):
        if self.meshes is None:
            self.upload()
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, rendu.texture("fichier:src/textures/texture.png"))
        self.mesh_scan.draw()
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)
        super().draw()
        if getattr(self, "eclats", None):
            glColor3f(0.8, 0.88, 1.0)
            glBegin(GL_TRIANGLES)
            glNormal3f(0, 1, 0)
            for eclat in self.eclats:
                for p in eclat:
                    glVertex3f(*p)
            glEnd()


def construire_apollon():
    """Le scan est décalé de 1,5 vers le haut : son sol est en y = 0, comme toutes les salles."""
    s = SalleApollon("apollon", -3.75, -22.6, 5.25, 20.3)
    positions, uvs, normales = load_model(chemin("src", "models", "untitled.obj"))
    positions = positions + np.array((0, 1.5, 0), np.float32)
    s.scan = (positions, normales, uvs)
    # Carte des collisions : une case est un obstacle si le scan a de la matière à hauteur du corps
    tri = positions.reshape(-1, 3, 3)
    points = np.concatenate([positions, tri.mean(axis=1), (tri[:, 0] + tri[:, 1]) / 2,
                             (tri[:, 1] + tri[:, 2]) / 2, (tri[:, 2] + tri[:, 0]) / 2])
    corps = points[(points[:, 1] > 0.3) & (points[:, 1] < 1.9)]
    i = np.floor((corps[:, 2] - s.z0) / CELL).astype(int)
    j = np.floor((corps[:, 0] - s.x0) / CELL).astype(int)
    dedans = (i >= 0) & (i < s.nz) & (j >= 0) & (j < s.nx)
    compte = np.zeros((s.nz, s.nx), dtype=np.int32)
    np.add.at(compte, (i[dedans], j[dedans]), 1)
    grille = compte > 3  # quelques points isolés ne font pas un mur
    grille[[0, -1], :] = True
    grille[:, [0, -1]] = True
    hx, hz, h = VITRINE_SIZE
    X, Z = s.centres()
    for x, z, _ in VITRINES_APOLLON:
        grille |= (np.abs(X - x) < hx + 0.1) & (np.abs(Z - z) < hz + 0.1)
    # parcours en largeur depuis le départ : ce qui est inaccessible devient un mur (bouche les trous du scan)
    tient = ~dilate(grille, 1)
    depart = s.cellule(0.2, 18.2)
    atteint = np.zeros_like(grille)
    atteint[depart] = True
    file = deque([depart])
    while file:
        a, b = file.popleft()
        for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
            if tient[c, d] and not atteint[c, d]:
                atteint[c, d] = True
                file.append((c, d))
    s.atteint = atteint
    s.bloque = ~dilate(atteint, 1)
    s.opaque = np.where(s.bloque, 99.0, 0.0)
    for x, z, _ in VITRINES_APOLLON:
        s.opaque[(np.abs(X - x) < hx + 0.1) & (np.abs(Z - z) < hz + 0.1)] = h + 0.5
    # Parquet (le scan n'a pas de sol) et vitrines
    s.quad((-4.0, -0.02, 22.0), (6.0, -0.02, 22.0), (-4.0, -0.02, -24.0), "parquet", 0.25)
    s.quad((-200.0, -0.05, 200.0), (200.0, -0.05, 200.0), (-200.0, -0.05, -200.0), "parquet", 50.0)  # autour du musée
    for x, z, brisee in VITRINES_APOLLON:
        s.boite(x - hx, 0.0, z - hz, x + hx, h - 0.04, z + hz, "bois", bloquer=False, pas=0.3)
        s.boite(x - hx - 0.02, h - 0.04, z - hz - 0.02, x + hx + 0.02, h, z + hz + 0.02, "dorure", bloquer=False, pas=0.3)
        s.boite(x - hx + 0.04, h, z - hz + 0.04, x + hx - 0.04, h + 0.02, z + hz - 0.04, "velours", bloquer=False, pas=0.3)
        if brisee:
            for coins in (((x - hx, h, z - hz), (x + hx, h, z - hz), (x + hx, h + 0.5, z - hz), (x - hx, h + 0.5, z - hz)),
                          ((x - hx, h, z + hz), (x + hx, h, z + hz), (x + hx, h + 0.5, z + hz), (x - hx, h + 0.5, z + hz))):
                s.vitres.append((coins, (0.7, 0.85, 1.0, 0.13)))
            hasard = np.random.default_rng(7)
            eclats = []
            while len(eclats) < 40:
                cx, cz = x + hasard.uniform(-1.2, 1.2), z + hasard.uniform(-1.5, 1.5)
                if abs(cx - x) > hx or abs(cz - z) > hz:
                    eclats.append([(cx + hasard.uniform(-0.08, 0.08), 0.01, cz + hasard.uniform(-0.08, 0.08)) for _ in range(3)])
            s.eclats = eclats
        else:
            vitre_boite(s, x - hx, h, z - hz, x + hx, h + 0.5, z + hz)
    s.vitrines = VITRINES_APOLLON
    s.depart = (0.2, 0.0, 18.2, -90.0)
    s.ambiante_nuit = (0.07, 0.07, 0.1)
    s.ambiante_visite = (0.9, 0.9, 0.9)  # le scan a déjà son éclairage
    s.ciel = True
    s.lumieres = [(np.array((0.2, 3.5, z)), (1.0, 0.9, 0.75), 10.0) for z in (15, 5, -5, -15)]
    s.sol_son, s.visiteurs, s.chaise = "parquet", 7, (-2.1, 18.45, -45.0)
    for x, z, _ in VITRINES_APOLLON:
        for dx in (-1.25, 1.25):
            for dz in (-0.5, 0.5):
                s.points_vue.append((x + dx, z + dz, (x, 0.9, z)))
        for dx in (-2.6, 2.9):  # les murs peints et les dorures
            s.points_vue.append((x + dx * 0.8, z + 4.5, (x + dx * 1.4, 2.6, z + 4.5)))
    return s


# ---------------------------------------------------------------------------
# Salle des États : la Joconde et les Noces de Cana
# ---------------------------------------------------------------------------


def construire_etats():
    s = Salle("etats", -8.5, -18.5, 8.5, 18.5)
    s.plancher(-8, -18, 8, 18, 0.0, "parquet")
    centre = (0, 0)
    s.mur((-8, -18), (-8, 18), 0, 7.5, "mur_bleu", centre, portes=[(31.5, 34.5, 4.2)])
    s.mur((8, -18), (8, 18), 0, 7.5, "mur_bleu", centre, portes=[(1.5, 4.5, 4.2)])
    s.mur((-8, 18), (8, 18), 0, 7.5, "mur_bleu", centre)
    s.mur((-8, -18), (8, -18), 0, 7.5, "mur_bleu", centre, portes=[(6.5, 9.5, 4.5)])
    for a, b in (((-8, -18), (-8, 18)), ((8, -18), (8, 18)), ((-8, 18), (8, 18)), ((-8, -18), (8, -18))):
        s.mur(a, b, 7.5, 9.5, "plafond", centre)
    for x0, z0, x1, z1 in ((-8, -18, -7.82, 18), (7.82, -18, 8, 18), (-8, 17.82, 8, 18), (-8, -18, 8, -17.82)):
        s.boite(x0, 7.4, z0, x1, 7.62, z1, "dorure", bloquer=False, dessous=True)  # corniche dorée
    # Plafond avec une grande verrière (la nuit, un ciel bleu sombre)
    s.plafond(-8, -18, 8, -14, 9.5, "plafond")
    s.plafond(-8, 14, 8, 18, 9.5, "plafond")
    s.plafond(-8, -14, -5, 14, 9.5, "plafond")
    s.plafond(5, -14, 8, 14, 9.5, "plafond")
    for a, b in (((-5, -14), (5, -14)), ((-5, 14), (5, 14)), ((-5, -14), (-5, 14)), ((5, -14), (5, 14))):
        s.mur(a, b, 9.5, 10.6, "plafond", (0, 0), epaisseur=0.0)
    s.plafond(-5, -14, 5, 14, 10.6, "verriere", pas=2.0)
    # La Joconde sur sa cimaise, derrière sa vitre blindée et sa barrière
    s.boite(-3.5, 0.0, -13.3, 3.5, 5.5, -12.7, "mur_bleu")
    s.tableau("joconde", (0, 1.75, -12.7), (0, 0, 1), 1.1, cadre=0.1)
    s.objet("vitrine_joconde", (0, 0, -12.72))
    s.vitres.append((((-0.75, 0.63, -12.28), (0.75, 0.63, -12.28), (0.75, 2.9, -12.28), (-0.75, 2.9, -12.28)), (0.75, 0.88, 1.0, 0.1)))
    s.objet("barriere", (0, 0, -12.7))
    X, Z = s.centres()
    s.bloquer_si((np.hypot(X, Z + 12.7) < 2.75) & (Z > -12.7), 1.0)
    # Les Noces de Cana en face, et les Vénitiens sur les côtés
    s.tableau("noces_de_cana", (0, 4.1, 18), (0, 0, -1), 5.9)
    s.tableau("concert_champetre", (-8, 2.4, 6), (1, 0, 0), 2.1)
    s.tableau("femme_au_miroir", (-8, 2.4, -4), (1, 0, 0), 1.9)
    s.tableau("homme_au_gant", (8, 2.4, 6), (-1, 0, 0), 1.9)
    s.tableau("belle_nani", (8, 2.4, -4), (-1, 0, 0), 2.0)
    for z in (1.5, 7.5):
        s.objet("banc", (0, 0, z), 0, rect=(1.15, 0.35), hauteur=0.5)
    for x in (-4.2, 4.2):
        s.objet("banc", (x, 0, -6.5), 90, rect=(0.35, 1.15), hauteur=0.5)
    for position in ((-5, 5.5, 11), (5, 5.5, 11), (-5, 5.5, 0), (5, 5.5, 0), (0, 5.0, -8.5), (0, 6.0, 15)):
        s.lumiere(position, portee=10.0)
    s.depart = (0.0, 0.0, 11.0, -90.0)
    s.sol_son, s.visiteurs, s.chaise = "parquet", 6, (7.3, 12.5, 180.0)
    s.points_vue = [(x, z, (x * 1.2, 4.1, 18)) for x in (-4.5, -1.5, 1.5, 4.5) for z in (11.5, 13.5)]  # les Noces de Cana
    s.points_vue += [(x * 0.55, z, (x, 2.4, z)) for x in (-8, 8) for z in (-4, 6)]
    s.attroupement = ((0.0, 1.75, -12.7), [(r * math.cos(math.radians(a)), -12.7 + r * math.sin(math.radians(a)))
                                           for r, angles in ((3.2, (35, 62, 90, 118, 145)), (4.3, (52, 78, 104, 128)))
                                           for a in angles])
    s.ambiante_nuit = (0.09, 0.1, 0.16)
    s.ambiante_visite = (0.42, 0.42, 0.46)
    s.cartels.append((np.array((0, 1.75, -12.3)), "La Joconde", "Léonard de Vinci, vers 1503-1519. Le portrait le plus "
                      "célèbre du monde, protégé par une vitre blindée."))
    return s


# ---------------------------------------------------------------------------
# La Grande Galerie
# ---------------------------------------------------------------------------

ITALIENS = ["vierge_aux_rochers", "belle_ferronniere", "castiglione", "mort_de_la_vierge", "saint_jean_baptiste",
            "sainte_anne", "dentelliere", "tricheur", "concert_champetre", "femme_au_miroir", "homme_au_gant", "belle_nani"]


def construire_grande_galerie():
    s = Salle("grande_galerie", -5.5, -67, 5.5, 67)
    s.plancher(-5, -66, 5, 66, 0.0, "parquet", pas=0.75)
    s.mur((-5, -66), (-5, 66), 0, 8, "mur_beige", (0, 0))
    s.mur((5, -66), (5, 66), 0, 8, "mur_beige", (0, 0))
    s.mur((-5, 66), (5, 66), 0, 11.2, "mur_beige", (0, 0), portes=[(3.5, 6.5, 4.5)])
    s.mur((-5, -66), (5, -66), 0, 11.2, "mur_beige", (0, 0), portes=[(3.5, 6.5, 4.5)])
    s.panneau((0, 5.0, -65.95), (0, 0, 1), 1.4, 0.7, "sortie")
    s.voute(-5, 5, -66, 66, 8.0, 3.0, "caissons", pas=2.0)
    for z in np.arange(-60, 61, 8.0):
        s.plafond(-1.1, z - 2, 1.1, z + 2, 10.85, "verriere", pas=2.0)
    for z in (-44, -22, 0, 22, 44):  # arcs doubleaux sur colonnes
        for x in (-4.4, 4.4):
            s.colonne(x, z, 0.36, 0.0, 7.9, "marbre")
        s.voute(-4.9, 4.9, z - 0.45, z + 0.45, 7.9, 2.9, "marbre", pas=1.0)
        s.boite(-5, 7.7, z - 0.5, 5, 7.95, z + 0.5, "dorure", bloquer=False)
    k = 0
    for z in np.arange(-60, 62, 7.5):
        if min(abs(z - c) for c in (-44, -22, 0, 22, 44)) < 2.5:
            continue
        for cote, x in ((1, -5), (-1, 5)):
            nom = ITALIENS[k % len(ITALIENS)]
            k += 5 if cote > 0 else 7
            s.tableau(nom, (x, 2.6, z), (cote, 0, 0), 1.7 + 0.5 * ((k * 7) % 3) / 2)
    for i, z in enumerate((-52, -30, -8, 14, 36)):
        s.objet(f"statue:{i}", (4.1 if i % 2 else -4.1, 0, z + 5.5), 90 if i % 2 else -90, rayon=0.45, hauteur=2.8)
    for z in (-58, -37, -14, 8, 29, 52):
        s.objet("banc", (0, 0, z), 90, rect=(0.35, 1.15), hauteur=0.5)
    s.objet("echafaudage", (3.8, 0, 44.0), 90, rect=(0.6, 1.15), hauteur=3.4)
    for z in np.arange(-60, 61, 11.0):
        s.lumiere((3.0 if int(z) % 2 else -3.0, 5.5, z), portee=12.0)
    s.depart = (0.0, 0.0, 58.0, -90.0)
    s.sol_son, s.visiteurs, s.chaise = "parquet", 12, (4.45, 26.0, 180.0)
    s.groupe = (-3.3, 50.2, 180.0, (-5.0, 2.6, 52.5))
    s.ambiante_nuit = (0.12, 0.11, 0.13)
    s.ambiante_visite = (0.45, 0.43, 0.4)
    s.brume = 0.012
    s.fond = (0.05, 0.045, 0.045)
    return s


# ---------------------------------------------------------------------------
# Salle des Cariatides
# ---------------------------------------------------------------------------


def construire_cariatides():
    s = Salle("cariatides", -7.5, -17, 7.5, 15.5)
    s.plancher(-7, -16.5, 7, 15, 0.0, "damier")
    for (a, b), portes in ((((-7, -16.5), (-7, 15)), ()), (((7, -16.5), (7, 15)), ()), (((-7, 15), (7, 15)), [(5.5, 8.5, 4.2)]),
                         (((-7, -16.5), (7, -16.5)), ())):
        s.mur(a, b, 0, 7.0, "pierre", (0, 0), portes=portes)
    s.voute(-7, 7, -16.5, 15, 7.0, 3.4, "plafond", pas=2.0, fermer=True)
    for z in (-9, -3, 3, 9):
        for x in (-5.6, 5.6):
            s.colonne(x, z, 0.38, 0.0, 7.0, "marbre")
    # La tribune portée par les quatre cariatides de Jean Goujon
    for x in (-2.4, -0.8, 0.8, 2.4):
        s.objet("cariatide", (x, 0, -13.2), rayon=0.42, hauteur=3.3)
    s.boite(-3.4, 3.32, -16.5, 3.4, 3.85, -12.6, "marbre", bloquer=False, dessous=True)
    for x in np.arange(-3.2, 3.3, 0.4):
        s.boite(x - 0.06, 3.85, -12.75, x + 0.06, 4.45, -12.63, "marbre", bloquer=False)
    s.boite(-3.4, 4.45, -12.8, 3.4, 4.55, -12.6, "marbre", bloquer=False)
    for i, z in enumerate((-6, 0, 6, 12)):
        for cote in (-1, 1):
            s.objet(f"statue:{i * 2 + (cote > 0)}", (cote * 4.3, 0, z), 90 * -cote, rayon=0.45, hauteur=2.8)
    for position in ((0, 6, 11), (0, 6, 1), (0, 6, -9), (-4, 4, -14), (4, 4, -14)):
        s.lumiere(position, portee=10.0)
    s.depart = (0.0, 0.0, 13.5, -90.0)
    s.sol_son, s.visiteurs, s.chaise = "marbre", 6, (6.3, 13.2, 180.0)
    for i, z in enumerate((-6, 0, 6, 12)):  # les statues antiques
        for cote in (-1, 1):
            s.points_vue.append((cote * 2.6, z, (cote * 4.3, 1.6, z)))
    s.points_vue += [(x, -9.8, (x, 1.8, -13.2)) for x in (-2.0, 0.0, 2.0)]  # les Cariatides
    s.ambiante_nuit = (0.1, 0.06, 0.07)
    s.ambiante_visite = (0.45, 0.43, 0.42)
    s.cartels.append((np.array((0, 1.8, -13.2)), "Les Cariatides", "Jean Goujon, 1550. Quatre femmes de pierre portent "
                      "la tribune des musiciens : elles donnent son nom à la salle."))
    return s


# ---------------------------------------------------------------------------
# La crypte du Sphinx
# ---------------------------------------------------------------------------

STELES = [(-3.3, 1.2, 90), (3.3, 1.2, -90), (-3.3, -5.8, 90), (3.3, -5.8, -90)]  # (x, z, lacet) : face vers le centre


def construire_sphinx():
    s = Salle("sphinx", -8.5, -10.5, 8.5, 10.5)
    s.plancher(-8, -10, 8, 10, 0.0, "dalles")
    for (a, b), portes in ((((-8, -10), (-8, 10)), ()), (((8, -10), (8, 10)), ()), (((-8, 10), (8, 10)), [(6.5, 9.5, 2.8)]),
                         (((-8, -10), (8, -10)), ())):
        s.mur(a, b, 0, 3.0, "hieroglyphes", (0, 0), portes=portes)
        s.mur(a, b, 3.0, 3.4, "pierre_sombre", (0, 0))
    s.voute(-8, 8, -10, 10, 3.4, 2.6, "pierre_sombre", pas=1.5, fermer=True)
    for x in (-5.4, 5.4):
        for z in (-3.0, 5.0):
            s.boite(x - 0.45, 0.0, z - 0.45, x + 0.45, 4.2, z + 0.45, "pierre")
    s.objet("sphinx", (0, 0, -2.6), rect=(1.0, 2.55), hauteur=0.7)  # couché : il ne cache que ce qui est bas
    for (x, z, lacet), symbole in zip(STELES, SYMBOLES):
        s.objet(f"stele:{symbole}", (x, 0, z), lacet, rect=(0.35, 0.45), hauteur=1.0)
    for x, z in ((-6.5, -8.5), (6.5, -8.5), (-6.5, 8.3), (6.5, 8.3)):
        s.objet("brasero", (x, 0, z), rayon=0.4, hauteur=1.0)
        s.lumiere((x, 1.4, z), (1.0, 0.55, 0.2), 7.0)
    s.lumiere((0, 3.5, -2.5), (0.9, 0.8, 0.7), 8.0)
    s.depart = (0.0, 0.0, 8.5, -90.0)
    s.visiteurs = 5
    s.points_vue = [(0.0, 1.9, (0, 1.3, -0.6)), (-2.1, -2.6, (0, 0.8, -2.6)), (2.1, -2.6, (0, 0.8, -2.6)),
                    (-1.7, 0.9, (0, 1.2, -1.0)), (1.7, 0.9, (0, 1.2, -1.0))]
    s.points_vue += [(x + (1.3 if x < 0 else -1.3), z, (x, 1.0, z)) for x, z, _ in STELES]
    s.points_vue += [(x * 0.9, z, (x * 1.3, 1.6, z)) for x in (-6.0, 6.0) for z in (-6.0, 1.0, 7.0)]  # hiéroglyphes
    s.ambiante_nuit = (0.07, 0.05, 0.04)
    s.ambiante_visite = (0.42, 0.38, 0.34)
    s.feux = [(x, 1.1, z) for x, z in ((-6.5, -8.5), (6.5, -8.5), (-6.5, 8.3), (6.5, 8.3))]
    s.cartels.append((np.array((0, 1.5, -1.0)), "Le Grand Sphinx de Tanis", "Égypte, vers 2600 av. J.-C. (?). "
                      "Un seul bloc de granit rose, long de près de cinq mètres."))
    return s


# ---------------------------------------------------------------------------
# L'escalier Daru et la Victoire de Samothrace
# ---------------------------------------------------------------------------

PALIER = 4.8  # hauteur du palier de la Victoire


def construire_daru():
    s = Salle("daru", -7.5, -17.5, 7.5, 16.5)
    s.plancher(-7, 4, 7, 16, 0.0, "dalles")
    s.marches(-4.5, 4.5, 4.0, -8.0, 0.0, PALIER, 24, "marbre")
    s.plancher(-7, -17, 7, -8, PALIER, "dalles")
    for x0, x1 in ((-7, -4.5), (4.5, 7)):  # maçonnerie de chaque côté de l'escalier
        s.boite(x0, 0.0, -8.0, x1, PALIER, 4.0, "pierre")
        for x in np.arange(x0 + 0.2, x1, 0.45):  # balustrade
            s.boite(x - 0.05, PALIER, 3.7, x + 0.05, PALIER + 0.8, 3.85, "marbre", bloquer=False)
        s.boite(x0, PALIER + 0.8, 3.65, x1, PALIER + 0.9, 3.9, "marbre", bloquer=False)
    haut = 14.0
    s.mur((-7, 4), (-7, 16), 0, haut, "pierre", (0, 10))
    s.mur((7, 4), (7, 16), 0, haut, "pierre", (0, 10))
    s.mur((-7, 16), (7, 16), 0, haut, "pierre", (0, 10), portes=[(5.5, 8.5, 4.2)])
    s.mur((-7, -17), (-7, 4), PALIER, haut, "pierre", (0, -10), portes=[(0.8, 3.8, 4.2)])
    s.mur((7, -17), (7, 4), PALIER, haut, "pierre", (0, -10), portes=[(0.8, 3.8, 4.2)])
    s.mur((-7, -17), (7, -17), PALIER, haut, "pierre", (0, -10))
    s.plafond(-7, -17, 7, -4, haut, "plafond", pas=2.0)
    s.plafond(-7, 8, 7, 16, haut, "plafond", pas=2.0)
    s.plafond(-7, -4, -3, 8, haut, "plafond", pas=2.0)
    s.plafond(3, -4, 7, 8, haut, "plafond", pas=2.0)
    s.plafond(-3, -4, 3, 8, haut + 0.5, "verriere", pas=2.0)
    # La Victoire sur sa proue, en haut des marches
    s.objet("victoire", (0, PALIER, -12.5), rect=(1.2, 2.0), hauteur=9.0)
    s.bloquer_rect(-1.2, -14.6, 1.2, -10.5, 9.0)
    # La vitrine de la main de la Victoire, côté droit du palier
    s.objet("socle", (5.4, PALIER, -12.0), rayon=0.45, hauteur=PALIER + 1.2)
    s.objet("main_victoire", (5.4, PALIER + 1.0, -12.0), -90)
    vitre_boite(s, 5.1, PALIER + 1.0, -12.3, 5.7, PALIER + 1.45, -11.7)
    # Les œuvres
    s.tableau("liberte", (-7, PALIER + 2.6, -10.3), (1, 0, 0), 3.0)
    s.tableau("radeau_meduse", (7, PALIER + 2.8, -10.4), (-1, 0, 0), 3.0)
    s.tableau("sacre_napoleon", (-7, 3.4, 10), (1, 0, 0), 3.2)
    s.tableau("serment_horaces", (7, 3.2, 10), (-1, 0, 0), 2.9)
    s.tableau("grande_odalisque", (-3.8, 2.6, 16), (0, 0, -1), 1.6)
    s.tableau("madame_recamier", (3.8, 2.6, 16), (0, 0, -1), 1.6)
    for x, z in ((-6.3, 6.5), (6.3, 6.5), (-6.3, 13.5), (6.3, 13.5)):
        s.objet(f"buste:{int(x + z)}", (x, 0, z), 90 if x < 0 else -90, rayon=0.4, hauteur=1.8)
    s.lumiere((0, 11, 0), (0.55, 0.62, 0.85), 18.0)
    s.lumiere((0, PALIER + 4, -10), (0.9, 0.9, 1.0), 9.0)
    s.lumiere((0, 5, 12), (0.9, 0.8, 0.65), 10.0)
    s.lumiere((-5, PALIER + 3, -14), (0.9, 0.8, 0.65), 10.0)
    s.lumiere((5, PALIER + 3, -14), (0.9, 0.8, 0.65), 10.0)
    s.depart = (0.0, 0.0, 14.5, -90.0)
    s.visiteurs = 9
    s.points_vue = [(x, -8.6, (0, PALIER + 2.5, -12.5)) for x in (-2.4, -0.8, 0.8, 2.4)]
    s.points_vue += [(x, 6.0, (0, PALIER + 2.5, -12.5)) for x in (-2.0, 2.0)]  # la Victoire vue d'en bas
    s.points_vue += [(4.2, -12.0, (5.4, PALIER + 1.2, -12.0))]  # la main de la Victoire
    s.points_vue += [(x * 0.62, z, (x, 1.3, z)) for x in (-6.3, 6.3) for z in (6.5, 13.5)]  # les bustes
    s.ambiante_nuit = (0.13, 0.14, 0.2)  # clair de lune : assez pour s'orienter, assez sombre pour se cacher
    s.ambiante_visite = (0.42, 0.42, 0.45)
    s.cartels.append((np.array((0, PALIER + 2.5, -12.0)), "La Victoire de Samothrace", "Grèce, vers 190 av. J.-C. "
                      "La déesse de la victoire se pose sur la proue d'un navire de guerre. Découverte en 1863."))
    s.cartels.append((np.array((5.4, PALIER + 1.2, -12.0)), "La main de la Victoire", "Retrouvée à Samothrace en 1950, "
                      "cette main droite est exposée à côté de la statue."))
    return s


SALLES = {  # nom : (titre, emplacement, fonction de construction)
    "apollon": ("Galerie d'Apollon", "Aile Denon, 1er étage", construire_apollon),
    "etats": ("Salle des États", "Aile Denon, 1er étage", construire_etats),
    "grande_galerie": ("Grande Galerie", "Aile Denon, 1er étage", construire_grande_galerie),
    "cariatides": ("Salle des Cariatides", "Aile Sully, rez-de-chaussée", construire_cariatides),
    "sphinx": ("Crypte du Sphinx", "Aile Sully, sous-sol", construire_sphinx),
    "daru": ("Escalier Daru", "Aile Denon", construire_daru),
}


def construire(nom):
    salle = SALLES[nom][2]()
    salle.titre, salle.lieu = SALLES[nom][:2]
    salle.grilles0 = (salle.bloque.copy(), salle.opaque.copy(), salle.sol.copy())
    return salle

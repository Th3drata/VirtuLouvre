"""Modèles 3D du jeu, construits en code à partir de formes simples (NumPy) : personnages, statues,
joyaux, mobilier, indices... Aucun fichier à charger : tout est calculé au lancement.

Un modèle est un ensemble de « parties » (pour animer les personnages : jambes, bras...) ;
chaque partie regroupe ses triangles par matériau (or, marbre, uniforme...)."""

import math

import numpy as np
from OpenGL.GL import *

MATERIAUX = {  # nom : (couleur, reflet 0-1, dureté du reflet, émission éventuelle)
    "or": ((0.85, 0.64, 0.24), 0.9, 60, None),
    "argent": ((0.78, 0.79, 0.83), 1.0, 80, None),
    "diamant": ((0.9, 0.95, 1.0), 1.0, 110, (0.16, 0.17, 0.2)),
    "saphir": ((0.1, 0.22, 0.9), 1.0, 100, (0.02, 0.05, 0.2)),
    "emeraude": ((0.05, 0.68, 0.32), 1.0, 100, (0.0, 0.12, 0.05)),
    "perle": ((0.96, 0.93, 0.87), 0.7, 40, (0.1, 0.1, 0.09)),
    "marbre": ((0.9, 0.88, 0.84), 0.25, 20, None),
    "marbre_gris": ((0.6, 0.6, 0.62), 0.3, 25, None),
    "granit": ((0.62, 0.42, 0.38), 0.35, 30, None),
    "pierre": ((0.72, 0.66, 0.56), 0.05, 5, None),
    "bronze": ((0.45, 0.3, 0.16), 0.7, 40, None),
    "bois": ((0.36, 0.22, 0.13), 0.2, 15, None),
    "bois_clair": ((0.66, 0.5, 0.32), 0.15, 10, None),
    "velours": ((0.5, 0.06, 0.08), 0.05, 5, None),
    "velours_bleu": ((0.14, 0.12, 0.38), 0.05, 5, None),
    "uniforme": ((0.08, 0.1, 0.2), 0.1, 10, None),
    "peau": ((0.86, 0.66, 0.53), 0.15, 10, None),
    "peau2": ((0.55, 0.38, 0.28), 0.15, 10, None),
    "noir": ((0.05, 0.05, 0.06), 0.3, 30, None),
    "sweat": ((0.2, 0.2, 0.22), 0.05, 5, None),
    "jean": ((0.12, 0.16, 0.3), 0.05, 5, None),
    "jaune": ((0.95, 0.78, 0.05), 0.5, 30, None),
    "fluo": ((0.85, 0.95, 0.08), 0.1, 10, (0.14, 0.16, 0.0)),
    "reflechissant": ((0.8, 0.8, 0.8), 1.0, 60, (0.12, 0.12, 0.12)),
    "manteau": ((0.1, 0.09, 0.09), 0.15, 12, None),
    "metal": ((0.4, 0.41, 0.45), 0.8, 50, None),
    "orange": ((0.95, 0.45, 0.06), 0.4, 30, None),
    "ampoule": ((1.0, 0.95, 0.75), 0.5, 10, (1.0, 0.92, 0.65)),
    "laser": ((1.0, 0.1, 0.1), 0.5, 10, (1.0, 0.1, 0.08)),
    "ecran": ((0.1, 0.9, 0.4), 0.5, 10, (0.1, 0.8, 0.35)),
    "papier": ((0.92, 0.9, 0.84), 0.05, 5, None),
    "cuir": ((0.3, 0.16, 0.08), 0.2, 15, None),
    "boue": ((0.22, 0.16, 0.09), 0.05, 5, None),
    "bache": ((0.15, 0.3, 0.6), 0.1, 10, None),
    "carton": ((0.62, 0.48, 0.3), 0.05, 5, None),
    "gris": ((0.5, 0.5, 0.52), 0.3, 20, None),
    "blanc": ((0.92, 0.92, 0.9), 0.2, 15, None),
}

# ---------------------------------------------------------------------------
# Géométrie : une forme simple = (triangles (n, 3, 3), normales (n, 3, 3))
# ---------------------------------------------------------------------------


def _normaliser(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n < 1e-12, 1.0, n)


def plat(tris):
    """Normales « plates » : une par triangle (facettes nettes)."""
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    n = _normaliser(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]))
    return tris, np.repeat(n[:, None], 3, axis=1)


def _vers_exterieur(tris, centre):
    """Retourne les triangles qui regardent vers le centre (formes convexes)."""
    tris = np.array(tris, float).reshape(-1, 3, 3)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    dedans = np.einsum("ij,ij->i", n, tris.mean(1) - np.asarray(centre, float)) < 0
    tris[dedans] = tris[dedans][:, [0, 2, 1]]
    return tris


def grille(P, N):
    """Surface lisse à partir d'une grille de points P (nu, nv, 3) et de leurs normales N."""
    coins = (P[:-1, :-1], P[1:, :-1], P[1:, 1:], P[:-1, 1:])
    normales = (N[:-1, :-1], N[1:, :-1], N[1:, 1:], N[:-1, 1:])
    tris = np.concatenate([np.stack([coins[0], coins[1], coins[2]], -2).reshape(-1, 3, 3),
                           np.stack([coins[0], coins[2], coins[3]], -2).reshape(-1, 3, 3)])
    norms = np.concatenate([np.stack([normales[0], normales[1], normales[2]], -2).reshape(-1, 3, 3),
                            np.stack([normales[0], normales[2], normales[3]], -2).reshape(-1, 3, 3)])
    faces = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    garder = np.linalg.norm(faces, axis=1) > 1e-12  # triangles aplatis (aux pôles)
    tris, norms, faces = tris[garder], norms[garder], faces[garder]
    envers = np.einsum("ij,ij->i", faces, norms.sum(1)) < 0  # sens du triangle accordé à sa normale
    tris[envers] = tris[envers][:, [0, 2, 1]]
    norms[envers] = norms[envers][:, [0, 2, 1]]
    return tris, norms


def boite(x0, y0, z0, x1, y1, z1):
    q = [((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)), ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)),
         ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)), ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
         ((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)), ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))]
    tris = [t for a, b, c, d in q for t in ((a, b, c), (a, c, d))]
    return plat(_vers_exterieur(tris, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def revolution(profil, n=20):
    """Surface de révolution autour de l'axe y ; profil = [(rayon, y), ...] de bas en haut."""
    p = np.asarray(profil, float)
    r, y = p[:, 0], p[:, 1]
    nr, ny = np.gradient(y), -np.gradient(r)  # normale au profil, vers l'extérieur
    longueur = np.hypot(nr, ny)
    nr, ny = nr / np.where(longueur < 1e-12, 1, longueur), ny / np.where(longueur < 1e-12, 1, longueur)
    a = np.linspace(0, 2 * math.pi, n + 1)
    ca, sa = np.cos(a)[None, :], np.sin(a)[None, :]
    un = np.ones_like(ca)
    P = np.stack([r[:, None] * ca, y[:, None] * un, r[:, None] * sa], -1)
    N = np.stack([nr[:, None] * ca, ny[:, None] * un, nr[:, None] * sa], -1)
    return grille(P, N)


def disque(r, y, vers_haut=True, n=16):
    a = np.linspace(0, 2 * math.pi, n + 1)
    tris = [((0, y, 0), (r * math.cos(a[k]), y, r * math.sin(a[k])), (r * math.cos(a[k + 1]), y, r * math.sin(a[k + 1])))
            for k in range(n)]
    return plat(_vers_exterieur(tris, (0, y - (1 if vers_haut else -1), 0)))


def cylindre(r0, r1, y0, y1, n=16, bouchons=True):
    geo = revolution([(r0, y0), (r1, y1)], n)
    if bouchons:
        geo = fusion(geo, disque(r0, y0, False, n), disque(r1, y1, True, n))
    return geo


def sphere(r, n=16, m=10):
    t = np.linspace(0, math.pi, m + 1)
    return revolution(np.column_stack([r * np.sin(t), -r * np.cos(t)]), n)


def tore(R, r, a0=0.0, a1=2 * math.pi, n=32, m=8):
    """Anneau dans le plan horizontal (x, z), éventuellement ouvert (arc de a0 à a1)."""
    u = np.linspace(a0, a1, n + 1)[:, None]
    v = np.linspace(0, 2 * math.pi, m + 1)[None, :]
    P = np.stack([(R + r * np.cos(v)) * np.cos(u), r * np.sin(v) * np.ones_like(u), (R + r * np.cos(v)) * np.sin(u)], -1)
    C = np.stack([R * np.cos(u) * np.ones_like(v), 0 * u * v, R * np.sin(u) * np.ones_like(v)], -1)
    return grille(P, _normaliser(P - C))


def tube(points, r, m=8):
    """Tube le long d'une ligne brisée (chaînes, cordes, tubes d'échafaudage, rubans...)."""
    pts = np.asarray(points, float)
    rayons = np.broadcast_to(np.asarray(r, float), (len(pts),))[:, None, None]
    T = _normaliser(np.gradient(pts, axis=0))
    aide = np.array((0.0, 1.0, 0.0)) if abs(T[0, 1]) < 0.9 else np.array((1.0, 0.0, 0.0))
    Ns = [_normaliser(np.cross(T[0], aide))]
    for i in range(1, len(pts)):  # repère transporté le long de la ligne (pas de torsion)
        n = Ns[-1] - (Ns[-1] @ T[i]) * T[i]
        Ns.append(_normaliser(n) if np.linalg.norm(n) > 1e-9 else Ns[-1])
    Nv = np.array(Ns)
    B = np.cross(T, Nv)
    v = np.linspace(0, 2 * math.pi, m + 1)[None, :, None]
    P = pts[:, None, :] + rayons * (np.cos(v) * Nv[:, None, :] + np.sin(v) * B[:, None, :])
    return grille(P, _normaliser(P - pts[:, None, :]))


def pierre(facettes=8, table=0.55, couronne=0.35, pavillon=0.85):
    """Pierre précieuse taillée : table plate en haut, couronne, rondiste, pavillon pointu en bas."""
    a = np.linspace(0, 2 * math.pi, facettes, endpoint=False)
    ceinture = np.column_stack([np.cos(a), np.zeros(facettes), np.sin(a)])
    b = a + math.pi / facettes
    dessus = np.column_stack([table * np.cos(b), np.full(facettes, couronne), table * np.sin(b)])
    haut, pointe = (0, couronne, 0), (0, -pavillon, 0)
    tris = []
    for k in range(facettes):
        s = (k + 1) % facettes
        tris += [(haut, dessus[k], dessus[s]), (ceinture[k], ceinture[s], dessus[k]),
                 (ceinture[s], dessus[s], dessus[k]), (ceinture[k], ceinture[s], pointe)]
    return plat(_vers_exterieur(tris, (0, 0, 0)))


def prisme(polygone, z0, z1):
    """Polygone du plan (x, y) épaissi entre z0 et z1 (ailes, symboles, profils...)."""
    p = np.asarray(polygone, float)
    if np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]) < 0:
        p = p[::-1]  # sens inverse des aiguilles d'une montre
    c = p.mean(0)
    tris, voulues = [], []
    for i in range(len(p)):
        q, r = p[i], p[(i + 1) % len(p)]
        tris += [((c[0], c[1], z1), (q[0], q[1], z1), (r[0], r[1], z1)), ((c[0], c[1], z0), (r[0], r[1], z0), (q[0], q[1], z0))]
        voulues += [(0, 0, 1), (0, 0, -1)]
        cote = (r[1] - q[1], q[0] - r[0], 0)
        tris += [((q[0], q[1], z0), (r[0], r[1], z0), (r[0], r[1], z1)), ((q[0], q[1], z0), (r[0], r[1], z1), (q[0], q[1], z1))]
        voulues += [cote, cote]
    tris = np.array(tris, float)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    envers = np.einsum("ij,ij->i", n, np.array(voulues, float)) < 0
    tris[envers] = tris[envers][:, [0, 2, 1]]
    return plat(tris)


def fusion(*geos):
    geos = [g for g in geos if g is not None and len(g[0])]
    return np.concatenate([g[0] for g in geos]), np.concatenate([g[1] for g in geos])


def _rotation(axe, degres):
    axe = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}.get(axe, axe)
    k = np.asarray(axe, float) / np.linalg.norm(axe)
    a = math.radians(degres)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.identity(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def deplacer(geo, d):
    return geo[0] + np.asarray(d, float), geo[1]


def tourner(geo, axe, degres):
    R = _rotation(axe, degres)
    return geo[0] @ R.T, geo[1] @ R.T


def etirer(geo, s):
    s = np.broadcast_to(np.asarray(s, float), (3,))
    return geo[0] * s, _normaliser(geo[1] / s)


def repere(geo, avant, haut=(0, 1, 0)):
    """Place une forme construite « debout » : son axe y local part vers `avant`, son axe z local vers `haut`."""
    avant = _normaliser(np.asarray(avant, float))
    haut = np.asarray(haut, float) - (np.asarray(haut, float) @ avant) * avant
    haut = _normaliser(haut) if np.linalg.norm(haut) > 1e-6 else _normaliser(np.cross(avant, (1.0, 0.0, 0.0)))
    cote = np.cross(avant, haut)
    M = np.column_stack([cote, avant, haut])
    return geo[0] @ M.T, geo[1] @ M.T


class Forme:
    """Morceau de modèle : des formes simples regroupées par matériau."""

    def __init__(self):
        self.mats = {}

    def add(self, mat, *geos):
        self.mats.setdefault(mat, []).extend(g for g in geos if g is not None)
        return self

    def merge(self, autre, transformation=None):
        for mat, geos in autre.mats.items():
            self.add(mat, *(transformation(g) if transformation else g for g in geos))
        return self

    def moved(self, d):
        return Forme().merge(self, lambda g: deplacer(g, d))

    def turned(self, axe, degres):
        return Forme().merge(self, lambda g: tourner(g, axe, degres))

    def scaled(self, s):
        return Forme().merge(self, lambda g: etirer(g, s))

    def tableaux(self):
        return {mat: fusion(*geos) for mat, geos in self.mats.items() if geos}


class Modele:
    """Un modèle prêt à dessiner : une « display list » OpenGL par partie, compilée à la première utilisation."""

    def __init__(self, parties, **infos):
        self.parties = parties if isinstance(parties, dict) else {"corps": parties}
        self.infos = infos
        self.listes = None

    def triangles(self):
        return sum(len(t) for forme in self.parties.values() for t, _ in forme.tableaux().values())

    def bornes(self):
        points = np.concatenate([t.reshape(-1, 3) for f in self.parties.values() for t, _ in f.tableaux().values()])
        return points.min(0), points.max(0)

    def compiler(self):
        self.listes = {}
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        for nom, forme in self.parties.items():
            liste = glGenLists(1)
            glNewList(liste, GL_COMPILE)
            for mat, (tris, norms) in forme.tableaux().items():
                couleur, reflet, durete, emission = MATERIAUX[mat]
                glColor3f(*couleur)
                glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (reflet, reflet, reflet, 1.0))
                glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, durete)
                glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (*(emission or (0, 0, 0)), 1.0))
                sommets = np.ascontiguousarray(tris.reshape(-1, 3), dtype=np.float32)
                normales = np.ascontiguousarray(norms.reshape(-1, 3), dtype=np.float32)
                glVertexPointer(3, GL_FLOAT, 0, sommets)  # (les données sont copiées dans la liste)
                glNormalPointer(GL_FLOAT, 0, normales)
                glDrawArrays(GL_TRIANGLES, 0, len(sommets))
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
            glEndList()
            self.listes[nom] = liste
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

    def draw(self, partie="corps"):
        if self.listes is None:
            self.compiler()
        glCallList(self.listes[partie])


# ---------------------------------------------------------------------------
# Motifs de joaillerie
# ---------------------------------------------------------------------------


def gemme(centre, taille, mat, avant=(0, 0, 1), haut=(0, 1, 0), allonge=1.0, facettes=8):
    """Une pierre posée en `centre`, table tournée vers `avant`, étirée selon `haut` si allonge > 1."""
    g = etirer(pierre(facettes), (taille, taille * 0.8, taille * allonge))
    return Forme().add(mat, deplacer(repere(g, avant, haut), centre))


def motif(centre, taille, mat, avant=(0, 0, 1), haut=(0, 1, 0), allonge=1.3, entourage=10, metal="or"):
    """Pierre centrale entourée d'un cercle de petits diamants (motif typique des parures)."""
    avant = _normaliser(np.asarray(avant, float))
    haut_v = _normaliser(np.asarray(haut, float) - (np.asarray(haut, float) @ avant) * avant)
    cote = np.cross(avant, haut_v)
    f = gemme(centre, taille, mat, avant, haut_v, allonge)
    c = np.asarray(centre, float)
    for k in range(entourage):
        a = 2 * math.pi * k / entourage
        p = c + (cote * math.cos(a) * taille * 1.35 + haut_v * math.sin(a) * taille * allonge * 1.3) - avant * 0.01
        f.merge(gemme(p, taille * 0.24, "diamant", avant, haut_v, facettes=6))
    anneau = etirer(tore(1.0, 0.05, n=24, m=5), (taille * 1.35, taille * 1.35, taille * allonge * 1.3))
    f.add(metal, deplacer(repere(anneau, avant, haut_v), c - avant * 0.02))  # (l'anneau entoure la pierre)
    return f


def goutte(accroche, taille, mat, avant=(0, 0, 1), metal="or"):
    """Pampille : petit diamant d'attache puis pierre en poire qui pend sous le point d'accroche."""
    c = np.asarray(accroche, float)
    f = gemme(c, taille * 0.3, "diamant", avant, facettes=6)
    f.add(metal, tube([c, c - (0, taille * 0.9, 0)], 0.006, 5))
    f.merge(gemme(c - (0, taille * 1.9, 0), taille, mat, avant, allonge=1.7))
    return f


def arc_u(n, largeur=0.42, profondeur=0.5, haut=0.18, angle=100):
    """Points d'un collier vu de face (en U)."""
    t = np.radians(np.linspace(-angle, angle, n))
    return np.column_stack([largeur * np.sin(t), haut - profondeur * (1 - np.cos(t)) / (1 - math.cos(math.radians(angle))) * 0.9,
                            np.zeros(n)])


# ---------------------------------------------------------------------------
# Les joyaux de la Couronne (interprétations libres)
# ---------------------------------------------------------------------------


def joyau(k):
    f = Forme()
    if k in (0, 6):  # diadèmes (saphirs / perles de l'impératrice Eugénie)
        metal = "or" if k == 0 else "argent"
        f.add(metal, tore(0.42, 0.016, math.radians(-8), math.radians(188), 48, 6))
        for i, degres in enumerate(range(30, 151, 20)):
            u = math.radians(degres)
            dehors = np.array((math.cos(u), 0.0, math.sin(u)))
            base = dehors * 0.42
            grandeur = 1.0 - abs(degres - 90) / 120
            hauteur = 0.07 + 0.16 * grandeur
            f.add(metal, tube([base, base + (0, hauteur, 0)], 0.008, 5))
            centre = base + (0, hauteur, 0) + dehors * 0.012
            if k == 0:
                f.merge(motif(centre, 0.045 + 0.03 * grandeur, "saphir", dehors, metal=metal))
                f.merge(gemme(centre + (0, 0.06 + 0.05 * grandeur, 0), 0.018, "diamant", dehors, facettes=6))
            else:
                for j in range(9):  # arche de perles
                    a = math.pi * j / 8
                    p = base + dehors * 0.01 + (0, hauteur * 0.25 + math.sin(a) * hauteur, 0) + \
                        np.cross(dehors, (0, 1, 0)) * math.cos(a) * 0.055
                    f.add("perle", deplacer(sphere(0.011, 8, 5), p))
                f.add("perle", deplacer(etirer(sphere(1, 10, 7), (0.022, 0.03, 0.022)), centre - (0, hauteur * 0.15, 0)))
                f.merge(gemme(centre + (0, 0.07, 0), 0.02, "diamant", dehors, facettes=6))
                f.add("perle", deplacer(sphere(0.02, 10, 6), base + (0, hauteur + 0.07, 0)))
        for degres in range(-5, 186, 12):
            u = math.radians(degres)
            f.merge(gemme((0.435 * math.cos(u), 0.0, 0.435 * math.sin(u)), 0.012, "diamant",
                          (math.cos(u), 0, math.sin(u)), facettes=6))
    elif k in (1, 3):  # colliers (saphirs / émeraudes de Marie-Louise)
        pierre_mat = "saphir" if k == 1 else "emeraude"
        points = arc_u(60)
        f.add("or", tube(points, 0.007, 5))
        n = 9 if k == 1 else 11
        for i, p in enumerate(arc_u(n, angle=80)):
            grandeur = 1 - abs(i - (n - 1) / 2) / n
            f.merge(motif(p, 0.03 + 0.03 * grandeur, pierre_mat, entourage=8))
            if k == 3 and abs(i - (n - 1) / 2) <= 2:
                f.merge(goutte(p - (0, 0.07, 0), 0.03 + 0.012 * grandeur, "emeraude"))
        if k == 1:
            bas = arc_u(n, angle=80)[n // 2]
            f.merge(goutte(bas - (0, 0.08, 0), 0.05, "saphir"))
    elif k in (2, 4):  # boucles d'oreilles (une en saphir / une paire en émeraude)
        positions = (0.0,) if k == 2 else (-0.17, 0.17)
        mat = "saphir" if k == 2 else "emeraude"
        for x in positions:
            haut = np.array((x, 0.38, 0.0))
            f.add("or", deplacer(tourner(tore(0.05, 0.007, 0, math.pi, 12, 5), "x", -90), haut + (0, 0.02, 0)))
            f.merge(motif(haut - (0, 0.05, 0), 0.04, "diamant", entourage=8))
            f.add("or", tube([haut - (0, 0.09, 0), haut - (0, 0.16, 0)], 0.006, 5))
            f.merge(motif(haut - (0, 0.3, 0), 0.075 if k == 2 else 0.06, mat, allonge=1.45, entourage=12))
            f.merge(goutte(haut - (0, 0.44, 0), 0.025, "diamant"))
    elif k == 5:  # broche reliquaire
        f.add("argent", tourner(etirer(cylindre(0.3, 0.3, -0.015, 0.015, 32), (1, 1, 1.25)), "x", 90))
        f.merge(motif((0, 0, 0.03), 0.09, "diamant", allonge=1.2, entourage=12, metal="argent"))
        for j in range(10):
            a = 2 * math.pi * j / 10
            f.merge(gemme((0.23 * math.cos(a), 0.29 * math.sin(a), 0.025), 0.035, "diamant", facettes=8))
        for x in (-0.12, 0.0, 0.12):
            f.merge(goutte((x, -0.37, 0.01), 0.03, "diamant", metal="argent"))
    elif k == 7:  # grand nœud de corsage
        boucle = [(0.05 + 0.2 * (1 - math.cos(t)), 0.13 * math.sin(t) + 0.03 * math.sin(2 * t), 0)
                  for t in np.linspace(0, 2 * math.pi, 40)]
        for signe in (1, -1):
            points = [(signe * x, y, z) for x, y, z in boucle]
            f.add("argent", tube(points, 0.035, 7))
            for p in points[::3]:
                f.merge(gemme(np.array(p) + (0, 0, 0.035), 0.022, "diamant", facettes=6))
            queue = [(signe * (0.03 + 0.2 * t), -0.05 - 0.4 * t + 0.04 * math.sin(6 * t), 0) for t in np.linspace(0, 1, 20)]
            f.add("argent", tube(queue, 0.03, 7))
            for p in queue[::3]:
                f.merge(gemme(np.array(p) + (0, 0, 0.03), 0.02, "diamant", facettes=6))
            f.merge(goutte(np.array(queue[-1]) - (0, 0.03, 0), 0.035, "diamant", metal="argent"))
        f.add("argent", etirer(sphere(1, 14, 9), (0.08, 0.1, 0.05)))
        f.merge(motif((0, 0, 0.05), 0.05, "diamant", entourage=8, metal="argent"))
    return Modele(f)


def couronne():
    """Couronne de l'impératrice Eugénie (interprétation libre) : bandeau, arceaux, globe et croix."""
    f = Forme()
    f.add("or", revolution([(0.3, 0.0), (0.31, 0.02), (0.31, 0.12), (0.3, 0.14)], 32))
    for j in range(16):
        a = 2 * math.pi * j / 16
        dehors = (math.cos(a), 0, math.sin(a))
        f.merge(gemme((0.315 * math.cos(a), 0.07, 0.315 * math.sin(a)), 0.03,
                      "emeraude" if j % 2 else "diamant", dehors))
    for j in range(8):
        a = 2 * math.pi * j / 8
        arceau = [(0.3 * math.cos(t) * math.cos(a), 0.14 + 0.28 * math.sin(t), 0.3 * math.cos(t) * math.sin(a))
                  for t in np.linspace(0, math.pi / 2, 16)]
        f.add("or", tube(arceau, 0.018, 6))
        for p in arceau[2::3]:
            f.merge(gemme(np.array(p) * 1.05, 0.016, "diamant", np.array(p) - (0, 0.14, 0), facettes=6))
        f.add("or", deplacer(etirer(sphere(1, 8, 6), (0.05, 0.06, 0.03)), (0.3 * math.cos(a), 0.2, 0.3 * math.sin(a))))
    f.add("or", deplacer(sphere(0.06, 14, 9), (0, 0.46, 0)))
    f.add("or", boite(-0.012, 0.5, -0.012, 0.012, 0.64, 0.012), boite(-0.045, 0.56, -0.012, 0.045, 0.59, 0.012))
    f.add("velours", revolution([(0.28, 0.1), (0.25, 0.25), (0.12, 0.38), (0.0, 0.4)], 24))
    return Modele(f)


# ---------------------------------------------------------------------------
# Personnages (5 parties animées : corps, jambes, bras)
# ---------------------------------------------------------------------------

HANCHE, EPAULE = 0.86, 1.33  # hauteur des articulations
LAMPE = np.array((-0.235, 1.13, 0.52))  # bout de la lampe (bras droit tendu), repère du personnage

TENUES = {
    "gardien": dict(haut="uniforme", bas="uniforme", peau="peau", tete="casquette", gilet=False, lampe=True, manteau=False),
    "voleur": dict(haut="sweat", bas="jean", peau="peau2", tete="casque", gilet=True, lampe=False, manteau=False),
    "guetteur": dict(haut="sweat", bas="jean", peau="peau", tete="bonnet", gilet=True, lampe=True, manteau=False),
    "chef": dict(haut="manteau", bas="noir", peau="peau", tete="chapeau", gilet=False, lampe=False, manteau=True),
}


def humain(tenue):
    t = TENUES[tenue]
    corps = Forme()
    corps.add(t["haut"], etirer(cylindre(0.115, 0.125, 0.84, 1.34, 14), (1.6, 1, 1)))
    corps.add(t["haut"], deplacer(etirer(sphere(1, 14, 8), (0.215, 0.075, 0.125)), (0, 1.33, 0)))
    corps.add(t["bas"], etirer(cylindre(0.118, 0.112, 0.76, 0.9, 14), (1.5, 1, 1)))
    corps.add("noir", etirer(cylindre(0.122, 0.122, 0.86, 0.9, 14, False), (1.52, 1, 1.02)))  # ceinture
    corps.add(t["peau"], cylindre(0.045, 0.048, 1.34, 1.46, 10))
    corps.add(t["peau"], deplacer(etirer(sphere(1, 16, 10), (0.09, 0.115, 0.1)), (0, 1.54, 0)))
    corps.add(t["peau"], deplacer(etirer(sphere(1, 6, 4), (0.016, 0.028, 0.02)), (0, 1.53, 0.1)))
    for x in (-0.035, 0.035):
        corps.add("noir", deplacer(sphere(0.012, 6, 4), (x, 1.56, 0.09)))
    if t["tete"] == "casquette":
        corps.add("uniforme", cylindre(0.098, 0.102, 1.585, 1.665, 16))
        corps.add("noir", deplacer(etirer(cylindre(0.08, 0.08, 0, 0.012, 12), (1, 1, 0.7)), (0, 1.585, 0.1)))
        corps.add("or", boite(-0.015, 1.61, 0.098, 0.015, 1.64, 0.105))
    elif t["tete"] == "casque":
        corps.add("jaune", revolution([(0.12, 1.59), (0.118, 1.63), (0.1, 1.68), (0.06, 1.71), (0.0, 1.72)], 16))
        corps.add("jaune", cylindre(0.14, 0.14, 1.585, 1.595, 16))
    elif t["tete"] == "bonnet":
        corps.add("noir", revolution([(0.103, 1.57), (0.102, 1.62), (0.08, 1.67), (0.0, 1.69)], 14))
    else:  # chapeau
        corps.add("noir", cylindre(0.1, 0.095, 1.6, 1.72, 16), cylindre(0.17, 0.17, 1.6, 1.61, 20))
    if t["gilet"]:
        corps.add("fluo", etirer(cylindre(0.128, 0.137, 0.92, 1.34, 14, False), (1.62, 1, 1)))
        for y in (1.02, 1.17):
            corps.add("reflechissant", etirer(cylindre(0.131, 0.132, y, y + 0.03, 14, False), (1.63, 1, 1.01)))
    if t["manteau"]:
        corps.add("manteau", etirer(revolution([(0.25, 0.3), (0.2, 0.85), (0.13, 0.95)], 16), (1.35, 1, 1)))
        corps.add("manteau", etirer(cylindre(0.1, 0.11, 1.34, 1.42, 12, False), (1.4, 1, 1)))
    if tenue == "gardien":
        corps.add("or", boite(0.07, 1.2, 0.123, 0.12, 1.26, 0.132))

    jambes = {}
    for nom, x in (("jambe_g", 0.09), ("jambe_d", -0.09)):
        jambe = Forme().add(t["bas"], deplacer(cylindre(0.052, 0.07, 0.08, HANCHE, 10), (x, 0, 0)))
        jambe.add("noir", boite(x - 0.05, 0.0, -0.06, x + 0.05, 0.09, 0.15))
        jambes[nom] = jambe
    bras = {}
    for nom, x in (("bras_g", 0.235), ("bras_d", -0.235)):
        b = Forme()
        if nom == "bras_d" and t["lampe"]:  # bras tendu qui tient la lampe
            b.add(t["haut"], tube([(x, EPAULE, 0), (x, 1.1, 0.03)], 0.047, 8))
            b.add(t["haut"], tube([(x, 1.1, 0.03), (x, 1.12, 0.3)], 0.04, 8))
            b.add(t["peau"], deplacer(sphere(0.045, 10, 6), (x, 1.12, 0.33)))
            b.add("noir", deplacer(tourner(cylindre(0.03, 0.04, 0.0, 0.2, 12), "x", 90), (x, 1.13, 0.32)))
            b.add("ampoule", deplacer(tourner(disque(0.036, 0.0, True, 12), "x", 90), (x, 1.13, LAMPE[2] + 0.005)))
        else:
            b.add(t["haut"], tube([(x, EPAULE, 0), (x * 1.04, 1.06, 0), (x * 1.04, 0.87, 0.02)], [0.05, 0.043, 0.037], 8))
            b.add(t["peau"], deplacer(sphere(0.045, 10, 6), (x * 1.04, 0.83, 0.02)))
        bras[nom] = b
    return Modele({"corps": corps, **jambes, **bras}, lampe=t["lampe"])


# ---------------------------------------------------------------------------
# Statues et œuvres
# ---------------------------------------------------------------------------


def drape(profil, plis=14, force=0.06, n=36):
    """Corps drapé : surface de révolution dont le rayon ondule en plis verticaux."""
    tris, norms = revolution(profil, n)
    x, z = tris[..., 0], tris[..., 2]
    a = np.arctan2(z, x)
    k = 1 + force * np.sin(plis * a + 3 * tris[..., 1]) * np.clip(1.6 - tris[..., 1] / 1.4, 0.3, 1.2)
    tris = tris.copy()
    tris[..., 0] *= k
    tris[..., 2] *= k
    return tris, norms


def victoire():
    """La Victoire de Samothrace sur sa proue de navire (sans tête ni bras, comme l'originale)."""
    f = Forme()
    proue = [(-1.7, 0.0), (1.2, 0.0), (1.9, 0.45), (1.75, 1.2), (1.1, 1.6), (-1.7, 1.6)]
    tris, _ = prisme(proue, -0.85, 0.85)
    tris = tris[:, :, [2, 1, 0]].copy()  # profil dessiné dans (z, y), épaisseur selon x
    tris[..., 0] *= np.clip(1.0 - np.maximum(tris[..., 2], 0) / 2.3, 0.18, 1.0)  # la proue s'affine vers l'avant
    f.add("marbre_gris", plat(_vers_exterieur(tris, (0, 0.8, 0))))
    f.add("marbre_gris", boite(-1.1, -0.4, -2.0, 1.1, 0.0, 1.6))
    corps = Forme()
    corps.add("marbre", etirer(drape([(0.0, 0.0), (0.52, 0.02), (0.52, 0.25), (0.44, 0.7), (0.34, 1.05), (0.3, 1.22),
                                      (0.0, 1.24)], plis=18, force=0.08), (1.25, 1, 0.85)))  # jupe drapée
    corps.add("marbre", etirer(drape([(0.0, 1.1), (0.3, 1.12), (0.33, 1.35), (0.4, 1.6), (0.38, 1.75), (0.22, 1.88),
                                      (0.1, 1.95), (0.0, 1.97)], plis=10, force=0.04), (1.3, 1, 0.75)))  # buste
    corps.add("marbre", deplacer(tourner(etirer(sphere(1, 12, 8), (0.17, 0.55, 0.19)), "x", 28), (0.15, 0.75, 0.24)))  # jambe en avant
    for s in (1, -1):
        corps.add("marbre", tube([(s * 0.4, 1.78, 0.0), (s * 0.52, 1.6, -0.06)], 0.08, 8))  # bras disparus
    corps.add("marbre", tube([(-0.25, 0.95, -0.2), (-0.55, 0.7, -0.75), (-0.6, 0.45, -1.1), (-0.45, 0.25, -1.3)],
                             [0.16, 0.13, 0.09, 0.05], 8))  # drapé qui vole au vent

    def penche(g):  # elle se penche en avant, face au vent
        tris = g[0].copy()
        tris[..., 2] += 0.12 * tris[..., 1]
        return tris, g[1]

    f.merge(corps, lambda g: deplacer(penche(g), (0, 1.6, -0.2)))
    aile = [(0, 0), (0.15, 0.5), (0.45, 1.05), (0.85, 1.55), (1.3, 1.95), (1.65, 2.1), (1.85, 1.9), (1.85, 1.4),
            (1.7, 0.85), (1.45, 0.4), (1.05, 0.05), (0.55, -0.12)]  # aile large, pointe relevée vers l'arrière
    for signe in (1, -1):
        epaule = np.array((signe * 0.2, 3.25, -0.3))
        envergure = _normaliser(np.array((signe * 0.62, 0.3, -0.72)))  # ailes ouvertes vers l'arrière et les côtés
        dessus = np.array((0.0, 1.0, 0.25))
        dessus = _normaliser(dessus - (dessus @ envergure) * envergure)  # repère orthonormé
        for couche, (echelle, decalage) in enumerate(((1.0, 0.0), (0.85, 0.08), (0.68, 0.16), (0.5, 0.24))):
            geo = etirer(prisme(aile, -0.03 - 0.015 * couche, 0.03 + 0.015 * couche), (echelle * 1.1, echelle * 0.7, 1))  # plumes
            tris, norms = geo
            M = np.column_stack([envergure, dessus, np.cross(envergure, dessus)])
            f.add("marbre", deplacer((tris @ M.T, norms @ M.T), epaule - dessus * (0.25 + decalage) + envergure * decalage))
    return Modele(f)


def sphinx():
    """Le Grand Sphinx de Tanis, en granit rose : corps de lion couché, tête coiffée du némès."""
    f = Forme()
    f.add("granit", boite(-0.95, 0.0, -2.5, 0.95, 0.4, 2.5))
    f.add("granit", deplacer(etirer(sphere(1, 18, 12), (0.62, 0.45, 1.3)), (0, 0.85, -0.55)))
    f.add("granit", deplacer(etirer(sphere(1, 16, 10), (0.66, 0.5, 0.65)), (0, 0.85, -1.45)))
    f.add("granit", deplacer(etirer(sphere(1, 16, 10), (0.55, 0.62, 0.5)), (0, 1.0, 0.45)))
    for x in (-0.36, 0.36):
        f.add("granit", boite(x - 0.17, 0.4, 0.2, x + 0.17, 0.66, 1.95))
        f.add("granit", deplacer(etirer(sphere(1, 10, 6), (0.18, 0.14, 0.2)), (x, 0.52, 1.95)))
    f.add("granit", tube([(0.62, 0.55, -1.9), (0.66, 0.5, -1.3), (0.64, 0.45, -0.7)], 0.07, 6))
    f.add("granit", deplacer(etirer(sphere(1, 16, 10), (0.3, 0.36, 0.3)), (0, 1.62, 0.78)))  # tête
    f.add("granit", deplacer(etirer(sphere(1, 16, 10), (0.36, 0.24, 0.36)), (0, 1.8, 0.7)))  # dessus du némès
    for x in (-0.3, 0.3):
        f.add("granit", boite(x - 0.07, 1.15, 0.6, x + 0.07, 1.72, 0.85))  # pans du némès
    f.add("granit", boite(-0.05, 1.46, 1.02, 0.05, 1.62, 1.1))  # nez
    f.add("granit", boite(-0.06, 1.2, 0.92, 0.06, 1.36, 1.02))  # barbe
    f.add("noir", boite(-0.16, 1.66, 1.03, -0.07, 1.69, 1.06), boite(0.07, 1.66, 1.03, 0.16, 1.69, 1.06))
    f.add("granit", deplacer(cylindre(0.03, 0.02, 0.0, 0.14, 8), (0, 1.9, 1.02)))  # uræus
    return Modele(f)


def cariatide():
    f = Forme()
    f.add("marbre", drape([(0.0, 0.0), (0.36, 0.02), (0.34, 0.8), (0.27, 1.3), (0.24, 1.6), (0.3, 2.1), (0.26, 2.45),
                           (0.12, 2.6), (0.0, 2.62)], plis=18, force=0.08))
    f.add("marbre", deplacer(etirer(sphere(1, 14, 9), (0.14, 0.18, 0.15)), (0, 2.78, 0)))
    f.add("marbre", cylindre(0.2, 0.28, 2.93, 3.2, 16))  # corbeille sur la tête (polos)
    f.add("marbre", boite(-0.4, 3.2, -0.4, 0.4, 3.32, 0.4))
    for x in (-0.3, 0.3):
        f.add("marbre", tube([(x, 2.4, 0), (x * 1.1, 2.0, 0.05)], 0.06, 6))  # bras coupés au coude
    return Modele(f)


def statue(graine=0, bras=True):
    """Statue grecque drapée sur son socle (variantes selon la graine)."""
    h = np.random.default_rng(graine)
    f = socle(1.0).parties["corps"]
    drap = drape([(0.0, 0.0), (0.3, 0.02), (0.28, 0.6), (0.2, 0.95), (0.19, 1.2), (0.21, 1.4), (0.14, 1.55), (0.0, 1.58)],
                 plis=int(h.integers(10, 18)), force=0.07)
    f.add("marbre", deplacer(drap, (0, 1.0, 0)))
    f.add("marbre", deplacer(etirer(sphere(1, 12, 8), (0.1, 0.13, 0.11)), (0, 2.72, 0)))
    f.add("marbre", deplacer(cylindre(0.05, 0.05, 0, 0.12, 8), (0, 2.55, 0)))
    if bras:
        lever = h.uniform(-0.3, 0.6)
        f.add("marbre", tube([(0.2, 2.45, 0), (0.3, 2.15 + lever * 0.3, 0.1), (0.33, 1.95 + lever, 0.18)], 0.045, 6))
        f.add("marbre", tube([(-0.2, 2.45, 0), (-0.28, 2.1, 0.05), (-0.22, 1.85, 0.12)], 0.045, 6))
    return Modele(f)


def buste(graine=0):
    f = Forme()
    f.add("marbre_gris", cylindre(0.2, 0.18, 0, 1.2, 16), cylindre(0.26, 0.26, 0, 0.08, 16), cylindre(0.24, 0.24, 1.12, 1.2, 16))
    f.add("marbre", etirer(revolution([(0.13, 1.2), (0.16, 1.28), (0.2, 1.38), (0.16, 1.46), (0.07, 1.5), (0.0, 1.5)], 18),
                           (1.7, 1, 1)))  # poitrine et épaules
    f.add("marbre", deplacer(cylindre(0.055, 0.06, 0, 0.12, 8), (0, 1.46, 0)))
    f.add("marbre", deplacer(etirer(sphere(1, 14, 9), (0.11, 0.14, 0.12)), (0, 1.66, 0.01)))
    return Modele(f)


def main_victoire():
    """La main droite de la Victoire (retrouvée en 1950), présentée dans une petite vitrine."""
    f = Forme()
    f.add("marbre", deplacer(etirer(sphere(1, 10, 7), (0.07, 0.09, 0.03)), (0, 0.1, 0)))
    for i, x in enumerate((-0.045, -0.015, 0.015, 0.045)):
        f.add("marbre", tube([(x, 0.17, 0), (x * 1.1, 0.24 + 0.02 * (i in (1, 2)), 0.01)], 0.013, 5))
    f.add("marbre", tube([(0.06, 0.08, 0), (0.1, 0.14, 0.02)], 0.015, 5))
    return Modele(f)


# ---------------------------------------------------------------------------
# Mobilier, décor et indices
# ---------------------------------------------------------------------------


def socle(h=1.0, r=0.34, mat="marbre"):
    return Modele(Forme().add(mat, revolution([(0.0, 0.0), (r, 0.0), (r, 0.08), (r * 0.8, 0.14), (r * 0.8, h - 0.14),
                                                (r, h - 0.08), (r, h), (0.0, h)], 20)))


def banc():
    f = Forme().add("velours", boite(-1.1, 0.36, -0.28, 1.1, 0.47, 0.28))
    f.add("bois", boite(-1.12, 0.3, -0.3, 1.12, 0.36, 0.3))
    for x in (-1.0, 1.0):
        for z in (-0.22, 0.22):
            f.add("bois", boite(x - 0.04, 0.0, z - 0.04, x + 0.04, 0.3, z + 0.04))
    return Modele(f)


def poteau():
    return Modele(Forme().add("or", revolution([(0.0, 0.0), (0.16, 0.0), (0.16, 0.03), (0.04, 0.06), (0.025, 0.1),
                                                 (0.025, 0.88), (0.045, 0.92), (0.035, 0.97), (0.0, 0.98)], 16)))


def corde(a, b, affaissement=0.14):
    """Corde de velours entre deux poteaux (a et b : sommets des poteaux)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    t = np.linspace(0, 1, 16)[:, None]
    points = a + (b - a) * t - np.array((0, 1, 0)) * affaissement * 4 * t * (1 - t)
    return Forme().add("velours", tube(points, 0.022, 6))


def echafaudage(largeur=2.2, hauteur=3.4, profondeur=1.1):
    f = Forme()
    x0, x1, z0, z1 = -largeur / 2, largeur / 2, -profondeur / 2, profondeur / 2
    for x in (x0, x1):
        for z in (z0, z1):
            f.add("metal", tube([(x, 0, z), (x, hauteur, z)], 0.03, 6))
    for y in np.arange(0.9, hauteur + 0.01, 1.2):
        for (ax, az), (bx, bz) in (((x0, z0), (x1, z0)), ((x0, z1), (x1, z1)), ((x0, z0), (x0, z1)), ((x1, z0), (x1, z1))):
            f.add("metal", tube([(ax, y, az), (bx, y, bz)], 0.025, 6))
        f.add("bois_clair", boite(x0, y, z0, x1, y + 0.05, z1))
    f.add("metal", tube([(x0, 0.2, z1), (x1, hauteur - 0.2, z1)], 0.022, 6))
    f.add("bache", boite(x0 - 0.02, 1.0, z0 - 0.03, x1 + 0.02, hauteur, z0 - 0.02))
    return Modele(f)


def chariot():
    """Chariot de chantier renversé en travers du passage par le voleur."""
    f = Forme().add("metal", boite(-0.7, 0.25, -0.4, 0.7, 0.3, 0.4))
    for x in (-0.65, 0.65):
        f.add("metal", tube([(x, 0.3, -0.35), (x, 1.0, -0.35)], 0.025, 6))
    f.add("metal", tube([(-0.65, 1.0, -0.35), (0.65, 1.0, -0.35)], 0.025, 6))
    for x in (-0.55, 0.55):
        for z in (-0.3, 0.3):
            f.add("noir", deplacer(tourner(cylindre(0.12, 0.12, -0.04, 0.04, 12), "z", 90), (x, 0.12, z)))
    f.add("carton", boite(-0.6, 0.3, -0.3, 0.05, 0.75, 0.3), boite(0.1, 0.3, -0.25, 0.6, 0.6, 0.25))
    f.add("carton", boite(-0.4, 0.75, -0.2, 0.0, 1.0, 0.2))
    return Modele(f)


def caisse(l=1.0, h=0.8, p=0.8):
    f = Forme().add("bois_clair", boite(-l / 2, 0, -p / 2, l / 2, h, p / 2))
    for y in (0.0, h - 0.08):
        f.add("bois", boite(-l / 2 - 0.01, y, -p / 2 - 0.01, l / 2 + 0.01, y + 0.08, p / 2 + 0.01))
    f.add("noir", boite(-0.2, h * 0.45, p / 2, 0.2, h * 0.6, p / 2 + 0.005))  # marquage
    return Modele(f)


def emetteur():
    """Boîtier de laser (le rayon part du point (0, 0, 0.08))."""
    f = Forme().add("noir", boite(-0.07, -0.07, -0.06, 0.07, 0.07, 0.06))
    f.add("laser", deplacer(sphere(0.03, 8, 5), (0, 0, 0.065)))
    return Modele(f)


def panneau_alarme():
    f = Forme().add("metal", boite(-0.35, 0.0, -0.06, 0.35, 0.5, 0.06))
    f.add("ecran", boite(-0.25, 0.22, 0.06, 0.1, 0.42, 0.07))
    f.add("laser", deplacer(tourner(cylindre(0.045, 0.045, 0, 0.04, 12), "x", 90), (0.2, 0.3, 0.06)))
    f.add("noir", boite(-0.25, 0.06, 0.06, 0.25, 0.14, 0.075))
    return Modele(f)


SYMBOLES = ("ankh", "oeil", "scarabee", "ibis")


def stele(symbole):
    """Pupitre de pierre gravé d'un symbole égyptien en relief doré (visible sur le dessus incliné)."""
    f = Forme().add("pierre", boite(-0.4, 0.0, -0.3, 0.4, 0.95, 0.3))
    plaque = Forme().add("bronze", boite(-0.32, 0.0, -0.26, 0.32, 0.04, 0.26))
    if symbole == "ankh":
        plaque.add("or", deplacer(etirer(tore(0.07, 0.022, n=16, m=5), (1, 1, 1.3)), (0, 0.05, -0.1)),
                   boite(-0.025, 0.04, -0.02, 0.025, 0.07, 0.22), boite(-0.13, 0.04, -0.02, 0.13, 0.07, 0.03))
    elif symbole == "oeil":
        plaque.add("or", deplacer(etirer(tore(0.14, 0.02, n=20, m=5), (1, 1, 0.45)), (0, 0.05, 0)),
                   deplacer(sphere(0.045, 10, 6), (0, 0.05, 0)), tube([(-0.02, 0.06, 0.06), (-0.06, 0.06, 0.2)], 0.018, 5))
    elif symbole == "scarabee":
        plaque.add("or", deplacer(etirer(sphere(1, 12, 8), (0.1, 0.04, 0.14)), (0, 0.05, 0)))
        for s in (-1, 1):
            for z in (-0.08, 0.0, 0.08):
                plaque.add("or", tube([(s * 0.08, 0.06, z), (s * 0.17, 0.06, z + 0.04)], 0.012, 4))
    else:  # ibis : oiseau à long bec courbe
        plaque.add("or", deplacer(etirer(sphere(1, 12, 8), (0.07, 0.04, 0.12)), (0, 0.05, 0.02)),
                   tube([(0, 0.07, -0.08), (0.02, 0.07, -0.15), (0.07, 0.07, -0.2), (0.12, 0.06, -0.19)], 0.014, 5),
                   tube([(0, 0.06, 0.1), (-0.03, 0.06, 0.22)], 0.012, 4), tube([(0.02, 0.06, 0.1), (0.05, 0.06, 0.22)], 0.012, 4))
    f.merge(plaque.turned("x", 25).moved((0, 0.97, 0.02)))  # pupitre incliné vers le visiteur
    return Modele(f)


def brasero():
    f = Forme().add("bronze", revolution([(0.0, 0.8), (0.3, 0.85), (0.34, 1.0), (0.3, 1.02), (0.0, 0.92)], 16))
    for k in range(3):
        a = 2 * math.pi * k / 3
        f.add("bronze", tube([(0.1 * math.cos(a), 0.85, 0.1 * math.sin(a)), (0.32 * math.cos(a), 0.0, 0.32 * math.sin(a))],
                             0.025, 5))
    f.add("noir", revolution([(0.0, 0.96), (0.26, 0.97), (0.0, 1.02)], 12))
    return Modele(f)


def barriere(rayon=2.6, angle=150):
    """Barrière en demi-cercle qui tient les visiteurs à distance de la Joconde (centrée en 0, vers +z)."""
    f = Forme()
    a = np.radians(np.linspace(90 - angle / 2, 90 + angle / 2, 30))
    rail = np.column_stack([rayon * np.cos(a), np.full(30, 0.95), rayon * np.sin(a)])
    f.add("bois", tube(rail, 0.05, 6), tube(rail - (0, 0.45, 0), 0.03, 6))
    for p in rail[::4]:
        f.add("bois", tube([p - (0, 0.95, 0), p], 0.04, 6))
    return Modele(f)


def vitrine_joconde():
    """Cadre métallique de la vitrine blindée (la vitre est dessinée à part, en transparence)."""
    f = Forme()
    for x in (-0.75, 0.75):
        f.add("metal", boite(x - 0.03, 0.6, -0.05, x + 0.03, 2.9, 0.45))
    f.add("metal", boite(-0.78, 2.9, -0.05, 0.78, 2.98, 0.45), boite(-0.78, 0.55, -0.05, 0.78, 0.63, 0.45))
    return Modele(f)


def gant():
    f = Forme().add("orange", etirer(sphere(1, 12, 8), (0.07, 0.025, 0.09)))
    for i, x in enumerate((-0.045, -0.015, 0.015, 0.045)):
        f.add("orange", tube([(x, 0.0, 0.07), (x * 1.2, 0.0, 0.14 + 0.01 * (i in (1, 2)))], 0.014, 5))
    f.add("orange", tube([(0.06, 0.0, 0.02), (0.11, 0.0, 0.07)], 0.015, 5))
    f.add("noir", deplacer(etirer(cylindre(0.075, 0.075, 0, 0.03, 12), (1, 1, 0.5)), (0, -0.015, -0.1)))
    return Modele(f)


def badge():
    f = Forme().add("blanc", boite(-0.045, 0, -0.065, 0.045, 0.008, 0.065))
    f.add("bache", boite(-0.045, 0.008, 0.03, 0.045, 0.01, 0.065))
    f.add("peau", boite(-0.03, 0.008, -0.04, 0.0, 0.01, 0.0))
    f.add("noir", boite(0.005, 0.008, -0.03, 0.035, 0.01, -0.025), boite(0.005, 0.008, -0.015, 0.035, 0.01, -0.01))
    return Modele(f)


def camera_cachee():
    f = Forme().add("noir", boite(-0.05, -0.04, -0.06, 0.05, 0.04, 0.06))
    f.add("noir", deplacer(tourner(cylindre(0.025, 0.03, 0, 0.05, 12), "x", 90), (0, 0, 0.06)))
    f.add("laser", deplacer(sphere(0.008, 6, 4), (0.035, 0.025, 0.06)))
    return Modele(f)


def carnet():
    f = Forme().add("cuir", boite(-0.1, 0, -0.14, 0.1, 0.012, 0.14))
    f.add("papier", boite(-0.095, 0.012, -0.135, 0.095, 0.03, 0.135))
    f.add("cuir", boite(-0.1, 0.03, -0.14, 0.1, 0.038, 0.14))
    f.add("velours", boite(0.02, 0.038, -0.14, 0.03, 0.04, 0.1))
    return Modele(f)


def plan():
    f = Forme().add("papier", boite(-0.25, 0, -0.18, 0.25, 0.004, 0.18))
    f.add("velours", tube([(-0.1, 0.006, -0.05), (0.05, 0.006, 0.02), (0.15, 0.006, -0.08)], 0.004, 4))
    f.add("noir", boite(-0.2, 0.004, -0.14, 0.2, 0.006, -0.13), boite(-0.2, 0.004, 0.12, 0.2, 0.006, 0.13))
    return Modele(f)


def ruban():
    return Modele(Forme().add("gris", boite(-0.12, -0.02, 0, 0.12, 0.02, 0.004), boite(-0.02, -0.1, 0, 0.02, 0.1, 0.004)))


def empreintes():
    """Traces de chaussures de chantier boueuses, qui mènent vers la porte de service (vers +x)."""
    f = Forme()
    for k in range(7):
        x, z = k * 0.45, (0.12 if k % 2 else -0.12)
        f.add("boue", deplacer(etirer(cylindre(1, 1, 0, 0.004, 12), (0.14, 1, 0.06)), (x, 0.003, z)))
        f.add("boue", deplacer(etirer(cylindre(1, 1, 0, 0.004, 10), (0.06, 1, 0.055)), (x - 0.19, 0.003, z)))
    return Modele(f)


def cadre_tableau(largeur, hauteur):
    """Petit tableau posé sur un chevalet (celui que le voleur emporte)."""
    f = Forme().add("or", boite(-largeur / 2 - 0.05, -hauteur / 2 - 0.05, -0.03, largeur / 2 + 0.05, hauteur / 2 + 0.05, 0.0))
    return Modele(f)


# ---------------------------------------------------------------------------
# Catalogue : chaque modèle n'est construit qu'une fois
# ---------------------------------------------------------------------------

FABRIQUES = {
    "socle": socle, "banc": banc, "poteau": poteau, "echafaudage": echafaudage, "chariot": chariot, "caisse": caisse,
    "emetteur": emetteur, "panneau_alarme": panneau_alarme, "brasero": brasero, "barriere": barriere,
    "vitrine_joconde": vitrine_joconde, "gant": gant, "badge": badge, "camera": camera_cachee, "carnet": carnet,
    "plan": plan, "ruban": ruban, "empreintes": empreintes, "couronne": couronne, "victoire": victoire,
    "sphinx": sphinx, "cariatide": cariatide, "main_victoire": main_victoire,
}
_CACHE = {}


def modele(nom):
    """modele("victoire"), modele("humain:gardien"), modele("joyau:3"), modele("statue:2"), modele("stele:ibis")..."""
    if nom not in _CACHE:
        base, _, parametre = nom.partition(":")
        if base == "humain":
            _CACHE[nom] = humain(parametre)
        elif base == "joyau":
            _CACHE[nom] = joyau(int(parametre))
        elif base == "statue":
            _CACHE[nom] = statue(int(parametre), bras=int(parametre) % 3 != 2)
        elif base == "buste":
            _CACHE[nom] = buste(int(parametre))
        elif base == "stele":
            _CACHE[nom] = stele(parametre)
        else:
            _CACHE[nom] = FABRIQUES[base]()
    return _CACHE[nom]

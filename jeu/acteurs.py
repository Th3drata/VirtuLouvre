"""Le joueur et les autres personnages (gardiens, voleurs, guetteurs, chef du Cercle, visiteurs)."""

import math
import random

import numpy as np
from OpenGL.GL import *

from .base import BODY, CROUCH_BODY, CROUCH_EYE, EYE, angle_vers, clamp, ecart_angle
from .modeles import modele


class Player:
    """Caméra à la première personne : marche, course (avec endurance), saut, accroupissement, vol.
    `pos` est la position des pieds ; les yeux sont au-dessus."""

    WALK, RUN, SNEAK, FLY = 2.6, 5.0, 1.3, 4.5  # vitesses en unités par seconde
    GRAVITY, JUMP = 15.0, 4.8

    def __init__(self, x, y, z, yaw=-90.0):
        self.pos = np.array([x, y, z], dtype=float)
        self.vel = np.zeros(3)
        self.yaw, self.pitch = yaw, 0.0
        self.flying = self.crouch = self.walking = self.sprinting = self.want_jump = False
        self.on_ground = True
        self.stamina, self.epuise = 1.0, False
        self.hauteur_yeux = EYE
        self.oeil_y = y + EYE  # hauteur des yeux lissée (pas de saccade dans les escaliers)
        self.bob = 0.0

    def front(self):
        lacet, tangage = math.radians(self.yaw), math.radians(self.pitch)
        return np.array([math.cos(lacet) * math.cos(tangage), math.sin(tangage), math.sin(lacet) * math.cos(tangage)])

    def eye(self):
        return np.array((self.pos[0], self.oeil_y + math.sin(self.bob) * 0.035, self.pos[2]))

    def corps(self):
        """Segment des pieds au sommet de la tête (pour les lasers)."""
        return self.pos + (0.0, 0.05, 0.0), self.pos + (0.0, CROUCH_BODY if self.crouch else BODY, 0.0)

    def look(self, dx, dy, sensibilite):
        self.yaw = (self.yaw + dx * sensibilite) % 360
        self.pitch = max(-89.0, min(89.0, self.pitch - dy * sensibilite))

    def update(self, dt, held, salle, can_fly=False, endurance=False):
        """Avance le joueur de `dt` secondes ; `held(action)` dit si une touche est enfoncée."""
        if not can_fly:
            self.flying = False
        self.crouch = held("crouch") and not self.flying
        lacet = math.radians(self.yaw)
        fx, fz = math.cos(lacet), math.sin(lacet)
        avant, cote = held("forward") - held("back"), held("right") - held("left")
        dx, dz = avant * fx - cote * fz, avant * fz + cote * fx
        n = math.hypot(dx, dz)
        if self.stamina <= 0.0:
            self.epuise = True  # à bout de souffle : il faut récupérer un peu avant de recourir
        elif self.stamina > 0.35:
            self.epuise = False
        self.sprinting = held("sprint") and not self.crouch and n > 0 and not (endurance and self.epuise)
        vitesse = self.SNEAK if self.crouch else self.RUN if self.sprinting else self.WALK
        if self.flying:
            vitesse *= 1.8
        if endurance:
            self.stamina = clamp(self.stamina + (-dt / 6.0 if self.sprinting else dt / 4.0), 0.0, 1.0)
        cible = (dx / n * vitesse, dz / n * vitesse) if n else (0.0, 0.0)
        douceur = min(1.0, dt * 12)  # accélération progressive
        self.vel[0] += (cible[0] - self.vel[0]) * douceur
        self.vel[2] += (cible[1] - self.vel[2]) * douceur
        x, z = self.pos[0], self.pos[2]
        mx, mz = self.vel[0] * dt, self.vel[2] * dt
        if self.flying or not salle.libre(x, z, self.pos[1]):  # en vol (ou coincé) : on passe partout
            x, z = x + mx, z + mz
        else:  # un axe après l'autre : on glisse le long des murs au lieu de s'y coller
            if salle.libre(x + mx, z, self.pos[1]):
                x += mx
            if salle.libre(x, z + mz, self.pos[1]):
                z += mz
        self.pos[0], self.pos[2] = x, z

        sol = salle.sol_sous(x, z)
        if self.flying:
            self.pos[1] = max(sol, self.pos[1] + (held("jump") - held("crouch")) * self.FLY * dt)
            self.on_ground = False
        else:
            if self.want_jump and self.on_ground and not self.crouch:
                self.vel[1] = self.JUMP
                self.on_ground = False
            self.vel[1] -= self.GRAVITY * dt
            self.pos[1] += self.vel[1] * dt
            if self.pos[1] <= sol:
                self.pos[1], self.vel[1], self.on_ground = sol, 0.0, True
            elif self.on_ground and self.pos[1] - sol < 0.5 and self.vel[1] <= 0:
                self.pos[1], self.vel[1] = sol, 0.0  # on descend les marches au lieu de tomber de chacune
            else:
                self.on_ground = False
        self.want_jump = False
        self.hauteur_yeux += ((CROUCH_EYE if self.crouch else EYE) - self.hauteur_yeux) * min(1.0, dt * 10)
        cible_y = self.pos[1] + self.hauteur_yeux
        self.oeil_y = self.oeil_y + (cible_y - self.oeil_y) * min(1.0, dt * 14) if self.on_ground else cible_y
        self.walking = self.on_ground and not self.flying and n > 0
        if self.walking:
            self.bob += dt * vitesse * 3.2


def _t(v):
    m = np.identity(4)
    m[:3, 3] = v
    return m


def _r(axe, degres):
    """Rotation 4 × 4 comme glRotatef(degres, *axe) pour un axe x, y ou z."""
    c, s = math.cos(math.radians(degres)), math.sin(math.radians(degres))
    i, j = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axe]
    m = np.identity(4)
    m[i, i] = m[j, j] = c
    m[i, j], m[j, i] = -s, s
    return m


POSES_BRAS = {  # pose : (épaule : balancé avant/arrière, écart ; coude : pliure, torsion) pour le bras gauche
    "mains_en_l_air": ((-165, 20), (-20, 0)),
    "bras_croises": ((-14, 8), (-100, -78)),
    "mains_dos": ((32, 10), (-80, -88)),
    "photo": ((-72, 6), (-68, -32)),
    "assis": ((-28, 6), (-48, 0)),
    "porte": ((-30, 16), (-62, 0)),  # il porte un tableau contre lui
}


class PNJ:
    """Personnage non joueur : se déplace, patrouille, regarde autour de lui, tient parfois une lampe.
    Il est articulé (cuisses, genoux, bras, coudes, tête) et prend des poses : "normal", "course",
    "mains_en_l_air", "bras_croises", "mains_dos", "photo", "telephone", "pointe", "assis"."""

    def __init__(self, tenue, x, z, yaw=0.0, salle=None, vitesse=1.3, nom_modele=None):
        self.modele = modele(nom_modele or "humain:" + tenue)
        self.os = self.modele.infos["articulations"]
        self.pos = np.array((x, salle.sol_sous(x, z) if salle else 0.0, z), float)
        self.yaw, self.vitesse = yaw, vitesse
        self.phase = self.ampleur = 0.0
        self.pose = "normal"
        self.route, self.index, self.attente, self.regard = [], 0, 0.0, yaw
        self.t = random.uniform(0, 100)
        self.tete = [0.0, 0.0]  # lacet et tangage de la tête par rapport au corps
        self.porte = None  # dessine ce qu'il tient contre lui (dans le repère du buste)
        self.lampe_allumee = self.modele.infos.get("lampe", False)
        self.alerte = 0.0  # 0 : ne voit rien ; 1 : a repéré le joueur
        self.distrait = 0.0  # temps restant à regarder vers un bruit

    def oeil(self):
        return self.pos + (0.0, 1.55 * self.modele.infos["taille"], 0.0)

    def devant(self):
        a = math.radians(self.yaw)
        return np.array((math.cos(a), 0.0, math.sin(a)))

    # --- Squelette ---

    def angles(self):
        """Angles des articulations pour l'image en cours (marche, course, poses, respiration)."""
        a, s, t = min(self.ampleur, 1.4), math.sin(self.phase), self.t
        cuisse, genou = 30 * a * s, 5 + 60 * a * max(0.0, math.cos(self.phase)) ** 1.5
        cuisse2, genou2 = -cuisse, 5 + 60 * a * max(0.0, -math.cos(self.phase)) ** 1.5
        course = max(0.0, min(1.0, (a - 0.6) / 0.6))
        balance = 24 * a * s
        repos = 2.5 * math.sin(t * 1.6) * (1 - min(1.0, a * 2))  # respiration, à l'arrêt
        coude = -10 - 70 * course + repos
        A = {"penche": 9 * course, "y": -self.os["bassin"][1] * (1 - math.cos(math.radians(cuisse))),
             "cuisse_g": -cuisse, "genou_g": genou, "cuisse_d": -cuisse2, "genou_d": genou2,
             "epaule_g": (balance * 1.3 + repos, 6), "coude_g": (coude, 0), "epaule_d": (-balance * 1.3 - repos, 6),
             "coude_d": (coude, 0), "tete": (self.tete[0] + 6 * math.sin(t * 0.37), self.tete[1] + 2 * math.sin(t * 0.23))}
        pose = self.pose
        if pose == "assis":
            A.update(y=0.49 - self.os["bassin"][1], cuisse_g=-88, genou_g=86, cuisse_d=-84, genou_d=90, penche=-4)
        if pose in POSES_BRAS:
            (e, ecart), (pli, torsion) = POSES_BRAS[pose]
            A["epaule_g"], A["coude_g"] = (e + repos, ecart), (pli, torsion)
            A["epaule_d"], A["coude_d"] = (e - repos, ecart), (pli, torsion)
        elif pose == "telephone":
            A["epaule_d"], A["coude_d"], A["tete"] = (-22, 6), (-82, -20), (self.tete[0] * 0.3, 24)
        elif pose == "pointe":
            A["epaule_d"], A["coude_d"] = (-128 + 4 * math.sin(t * 2), 14), (-8, 0)
        if self.modele.infos.get("lampe") and pose != "mains_en_l_air":
            A["epaule_d"], A["coude_d"] = (-40 + balance * 0.12, 4), (-38, 0)  # la lampe éclaire devant lui
        if pose == "photo":
            A["tete"] = (0.0, -6.0)
        return A

    def _chaine(self, A, partie):
        """Transformations (comme les appels OpenGL) qui placent une partie du corps."""
        o = self.os
        base = [("t", self.pos), ("r", "y", 90 - self.yaw), ("t", (0.0, A["y"], 0.0))]
        buste = base + [("p", o["bassin"], [("x", A["penche"])])]
        cote = partie[-1]
        signe = 1 if cote == "g" else -1
        if partie.startswith(("cuisse", "jambe")):
            chaine = base + [("p", o["hanche_" + cote], [("x", A["cuisse_" + cote])])]
            return chaine + [("p", o["genou_" + cote], [("x", A["genou_" + cote])])] if partie.startswith("jambe") else chaine
        if partie.startswith(("bras", "avantbras")):
            (e, ecart), (pli, torsion) = A["epaule_" + cote], A["coude_" + cote]
            chaine = buste + [("p", o["epaule_" + cote], [("z", signe * ecart), ("x", e)])]
            if partie.startswith("avantbras"):
                chaine += [("p", o["coude_" + cote], [("y", signe * torsion), ("x", pli)])]
            return chaine
        if partie == "tete":
            return buste + [("p", o["cou"], [("y", A["tete"][0]), ("x", A["tete"][1])])]
        return buste

    @staticmethod
    def _gl(chaine):
        for op in chaine:
            if op[0] == "t":
                glTranslatef(*op[1])
            elif op[0] == "r":
                glRotatef(op[2], *{"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[op[1]])
            else:
                glTranslatef(*op[1])
                for axe, degres in op[2]:
                    glRotatef(degres, *{"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axe])
                glTranslatef(*-np.asarray(op[1]))

    @staticmethod
    def _matrice(chaine):
        m = np.identity(4)
        for op in chaine:
            if op[0] == "t":
                m = m @ _t(op[1])
            elif op[0] == "r":
                m = m @ _r(op[1], op[2])
            else:
                m = m @ _t(op[1])
                for axe, degres in op[2]:
                    m = m @ _r(axe, degres)
                m = m @ _t(-np.asarray(op[1]))
        return m

    def lampe(self):
        """(position, direction) de la lampe torche, qui suit l'avant-bras droit."""
        m = self._matrice(self._chaine(self.angles(), "avantbras_d"))
        return (m @ (*self.modele.infos["bout_lampe"], 1.0))[:3], m[:3, :3] @ (0.0, -1.0, 0.0)

    # --- Déplacements ---

    def tourner_vers(self, lacet, dt, vitesse=200.0):
        ecart = ecart_angle(self.yaw, lacet)
        self.yaw += clamp(ecart, -vitesse * dt, vitesse * dt)

    def avancer_vers(self, x, z, dt, salle, vitesse=None):
        """Marche vers (x, z) ; renvoie True une fois arrivé."""
        vitesse = self.vitesse if vitesse is None else vitesse
        self.t += dt
        dx, dz = x - self.pos[0], z - self.pos[2]
        d = math.hypot(dx, dz)
        if d < 0.05:
            self.ralentir(dt)
            return True
        self.tourner_vers(angle_vers(dx, dz), dt, 260)
        pas = min(d, vitesse * dt)
        self.pos[0] += dx / d * pas
        self.pos[2] += dz / d * pas
        if salle:
            self.pos[1] += (salle.sol_sous(self.pos[0], self.pos[2]) - self.pos[1]) * min(1.0, dt * 12)
        self.ampleur += (min(1.3, vitesse / 3.4) - self.ampleur) * min(1.0, dt * 6)
        self.phase += dt * vitesse * 3.3 / max(0.8, self.modele.infos["taille"])
        return d <= pas + 1e-6

    def ralentir(self, dt):
        """À l'arrêt : les jambes reviennent doucement à la verticale."""
        self.ampleur = max(0.0, self.ampleur - dt * 4)

    def patrouiller(self, dt, salle):
        """Suit sa ronde : [(x, z, pause en secondes, lacet du regard pendant la pause ou None), ...]."""
        self.t += dt
        if self.distrait > 0:  # un bruit : il se tourne et regarde
            self.distrait -= dt
            self.tourner_vers(self.regard, dt, 160)
            self.ralentir(dt)
            return
        if not self.route:
            self.ralentir(dt)
            return
        x, z, pause, regard = self.route[self.index]
        if self.attente > 0:
            self.attente -= dt
            self.tourner_vers(self.regard + 45 * math.sin(self.t * 1.3), dt, 90)  # il regarde autour de lui
            self.ralentir(dt)
            if self.attente <= 0:
                self.index = (self.index + 1) % len(self.route)
        elif self.avancer_vers(x, z, dt, salle):
            if pause > 0:
                self.attente = pause
                self.regard = self.yaw if regard is None else regard
            else:  # point de passage : on continue directement
                self.index = (self.index + 1) % len(self.route)

    def entendre(self, point):
        """Se retourne vers un bruit (le joueur qui court)."""
        self.regard = angle_vers(point[0] - self.pos[0], point[2] - self.pos[2])
        self.distrait = 2.5

    def voit(self, point, salle, portee, demi_angle=33.0):
        """Le point est-il dans son champ de vision (portée, angle) et à découvert ?"""
        oeil = self.oeil()
        dx, dz = point[0] - oeil[0], point[2] - oeil[2]
        distance = math.hypot(dx, dz)
        if distance > portee:
            return False
        if distance > 1.0 and abs(ecart_angle(self.yaw, angle_vers(dx, dz))) > demi_angle:
            return False
        return salle.vue_libre(oeil, point)

    def regarder(self, point, dt):
        """Tourne la tête vers un point (s'il est devant lui), sinon la ramène droit devant."""
        lacet, tangage = 0.0, 0.0
        if point is not None:
            oeil = self.oeil()
            dx, dy, dz = point[0] - oeil[0], point[1] - oeil[1], point[2] - oeil[2]
            ecart = ecart_angle(self.yaw, angle_vers(dx, dz))
            if abs(ecart) < 100:
                lacet = -clamp(ecart, -70, 70)
                tangage = clamp(-math.degrees(math.atan2(dy, math.hypot(dx, dz))), -25, 30)
        k = min(1.0, dt * 4)
        self.tete[0] += (lacet - self.tete[0]) * k
        self.tete[1] += (tangage - self.tete[1]) * k

    def draw(self):
        A, m = self.angles(), self.modele
        for partie in m.parties:
            glPushMatrix()
            self._gl(self._chaine(A, partie))
            m.draw(partie)
            if partie == "corps" and self.porte:
                self.porte()
            glPopMatrix()


class Foule:
    """Les figurants d'une salle : visiteurs qui vont d'une œuvre à l'autre, gardien sur sa chaise,
    groupe autour d'une guide, attroupement devant la Joconde..."""

    def __init__(self, salle):
        self.salle, self.gens, self.chaises = salle, [], []
        self.places = []  # (x, z, lacet, point regardé) : devant chaque œuvre

    def peupler(self, n, graine=0):
        """Remplit la salle pour la visite libre (ou le menu)."""
        s, h = self.salle, random.Random(graine)
        for c, normale, largeur, hauteur, *_ in s.oeuvres:
            recul = 1.5 + 0.35 * max(largeur, hauteur)
            for decalage in ((-0.35, 0.35) if largeur > 2.5 else (0.0,)):
                x = c[0] + normale[0] * recul + normale[2] * decalage * largeur
                z = c[2] + normale[2] * recul - normale[0] * decalage * largeur
                self.places.append((x, z, angle_vers(-normale[0], -normale[2]), np.array(c, float)))
        for x, z, cible in s.points_vue:
            self.places.append((x, z, angle_vers(cible[0] - x, cible[2] - z), np.array(cible, float)))
        self.places = [p for p in self.places if s.libre(p[0], p[1], s.sol_sous(p[0], p[1]))]
        graines = h.sample(range(40), min(40, n + 12))
        if s.chaise:
            x, z, lacet = s.chaise
            gardien = PNJ("", x, z, lacet, s, nom_modele=h.choice(["humain:gardien", "humain:gardienne"]))
            gardien.pose, gardien.comportement = "assis", "assis"
            self.gens.append(gardien)
            self.chaises.append((x, s.sol_sous(x, z), z, lacet))
        if s.groupe:  # une guide et son groupe devant un tableau
            x, z, lacet, cible = s.groupe
            guide = PNJ("", x, z, lacet - 60, s, nom_modele="humain:guide")
            guide.comportement, guide.cible = "guide", np.array(cible, float)
            self.gens.append(guide)
            for k in range(5):
                a = math.radians(lacet + 180 + (k - 2) * 26)
                px, pz = x + math.cos(a) * 1.9 - math.cos(math.radians(lacet)) * 0.8, z + math.sin(a) * 1.9 - math.sin(math.radians(lacet)) * 0.8
                if s.libre(px, pz, s.sol_sous(px, pz)):
                    p = PNJ("", px, pz, angle_vers(x - px, z - pz), s, nom_modele=f"visiteur:{graines.pop()}")
                    p.comportement, p.cible = "ecoute", guide
                    self.gens.append(p)
        if s.attroupement:  # la foule devant la Joconde, téléphones levés
            cible, positions = s.attroupement
            for x, z in positions:
                p = PNJ("", x, z, angle_vers(cible[0] - x, cible[2] - z), s, nom_modele=f"visiteur:{graines.pop()}")
                p.comportement, p.cible = "admire", np.array(cible, float)
                self.gens.append(p)
        for _ in range(min(n, len(self.places))):
            x, z, lacet, cible = h.choice(self.places)
            p = PNJ("", x, z, lacet, s, vitesse=h.uniform(0.9, 1.25), nom_modele=f"visiteur:{graines.pop()}")
            p.comportement, p.cible, p.chrono, p.but = "visite", cible, h.uniform(0, 8), None
            self.gens.append(p)
        return self

    def ajouter(self, p, comportement="reste", cible=None):
        p.comportement, p.cible = comportement, cible
        self.gens.append(p)
        return p

    def chemin_libre(self, a, b):
        s = self.salle
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.3))
        pied = s.sol_sous(*a)
        for k in range(1, n + 1):
            x, z = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
            if not s.libre(x, z, pied):
                return False
            pied = s.sol_sous(x, z)
        return True

    def update(self, dt, joueur=None, audio=None):
        s = self.salle
        oeil = joueur.eye() if joueur else None
        occupees = {id(p.but) for p in self.gens if getattr(p, "but", None)}
        for p in self.gens:
            p.t += dt
            proche = oeil is not None and math.hypot(oeil[0] - p.pos[0], oeil[2] - p.pos[2]) < 3.0
            c = p.comportement
            if c == "visite":
                if p.but is not None:  # il marche vers l'œuvre suivante
                    x, z, lacet, cible = p.but
                    if p.avancer_vers(x, z, dt, s):
                        p.but, p.cible, p.chrono = None, cible, random.uniform(5, 14)
                        p.regard = lacet
                        p.pose = random.choice(["normal", "normal", "mains_dos", "bras_croises"] +
                                               ["photo", "telephone"] * (p.modele.infos["accessoire"] == "telephone"))
                    p.regarder(oeil if proche else None, dt)
                else:  # il regarde l'œuvre, puis choisit une autre œuvre pas trop loin
                    p.tourner_vers(p.regard, dt, 120)
                    p.ralentir(dt)
                    p.regarder(oeil if proche and random.random() < 0.5 else p.cible, dt)
                    p.chrono -= dt
                    if p.chrono <= 0:
                        a = (p.pos[0], p.pos[2])
                        options = sorted((q for q in self.places if id(q) not in occupees and
                                          0.5 < math.hypot(q[0] - a[0], q[1] - a[1]) < 14),
                                         key=lambda q: random.random())[:6]
                        but = next((q for q in options if self.chemin_libre(a, (q[0], q[1]))), None)
                        if but:
                            p.but, p.pose = but, "normal"
                            occupees.add(id(but))
                        p.chrono = random.uniform(2, 5)
            elif c == "assis":
                p.regarder(oeil if proche else p.pos + (math.cos(p.t * 0.2) * 3 + p.devant()[0] * 4, 1.2,
                                                           math.sin(p.t * 0.2) * 3 + p.devant()[2] * 4), dt)
            elif c == "guide":  # elle montre le tableau, puis se tourne vers son groupe
                montre = (p.t % 9) < 4
                p.pose = "pointe" if montre else "normal"
                p.regarder(p.cible if montre else (oeil if proche else None), dt)
            elif c == "ecoute":
                p.regarder(p.cible.oeil() if (p.t % 11) < 6 else getattr(p.cible, "cible", None), dt)
            elif c == "admire":
                p.chrono = getattr(p, "chrono", 0.0) - dt
                if p.chrono <= 0:
                    p.pose, p.chrono = random.choice(["photo", "photo", "normal", "telephone", "bras_croises"]), random.uniform(4, 10)
                p.regarder(p.cible if p.pose != "telephone" else None, dt)
            else:
                p.regarder(oeil if proche else p.cible, dt)
            if audio and oeil is not None and p.ampleur > 0.2:  # bruits de pas des visiteurs
                foulee = int(p.phase / math.pi)
                if foulee != getattr(p, "foulee", foulee):
                    audio.spatial("pas_visiteur", p.pos, joueur.pos, joueur.yaw, 9.0)
                p.foulee = foulee
            if joueur is not None and not joueur.flying:  # on ne traverse pas les gens
                dx, dz = joueur.pos[0] - p.pos[0], joueur.pos[2] - p.pos[2]
                d = math.hypot(dx, dz)
                if 1e-6 < d < 0.55 and abs(joueur.pos[1] - p.pos[1]) < 1.0:
                    x, z = p.pos[0] + dx / d * 0.55, p.pos[2] + dz / d * 0.55
                    if s.libre(x, z, joueur.pos[1]):
                        joueur.pos[0], joueur.pos[2] = x, z

    def draw(self):
        for x, y, z, lacet in self.chaises:
            glPushMatrix()
            glTranslatef(x, y, z)
            glRotatef(90 - lacet, 0, 1, 0)
            modele("chaise").draw()
            glPopMatrix()
        for p in self.gens:
            p.draw()

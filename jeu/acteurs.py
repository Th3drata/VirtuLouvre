"""Le joueur et les autres personnages (gardiens, voleurs, guetteurs, chef du Cercle)."""

import math

import numpy as np
from OpenGL.GL import *

from .base import BODY, CROUCH_BODY, CROUCH_EYE, EYE, angle_vers, clamp, ecart_angle
from .modeles import EPAULE, HANCHE, LAMPE, modele


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


class PNJ:
    """Personnage non joueur : se déplace, patrouille, regarde autour de lui, tient parfois une lampe."""

    def __init__(self, tenue, x, z, yaw=0.0, salle=None, vitesse=1.3):
        self.modele = modele("humain:" + tenue)
        self.pos = np.array((x, salle.sol_sous(x, z) if salle else 0.0, z), float)
        self.yaw, self.vitesse = yaw, vitesse
        self.phase = self.ampleur = 0.0
        self.pose = "normal"  # "normal", "course" ou "mains_en_l_air"
        self.route, self.index, self.attente, self.regard = [], 0, 0.0, yaw
        self.t = 0.0
        self.lampe_allumee = self.modele.infos.get("lampe", False)
        self.alerte = 0.0  # 0 : ne voit rien ; 1 : a repéré le joueur
        self.distrait = 0.0  # temps restant à regarder vers un bruit

    def oeil(self):
        return self.pos + (0.0, 1.55, 0.0)

    def devant(self):
        a = math.radians(self.yaw)
        return np.array((math.cos(a), 0.0, math.sin(a)))

    def _vers_monde(self, local):
        """Point du repère du personnage (qui regarde vers +z) -> monde."""
        t = math.radians(90 - self.yaw)
        x, y, z = local
        return self.pos + np.array((x * math.cos(t) + z * math.sin(t), y, -x * math.sin(t) + z * math.cos(t)))

    def lampe(self):
        """(position, direction) de la lampe torche, légèrement pointée vers le sol."""
        a, p = math.radians(self.yaw), math.radians(-12)
        return self._vers_monde(LAMPE), np.array((math.cos(a) * math.cos(p), math.sin(p), math.sin(a) * math.cos(p)))

    def tourner_vers(self, lacet, dt, vitesse=200.0):
        ecart = ecart_angle(self.yaw, lacet)
        self.yaw += clamp(ecart, -vitesse * dt, vitesse * dt)

    def avancer_vers(self, x, z, dt, salle, vitesse=None):
        """Marche vers (x, z) ; renvoie True une fois arrivé."""
        vitesse = self.vitesse if vitesse is None else vitesse
        dx, dz = x - self.pos[0], z - self.pos[2]
        d = math.hypot(dx, dz)
        if d < 0.05:
            self.ampleur = max(0.0, self.ampleur - dt * 4)
            return True
        self.tourner_vers(angle_vers(dx, dz), dt, 260)
        pas = min(d, vitesse * dt)
        self.pos[0] += dx / d * pas
        self.pos[2] += dz / d * pas
        if salle:
            self.pos[1] += (salle.sol_sous(self.pos[0], self.pos[2]) - self.pos[1]) * min(1.0, dt * 12)
        self.ampleur += (min(1.3, vitesse / 2.6) - self.ampleur) * min(1.0, dt * 6)
        self.phase += dt * vitesse * 3.3
        return d <= pas + 1e-6

    def patrouiller(self, dt, salle):
        """Suit sa ronde : [(x, z, pause en secondes, lacet du regard pendant la pause ou None), ...]."""
        self.t += dt
        if self.distrait > 0:  # un bruit : il se tourne et regarde
            self.distrait -= dt
            self.tourner_vers(self.regard, dt, 160)
            self.ampleur = max(0.0, self.ampleur - dt * 4)
            return
        if not self.route:
            return
        x, z, pause, regard = self.route[self.index]
        if self.attente > 0:
            self.attente -= dt
            self.tourner_vers(self.regard + 45 * math.sin(self.t * 1.3), dt, 90)  # il regarde autour de lui
            self.ampleur = max(0.0, self.ampleur - dt * 4)
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

    def draw(self):
        m = self.modele
        glPushMatrix()
        glTranslatef(*self.pos)
        glRotatef(90 - self.yaw, 0, 1, 0)
        glTranslatef(0, abs(math.sin(self.phase)) * 0.035 * self.ampleur, 0)
        m.draw("corps")
        balance = math.sin(self.phase) * 32 * self.ampleur
        for partie, x, angle in (("jambe_g", 0.09, balance), ("jambe_d", -0.09, -balance)):
            _articuler(m, partie, (x, HANCHE, 0), angle)
        for partie, x, signe in (("bras_g", 0.235, -1), ("bras_d", -0.235, 1)):
            if self.pose == "mains_en_l_air":
                angle = -165
            elif partie == "bras_d" and m.infos.get("lampe"):
                angle = 0  # le bras qui tient la lampe reste tendu
            else:
                angle = signe * balance * (1.4 if self.pose == "course" else 0.8)
            _articuler(m, partie, (x, EPAULE, 0), angle)
        glPopMatrix()


def _articuler(m, partie, pivot, angle):
    glPushMatrix()
    glTranslatef(*pivot)
    glRotatef(angle, 1, 0, 0)
    glTranslatef(-pivot[0], -pivot[1], -pivot[2])
    m.draw(partie)
    glPopMatrix()

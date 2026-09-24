"""Interface 2D : dessinée avec pygame sur une surface, plaquée en texture par-dessus la 3D."""

import math

import numpy as np
import pygame
from OpenGL.GL import *

from .base import GOLD, IVORY, SERIF_FONT, chemin, wrap


class UI:
    """Les coordonnées sont « virtuelles » : 720 de haut, la largeur suit le format de la fenêtre.
    Tout est mis à l'échelle au moment de dessiner, donc le texte reste net à toute résolution.
    C'est une interface « immédiate » : button() dessine le bouton ET dit s'il vient d'être cliqué."""

    H = 720

    def __init__(self):
        self.texture = glGenTextures(1)
        self.fonts, self.cache, self.icons = {}, {}, {}
        self.window = None
        self.click = None  # position du clic de cette image, None sinon
        self.wheel = 0  # molette de la souris
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

    def to_pixels(self, r):
        """Rectangle virtuel -> rectangle en pixels de la fenêtre (origine en haut à gauche)."""
        sx, sy = self.window[0] / self.W, self.window[1] / self.H
        return round(r[0] * sx), round(r[1] * sy), round(r[2] * sx), round(r[3] * sy)

    def px(self, r):
        return pygame.Rect(round(r[0] * self.k), round(r[1] * self.k), round(r[2] * self.k), round(r[3] * self.k))

    def font(self, taille, serif=False):
        if (taille, serif) not in self.fonts:
            self.fonts[taille, serif] = pygame.font.Font(SERIF_FONT if serif else None, max(8, round(taille * self.k)))
        return self.fonts[taille, serif]

    def largeur_texte(self, texte, taille, serif=False):
        return self.font(taille, serif).size(texte)[0] / self.k

    def text(self, texte, taille, pos, couleur=IVORY, ancre="center", serif=False, alpha=255):
        image = self.font(taille, serif).render(texte, True, couleur)
        if alpha < 255:
            image.set_alpha(max(0, alpha))
        r = image.get_rect(**{ancre: (round(pos[0] * self.k), round(pos[1] * self.k))})
        self.surface.blit(image, r)
        return pygame.FRect(r.x / self.k, r.y / self.k, r.w / self.k, r.h / self.k)

    def paragraph(self, texte, taille, pos, largeur, couleur=IVORY, interligne=1.35, ancre="midtop", serif=False, alpha=255):
        """Texte sur plusieurs lignes, coupé pour tenir dans `largeur` ; renvoie l'ordonnée sous le texte."""
        x, y = pos
        pas = taille * interligne
        for ligne in wrap(texte, largeur, lambda l: self.largeur_texte(l, taille, serif)):
            if ligne:
                self.text(ligne, taille, (x, y), couleur, ancre, serif, alpha)
            y += pas
        return y

    def rect(self, couleur, r, rayon=0, epaisseur=0):
        pr = self.px(r)
        epaisseur = max(1, round(epaisseur * self.k)) if epaisseur else 0
        if len(couleur) == 4:  # semi-transparent : on passe par une surface pour mélanger les couleurs
            calque = pygame.Surface(pr.size, pygame.SRCALPHA)
            pygame.draw.rect(calque, couleur, calque.get_rect(), epaisseur, round(rayon * self.k))
            self.surface.blit(calque, pr)
        else:
            pygame.draw.rect(self.surface, couleur, pr, epaisseur, round(rayon * self.k))

    def panel(self, r, alpha=225):
        """Panneau sombre à bord doré (briefings, fiches d'indices...)."""
        self.rect((10, 10, 16, alpha), r, rayon=18)
        self.rect(GOLD, r, rayon=18, epaisseur=1)

    def line(self, couleur, a, b, epaisseur=1):
        pygame.draw.line(self.surface, couleur, (round(a[0] * self.k), round(a[1] * self.k)),
                         (round(b[0] * self.k), round(b[1] * self.k)), max(1, round(epaisseur * self.k)))

    def polygon(self, couleur, points, epaisseur=0):
        pygame.draw.polygon(self.surface, couleur, [(x * self.k, y * self.k) for x, y in points],
                            max(1, round(epaisseur * self.k)) if epaisseur else 0)

    def circle(self, couleur, centre, rayon, epaisseur=0):
        pygame.draw.circle(self.surface, couleur, (round(centre[0] * self.k), round(centre[1] * self.k)),
                           max(1, round(rayon * self.k)), max(1, round(epaisseur * self.k)) if epaisseur else 0)

    def diamond(self, centre, r, couleur, plein=True):
        x, y = centre
        self.polygon(couleur, [(x, y - r), (x + r * 0.8, y), (x, y + r), (x - r * 0.8, y)], 0 if plein else 1.5)

    def star(self, centre, r, plein=True, couleur=GOLD):
        points = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            points.append((centre[0] + rr * math.cos(a), centre[1] + rr * math.sin(a)))
        self.polygon(couleur if plein else (90, 84, 74), points, 0 if plein else 1.5)

    def stars(self, centre, nombre, taille=14, total=3):
        for k in range(total):
            self.star((centre[0] + (k - (total - 1) / 2) * taille * 2.3, centre[1]), taille, k < nombre)

    def bar(self, r, valeur, couleur, fond=(255, 255, 255, 40)):
        self.rect(fond, r, rayon=r[3] / 2)
        if valeur > 0:
            self.rect(couleur, (r[0], r[1], max(r[3], r[2] * min(1.0, valeur)), r[3]), rayon=r[3] / 2)

    def hovered(self, r):
        return pygame.FRect(r).collidepoint(self.mouse())

    def hit(self, r):
        """Vrai si le clic de cette image tombe dans le rectangle (le clic est alors consommé)."""
        if self.click and pygame.FRect(r).collidepoint(self.click):
            self.click, self.clicked = None, True
            return True
        return False

    def button(self, texte, pos, taille=30, ancre="center", couleur=IVORY, serif=False, actif=True):
        """Bouton texte : surligné au survol, renvoie True s'il vient d'être cliqué."""
        w, h = self.font(taille, serif).size(texte)
        r = pygame.FRect(0, 0, w / self.k + 28, h / self.k + 14)
        setattr(r, ancre, pos)
        if not actif:
            self.text(texte, taille, r.center, (90, 84, 74), serif=serif)
            return False
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

    def overlay(self, sorte, force=1.0):
        """Grands dégradés calculés une fois par taille de fenêtre (fond du menu, vignette, alerte rouge)."""
        if sorte not in self.cache:
            w, h = self.surface.get_size()
            couleur = (0, 0, 0)
            if sorte == "menu":  # sombre à gauche (sous le texte) et en bas, plus clair ailleurs
                x, y = np.linspace(0, 1, w)[:, None], np.linspace(0, 1, h)[None, :]
                alpha = np.maximum(np.clip(1.1 - x * 1.5, 0.15, 0.9), np.clip((y - 0.8) * 3.5, 0, 0.7))
            else:  # vignette : coins assombris (ou rougis pour l'alerte)
                x, y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h), indexing="ij")
                alpha = np.clip((np.hypot(x, y) - 0.6) * 1.2, 0, 0.8)
                if sorte == "alerte":
                    couleur, alpha = (200, 20, 20), np.clip((np.hypot(x, y) - 0.3) * 1.4, 0, 1)
            calque = pygame.Surface((w, h), pygame.SRCALPHA)
            calque.fill((*couleur, 255))
            pygame.surfarray.pixels_alpha(calque)[:] = (alpha * 255).astype(np.uint8)
            self.cache[sorte] = calque
        calque = self.cache[sorte]
        if force < 1.0:
            calque = calque.copy()
            calque.set_alpha(round(255 * max(0.0, force)))
        self.surface.blit(calque, (0, 0))

    def draw(self):
        """Envoie la surface à la carte graphique et la plaque sur tout l'écran."""
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, *self.surface.get_size(), GL_RGBA, GL_UNSIGNED_BYTE,
                        pygame.image.tobytes(self.surface, "RGBA"))
        glViewport(0, 0, *self.window)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, 1, 1, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDisable(GL_FOG)
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

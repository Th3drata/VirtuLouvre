"""Les six nuits de la campagne : une mission par salle, chacune avec sa mécanique.

Une mission prépare la salle (objets, personnages), fait avancer sa logique à chaque image (update),
propose des interactions (touche E), dessine ce qui lui est propre et son morceau d'interface (hud)."""

import math
import random

import numpy as np
from OpenGL.GL import *

from . import rendu
from .acteurs import PNJ
from .base import BLUE, BODY, CROUCH_BODY, DIM, GOLD, GREEN, RED, angle_vers, ecart_angle, seg_seg_distance, smoothstep
from .modeles import SYMBOLES, modele
from .salles import PALIER, STELES, dessiner_modele, dilate


class Interaction:
    """Quelque chose à faire avec la touche E quand on le regarde de près."""

    def __init__(self, position, texte, action, rayon=2.4):
        self.position, self.texte, self.action, self.rayon = np.asarray(position, float), texte, action, rayon


def dessiner_centre(m, position, lacet, echelle):
    """Dessine un modèle centré sur `position` (il tourne sur lui-même autour de son centre)."""
    if "centre" not in m.infos:
        lo, hi = m.bornes()
        m.infos["centre"] = (lo + hi) / 2
    glPushMatrix()
    glTranslatef(*position)
    glRotatef(lacet, 0, 1, 0)
    glScalef(echelle, echelle, echelle)
    glTranslatef(*-m.infos["centre"])
    m.draw()
    glPopMatrix()


class Mission:
    id = salle_id = titre = heure = intro = objectif = victoire = ""
    nuit = 0
    duree = None  # temps limite en secondes (None : pas de limite)
    eclairage = 0.6  # intensité des lumières de la salle (0 : éteintes)
    lampe = True  # lampe torche allumée au départ
    musique, ambiance = "enquete", "nuit"  # voir sons.MUSIQUES et sons.AMBIANCES
    endurance = False  # course limitée par le souffle
    astuces = ()
    fin_temps = "Le temps est écoulé."
    progression = ""  # petit texte sous l'objectif (« 3 / 8 »...)

    def __init__(self, app, point=0, essais=0):
        self.app, self.salle = app, app.salle
        self.temps, self.erreurs, self.point, self.essais = 0.0, 0, point, essais
        self.fini = False

    def depart(self):
        return self.salle.depart

    def demarrer(self):
        pass

    def update(self, dt):
        pass

    def interactions(self):
        return []

    def draw3d(self, cam):
        pass

    def effets(self, cam, droite, haut):
        pass

    def hud(self, ui):
        pass

    def spots(self):
        return []

    def etoiles(self):
        return 1

    def gagner(self, texte=None):
        if not self.fini:
            self.fini = True
            self.app.fin_mission(True, texte or self.victoire)

    def perdre(self, texte):
        if not self.fini:
            self.fini = True
            self.app.fin_mission(False, texte)


# ---------------------------------------------------------------------------
# Nuit 1 — Galerie d'Apollon : les joyaux de la Couronne
# ---------------------------------------------------------------------------

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
PICK_RADIUS = 1.2


def cachettes_apollon(salle):
    """Cases accessibles un peu à l'écart des murs (dans la galerie scannée), + la vitrine brisée."""
    loin = ~dilate(~salle.atteint, 1)
    X, Z = salle.centres()
    spots = [(float(x), 0.35, float(z)) for x, z, ok in zip(X.ravel(), Z.ravel(), loin.ravel())
             if ok and math.hypot(x - 0.2, z - 18.2) > 3.5]
    x, z, _ = next(v for v in salle.vitrines if v[2])
    return spots, (x, 1.12, z)


def placer_joyaux(spots, vitrine, hasard, zmin=-22.6, zmax=20.3):
    """Une cachette par tronçon de galerie : les joyaux sont répartis sur toute la longueur."""
    n = len(JEWELS)
    bornes = np.linspace(zmin, zmax, n + 1)
    choix = []
    for a, b in zip(bornes, bornes[1:]):
        options = [s for s in spots if a <= s[2] < b and s not in choix]
        choix.append(hasard.choice(options or [s for s in spots if s not in choix]))
    if hasard.random() < 0.6:  # souvent, un joyau est resté dans la vitrine brisée
        k = min(range(n), key=lambda i: abs(choix[i][2] - vitrine[2]))
        choix[k] = vitrine
    return choix


class MissionJoyaux(Mission):
    id = salle_id = "apollon"
    nuit = 1
    titre = "Les joyaux de la Couronne"
    heure = "Nuit 1 — 23 h 47"
    intro = ("Galerie d'Apollon. Les joyaux de la Couronne viennent d'être dérobés ! Dans leur fuite, les voleurs ont "
             "semé leur butin dans la galerie, plongée dans le noir. Retrouve les huit joyaux avant l'arrivée de la police.")
    objectif = "Retrouver les 8 joyaux"
    duree = 180
    eclairage = 0.0
    astuces = ("Ta lampe fait scintiller les pierres.", "Le détecteur bipe plus vite quand tu t'approches d'un joyau.")
    victoire = ("Les huit joyaux sont retrouvés. Au fond de la vitrine brisée, un ticket froissé : « Salle des États, "
                "samedi, minuit ». Les voleurs ne sont pas des amateurs : ils se font appeler le Cercle.")
    fin_temps = "La police arrive... et il manque encore des joyaux."

    def demarrer(self):
        spots, vitrine = cachettes_apollon(self.salle)
        cachettes = placer_joyaux(spots, vitrine, random.Random())
        self.joyaux = [{"nom": nom, "couleur": couleur, "modele": modele(f"joyau:{k}"), "pos": np.array(p), "trouve": False}
                       for k, ((nom, couleur), p) in enumerate(zip(JEWELS, cachettes))]
        self.signal, self.bip, self.flash = 0.0, 1.0, 0.0

    def update(self, dt):
        joueur = self.app.player
        for j in self.joyaux:
            d = j["pos"] - joueur.pos
            if not j["trouve"] and math.hypot(d[0], d[2]) < PICK_RADIUS and abs(d[1]) < 2.0:
                j["trouve"] = True
                self.app.notice(j["nom"], "retrouvé !")
                self.app.audio.play("joyau")
                self.app.burst(j["pos"], j["couleur"])
        restants = [j for j in self.joyaux if not j["trouve"]]
        if not restants:
            self.gagner()
            return
        distance = min(float(np.linalg.norm(j["pos"] - joueur.pos)) for j in restants)
        self.signal = max(0.0, 1.0 - distance / 20.0)
        self.bip -= dt
        self.flash = max(0.0, self.flash - dt * 4)
        if self.bip <= 0:  # détecteur : de plus en plus rapide près du joyau le plus proche
            self.app.audio.play("sonar_proche" if distance < 4 else "sonar_moyen" if distance < 10 else "sonar_loin")
            self.bip, self.flash = min(1.6, 0.12 + 0.07 * distance), 1.0

    def lueur(self, cam, p):
        """0 à 1 : le joyau est-il dans le faisceau de la lampe ?"""
        vers = p - cam.eye()
        distance = float(np.linalg.norm(vers)) or 1.0
        if not self.app.torche:
            return 0.0
        return smoothstep(0.85, 0.97, float(vers @ cam.front()) / distance) * max(0.0, 1 - distance / 16)

    def draw3d(self, cam):
        t = self.app.t
        for i, j in enumerate(self.joyaux):
            if not j["trouve"]:
                dessiner_centre(j["modele"], j["pos"] + (0, 0.06 * math.sin(t * 2 + i), 0), t * 50 + i * 45, 0.42)

    def effets(self, cam, droite, haut):
        t, liste = self.app.t, []
        for i, j in enumerate(self.joyaux):
            if not j["trouve"]:
                eclat = self.lueur(cam, j["pos"])
                vers = j["pos"] - cam.eye()
                distance = float(np.linalg.norm(vers)) or 1.0
                taille = 0.3 + 0.5 * eclat
                scintille = 0.5 + 0.5 * math.sin(t * 5 + i * 1.7)
                liste.append((j["pos"] - vers / distance * min(taille, distance / 2), taille, j["couleur"],
                              0.07 + 0.1 * scintille + 0.8 * eclat))
        rendu.halos(liste, droite, haut)

    def hud(self, ui):
        trouves = sum(j["trouve"] for j in self.joyaux)
        for i, j in enumerate(self.joyaux):
            ui.diamond((48 + i * 22, 118), 8, j["couleur"] if j["trouve"] else DIM, j["trouve"])
        cx = ui.W / 2
        ui.text("DÉTECTEUR", 16, (cx, ui.H - 76), GOLD)
        allumes = round(self.signal * 16)
        for k in range(16):
            couleur = tuple(int(BLUE[c] + (RED[c] - BLUE[c]) * k / 15) for c in range(3))
            if k >= allumes:
                couleur = (60, 60, 70)
            elif self.flash > 0:
                couleur = tuple(min(255, int(c + (255 - c) * self.flash * 0.6)) for c in couleur)
            ui.rect(couleur, (cx - 175 + k * 22, ui.H - 58, 18, 12), rayon=3)
        self.progression = f"{trouves} / {len(self.joyaux)}"

    def etoiles(self):
        return 3 if self.temps <= 90 else 2 if self.temps <= 150 else 1


# ---------------------------------------------------------------------------
# Nuit 2 — Salle des États : l'enquête
# ---------------------------------------------------------------------------

INDICES = [  # (modèle, position, lacet, échelle, rayon d'examen, titre, texte)
    ("empreintes", (4.6, 0.0, -14.8), 0, 1.0, 2.8, "Des traces de pas",
     "Des empreintes de chaussures de chantier, blanches de plâtre, mènent tout droit à la porte de service."),
    ("gant", (-3.55, 0.03, -7.3), 30, 1.3, 2.2, "Un gant de travail",
     "Un gant orange. Sur l'étiquette cousue : « Atelier de restauration — équipe de nuit »."),
    ("badge", (2.4, 0.01, 16.4), 20, 1.4, 2.2, "Un badge d'accès",
     "Le badge d'une entreprise de restauration... dont personne n'a jamais entendu parler au musée. C'est un faux."),
    ("camera", (7.84, 3.53, 6.6), -90, 1.3, 3.6, "Une caméra cachée",
     "Une mini-caméra posée sur un cadre. Elle filme la Joconde... et surtout les rondes des gardiens."),
    ("carnet", (0.5, 0.47, 7.5), 15, 1.3, 2.2, "Un carnet oublié",
     "« Vitre de la Joconde : blindée, impossible. Plan B : la Grande Galerie, jeudi, pendant les travaux de "
     "l'échafaudage. On passera pour des restaurateurs. »"),
    ("ruban", (0.4, 2.35, -12.27), 0, 1.0, 3.6, "Du ruban adhésif",
     "Des morceaux de ruban sur la vitre de la Joconde : ils ont testé la vitre blindée. Elle a résisté."),
]
QUESTIONS = [  # (question, choix, indice de la bonne réponse, explication)
    ("Quelle est la vraie cible du Cercle ?", ["La Joconde", "Un tableau de la Grande Galerie", "Les Noces de Cana"], 1,
     "La vitre de la Joconde a résisté, et le carnet parle de la Grande Galerie."),
    ("Comment comptent-ils agir ?", ["En passant par la verrière du toit", "Déguisés en restaurateurs, avec de faux badges",
                                     "Cachés parmi les visiteurs"], 1,
     "Gant d'atelier, faux badge, traces de plâtre : ce sont de faux restaurateurs."),
    ("Quand vont-ils frapper ?", ["Cette nuit, tout de suite", "Pendant les travaux de l'échafaudage",
                                  "Le jour de la fermeture annuelle"], 1,
     "Le carnet est clair : pendant les travaux de l'échafaudage."),
]


class MissionIndices(Mission):
    id = salle_id = "etats"
    nuit = 2
    titre = "Les indices de la Joconde"
    heure = "Nuit 2 — samedi, minuit"
    intro = ("Salle des États, le rendez-vous du ticket. Le Cercle n'est pas venu... mais il est passé par là : il a "
             "laissé des traces. La conservatrice t'ouvre la salle : fouille-la à la lampe, examine chaque indice, puis "
             "devine son prochain coup.")
    objectif = "Trouver les 6 indices"
    duree = 360
    eclairage = 0.45
    astuces = ("Regarde un objet suspect de près et appuie sur E pour l'examiner.",
               "Pense aussi à regarder en hauteur, et du côté de la Joconde.")
    victoire = ("Tout concorde : le Cercle va voler un tableau de la Grande Galerie, déguisé en équipe de restauration, "
                "pendant les travaux. Le conservateur t'envoie surveiller l'échafaudage...")
    fin_temps = "Le jour se lève : les indices seront effacés par le ménage."
    ambiance = "pluie"

    def demarrer(self):
        self.trouves = [False] * len(INDICES)
        self.question = 0
        self.conservatrice = self.app.foule.ajouter(PNJ("conservatrice", -2.3, 13.6, yaw=-40, salle=self.salle))
        self.conservatrice.pose = "bras_croises"

    def parler(self):
        n = sum(self.trouves)
        conseil = ("« Ils sont passés pendant la ronde de minuit. Regardez partout : par terre, sur les bancs... et même "
                   "en hauteur, sur les cadres. »" if n < 3 else "« Vous avancez bien. N'oubliez pas la Joconde : ils "
                   "ont sûrement voulu tester sa vitre. »" if n < 6 else "« Alors, qu'est-ce qu'ils préparent ? »")
        self.app.ouvrir_examen("La conservatrice", conseil, f"{n} indice{'s' if n > 1 else ''} sur {len(INDICES)}", None)

    def examiner(self, k):
        self.trouves[k] = True
        self.app.audio.play("loupe")
        _, _, _, _, _, titre, texte = INDICES[k]
        n = sum(self.trouves)
        suite = self.deduire if n == len(INDICES) else None
        self.app.ouvrir_examen(titre, texte, f"Indice {n} sur {len(INDICES)} ajouté au carnet d'enquête", suite)

    def deduire(self):
        self.app.ouvrir_deduction(self)

    def repondre(self, choix):
        """Réponse à la question en cours : renvoie (juste ?, explication)."""
        question, _, bonne, explication = QUESTIONS[self.question]
        if choix == bonne:
            self.question += 1
            if self.question == len(QUESTIONS):
                self.gagner()
            return True, explication
        self.erreurs += 1
        self.temps += 20
        return False, "Relis ton carnet... (-20 s)"

    def interactions(self):
        return [Interaction(np.asarray(pos) + (0, 0.05, 0), "Examiner", lambda k=k: self.examiner(k), rayon)
                for k, (_, pos, _, _, rayon, _, _) in enumerate(INDICES) if not self.trouves[k]] + \
            [Interaction(self.conservatrice.oeil() - (0, 0.3, 0), "Parler à la conservatrice", self.parler, 2.6)]

    def draw3d(self, cam):
        for k, (nom, pos, lacet, echelle, *_rest) in enumerate(INDICES):
            dessiner_modele(modele(nom), pos, lacet, echelle)

    def effets(self, cam, droite, haut):
        t = self.app.t
        rendu.halos([(np.asarray(pos) + (0, 0.08, 0), 0.18, GOLD, 0.12 + 0.1 * math.sin(t * 3 + k))
                     for k, (_, pos, *_rest) in enumerate(INDICES) if not self.trouves[k]], droite, haut)

    def hud(self, ui):
        for k in range(len(INDICES)):
            ui.circle(GOLD if self.trouves[k] else DIM, (48 + k * 22, 118), 7, 0 if self.trouves[k] else 1.5)
        self.progression = f"{sum(self.trouves)} / {len(INDICES)}"

    def etoiles(self):
        return 3 if self.erreurs == 0 and self.temps < 240 else 2 if self.erreurs <= 1 else 1


# ---------------------------------------------------------------------------
# Nuit 3 — Grande Galerie : la poursuite
# ---------------------------------------------------------------------------

ROUTE_VOLEUR = [(3.0, 41.0), (1.8, 35.0), (-2.4, 29.0), (-1.2, 20.0), (2.4, 8.0), (0.6, -2.0), (-2.4, -14.0),
                (0.9, -26.0), (2.4, -37.0), (0.0, -47.0), (-2.2, -58.0), (0.0, -65.0)]
LACHERS = {3: "chariot", 6: "caisse", 9: "chariot"}  # étape de la route : obstacle renversé derrière lui
REGARDS = (4, 8)  # étapes où il s'arrête un instant pour regarder derrière lui
VITESSE_VOLEUR = (4.4, 3.4, 25.0)  # il part vite puis s'essouffle : de 4,4 à 3,4 en 25 s (le joueur court à 5,0)


class MissionPoursuite(Mission):
    id = salle_id = "grande_galerie"
    nuit = 3
    titre = "La poursuite"
    heure = "Nuit 3 — jeudi, 2 h 10"
    intro = ("Grande Galerie. Un faux restaurateur vient de décrocher La Belle Ferronnière de Léonard de Vinci, près de "
             "l'échafaudage. Il t'a vu : il fonce vers la sortie de secours, à l'autre bout de la galerie. Rattrape-le !")
    objectif = "Rattraper le voleur"
    eclairage = 0.75
    lampe = False
    endurance = True
    musique = "poursuite"
    astuces = ("Maj pour courir : attention à ton souffle, il se recharge quand tu marches.",
               "Coupe les virages : il zigzague entre les bancs.")
    victoire = ("Le faux restaurateur est arrêté, La Belle Ferronnière sous le bras. Il avoue : le butin du Cercle est caché "
                "sous le Sphinx, dans la crypte... mais pour y aller, il faut traverser la salle des Cariatides, où le chef "
                "a rallumé les lasers de sécurité.")

    def demarrer(self):
        self.voleur = PNJ("voleur", 2.6, 44.5, yaw=-90, salle=self.salle, vitesse=VITESSE_VOLEUR[0])
        self.voleur.pose, self.voleur.porte = "porte", self.dessiner_tableau
        self.gardien = PNJ("gardien", -1.2, 64.8, yaw=-90, salle=self.salle, vitesse=2.9)  # il arrive en renfort
        self.gardien.etape = 0
        self.etape, self.pause, self.lent, self.attrape = 0, 1.0, 0.0, None
        self.obstacles = []
        self.distance = 12.0
        self.app.notice("Hé ! Arrêtez-vous !", "", RED)
        self.app.audio.play("sifflet")

    def update(self, dt):
        v, joueur = self.voleur, self.app.player
        distance = math.hypot(v.pos[0] - joueur.pos[0], v.pos[2] - joueur.pos[2])
        self.distance = distance
        if self.attrape is not None:
            self.attrape -= dt
            self.suivre_gardien(dt)
            if self.attrape <= 0:
                self.gagner()
            return
        self.suivre_gardien(dt)
        if distance < 1.3:  # rattrapé !
            v.pose, v.ampleur, v.porte, self.attrape = "mains_en_l_air", 0.0, None, 1.4
            v.yaw = angle_vers(joueur.pos[0] - v.pos[0], joueur.pos[2] - v.pos[2])
            self.app.audio.play("menottes")
            self.app.notice("Arrêté !", "Le voleur lève les mains.", GREEN)
            return
        if self.pause > 0:
            self.pause -= dt
            v.tourner_vers(angle_vers(joueur.pos[0] - v.pos[0], joueur.pos[2] - v.pos[2]), dt, 400)
            v.ampleur = max(0.0, v.ampleur - dt * 5)
            return
        self.lent = max(0.0, self.lent - dt)
        x, z = ROUTE_VOLEUR[self.etape]
        debut, fin, duree = VITESSE_VOLEUR
        vitesse = debut + (fin - debut) * min(1.0, self.temps / duree)
        if v.avancer_vers(x, z, dt, self.salle, 2.4 if self.lent > 0 else vitesse):
            if self.etape == len(ROUTE_VOLEUR) - 1:
                self.perdre("Le voleur s'est échappé par la sortie de secours, La Belle Ferronnière sous le bras.")
                return
            if self.etape in LACHERS:
                self.lacher(LACHERS[self.etape])
            if self.etape in REGARDS:
                self.pause = 0.6
            self.etape += 1
        foulee = int(v.phase / math.pi)
        if foulee != getattr(v, "foulee", foulee):
            self.app.audio.spatial("pas", v.pos, joueur.pos, joueur.yaw)
        v.foulee = foulee

    def suivre_gardien(self, dt):
        """Le gardien de nuit court derrière, sur le chemin du voleur, et s'arrête près de lui s'il est pris."""
        g, v = self.gardien, self.voleur
        if self.temps < 1.5:  # il vient de siffler
            return
        if math.hypot(g.pos[0] - v.pos[0], g.pos[2] - v.pos[2]) < 2.6 and self.attrape is not None:
            g.ralentir(dt)
            g.tourner_vers(angle_vers(v.pos[0] - g.pos[0], v.pos[2] - g.pos[2]), dt)
            return
        x, z = ROUTE_VOLEUR[min(g.etape, self.etape, len(ROUTE_VOLEUR) - 1)]
        if g.avancer_vers(x, z, dt, self.salle) and g.etape < self.etape:
            g.etape += 1

    def dessiner_tableau(self):
        """La Belle Ferronnière, serrée contre le voleur (dessinée dans le repère de son buste)."""
        rendu.draw_box(-0.2, 0.9, 0.16, 0.2, 1.42, 0.2, (0.8, 0.62, 0.25))
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, rendu.texture("tableau:belle_ferronniere"))
        glColor3f(1, 1, 1)
        glNormal3f(0, 0, 1)
        glBegin(GL_QUADS)
        for (u, w), (x, y) in zip(((0, 0), (1, 0), (1, 1), (0, 1)), ((0.17, 0.93), (-0.17, 0.93), (-0.17, 1.39), (0.17, 1.39))):
            glTexCoord2f(u, w)
            glVertex3f(x, y, 0.205)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def lacher(self, nom):
        """Il renverse un chariot ou une caisse derrière lui (sauf si le joueur est juste dessus)."""
        v, joueur = self.voleur, self.app.player
        p = v.pos - v.devant() * 2.0
        if math.hypot(p[0] - joueur.pos[0], p[2] - joueur.pos[2]) < 2.5:
            return
        lacet = random.uniform(-30, 30) + 90
        self.obstacles.append((modele(nom), p.copy(), lacet))
        self.salle.bloquer_rect(p[0] - 0.8, p[2] - 0.55, p[0] + 0.8, p[2] + 0.55, 1.0)
        self.lent = 0.8
        self.app.audio.spatial("fracas", p, joueur.pos, joueur.yaw, 30.0)

    def draw3d(self, cam):
        self.voleur.draw()
        self.gardien.draw()
        for m, p, lacet in self.obstacles:
            dessiner_modele(m, p, lacet)

    def hud(self, ui):
        cx = ui.W / 2
        ui.text(f"VOLEUR : {self.distance * 1.15:.0f} m", 22, (cx, ui.H - 86), RED if self.distance > 8 else GOLD)
        ui.text("SOUFFLE", 14, (cx, ui.H - 60), DIM)
        joueur = self.app.player
        ui.bar((cx - 120, ui.H - 48, 240, 8), joueur.stamina, RED if joueur.epuise else GREEN)
        self.progression = f"{self.distance * 1.15:.0f} m"

    def etoiles(self):
        return 3 if self.temps <= 22 else 2 if self.temps <= 32 else 1


# ---------------------------------------------------------------------------
# Nuit 4 — Salle des Cariatides : le labyrinthe laser
# ---------------------------------------------------------------------------


def laser_fixe(a, b):
    return {"type": "fixe", "a": np.array(a, float), "b": np.array(b, float)}


class MissionLasers(Mission):
    id = salle_id = "cariatides"
    nuit = 4
    titre = "Le labyrinthe laser"
    heure = "Nuit 4 — vendredi, 1 h 30"
    intro = ("Salle des Cariatides. Le chef du Cercle a rallumé les lasers de sécurité pour ralentir quiconque le suit vers "
             "la crypte. Traverse la salle sans toucher un rayon et coupe l'alarme, sous la tribune des Cariatides.")
    objectif = "Couper l'alarme sous la tribune"
    duree = 300
    eclairage = 0.25
    musique = "lasers"
    astuces = ("Espace pour sauter par-dessus un rayon bas, C pour t'accroupir sous un rayon haut.",
               "Trois alarmes et c'est fini. Les dalles vertes sont des points de contrôle.")
    victoire = ("Le panneau s'éteint, les rayons tombent. Au fond de la salle, l'escalier de service descend vers la crypte "
                "du Sphinx. Le butin du Cercle t'attend peut-être là-dessous.")
    fin_temps = "Trop tard : l'équipe de sécurité a verrouillé la salle."
    POINTS = [(0.0, 13.5), (0.0, 5.3), (0.0, -3.7), (0.0, -11.9)]

    def depart(self):
        x, z = self.POINTS[self.point]
        return (x, 0.0, z, -90.0)

    def demarrer(self):
        L = [laser_fixe((-7, 0.35, 10.6), (7, 0.35, 10.6)), laser_fixe((-7, 1.45, 9.0), (7, 1.45, 9.0)),
             laser_fixe((-7, 0.3, 7.3), (0, 0.3, 7.3)), laser_fixe((0, 1.45, 7.3), (7, 1.45, 7.3)),
             laser_fixe((0, 0.0, 7.3), (0, 2.6, 7.3))]
        for x in (-3.7, 3.7):  # murs de rayons de chaque côté du couloir
            for y in (0.3, 0.9, 1.5, 2.1):
                L.append(laser_fixe((x, y, 5.0), (x, y, -12.2)))
        for i, z in enumerate((3.0, 0.5, -2.0)):
            L.append({"type": "balai", "a": np.array((0, 0.0, z)), "b": np.array((0, 2.6, z)), "amp": 3.35,
                      "w": (1.2, 1.6, 2.0)[i], "phi": i * 1.7})
        L.append({"type": "rotatif", "c": np.array((0, 0.35, -8.0)), "r": 3.55, "w": 1.0, "phi": 0.0})
        for y in (0.3, 0.8, 1.3, 1.8):
            L.append({"type": "clignotant", "a": np.array((-3.7, y, -10.6)), "b": np.array((3.7, y, -10.6)),
                      "periode": 2.6, "allume": 1.5})
        self.lasers = L
        self.vies, self.touche, self.flash = 3, 0.0, 0.0
        self.pivot = modele("socle")
        self.salle.bloquer_disque(0, -8.0, 0.3, 0.5)  # le poteau du laser tournant

    def segments(self):
        t = self.app.t
        for l in self.lasers:
            if l["type"] == "fixe":
                yield l, l["a"], l["b"], True
            elif l["type"] == "balai":
                decalage = np.array((l["amp"] * math.sin(l["w"] * t + l["phi"]), 0, 0))
                yield l, l["a"] + decalage, l["b"] + decalage, True
            elif l["type"] == "rotatif":
                a = l["w"] * t + l["phi"]
                d = np.array((math.cos(a), 0, math.sin(a))) * l["r"]
                yield l, l["c"] - d, l["c"] + d, True
            else:
                yield l, l["a"], l["b"], (t % l["periode"]) < l["allume"]

    def update(self, dt):
        joueur = self.app.player
        self.flash = max(0.0, self.flash - dt * 1.5)
        oeil = joueur.eye()  # plus on est près d'un rayon, plus on entend son bourdonnement
        proche = min(seg_seg_distance(oeil, oeil, a, b) for l, a, b, actif in self.segments() if actif)
        self.app.audio.boucle("lasers", max(0.0, 1 - proche / 4.0) ** 2)
        for k in range(self.point + 1, len(self.POINTS)):  # points de contrôle
            if joueur.pos[2] < self.POINTS[k][1] + 0.3 and abs(joueur.pos[0]) < 3.5:
                self.point = k
                self.app.toast = ("Point de contrôle", self.app.t)
        if self.touche > 0:
            self.touche -= dt
            return
        pieds, tete = joueur.corps()
        for l, a, b, actif in self.segments():
            if actif and seg_seg_distance(pieds, tete, a, b) < 0.23:
                self.vies -= 1
                self.erreurs += 1
                self.app.audio.play("alarme")
                self.flash, self.touche = 1.0, 1.2
                if self.vies <= 0:
                    self.perdre("Trois alarmes : les gardiens arrivent et verrouillent la salle.")
                    return
                x, y, z, lacet = self.depart()
                joueur.pos[:] = (x, y, z)
                joueur.vel[:] = 0
                joueur.yaw, joueur.pitch = lacet, 0.0
                self.app.notice("Alarme !", f"Encore {self.vies} essai{'s' if self.vies > 1 else ''}.", RED)
                return

    def couper(self):
        self.app.audio.boucle("lasers", 0)
        self.app.audio.play("coupure")
        self.gagner()

    def interactions(self):
        return [Interaction((0, 1.35, -16.4), "Couper l'alarme", self.couper, 2.6)]

    def draw3d(self, cam):
        for l, a, b, actif in self.segments():
            for p in (a, b) if l["type"] != "rotatif" else ():
                glPushMatrix()
                glTranslatef(*p)
                rendu.draw_box(-0.06, -0.06, -0.06, 0.06, 0.06, 0.06, (0.08, 0.08, 0.09))
                glPopMatrix()
        dessiner_modele(self.pivot, (0, 0, -8.0), 0, 0.45)
        dessiner_modele(modele("panneau_alarme"), (0, 1.1, -16.42))

    def effets(self, cam, droite, haut):
        oeil = cam.eye()
        for l, a, b, actif in self.segments():
            if actif:
                rendu.faisceau(a, b, oeil, 0.09, (255, 40, 30), 0.9)
                rendu.faisceau(a, b, oeil, 0.025, (255, 200, 190), 1.0)
        halos = [(np.array((x, 0.03, z)), 0.9, GREEN, 0.35) for k, (x, z) in enumerate(self.POINTS) if k > self.point]
        halos.append((np.array((0.2, 1.4, -16.3)), 0.25, (80, 255, 140), 0.6 + 0.3 * math.sin(self.app.t * 4)))
        rendu.halos(halos, droite, haut)

    def hud(self, ui):
        for k in range(3):
            ui.diamond((48 + k * 22, 118), 8, RED if k < self.vies else DIM, k < self.vies)
        if self.flash > 0:
            ui.overlay("alerte", self.flash)
        self.progression = f"{self.vies} essai{'s' if self.vies > 1 else ''}"

    def etoiles(self):
        return 3 if self.erreurs == 0 else 2 if self.erreurs == 1 else 1


# ---------------------------------------------------------------------------
# Nuit 5 — Crypte du Sphinx : l'énigme
# ---------------------------------------------------------------------------

NOMS_SYMBOLES = {"ankh": "l'ankh", "oeil": "l'œil d'Horus", "scarabee": "le scarabée", "ibis": "l'ibis"}


class MissionSphinx(Mission):
    id = salle_id = "sphinx"
    nuit = 5
    titre = "L'énigme du Sphinx"
    heure = "Nuit 5 — samedi, 3 h 00"
    intro = ("Crypte du Sphinx. D'après le voleur, le Cercle cache son butin sous le grand Sphinx de Tanis. Le chef a "
             "protégé la cachette par une énigme : parle au Sphinx, puis répète les symboles qu'il te montre.")
    objectif = "Réussir les 3 épreuves du Sphinx"
    duree = 300
    eclairage = 1.0
    lampe = False
    musique, ambiance = "sphinx", "crypte"
    astuces = ("Regarde bien l'ordre des symboles qui s'allument, et écoute leurs notes.",
               "Une erreur coûte 15 secondes et le Sphinx recommence.")
    victoire = ("Le tiroir de pierre renfermait la couronne de l'impératrice Eugénie... et un message du Cercle : "
                "« Dernier rendez-vous : au pied de la Victoire de Samothrace. Viens seul. »")

    def demarrer(self):
        h = random.Random()
        self.sequences = [[h.randrange(4) for _ in range(n)] for n in (3, 4, 5)]
        self.manche, self.etat, self.chrono = 0, "attente", 0.0
        self.saisie, self.montre, self.allume = [], 0, [0.0] * 4
        self.tiroir = 0.0
        self.premiere = True

    def ecouter(self):
        if self.premiere:
            self.premiere = False
            self.app.audio.play("sphinx_voix")
            self.app.ouvrir_examen("Le Sphinx parle", "« Je montre, tu répètes. Réussis trois fois mes épreuves, "
                                   "et mon trésor sera tien. »", "Regarde les symboles s'allumer, dans l'ordre.", None)
        self.commencer_manche(0.8)

    def commencer_manche(self, delai):
        self.etat, self.chrono, self.montre, self.saisie = "montre", delai, 0, []

    def toucher(self, k):
        self.allume[k] = 0.35
        self.app.audio.play(f"note{k}")
        sequence = self.sequences[self.manche]
        if k != sequence[len(self.saisie)]:
            self.erreurs += 1
            self.temps += 15
            self.app.audio.play("grondement")
            self.app.notice("Mauvais symbole...", "Le Sphinx gronde et recommence. (-15 s)", RED)
            self.commencer_manche(1.6)
            return
        self.saisie.append(k)
        if len(self.saisie) == len(sequence):
            self.manche += 1
            if self.manche == len(self.sequences):
                self.etat = "ouvert"
                self.app.audio.play("tiroir")
                self.app.notice("La pierre bouge...", "Un tiroir sort du socle du Sphinx.", GOLD)
            else:
                self.app.audio.play("loupe")
                self.app.notice(f"Épreuve {self.manche} réussie", "Le Sphinx continue.", GREEN)
                self.commencer_manche(1.4)

    def prendre(self):
        self.etat = "fin"
        self.app.audio.play("joyau")
        self.app.burst(self.position_couronne(), (255, 210, 120))
        self.gagner()

    def position_couronne(self):
        return np.array((0.0, 0.56, -0.65 + 1.0 * self.tiroir))

    def update(self, dt):
        self.allume = [max(0.0, a - dt) for a in self.allume]
        if self.etat == "montre":
            self.chrono -= dt
            if self.chrono <= 0:
                sequence = self.sequences[self.manche]
                if self.montre < len(sequence):
                    k = sequence[self.montre]
                    self.allume[k] = 0.6
                    self.app.audio.play(f"note{k}")
                    self.montre += 1
                    self.chrono = 0.85
                else:
                    self.etat = "saisie"
        elif self.etat == "ouvert":
            self.tiroir = min(1.0, self.tiroir + dt / 2.0)

    def interactions(self):
        if self.etat == "attente":
            return [Interaction((0, 1.4, -0.6), "Parler au Sphinx", self.ecouter, 3.4)]
        if self.etat == "saisie":
            return [Interaction((x, 1.05, z), f"Toucher {NOMS_SYMBOLES[s]}", lambda k=k: self.toucher(k), 2.3)
                    for k, ((x, z, _), s) in enumerate(zip(STELES, SYMBOLES))]
        if self.etat == "ouvert" and self.tiroir >= 1.0:
            return [Interaction(self.position_couronne(), "Prendre la couronne", self.prendre, 2.6)]
        return []

    def draw3d(self, cam):
        z = -0.4 + 1.0 * self.tiroir
        rendu.draw_box(-0.55, 0.05, z - 0.5, 0.55, 0.38, z, (0.62, 0.42, 0.38))
        if self.etat == "ouvert":
            dessiner_centre(modele("couronne"), self.position_couronne() + (0, 0.1, 0), self.app.t * 30, 0.55)

    def effets(self, cam, droite, haut):
        halos = []
        for k, (x, z, lacet) in enumerate(STELES):
            if self.allume[k] > 0:
                halos.append((np.array((x + math.sin(math.radians(lacet)) * 0.05, 1.12, z)), 0.9, GOLD, min(1.0, self.allume[k] * 2)))
        if self.etat == "montre":
            for x in (-0.11, 0.11):
                halos.append((np.array((x, 1.675, -1.53)), 0.12, (255, 120, 40), 0.9))
        for x, y, z in self.salle.feux:  # flammes des braseros
            for k in range(3):
                vacille = 0.5 + 0.5 * math.sin(self.app.t * (7 + k) + x * 3 + k)
                halos.append((np.array((x, y + 0.12 * k, z)), 0.35 - 0.08 * k + 0.08 * vacille, (255, 140 - 30 * k, 40), 0.7))
        if self.etat == "ouvert" and self.tiroir >= 1.0:
            halos.append((self.position_couronne() + (0, 0.2, 0), 0.6, (255, 220, 140), 0.4))
        rendu.halos(halos, droite, haut)

    def hud(self, ui):
        manche = min(self.manche + 1, 3)
        for k in range(3):
            ui.diamond((48 + k * 22, 118), 8, GOLD if k < self.manche else DIM, k < self.manche)
        if self.etat in ("montre", "saisie"):
            n = len(self.sequences[self.manche])
            for k in range(n):
                fait = self.montre > k if self.etat == "montre" else len(self.saisie) > k
                ui.circle(GOLD if fait else DIM, (ui.W / 2 + (k - (n - 1) / 2) * 22, ui.H - 70), 6, 0 if fait else 1.5)
            ui.text("LE SPHINX MONTRE..." if self.etat == "montre" else "À TOI : RÉPÈTE LES SYMBOLES", 18,
                    (ui.W / 2, ui.H - 96), GOLD)
        self.progression = f"Épreuve {manche} / 3"

    def etoiles(self):
        return 3 if self.erreurs == 0 else 2 if self.erreurs <= 2 else 1


# ---------------------------------------------------------------------------
# Nuit 6 — Escalier Daru : la Victoire de Samothrace
# ---------------------------------------------------------------------------

CAISSES = [(-3.8, 7.6), (3.9, 12.2), (-3.9, -1.0), (3.9, -9.4), (-3.0, -15.6)]


class MissionVictoire(Mission):
    id = salle_id = "daru"
    nuit = 6
    titre = "La Victoire de Samothrace"
    heure = "Nuit 6 — dimanche, 4 h 00"
    intro = ("Escalier Daru. Le chef du Cercle t'attend au pied de la Victoire de Samothrace, en haut des marches. Ses "
             "guetteurs patrouillent avec leurs lampes. Monte sans te faire voir, approche-le par-derrière et arrête-le.")
    objectif = "Arrêter le chef du Cercle"
    eclairage = 0.65
    lampe = False
    musique, ambiance = "infiltration", "pluie"
    astuces = ("Reste hors des faisceaux des guetteurs. Accroupi (C), tu es plus discret, et caché derrière une caisse.",
               "Ta lampe allumée te fait repérer de plus loin. Si tu cours, ils t'entendent.")
    victoire = ("Le chef du Cercle est arrêté au pied de la Victoire de Samothrace. Les joyaux, la couronne et La Belle "
                "Ferronnière retrouvent leur place. Le musée te remercie : te voilà gardien d'honneur du Louvre.")
    POINTS = [(0.0, 0.0, 14.5, -90.0), (-3.3, 0.0, 4.9, -90.0), (3.2, PALIER, -8.8, -90.0)]

    def depart(self):
        return self.POINTS[self.point]

    def demarrer(self):
        s = self.salle
        self.caisses = []
        for x, z in CAISSES:
            y = s.sol_sous(x, z)
            self.caisses.append((modele("caisse"), np.array((x, y, z)), 0.0))
            s.bloquer_rect(x - 0.5, z - 0.4, x + 0.5, z + 0.4, y + 1.25)
        g1 = PNJ("guetteur", -5.0, 9.5, yaw=-90, salle=s)
        g1.route = [(-5.0, 9.5, 2.5, 180.0), (5.0, 9.5, 2.5, 0.0)]  # à chaque bout, il regarde les tableaux
        g2 = PNJ("guetteur", 2.6, -7.0, yaw=-90, salle=s)
        g2.route = [(2.6, 3.4, 2.5, 90.0), (2.6, -7.0, 2.5, -90.0)]
        g2.index = 0
        g3 = PNJ("guetteur", -5.2, -15.6, yaw=0, salle=s)
        g3.route = [(-5.2, -9.4, 2.0, 60.0), (-5.2, -15.6, 2.0, 0.0)]
        self.guetteurs = [g1, g2, g3]
        self.chef = PNJ("chef", 4.2, -12.0, yaw=0.0, salle=s)
        self.chef_chrono, self.chef_retourne = 9.0, 0.0
        self.max_alerte, self.arrete = 0.0, None
        self.coeur, self.radio = 0.0, random.uniform(6, 12)

    def update(self, dt):
        joueur, s = self.app.player, self.salle
        if self.arrete is not None:
            self.arrete -= dt
            if self.arrete <= 0:
                self.gagner()
            return
        for k in range(self.point + 1, len(self.POINTS)):  # points de contrôle
            x, y, z, _ = self.POINTS[k]
            if joueur.pos[2] < z + 0.5 and joueur.pos[1] >= y - 0.3:
                self.point = k
                self.app.toast = ("Point de contrôle", self.app.t)
        for g in self.guetteurs:
            g.patrouiller(dt, s)
        # le chef regarde la main de la Victoire, et se retourne de temps en temps
        self.chef_chrono -= dt
        if self.chef_retourne > 0:
            self.chef_retourne -= dt
            self.chef.tourner_vers(140.0, dt, 120)
        else:
            self.chef.tourner_vers(0.0, dt, 120)
            if self.chef_chrono <= 0:
                self.chef_retourne, self.chef_chrono = 3.0, random.uniform(8, 12)
        tete = joueur.pos + (0.0, (CROUCH_BODY if joueur.crouch else BODY) - 0.1, 0.0)
        portee = (8.5 if self.app.torche else 5.5) * (0.7 if joueur.crouch else 1.0)
        for g in self.guetteurs + [self.chef]:
            distance = math.hypot(g.pos[0] - joueur.pos[0], g.pos[2] - joueur.pos[2])
            if g.voit(tete, s, portee if g is not self.chef else portee * 0.85, 33 if g is not self.chef else 40):
                g.alerte += dt * (1.8 if distance < 3 else 0.9)
                if g is not self.chef and g.alerte > 0.35:  # il a un doute : il se tourne vers toi
                    g.entendre(joueur.pos)
            else:
                g.alerte = max(0.0, g.alerte - dt * 0.4)
            if joueur.sprinting and distance < 6 and g is not self.chef:
                g.entendre(joueur.pos)
            self.max_alerte = max(self.max_alerte, g.alerte)
            if g.alerte >= 1.0:
                self.app.audio.play("sifflet")
                self.perdre("Repéré ! Un coup de sifflet, et le chef du Cercle s'enfuit par les toits.")
                return
            foulee = int(g.phase / math.pi)  # un bruit de pas à chaque foulée
            if distance < 10 and foulee != getattr(g, "foulee", foulee):
                self.app.audio.spatial("pas", g.pos, joueur.pos, joueur.yaw)
            g.foulee = foulee
        alerte = max(g.alerte for g in self.guetteurs + [self.chef])
        self.coeur -= dt
        if alerte > 0.15 and self.coeur <= 0:  # le cœur bat plus vite quand on se sent repéré
            self.app.audio.play("coeur", 0.4 + 0.6 * alerte)
            self.coeur = 1.0 - 0.55 * alerte
        self.radio -= dt
        if self.radio <= 0:  # les talkies-walkies des guetteurs grésillent de temps en temps
            g = min(self.guetteurs, key=lambda g: np.sum((g.pos - joueur.pos) ** 2))
            self.app.audio.spatial("radio", g.pos, joueur.pos, joueur.yaw, 16.0)
            self.radio = random.uniform(12, 22)

    def arreter(self):
        self.chef.pose = "mains_en_l_air"
        self.arrete = 1.8
        for g in self.guetteurs:
            g.route, g.pose = [], "mains_en_l_air"
        self.app.audio.play("menottes")
        self.app.notice("Arrêté !", "Le chef du Cercle lève les mains.", GREEN)

    def interactions(self):
        joueur, c = self.app.player, self.chef
        if self.arrete is not None:
            return []
        dans_son_dos = abs(ecart_angle(c.yaw, angle_vers(joueur.pos[0] - c.pos[0], joueur.pos[2] - c.pos[2]))) > 70
        if dans_son_dos:
            return [Interaction(c.pos + (0, 1.2, 0), "Arrêter le chef du Cercle", self.arreter, 2.0)]
        return []

    def spots(self):
        joueur = self.app.player
        proches = sorted(self.guetteurs, key=lambda g: np.sum((g.pos - joueur.pos) ** 2))[:2]
        return [(*g.lampe(), (1.3, 1.25, 1.1), 11.0) for g in proches]

    def draw3d(self, cam):
        for m, p, lacet in self.caisses:
            dessiner_modele(m, p, lacet)
        for g in self.guetteurs + [self.chef]:
            g.draw()

    def effets(self, cam, droite, haut):
        for g in self.guetteurs:
            if g.pose != "mains_en_l_air":
                bout, direction = g.lampe()
                rendu.cone_lumineux(bout, direction, 7.0, 22, (255, 240, 200), 0.09 + 0.25 * g.alerte)

    def hud(self, ui):
        alerte = max(g.alerte for g in self.guetteurs + [self.chef])
        ui.text("DISCRÉTION", 16, (ui.W / 2, ui.H - 76), GOLD)
        ui.bar((ui.W / 2 - 120, ui.H - 58, 240, 10), alerte, RED if alerte > 0.5 else GOLD)
        if alerte > 0.05:
            ui.overlay("alerte", alerte * 0.7)
        joueur = self.app.player
        conseils = []
        if self.app.torche:
            conseils.append("Lampe allumée : on te voit de loin")
        if joueur.crouch:
            conseils.append("Accroupi")
        if conseils:
            ui.text("  ·  ".join(conseils), 16, (ui.W / 2, ui.H - 34), DIM)
        self.progression = "Point de contrôle " + str(self.point) if self.point else "Au pied de l'escalier"

    def etoiles(self):
        return 3 if self.essais == 0 and self.max_alerte < 0.6 else 2 if self.essais <= 1 else 1


CAMPAGNE = [MissionJoyaux, MissionIndices, MissionPoursuite, MissionLasers, MissionSphinx, MissionVictoire]

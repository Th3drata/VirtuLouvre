"""La boucle du jeu : fenêtre, écrans (menu, carte, briefing, pause, fin...), rendu 3D et interactions."""

import math
import os
import random
import sys
import time

import numpy as np
import pygame
from OpenGL.GL import *

from . import rendu
from .acteurs import Foule, Player
from .base import (ACTIONS, ARROWS, BLUE, DIM, DOSSIER, GOLD, GREEN, IVORY, KEY_LABELS, RED, RESOLUTIONS, VERSION, chemin,
                   fmt_time, key_code, load_settings, save_settings)
from .interface import UI
from .missions import CAMPAGNE, QUESTIONS
from .salles import MATERIAUX_SALLE, SALLES, construire
from .sons import Audio

WINDOW_FLAGS = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE

DESCRIPTIONS = {  # visite libre
    "apollon": "Le scan 3D de la galerie des joyaux de la Couronne, sous le plafond peint par Delacroix.",
    "etats": "La Joconde derrière sa vitre blindée, face aux immenses Noces de Cana de Véronèse.",
    "grande_galerie": "Un couloir de chefs-d'œuvre : Léonard de Vinci, Raphaël, Caravage, Vermeer...",
    "cariatides": "Sculptures antiques et les quatre Cariatides de Jean Goujon.",
    "sphinx": "Le Grand Sphinx de Tanis veille dans une crypte couverte de hiéroglyphes.",
    "daru": "La Victoire de Samothrace domine le grand escalier.",
}
PLAN = {  # position des salles sur le plan de la carte (0-1)
    "apollon": (0.69, 0.66), "etats": (0.47, 0.77), "grande_galerie": (0.18, 0.83),
    "cariatides": (0.75, 0.42), "sphinx": (0.86, 0.66), "daru": (0.58, 0.72),
}


class App:
    """Une seule fenêtre OpenGL pour tout le jeu. Le menu s'affiche par-dessus un survol de la galerie d'Apollon."""

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
        glEnable(GL_NORMALIZE)  # les modèles réduits (glScale) gardent un éclairage juste
        self.ui = UI()
        self.ui.resize(*pygame.display.get_window_size())
        self.loading(0.02, "Sons et musique...")
        self.audio = Audio(self.settings["volume"], self.settings["musique"])
        self.salles = {}
        self.salle = self.charger_salle("apollon", 0.1)
        self.foule_menu = self.foule = Foule(self.salle).peupler(self.salle.visiteurs, 0)  # des visiteurs derrière le menu
        if self.settings["fullscreen"]:
            pygame.display.toggle_fullscreen()

        self.clock = pygame.time.Clock()
        self.running = True
        self.t = 0.0
        self.menu_cam = Player(0.2, 0.0, 10.0)
        self.player = Player(0.0, 0.0, 0.0)
        self.mode = None  # None (menus), "mission" ou "visite"
        self.mission = None
        self.mission_index = 0
        self.carte_choix = self.prochaine_mission()
        self.state = "menu"
        self.tab, self.confirmer_reset = "Vidéo", False
        self.settings_back = "menu"
        self.waiting_key = None
        self.skip_motion = False
        self.want_screenshot = False
        self.torche = False
        self.cible = None
        self.particles = []
        self.notice_data = self.toast = None
        self.examen = self.deduction_retour = self.fin = None
        self.keys = pygame.key.get_pressed()
        self.pas_joueur, self.au_sol = 0, True
        self.audio.music("menu")

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
            rendu_gl = (glGetString(GL_RENDERER) or b"?").decode("ascii", "replace")
            pygame.display.message_box(
                "VirtuLouvre", f"OpenGL 2.0 minimum est nécessaire (trouvé : {version}, {rendu_gl}).\n"
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

    def charger_salle(self, nom, debut=0.0):
        """Construit une salle la première fois (avec un écran de chargement), puis la garde en mémoire."""
        if nom not in self.salles:
            titre = SALLES[nom][0]
            self.loading(debut + 0.1, f"{titre} : construction...")
            salle = construire(nom)
            self.loading(debut + 0.45, f"{titre} : envoi à la carte graphique...")
            salle.upload()
            self.loading(debut + 0.7, f"{titre} : textures et tableaux...")
            for mat in salle.seaux:
                rendu.texture(MATERIAUX_SALLE.get(mat, (mat,))[0])
            if salle.ciel:
                rendu.texture("fichier:src/textures/texture.png")
                rendu.texture("fichier:src/textures/sky.png")
            for m, *_ in salle.objets:
                if m.listes is None:
                    m.compiler()
            self.loading(1.0, "C'est prêt !")
            self.salles[nom] = salle
        return self.salles[nom]

    # --- Touches ---

    def refresh_codes(self):
        """Traduit les noms de touches des réglages en codes pygame (+ les flèches, toujours actives)."""
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

    # --- Progression ---

    def progres(self, index):
        return self.settings["progress"].get(CAMPAGNE[index].id)

    def debloquee(self, index):
        return index == 0 or bool(self.progres(index - 1))

    def prochaine_mission(self):
        for k in range(len(CAMPAGNE)):
            if not self.progres(k):
                return k
        return len(CAMPAGNE) - 1

    def total_etoiles(self):
        return sum(self.progres(k)["stars"] for k in range(len(CAMPAGNE)) if self.progres(k))

    # --- Changements d'écran ---

    def set_state(self, etat):
        self.state = etat
        en_jeu = etat == "play"
        pygame.mouse.set_relative_mode(en_jeu)  # souris capturée et cachée pendant le jeu
        if en_jeu:
            pygame.mouse.get_rel()
            self.skip_motion = True  # le premier mouvement après capture peut être un grand saut
        else:
            self.audio.boucle("lasers", 0)

    def to_menu(self):
        self.mode, self.mission = None, None
        self.salle = self.salles["apollon"]
        self.salle.reset()
        self.foule = self.foule_menu
        self.particles = []
        self.audio.music("menu")
        self.audio.ambiance(None)
        self.set_state("menu")

    def lancer_mission(self, index, point=0, essais=0):
        classe = CAMPAGNE[index]
        self.salle = self.charger_salle(classe.salle_id)
        self.salle.reset()
        self.mission_index = index
        self.mission = classe(self, point, essais)
        x, y, z, lacet = self.mission.depart()
        self.player = Player(x, y, z, lacet)
        self.foule = Foule(self.salle)  # la mission y ajoute ses figurants
        self.mission.demarrer()
        self.mode, self.torche = "mission", classe.lampe
        self.particles, self.notice_data, self.cible, self.toast = [], None, None, None
        self.audio.music(classe.musique)
        self.audio.ambiance(classe.ambiance)
        self.audio.sol = self.salle.sol_son
        self.set_state("play")

    def lancer_visite(self, nom):
        self.salle = self.charger_salle(nom)
        self.salle.reset()
        self.mission = None
        x, y, z, lacet = self.salle.depart
        self.player = Player(x, y, z, lacet)
        self.foule = Foule(self.salle).peupler(self.salle.visiteurs, random.randrange(1000))
        self.mode, self.torche, self.visit_start = "visite", False, self.t
        self.particles, self.notice_data, self.toast = [], None, None
        self.audio.music("menu")
        self.audio.ambiance("foule")
        self.audio.sol = self.salle.sol_son
        self.set_state("play")

    def open_settings(self, retour):
        self.settings_back = retour
        self.waiting_key, self.confirmer_reset = None, False
        self.set_state("settings")

    def close_settings(self):
        self.waiting_key = None  # sinon la touche suivante serait avalée, dans n'importe quel écran
        save_settings(self.settings)
        self.set_state(self.settings_back)

    def ouvrir_examen(self, titre, texte, sous_titre, suite):
        self.examen = (titre, texte, sous_titre, suite)
        self.set_state("examen")

    def fermer_examen(self):
        suite = self.examen[3]
        self.examen = None
        self.set_state("play")
        if suite:
            suite()

    def ouvrir_deduction(self, mission):
        self.deduction_retour = None
        self.set_state("deduction")

    def fin_mission(self, gagne, texte):
        m = self.mission
        self.fin = {"gagne": gagne, "texte": texte, "temps": m.temps, "etoiles": m.etoiles() if gagne else 0,
                    "record": False, "index": self.mission_index, "point": m.point, "essais": m.essais}
        if gagne:
            ancien = self.settings["progress"].get(m.id, {})
            meilleur = ancien.get("best")
            self.fin["record"] = meilleur is not None and m.temps < meilleur
            self.settings["progress"][m.id] = {"stars": max(self.fin["etoiles"], ancien.get("stars", 0)),
                                               "best": round(min(m.temps, meilleur or m.temps), 2)}
            save_settings(self.settings)
            self.audio.play("victoire")
            self.carte_choix = min(self.mission_index + 1, len(CAMPAGNE) - 1)
        else:
            self.audio.play("echec")
        self.set_state("end")

    def notice(self, titre, sous_titre="", couleur=GOLD):
        self.notice_data = (titre, sous_titre, couleur, self.t)

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
        self.audio.update()
        if self.state == "play":
            self.update_play(dt)
        elif self.mode is None:
            self.foule.update(dt)
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
        if self.waiting_key:  # changement de touche dans les réglages
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
        s = self.state
        if e.key == pygame.K_F11 or (entree and e.mod & pygame.KMOD_ALT):  # (sur Mac, F11 règle le volume)
            self.toggle_fullscreen()
        elif e.key == pygame.K_F12:
            self.want_screenshot = True
        elif e.key == pygame.K_ESCAPE:
            if s == "play":
                self.set_state("pause")
            elif s == "pause":
                self.set_state("play")
            elif s == "settings":
                self.close_settings()
            elif s == "examen":
                self.fermer_examen()
            elif s in ("briefing",):
                self.set_state("carte")
            elif s in ("carte", "visite_choix", "credits", "fin"):
                self.to_menu()
            elif s == "end":
                self.to_menu()
                self.set_state("carte")
        elif s == "examen" and (entree or e.key in self.codes["interact"] or e.key == pygame.K_SPACE):
            self.fermer_examen()
        elif entree and s == "briefing":
            self.lancer_mission(self.carte_choix)
        elif s == "play":
            joueur = self.player
            if e.key in self.codes["interact"] and self.cible:
                self.cible.action()
            elif e.key in self.codes["jump"]:
                if joueur.on_ground and not joueur.crouch and not joueur.flying:
                    self.audio.play("saut")
                joueur.want_jump = True
            elif e.key in self.codes["torch"] and self.mode == "mission":
                self.torche = not self.torche
                self.audio.play("lampe")
            elif e.key in self.codes["fly"] and self.mode == "visite":
                if joueur.flying and not self.salle.libre(joueur.pos[0], joueur.pos[2], self.salle.sol_sous(*joueur.pos[[0, 2]])):
                    self.toast = ("Impossible d'atterrir ici", self.t)  # sinon on se poserait dans un mur
                else:
                    joueur.flying = not joueur.flying
                    joueur.vel[1] = 0.0

    # --- Mise à jour ---

    def update_play(self, dt):
        joueur = self.player
        joueur.update(dt, self.held, self.salle, can_fly=self.mode == "visite",
                      endurance=bool(self.mission and self.mission.endurance))
        self.bruits_de_pas(joueur)
        self.foule.update(dt, joueur, self.audio)
        m = self.mission
        if m:
            reste_avant = m.duree - m.temps if m.duree else None
            m.temps += dt
            if m.duree:
                reste = m.duree - m.temps
                if reste <= 0:
                    m.perdre(m.fin_temps)
                    return
                if math.ceil(reste) < math.ceil(reste_avant) <= 10:
                    self.audio.play("tick")  # les dix dernières secondes
            m.update(dt)
            if self.state != "play":
                return
        self.cible = self.chercher_cible()

    def bruits_de_pas(self, joueur):
        """Un bruit de pas à chaque foulée (au rythme du balancement de la caméra), selon le sol de la salle."""
        pas = int(joueur.bob / math.pi)
        if joueur.walking and pas != self.pas_joueur:
            self.audio.pas(self.salle.sol_son, 0.35 if joueur.crouch else 1.2 if joueur.sprinting else 0.75)
        self.pas_joueur = pas
        if joueur.on_ground and not self.au_sol and not joueur.flying:
            self.audio.play("atterrir_" + self.salle.sol_son)
        self.au_sol = joueur.on_ground or joueur.flying

    def chercher_cible(self):
        """L'interaction que le joueur regarde (la plus centrée, à portée et à découvert)."""
        if not self.mission:
            return None
        oeil, avant = self.player.eye(), self.player.front()
        meilleure, score = None, 1e9
        for inter in self.mission.interactions():
            vers = inter.position - oeil
            distance = float(np.linalg.norm(vers)) or 1e-6
            alignement = float(vers @ avant) / distance
            if distance > inter.rayon or (alignement < 0.93 and not (distance < 1.3 and alignement > 0.5)):
                continue
            if not self.salle.vue_libre(oeil, inter.position, marge=0.45):
                continue
            s = (1 - alignement) * 10 + distance * 0.2
            if s < score:
                meilleure, score = inter, s
        return meilleure

    def burst(self, pos, couleur):
        """Gerbe d'étincelles."""
        for _ in range(40):
            direction = np.random.normal(size=3)
            direction /= np.linalg.norm(direction)
            vie = random.uniform(0.6, 1.1)
            self.particles.append([np.array(pos, dtype=float), direction * random.uniform(0.8, 2.6) + (0, 1.2, 0),
                                   vie, vie, couleur])

    def update_particles(self, dt):
        for p in self.particles:
            p[1][1] -= 3.0 * dt
            p[0] += p[1] * dt
            p[2] -= dt
        self.particles = [p for p in self.particles if p[2] > 0]

    def update_menu_camera(self):
        """Lent survol de la galerie d'Apollon derrière le menu."""
        t, cam = self.t, self.menu_cam
        cam.pos[:] = (0.2 + 0.9 * math.sin(t * 0.11), 0.9 + 0.5 * math.sin(t * 0.07), -1.5 + 16 * math.sin(t * 0.04))
        cam.oeil_y = cam.pos[1] + 1.5
        cam.yaw = -90 + 28 * math.sin(t * 0.05)
        cam.pitch = 10 + 8 * math.sin(t * 0.09)

    # --- Dessin 3D ---

    def render(self):
        if self.mode is None:
            self.update_menu_camera()
        self.draw_scene(self.player if self.mode else self.menu_cam)
        ui = self.ui
        ui.surface.fill((0, 0, 0, 0))
        if self.state in ("play", "pause", "examen", "deduction"):
            self.screen_hud()
        {
            "menu": self.screen_menu, "settings": self.screen_settings, "credits": self.screen_credits,
            "carte": self.screen_carte, "briefing": self.screen_briefing, "visite_choix": self.screen_visites,
            "play": lambda: None, "pause": self.screen_pause, "end": self.screen_end, "examen": self.screen_examen,
            "deduction": self.screen_deduction, "fin": self.screen_fin,
        }[self.state]()
        if self.toast and self.t - self.toast[1] < 2.5:
            ui.text(self.toast[0], 20, (ui.W / 2, ui.H - 118), IVORY)
        ui.draw()

    def draw_scene(self, cam):
        salle, m = self.salle, self.mission
        largeur, hauteur = self.ui.window
        glViewport(0, 0, largeur, hauteur)
        glClearColor(*salle.fond, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        oeil, avant = cam.eye(), cam.front()
        rendu.camera(oeil, avant, self.settings["fov"], largeur / hauteur)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glDisable(GL_CULL_FACE)
        nuit = self.mode == "mission"
        if salle.ciel:  # ciel : une sphère centrée sur la caméra, dessinée sans profondeur (toujours au fond)
            if salle.meshes is None:
                salle.upload()
            glDisable(GL_LIGHTING)
            glDepthMask(GL_FALSE)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, rendu.texture("fichier:src/textures/sky.png"))
            glColor3f(*((0.06, 0.07, 0.12) if nuit else (1, 1, 1)))
            glPushMatrix()
            glTranslatef(*oeil)
            glCallList(salle.sky_list)
            glPopMatrix()
            glDisable(GL_TEXTURE_2D)
            glDepthMask(GL_TRUE)
        rendu.brouillard(salle.fond, salle.brume)
        intensite = m.eclairage if nuit else 1.0
        points = [(p, tuple(c * intensite for c in couleur), portee) for p, couleur, portee in salle.lumieres_proches(oeil)]
        rendu.eclairage(salle.ambiante_nuit if nuit else salle.ambiante_visite,
                        ((1.5, 1.42, 1.25), 10.0) if self.torche and nuit else None,
                        points if intensite > 0 else [], m.spots() if m else [])
        salle.draw()
        self.foule.draw()
        if m:
            m.draw3d(cam)
        glDisable(GL_LIGHTING)
        salle.draw_transparent()
        droite = np.cross(avant, (0.0, 1.0, 0.0))
        droite /= np.linalg.norm(droite) or 1.0
        haut = np.cross(droite, avant)
        rendu.debut_additif()
        if m:
            m.effets(cam, droite, haut)
        rendu.halos([(p[0], 0.07, p[4], p[2] / p[3]) for p in self.particles], droite, haut)
        rendu.fin_additif()
        glDisable(GL_FOG)

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
        ui.bar((x, y, largeur, 10), avancement, GOLD)
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
        ui.icon("icon", (74, 118, 60, 60))
        ui.text("VirtuLouvre", 84, (146, 150), GOLD, "midleft", serif=True)
        ui.text("Six nuits pour sauver les trésors du Louvre", 24, (80, 212), IVORY, "midleft")
        y = 290
        faites = sum(1 for k in range(len(CAMPAGNE)) if self.progres(k))
        for texte, action in (
            ("Campagne : les nuits du Louvre" if faites == 0 else f"Continuer la campagne (nuit {min(faites + 1, 6)})",
             lambda: self.set_state("carte")),
            ("Visite libre", lambda: self.set_state("visite_choix")),
            ("Paramètres", lambda: self.open_settings("menu")),
            ("Crédits", lambda: self.set_state("credits")),
            ("Quitter", lambda: setattr(self, "running", False)),
        ):
            if ui.button(texte, (66, y), 30, "midleft"):
                action()
            y += 56
        ui.text(f"Progression : {faites} nuit{'s' if faites > 1 else ''} sur {len(CAMPAGNE)}", 20, (80, ui.H - 70), DIM, "midleft")
        ui.star((88, ui.H - 40), 9)
        ui.text(f"{self.total_etoiles()} / {3 * len(CAMPAGNE)}", 20, (104, ui.H - 40), DIM, "midleft")
        ui.text(f"v{VERSION}  ·  F11 ou Alt+Entrée : plein écran", 18, (ui.W - 24, ui.H - 24), DIM, "bottomright")

    def screen_carte(self):
        """Carte de la campagne : plan schématique du Louvre et les six nuits."""
        ui = self.ui
        ui.rect((8, 8, 12, 225), (0, 0, ui.W, ui.H))
        if self.back_button():
            self.to_menu()
            return
        ui.text("Les nuits du Louvre", 46, (ui.W / 2, 62), GOLD, serif=True)
        px, py, pw, ph = 40, 110, ui.W * 0.58, 520
        P = lambda u, v: (px + u * pw, py + v * ph)
        seine = [P(u, 0.93 + 0.015 * math.sin(u * 20 + self.t)) for u in np.linspace(0, 1, 40)]
        ui.polygon((30, 50, 90), seine + [P(1, 1), P(0, 1)])
        ui.text("La Seine", 16, P(0.08, 0.965), (110, 140, 190), "midleft")
        batiment = (70, 62, 50)
        for (u0, v0, u1, v1) in ((0.36, 0.13, 0.73, 0.23), (0.36, 0.72, 0.73, 0.8), (0.02, 0.79, 0.36, 0.86),
                                  (0.73, 0.2, 0.97, 0.3), (0.73, 0.7, 0.97, 0.8), (0.73, 0.2, 0.79, 0.8), (0.91, 0.2, 0.97, 0.8)):
            a, b = P(u0, v0), P(u1, v1)
            ui.rect(batiment, (a[0], a[1], b[0] - a[0], b[1] - a[1]), rayon=3)
        ui.polygon((150, 170, 200), [P(0.52, 0.42), P(0.575, 0.52), P(0.465, 0.52)], 1.5)
        ui.text("Pyramide", 14, P(0.52, 0.56), DIM)
        ui.text("Cour Carrée", 14, P(0.85, 0.5), DIM)
        ui.text("Aile Richelieu", 14, P(0.55, 0.18), DIM)
        ui.text("Aile Denon", 14, P(0.395, 0.76), DIM)
        chemin_points = [P(*PLAN[c.salle_id]) for c in CAMPAGNE]
        for a, b in zip(chemin_points, chemin_points[1:]):
            for k in range(0, 10, 2):
                ui.line(DIM, (a[0] + (b[0] - a[0]) * k / 10, a[1] + (b[1] - a[1]) * k / 10),
                        (a[0] + (b[0] - a[0]) * (k + 1) / 10, a[1] + (b[1] - a[1]) * (k + 1) / 10), 1.5)
        for k, (classe, (x, y)) in enumerate(zip(CAMPAGNE, chemin_points)):
            ouvert, prog = self.debloquee(k), self.progres(k)
            r = 17
            if k == self.carte_choix:
                ui.circle(GOLD, (x, y), r + 6 + 2 * math.sin(self.t * 4), 2)
            ui.circle(GOLD if prog else (40, 38, 34) if ouvert else (28, 28, 30), (x, y), r)
            ui.circle(GOLD if ouvert else DIM, (x, y), r, 2)
            ui.text(str(k + 1), 22, (x, y + 1), (20, 18, 14) if prog else IVORY if ouvert else DIM, serif=True)
            if ui.hit((x - r - 4, y - r - 4, 2 * r + 8, 2 * r + 8)) and ouvert:
                self.carte_choix = k
        # fiche de la nuit choisie
        k = self.carte_choix
        classe, prog = CAMPAGNE[k], self.progres(k)
        x0 = px + pw + 40
        largeur = ui.W - x0 - 40
        ui.panel((x0, 110, largeur, 520))
        cx = x0 + largeur / 2
        ui.text(f"NUIT {classe.nuit}", 18, (cx, 146), GOLD)
        ui.text(classe.titre, 30, (cx, 184), IVORY, serif=True)
        ui.text(SALLES[classe.salle_id][0], 20, (cx, 218), DIM)
        y = ui.paragraph(classe.intro, 18, (cx, 250), largeur - 50, IVORY)
        ui.stars((cx, y + 26), prog["stars"] if prog else 0, 14)
        if prog and prog.get("best"):
            ui.text(f"Meilleur temps : {fmt_time(prog['best'])}", 18, (cx, y + 58), DIM)
        if self.debloquee(k):
            if ui.button("Commencer la nuit", (cx, 590), 28, couleur=GOLD):
                self.set_state("briefing")
        else:
            ui.text("Termine la nuit précédente pour débloquer celle-ci.", 18, (cx, 590), DIM)
        ui.text(f"{self.total_etoiles()} / {3 * len(CAMPAGNE)}", 22, (ui.W / 2 + 14, 660), GOLD, "midleft")
        ui.star((ui.W / 2, 660), 11)

    def screen_briefing(self):
        ui = self.ui
        classe = CAMPAGNE[self.carte_choix]
        ui.rect((0, 0, 0, 150), (0, 0, ui.W, ui.H))
        panneau = pygame.FRect(0, 0, 820, 540)
        panneau.center = (ui.W / 2, ui.H / 2)
        ui.panel(panneau)
        cx, y = panneau.centerx, panneau.y
        ui.text(classe.heure.upper(), 18, (cx, y + 44), GOLD)
        ui.text(classe.titre, 44, (cx, y + 88), IVORY, serif=True)
        ui.text(SALLES[classe.salle_id][0] + " — " + SALLES[classe.salle_id][1], 18, (cx, y + 124), DIM)
        y2 = ui.paragraph(classe.intro, 22, (cx, y + 158), 700, IVORY)
        ui.text("Objectif : " + classe.objectif + (f" en moins de {fmt_time(classe.duree)}" if classe.duree else ""),
                24, (cx, y2 + 16), GOLD)
        y3 = y2 + 56
        for astuce in classe.astuces:
            y3 = ui.paragraph(astuce, 18, (cx, y3), 700, DIM) + 4
        ui.text(f"{self.move_text()} : se déplacer  ·  {self.key_text('interact')} : examiner  ·  "
                f"{self.key_text('torch')} : lampe  ·  Échap : pause", 16, (cx, panneau.bottom - 92), DIM)
        if ui.button("Commencer (Entrée)", (cx + 120, panneau.bottom - 48), 28, couleur=GOLD):
            self.lancer_mission(self.carte_choix)
        elif ui.button("Retour", (cx - 160, panneau.bottom - 48), 28):
            self.set_state("carte")

    def screen_visites(self):
        ui = self.ui
        ui.rect((8, 8, 12, 215), (0, 0, ui.W, ui.H))
        if self.back_button():
            self.to_menu()
            return
        ui.text("Visite libre", 48, (ui.W / 2, 70), GOLD, serif=True)
        ui.text("Promène-toi où tu veux, vole avec G, et regarde les œuvres pour lire leur cartel.", 20, (ui.W / 2, 116), DIM)
        noms = list(SALLES)
        largeur, hauteur = 360, 190
        for k, nom in enumerate(noms):
            colonne, ligne = k % 3, k // 3
            x = ui.W / 2 + (colonne - 1) * (largeur + 24) - largeur / 2
            y = 160 + ligne * (hauteur + 24)
            r = (x, y, largeur, hauteur)
            survol = ui.hovered(r)
            ui.rect((255, 255, 255, 26 if survol else 12), r, rayon=14)
            ui.rect(GOLD if survol else (80, 74, 60), r, rayon=14, epaisseur=1)
            titre, lieu, _ = SALLES[nom]
            ui.text(titre, 26, (x + largeur / 2, y + 40), GOLD if survol else IVORY, serif=True)
            ui.text(lieu, 16, (x + largeur / 2, y + 72), DIM)
            ui.paragraph(DESCRIPTIONS[nom], 17, (x + largeur / 2, y + 100), largeur - 40, IVORY)
            if ui.hit(r):
                self.lancer_visite(nom)
                return

    def row(self, libelle, y):
        """Ligne de réglage : fond, libellé à gauche ; renvoie l'abscisse du bord droit."""
        ui = self.ui
        x0 = ui.W / 2 - 330
        ui.rect((255, 255, 255, 14), (x0, y - 21, 660, 42), rayon=10)
        ui.text(libelle, 24, (x0 + 22, y), IVORY, "midleft")
        return x0 + 638

    def screen_settings(self):
        ui, s = self.ui, self.settings
        ui.rect((8, 8, 12, 225), (0, 0, ui.W, ui.H))
        if self.back_button():
            self.close_settings()
            return
        ui.text("Paramètres", 52, (ui.W / 2, 64), GOLD, serif=True)
        for k, onglet in enumerate(("Vidéo", "Audio", "Touches", "Partie")):
            if ui.button(onglet, (ui.W / 2 + (k - 1.5) * 160, 124), 28, couleur=GOLD if onglet == self.tab else DIM):
                self.tab, self.waiting_key, self.confirmer_reset = onglet, None, False
        ui.line(GOLD, (ui.W / 2 - 330, 150), (ui.W / 2 + 330, 150))
        if self.tab == "Vidéo":
            xd = self.row("Résolution", 200)
            if pygame.display.is_fullscreen():
                ui.text("plein écran", 24, (xd, 200), DIM, "midright")
            else:
                largeur, hauteur = pygame.display.get_window_size()
                if ui.icon("arrow_right", (xd - 22, 189, 22, 22), IVORY):
                    self.change_resolution(+1)
                ui.text(f"{largeur} × {hauteur}", 24, (xd - 95, 200), IVORY)
                if ui.icon("arrow_left", (xd - 190, 189, 22, 22), IVORY):
                    self.change_resolution(-1)
            xd = self.row("Plein écran", 254)
            if ui.button("Oui" if pygame.display.is_fullscreen() else "Non", (xd + 14, 254), 24, "midright", BLUE):
                self.toggle_fullscreen()
            xd = self.row("Champ de vision", 308)
            s["fov"] = round(ui.slider("fov", (xd - 290, 304, 220, 8), s["fov"], 50, 100))
            ui.text(f"{s['fov']}°", 24, (xd, 308), IVORY, "midright")
            xd = self.row("Sensibilité de la souris", 362)
            s["sensitivity"] = ui.slider("sensi", (xd - 290, 358, 220, 8), s["sensitivity"], 0.03, 0.36)
            ui.text(f"{round(s['sensitivity'] / 0.12 * 100)} %", 24, (xd, 362), IVORY, "midright")
        elif self.tab == "Audio":
            for y, libelle, cle in ((200, "Volume général", "volume"), (254, "Musique", "musique")):
                xd = self.row(libelle, y)
                valeur = ui.slider(cle, (xd - 290, y - 4, 220, 8), s[cle], 0.0, 1.0)
                if valeur != s[cle]:
                    s[cle] = valeur
                    self.audio.set_volume(s["volume"], s["musique"])
                ui.text(f"{round(valeur * 100)} %", 24, (xd, y), IVORY, "midright")
            if ui.button("Tester le son", (ui.W / 2, 324), 24, couleur=BLUE):
                self.audio.play("joyau")
        elif self.tab == "Partie":
            nuits = sum(bool(self.progres(k)) for k in range(len(CAMPAGNE)))
            ui.text(f"Progression : {nuits} nuit{'s' if nuits > 1 else ''} sur {len(CAMPAGNE)}  ·  "
                    f"{self.total_etoiles()} / {3 * len(CAMPAGNE)} étoiles", 24, (ui.W / 2, 210), IVORY)
            if self.confirmer_reset:  # deux clics : on n'efface pas tout par erreur
                ui.text("Effacer toutes les nuits, étoiles et records ?", 22, (ui.W / 2, 280), RED)
                if ui.button("Oui, tout effacer", (ui.W / 2 - 20, 330), 24, "midright", RED):
                    s["progress"] = {}
                    save_settings(s)
                    self.carte_choix, self.confirmer_reset = 0, False
                    self.toast = ("Progression réinitialisée", self.t)
                if ui.button("Annuler", (ui.W / 2 + 20, 330), 24, "midleft", BLUE):
                    self.confirmer_reset = False
            elif ui.button("Réinitialiser la progression", (ui.W / 2, 290), 24, couleur=BLUE):
                self.confirmer_reset = True
        else:
            y = 184
            for action, libelle, _ in ACTIONS:
                xd = self.row(libelle, y)
                attente = self.waiting_key == action
                texte = "appuie sur une touche..." if attente else self.key_text(action)
                if ui.button(texte, (xd + 14, y), 22, "midright", GOLD if attente else BLUE):
                    self.waiting_key = action
                y += 44
            if ui.button("Touches par défaut", (ui.W / 2, y + 2), 22, couleur=BLUE):
                s["controls"] = {action: list(touches) for action, _, touches in ACTIONS}
                self.refresh_codes()
            ui.text("Les flèches marchent toujours  ·  Échap : pause  ·  F11 ou Alt+Entrée : plein écran  ·  F12 : capture",
                    17, (ui.W / 2, y + 38), DIM)

    def screen_credits(self):
        ui = self.ui
        ui.rect((8, 8, 12, 225), (0, 0, ui.W, ui.H))
        if self.back_button():
            self.set_state("menu")
            return
        gauche, droite = ui.W * 0.28, ui.W * 0.68
        ui.text("Crédits", 48, (gauche, 100), GOLD, serif=True)
        y = 158
        for titre, lignes in (
            ("Développé par", ["Albert Oscar", "Moors Michel", "Rinckenbach Yann"]),
            ("Projet de NSI", ["Trophées NSI"]),
            ("Galerie d'Apollon", ["Scan 3D de la galerie, musée du Louvre"]),
            ("Salles, personnages, statues et joyaux", ["Modélisés en code (Python + NumPy)"]),
            ("Tableaux", ["Reproductions du domaine public, Wikimedia Commons"]),
            ("Réalisé avec", ["Python · pygame-ce · PyOpenGL · NumPy"]),
        ):
            ui.text(titre, 18, (gauche, y), GOLD)
            y += 26
            for ligne in lignes:
                ui.text(ligne, 22, (gauche, y))
                y += 26
            y += 10
        ui.text("Merci d'avoir joué !", 30, (gauche, y + 16), IVORY, serif=True)
        ui.text("L'histoire", 48, (droite, 100), GOLD, serif=True)
        texte = ("Le 19 octobre 2025, huit joyaux de la Couronne ont vraiment été volés dans la galerie d'Apollon. "
                 "Ce jeu part de cet événement pour inventer une histoire : le Cercle, ses six nuits d'enquête et "
                 "ses personnages sont imaginaires.\n\nLes salles modélisées sont des évocations libres des vraies "
                 "salles du Louvre, et les joyaux des interprétations des originaux. Les tableaux, eux, sont les vrais : "
                 "regarde-les de près pour lire leur cartel.")
        ui.paragraph(texte, 20, (droite, 158), ui.W * 0.4, IVORY)

    def screen_hud(self):
        ui = self.ui
        ui.overlay("vignette")
        cx, cy = ui.W / 2, ui.H / 2
        m = self.mission
        if self.state == "play":
            for a, b in (((-7, 0), (-2, 0)), ((2, 0), (7, 0)), ((0, -7), (0, -2)), ((0, 2), (0, 7))):
                ui.line((255, 255, 255), (cx + a[0], cy + a[1]), (cx + b[0], cy + b[1]))
        if m:
            m.hud(ui)
            ui.text(f"NUIT {m.nuit} · {m.titre.upper()}", 16, (40, 30), GOLD, "topleft")
            ui.text(m.objectif, 22, (40, 50), IVORY, "topleft")
            ui.text(m.progression, 30, (40, 74), IVORY, "topleft", serif=True)
            if m.duree:
                reste = max(0.0, m.duree - m.temps)
                urgent = reste <= 30
                ui.text("TEMPS RESTANT", 16, (ui.W - 40, 30), GOLD, "topright")
                ui.text(fmt_time(math.ceil(reste)), 46, (ui.W - 40, 50), RED if urgent else IVORY, "topright", serif=True,
                        alpha=int(255 * (0.6 + 0.4 * abs(math.sin(self.t * 4)))) if urgent else 255)
            ui.text(f"Lampe {'allumée' if self.torche else 'éteinte'} ({self.key_text('torch')})", 16, (40, ui.H - 30),
                    GOLD if self.torche else DIM, "midleft")
            if self.notice_data and self.t - self.notice_data[3] < 3:
                titre, sous_titre, couleur, debut = self.notice_data
                alpha = int(255 * min(1.0, 3 - (self.t - debut)))
                ui.text(titre, 30, (cx, 150), couleur, serif=True, alpha=alpha)
                if sous_titre:
                    ui.text(sous_titre, 22, (cx, 184), IVORY, alpha=alpha)
        else:
            depuis = self.t - self.visit_start
            ui.text(self.salle.titre, 30, (40, 34), GOLD, "topleft", serif=True)
            ui.text(self.salle.lieu, 18, (40, 72), DIM, "topleft")
            if depuis < 10:
                ui.text(f"{self.move_text()} : se déplacer  ·  {self.key_text('fly')} : voler  ·  {self.key_text('jump')} / "
                        f"{self.key_text('crouch')} : monter / descendre  ·  Échap : menu",
                        20, (cx, ui.H - 40), IVORY, alpha=int(255 * min(1.0, 10 - depuis)))
            if self.player.flying:
                ui.text("MODE VOL", 20, (cx, 36), GOLD)
        if self.state != "play":
            return
        if self.cible:  # ce qu'on peut faire avec E
            texte = f"{self.key_text('interact')}   {self.cible.texte}"
            largeur = ui.largeur_texte(texte, 24) + 36
            ui.rect((10, 10, 16, 200), (cx - largeur / 2, cy + 46, largeur, 40), rayon=20)
            ui.rect(GOLD, (cx - largeur / 2, cy + 46, largeur, 40), rayon=20, epaisseur=1)
            ui.text(texte, 24, (cx, cy + 66), GOLD)
        else:
            self.cartel(ui)

    def cartel(self, ui):
        """Titre de l'œuvre regardée (tableaux et statues à moins de 7 mètres)."""
        oeil, avant = self.player.eye(), self.player.front()
        trouve = None
        for centre, normale, largeur, hauteur, titre, artiste, date in self.salle.oeuvres:
            vers = centre - oeil
            distance = float(np.linalg.norm(vers)) or 1e-6
            if distance < 7 and normale @ -vers > 0:
                angle = math.degrees(math.acos(min(1.0, float(vers @ avant) / distance)))
                if angle < math.degrees(math.atan(max(largeur, hauteur) / 2 / distance)) + 2:
                    trouve = (titre, f"{artiste}, {date}")
        for position, titre, texte in self.salle.cartels:
            vers = position - oeil
            distance = float(np.linalg.norm(vers)) or 1e-6
            if distance < 6 and float(vers @ avant) / distance > 0.94:
                trouve = (titre, texte)
        if trouve:
            titre, texte = trouve
            ui.rect((10, 10, 16, 180), (ui.W / 2 - 330, ui.H - 236, 660, 92), rayon=12)
            ui.text(titre, 26, (ui.W / 2, ui.H - 208), GOLD, serif=True)
            ui.paragraph(texte, 17, (ui.W / 2, ui.H - 184), 620, IVORY)

    def screen_pause(self):
        ui = self.ui
        ui.rect((0, 0, 0, 160), (0, 0, ui.W, ui.H))
        ui.text("Pause", 60, (ui.W / 2, 170), GOLD, serif=True)
        if self.mission:
            choix = [("Reprendre", lambda: self.set_state("play")),
                     ("Recommencer la nuit", lambda: self.lancer_mission(self.mission_index)),
                     ("Paramètres", lambda: self.open_settings("pause")),
                     ("Quitter la mission", lambda: (self.to_menu(), self.set_state("carte")))]
        else:
            choix = [("Reprendre", lambda: self.set_state("play")),
                     ("Changer de salle", lambda: (self.to_menu(), self.set_state("visite_choix"))),
                     ("Paramètres", lambda: self.open_settings("pause"))]
        choix.append(("Menu principal", self.to_menu))
        for k, (texte, action) in enumerate(choix):
            if ui.button(texte, (ui.W / 2, 270 + k * 56), 30):
                action()
                return

    def screen_examen(self):
        ui = self.ui
        titre, texte, sous_titre, _ = self.examen
        ui.rect((0, 0, 0, 120), (0, 0, ui.W, ui.H))
        panneau = pygame.FRect(0, 0, 640, 330)
        panneau.center = (ui.W / 2, ui.H / 2)
        ui.panel(panneau)
        ui.text(titre, 36, (panneau.centerx, panneau.y + 56), GOLD, serif=True)
        y = ui.paragraph(texte, 22, (panneau.centerx, panneau.y + 100), 560, IVORY)
        ui.text(sous_titre, 18, (panneau.centerx, max(y + 20, panneau.bottom - 96)), DIM)
        if ui.button("Continuer", (panneau.centerx, panneau.bottom - 44), 26, couleur=GOLD):
            self.fermer_examen()

    def screen_deduction(self):
        ui, m = self.ui, self.mission
        ui.rect((0, 0, 0, 150), (0, 0, ui.W, ui.H))
        panneau = pygame.FRect(0, 0, 760, 470)
        panneau.center = (ui.W / 2, ui.H / 2)
        ui.panel(panneau)
        if m.question >= len(QUESTIONS):
            return
        question, choix, _, _ = QUESTIONS[m.question]
        cx = panneau.centerx
        ui.text(f"DÉDUCTION {m.question + 1} / {len(QUESTIONS)}", 18, (cx, panneau.y + 40), GOLD)
        ui.text(question, 32, (cx, panneau.y + 86), IVORY, serif=True)
        for k, texte in enumerate(choix):
            if ui.button(texte, (cx, panneau.y + 160 + k * 60), 26):
                juste, explication = m.repondre(k)
                self.deduction_retour = (juste, explication, self.t)
                self.audio.play("loupe" if juste else "erreur")
                if m.fini:
                    return
        if self.deduction_retour and self.t - self.deduction_retour[2] < 4:
            juste, explication, _ = self.deduction_retour
            ui.paragraph(("Bien vu ! " if juste else "") + explication, 20, (cx, panneau.bottom - 86), 680,
                         GREEN if juste else RED)

    def screen_end(self):
        ui, f = self.ui, self.fin
        classe = CAMPAGNE[f["index"]]
        ui.rect((0, 0, 0, 180), (0, 0, ui.W, ui.H))
        cx = ui.W / 2
        if f["gagne"]:
            ui.text("Nuit réussie !", 56, (cx, 110), GOLD, serif=True)
            ui.stars((cx, 170), f["etoiles"], 20)
            record = "  ·  nouveau record !" if f["record"] else ""
            ui.text(f"{classe.titre} en {fmt_time(f['temps'])}{record}", 22, (cx, 214), IVORY)
        else:
            ui.text("Mission ratée...", 56, (cx, 120), RED, serif=True)
            ui.text(classe.titre, 22, (cx, 180), DIM)
        ui.paragraph(f["texte"], 24, (cx, 270), 760, IVORY)
        boutons = []
        if f["gagne"]:
            if f["index"] + 1 < len(CAMPAGNE):
                boutons.append(("Nuit suivante", lambda: (setattr(self, "carte_choix", f["index"] + 1), self.set_state("briefing"))))
            else:
                boutons.append(("Voir la fin", lambda: self.set_state("fin")))
            boutons.append(("Rejouer", lambda: self.lancer_mission(f["index"])))
        else:
            if f["point"] > 0:
                boutons.append(("Reprendre au point de contrôle", lambda: self.lancer_mission(f["index"], f["point"], f["essais"] + 1)))
            boutons.append(("Réessayer", lambda: self.lancer_mission(f["index"], 0, f["essais"] + 1)))
        boutons.append(("Carte", lambda: (self.to_menu(), self.set_state("carte"))))
        largeur = 300
        for k, (texte, action) in enumerate(boutons):
            x = cx + (k - (len(boutons) - 1) / 2) * largeur
            if ui.button(texte, (x, ui.H - 80), 26, couleur=GOLD if k == 0 else IVORY):
                action()
                return

    def screen_fin(self):
        ui = self.ui
        ui.rect((0, 0, 0, 200), (0, 0, ui.W, ui.H))
        cx = ui.W / 2
        ui.text("Fin", 72, (cx, 110), GOLD, serif=True)
        y = ui.paragraph("Six nuits, six salles, et le Cercle sous les verrous. Au matin, les premiers visiteurs entrent "
                         "sans se douter de rien : la Joconde sourit toujours, la Victoire déploie ses ailes au-dessus de "
                         "l'escalier, et les joyaux brillent de nouveau dans la galerie d'Apollon.", 24, (cx, 180), 760, IVORY)
        ui.stars((cx, y + 40), 3, 18)
        ui.text(f"{self.total_etoiles()} étoiles sur {3 * len(CAMPAGNE)}", 22, (cx, y + 84), GOLD)
        ui.text("Merci d'avoir joué !", 30, (cx, y + 140), IVORY, serif=True)
        ui.text("Albert Oscar · Moors Michel · Rinckenbach Yann", 20, (cx, y + 180), DIM)
        if ui.button("Retour au menu", (cx, ui.H - 70), 28, couleur=GOLD):
            self.to_menu()


# Projet : VirtuLouvre
# Auteurs : Albert Oscar, Moors Michel, Rinckenbach Yann

# -*- coding: utf-8 -*-
import pygame  # Importer la bibliothèque Pygame
import pygame.mixer
import random
import time
import os  # Importer le module os
import cv2  # Importer la bibliothèque OpenCV
from pygame.locals import *  # Importer les constantes Pygame
from OpenGL.GL import *  # Importer les fonctions OpenGL
from OpenGL.GLU import *  # Importer les fonctions OpenGL Utility
import numpy as np  # Importer la bibliothèque NumPy
import math  # Importer le module math
import sys
import json  # Importer le module json pour la gestion des fichiers de configuration

pygame.init()  # Initialiser Pygame
pygame.mixer.init()

# Charger et définir l'icône de la fenêtre
icon = pygame.image.load("src/icons/icon.png")
pygame.display.set_icon(icon)

walk_sound_effect = pygame.mixer.Sound("src/media/walk.mp3")
walk_sound_effect.set_volume(0.5)
# Centrer la fenêtre
os.environ["SDL_VIDEO_CENTERED"] = "1"
last_walk_sound_time = 0

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 200, 255)
HOVER_BLUE = (50, 150, 255)
GREEN = (0, 255, 0)


# Police
FONT = pygame.font.Font(None, 24)  # Réduit de 36 à 24
font = pygame.font.Font(None, 24)  # Réduit de 36 à 24

# Taille de la fenêtre
screenwidth = 2560
screenheight = 1440

current_state = "game"  # États possibles: "game", "game_menu", "settings"
slider_value = 110  # Valeur initiale du FOV
is_dragging = False  # État du curseur

# Au début du fichier, après les autres variables globales
master_volume = 0.5  # Volume par défaut à 50%

# Définition des contrôles par défaut
DEFAULT_CONTROLS = [
    ("Z", "Avancer"),
    ("S", "Reculer"),
    ("Q", "Gauche"),
    ("D", "Droite"),
    ("V", "Sprint"),
    ("ESPACE", "Voler"),
    ("SHIFT", "Descendre"),
    ("G", "Atterrir"),
    ("ÉCHAP", "Menu"),
    ("F11", "Plein écran"),
]

# Définition des contrôles actuels (initialisés avec les valeurs par défaut)
controls = DEFAULT_CONTROLS.copy()

# Variables globales pour le menu des contrôles
frame_x = 0
frame_y = 0
frame_width = 500
frame_height = 0
spacing = 40

# Variables globales pour la saisie de texte du volume
input_active = False
input_text = ""


class Player:

    def __init__(self, fov, aspect, near, far, vertices=None):
        self.fov = 110  # Champ de vision initial
        self.aspect = aspect  # Aspect ratio
        self.near = near  # Plan de vue proche
        self.far = 10000  # Plan de vue éloigné
        self.is_sprinting = False  # Initialiser le sprint à False
        self.base_speed = 0.1  # Vitesse de base
        self.sprint_multiplier = 3.0  # Multiplicateur de sprint
        self.initial_height = 0  # Hauteur initiale
        self.position = np.array(
            [0.0, self.initial_height, 5.0], dtype=np.float32
        )  # Position initiale
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=np.float32)  # Vitesse initiale
        self.acceleration = 0.1  # Accélération
        self.deceleration = 0.5  # Décélération
        self.max_velocity = 0.5  # Vitesse maximale
        self.front = np.array(
            [0.0, 0.0, -1.0], dtype=np.float32
        )  # Vecteur de direction
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)  # Vecteur vertical
        self.right = np.array([1.0, 0.0, 0.0], dtype=np.float32)  # Vecteur droit
        self.yaw = -90.0  # Angle de lacet
        self.pitch = 0.0  # Angle de tangage
        self.mouse_sensitivity = 0.05  # Sensibilité de la souris
        self.vertices = vertices or []  # Vertices
        self.last_valid_position = self.position.copy()  # Dernière position valide
        self.fly_speed = 0.1  # Vitesse de vol
        self.gravity = 0.08  # Gravité
        self.is_flying = True  # Initialiser le vol à True
        self.ground_level = 0.0  # Niveau du sol

    # Appliquer la projection
    def apply_projection(self):
        glMatrixMode(GL_PROJECTION)  # Changer le mode de la matrice à la projection
        glLoadIdentity()  # Réinitialiser la matrice
        gluPerspective(
            self.fov, self.aspect, self.near, self.far
        )  # Appliquer la perspective
        glMatrixMode(GL_MODELVIEW)  # Changer le mode de la matrice au modèle

    # Appliquer la vue
    def update_camera_vectors(self):
        self.front[0] = math.cos(math.radians(self.yaw)) * math.cos(
            math.radians(self.pitch)
        )  # Calculer la direction x
        self.front[1] = math.sin(math.radians(self.pitch))  # Calculer la direction y
        self.front[2] = math.sin(math.radians(self.yaw)) * math.cos(
            math.radians(self.pitch)
        )  # Calculer la direction z
        self.front = self.front / np.linalg.norm(
            self.front
        )  # Normaliser le vecteur de direction
        self.right = np.cross(
            self.front, np.array([0.0, 1.0, 0.0])
        )  # Calculer le vecteur droit
        self.right = self.right / np.linalg.norm(
            self.right
        )  # Normaliser le vecteur droit
        self.up = np.cross(self.right, self.front)  # Calculer le vecteur vertical

    # Mettre à jour la position du joueur
    def update(self, delta_time):
        new_position = self.position + self.velocity  # Calculer la nouvelle position
        if not self.is_flying:  # Si le joueur ne vole pas
            new_position[1] -= self.gravity  # Appliquer la gravité
            if (
                new_position[1] < self.ground_level + self.initial_height
            ):  # Si le joueur est au sol
                new_position[1] = (
                    self.ground_level + self.initial_height
                )  # Mettre à jour la position y
                self.velocity[1] = 0  # Réinitialiser la vitesse y
        if not self.check_collision(
            new_position
        ):  # Si le joueur n'est pas en collision
            self.last_valid_position = (
                new_position.copy()
            )  # Mettre à jour la dernière position valide
            self.position = new_position  # Mettre à jour la position
        else:
            self.position = (
                self.last_valid_position.copy()
            )  # Revenir à la dernière position valide
            self.velocity = np.zeros(3)  # Réinitialiser la vitesse
        self.velocity *= 1 - self.deceleration  # Appliquer la décélération

    # Mettre à jour la souris
    def process_mouse(self, xoffset, yoffset):
        self.yaw += xoffset * self.mouse_sensitivity  # Mettre à jour l'angle de lacet
        self.pitch += (
            yoffset * self.mouse_sensitivity
        )  # Mettre à jour l'angle de tangage
        if self.pitch > 89.0:  # Limiter l'angle de tangage
            self.pitch = 89.0  # Limiter l'angle de tangage
        if self.pitch < -89.0:  # Limiter l'angle de tangage
            self.pitch = -89.0  # Limiter l'angle de tangage
        self.update_camera_vectors()  # Mettre à jour les vecteurs de la cam

    # Mettre à jour le clavier
    def process_keyboard(self, keys):
        current_speed = self.base_speed * (
            self.sprint_multiplier if self.is_sprinting else 1.0
        )  # Calculer la vitesse actuelle

        # Convertir les touches personnalisées en codes Pygame
        key_mapping = {
            "Z": pygame.K_z,
            "S": pygame.K_s,
            "Q": pygame.K_q,
            "D": pygame.K_d,
            "V": pygame.K_v,
            "ESPACE": pygame.K_SPACE,
            "SHIFT": pygame.K_LSHIFT,
            "G": pygame.K_g,
            "ÉCHAP": pygame.K_ESCAPE,
            "F11": pygame.K_F11,
            # Ajout des touches supplémentaires
            "A": pygame.K_a,
            "B": pygame.K_b,
            "C": pygame.K_c,
            "E": pygame.K_e,
            "F": pygame.K_f,
            "H": pygame.K_h,
            "I": pygame.K_i,
            "J": pygame.K_j,
            "K": pygame.K_k,
            "L": pygame.K_l,
            "M": pygame.K_m,
            "N": pygame.K_n,
            "O": pygame.K_o,
            "P": pygame.K_p,
            "R": pygame.K_r,
            "T": pygame.K_t,
            "U": pygame.K_u,
            "W": pygame.K_w,
            "X": pygame.K_x,
            "Y": pygame.K_y,
            "0": pygame.K_0,
            "1": pygame.K_1,
            "2": pygame.K_2,
            "3": pygame.K_3,
            "4": pygame.K_4,
            "5": pygame.K_5,
            "6": pygame.K_6,
            "7": pygame.K_7,
            "8": pygame.K_8,
            "9": pygame.K_9,
            "F1": pygame.K_F1,
            "F2": pygame.K_F2,
            "F3": pygame.K_F3,
            "F4": pygame.K_F4,
            "F5": pygame.K_F5,
            "F6": pygame.K_F6,
            "F7": pygame.K_F7,
            "F8": pygame.K_F8,
            "F9": pygame.K_F9,
            "F10": pygame.K_F10,
            "F12": pygame.K_F12,
            "TAB": pygame.K_TAB,
            "CTRL": pygame.K_LCTRL,
            "ALT": pygame.K_LALT,
            "ENTER": pygame.K_RETURN,
            "BACKSPACE": pygame.K_BACKSPACE,
            "DELETE": pygame.K_DELETE,
            "INSERT": pygame.K_INSERT,
            "HOME": pygame.K_HOME,
            "END": pygame.K_END,
            "PAGEUP": pygame.K_PAGEUP,
            "PAGEDOWN": pygame.K_PAGEDOWN,
            "UP": pygame.K_UP,
            "DOWN": pygame.K_DOWN,
            "LEFT": pygame.K_LEFT,
            "RIGHT": pygame.K_RIGHT,
        }

        # Activer/Désactiver le sprint avec la touche personnalisée
        sprint_key = key_mapping.get(
            controls[4][0], pygame.K_v
        )  # Touche "V" par défaut
        if sprint_key and controls[4][0] != "-":  # Vérifier que la touche n'est pas "-"
            if keys[sprint_key]:
                self.is_sprinting = True
            else:
                self.is_sprinting = False

        # Gestion du vol et de l'atterrissage
        fly_key = key_mapping.get(
            controls[5][0], pygame.K_SPACE
        )  # Touche "ESPACE" par défaut
        land_key = key_mapping.get(controls[7][0], pygame.K_g)  # Touche "G" par défaut

        if land_key and controls[7][0] != "-":  # Vérifier que la touche n'est pas "-"
            if keys[land_key]:
                self.is_flying = False
        elif fly_key and controls[5][0] != "-":  # Vérifier que la touche n'est pas "-"
            if keys[fly_key]:
                self.is_flying = True

        if self.is_flying:
            if (
                fly_key and controls[5][0] != "-"
            ):  # Vérifier que la touche n'est pas "-"
                if keys[fly_key]:
                    self.position[1] += self.fly_speed
            if keys[pygame.K_LSHIFT]:
                self.position[1] -= self.fly_speed

        # Initialize movement direction vector
        move_dir = np.zeros(3, dtype=np.float32)

        # Calculer la direction de mouvement combinée avec les touches personnalisées
        forward_key = key_mapping.get(
            controls[0][0], pygame.K_z
        )  # Touche "Z" par défaut
        backward_key = key_mapping.get(
            controls[1][0], pygame.K_s
        )  # Touche "S" par défaut
        left_key = key_mapping.get(controls[2][0], pygame.K_q)  # Touche "Q" par défaut
        right_key = key_mapping.get(controls[3][0], pygame.K_d)  # Touche "D" par défaut

        if (
            forward_key and controls[0][0] != "-"
        ):  # Vérifier que la touche n'est pas "-"
            if keys[forward_key]:  # Forward
                forward_dir = np.array([self.front[0], 0, self.front[2]])
                if np.linalg.norm(forward_dir) > 0:
                    forward_dir = forward_dir / np.linalg.norm(forward_dir)
                    move_dir += forward_dir
                    walk_sound()

        if (
            backward_key and controls[1][0] != "-"
        ):  # Vérifier que la touche n'est pas "-"
            if keys[backward_key]:  # Backward
                backward_dir = np.array([self.front[0], 0, self.front[2]])
                if np.linalg.norm(backward_dir) > 0:
                    backward_dir = backward_dir / np.linalg.norm(backward_dir)
                    move_dir -= backward_dir
                    walk_sound()

        if left_key and controls[2][0] != "-":  # Vérifier que la touche n'est pas "-"
            if keys[left_key]:  # Left
                left_dir = np.array([self.right[0], 0, self.right[2]])
                if np.linalg.norm(left_dir) > 0:
                    left_dir = left_dir / np.linalg.norm(left_dir)
                    move_dir -= left_dir
                    walk_sound()

        if right_key and controls[3][0] != "-":  # Vérifier que la touche n'est pas "-"
            if keys[right_key]:  # Right
                right_dir = np.array([self.right[0], 0, self.right[2]])
                if np.linalg.norm(right_dir) > 0:
                    right_dir = right_dir / np.linalg.norm(right_dir)
                    move_dir += right_dir
                    walk_sound()

        # Normalize combined direction vector if it's not zero
        if np.linalg.norm(move_dir) > 0:
            move_dir = move_dir / np.linalg.norm(move_dir)
            self.velocity += move_dir * current_speed

        # Apply velocity limit
        velocity_length = np.linalg.norm(self.velocity)
        if velocity_length > self.max_velocity:
            self.velocity = (self.velocity / velocity_length) * self.max_velocity

    # Vérifier la collision
    def check_collision(self, new_position, collision_radius=0.8):
        camera_pos = np.array(new_position)  # Position de la caméra
        min_x, max_x = -200.0, 200.0  # Limites de la carte
        min_z, max_z = -200.0, 200.0  # Limites de la carte
        x, y, z = camera_pos  # Coordonnées de la caméra
        # Uniquement vérifier les limites de la carte
        if x < min_x or x > max_x or z < min_z or z > max_z:
            return True
        return False

    # Appliquer la vue
    def apply(self):
        target = self.position + self.front  # Calculer la cible
        glLoadIdentity()  # Réinitialiser la matrice
        gluLookAt(  # Appliquer la vue
            self.position[0],
            self.position[1],
            self.position[2],  # Position de la caméra
            target[0],
            target[1],
            target[2],  # Cible de la caméra
            self.up[0],
            self.up[1],
            self.up[2],  # Vecteur vertical
        )


def size_screen():
    if os.name == "nt":
        from ctypes import windll

        user32 = windll.user32
        largeur = user32.GetSystemMetrics(0)
        hauteur = user32.GetSystemMetrics(1)
    resolutions_16_9 = [
        (640, 360),
        (854, 480),
        (960, 540),
        (1280, 720),
        (1366, 768),
        (1600, 900),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160),
    ]
    dimensions_possibles = [
        (w, h) for w, h in resolutions_16_9 if w <= largeur and h <= hauteur
    ]
    # for w, h in dimensions_possibles:
    #   print(f"{w}, {h}")
    return dimensions_possibles


dimensions_possibles = size_screen()


# Fonction pour afficher les crédits
def toggle_fullscreen():
    pygame.display.toggle_fullscreen()  # Basculer en mode plein écran


# Désactiver le face culling pour voir des deux côtés
# Fonction pour afficher la grille
def grid():
    grid_height = -1.5  # Hauteur de la grille
    grid_size = 100  # Taille de la grille
    grid_step = 1  # Pas de la grille

    glBegin(GL_QUADS)  # Commencer le dessin des quadrilatères
    glColor3f(0.3, 0.3, 0.3)  # Couleur de la grille

    for x in range(-grid_size, grid_size, grid_step):
        for z in range(-grid_size, grid_size, grid_step):
            glVertex3f(x, grid_height, z)  # Coin bas gauche
            glVertex3f(x + grid_step, grid_height, z)  # Coin bas droit
            glVertex3f(x + grid_step, grid_height, z + grid_step)  # Coin haut droit
            glVertex3f(x, grid_height, z + grid_step)  # Coin haut gauche

    glEnd()  # Terminer le dessin des quadrilatères


def draw_textured_floor(
    texture_id, grid_size=200, texture_width=0.5, texture_height=0.5
):
    grid_height = -1.5  # Hauteur du sol

    # Calcul du nombre de répétitions en fonction de la taille de la grille et de la texture
    repeat_x = grid_size / texture_width
    repeat_y = grid_size / texture_height

    glEnable(GL_TEXTURE_2D)  # Activer les textures
    glBindTexture(GL_TEXTURE_2D, texture_id)  # Lier la texture du sol

    glBegin(GL_QUADS)
    glColor3f(1.0, 1.0, 1.0)  # Blanc pour afficher la texture correctement

    # Coordonnées de texture avec répétition pour le sol
    glTexCoord2f(0 * repeat_x, 0 * repeat_y)
    glVertex3f(-grid_size, grid_height, -grid_size)  # Coin bas-gauche
    glTexCoord2f(1 * repeat_x, 0 * repeat_y)
    glVertex3f(grid_size, grid_height, -grid_size)  # Coin bas-droit
    glTexCoord2f(1 * repeat_x, 1 * repeat_y)
    glVertex3f(grid_size, grid_height, grid_size)  # Coin haut-droit
    glTexCoord2f(0 * repeat_x, 1 * repeat_y)
    glVertex3f(-grid_size, grid_height, grid_size)  # Coin haut-gauche

    glEnd()

    glDisable(GL_TEXTURE_2D)  # Désactiver les textures après le dessin


# Fonction pour afficher les crédits
def render_text_to_texture(text, font, color=(255, 255, 0)):
    text_surface = font.render(text, True, color, (0, 0, 0))  # Rendre le texte
    text_data = pygame.image.tostring(
        text_surface, "RGBA", True
    )  # Convertir le texte en données
    width, height = text_surface.get_size()  # Récupérer la taille du texte
    texture_id = glGenTextures(1)  # Générer un identifiant de texture
    glBindTexture(GL_TEXTURE_2D, texture_id)  # Lier la texture
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA,
        width,
        height,
        0,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        text_data,
    )  # Appliquer la texture
    glTexParameteri(
        GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR
    )  # Paramètres de la texture
    glTexParameteri(
        GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR
    )  # Paramètres de la texture
    return (
        texture_id,
        width,
        height,
    )  # Retourner l'identifiant de la texture, la largeur et la hauteur


def walk_sound():
    global last_walk_sound_time
    current_time = time.time()
    # Only play sound if enough time has passed (prevent sound spamming)
    if current_time - last_walk_sound_time > 0.3:  # Adjust this value as needed
        walk_sound_effect.play()
        last_walk_sound_time = current_time


# Fonction pour afficher les crédits


def draw_skybox(texture_id, radius=1000):
    """Dessine une sphère texturée pour le ciel."""
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    glPushMatrix()
    glColor3f(1, 1, 1)  # Couleur blanche pour voir la texture correctement
    gluQuadricTexture(gluNewQuadric(), GL_TRUE)  # Activer la texture sur la sphère
    gluSphere(gluNewQuadric(), radius, 64, 64)  # Dessiner la sphère (rayon, détails)
    glPopMatrix()

    glDisable(GL_TEXTURE_2D)


def draw_fps(clock, font, screenwidth, screenheight):
    fps = int(clock.get_fps())  # Calculer les FPS
    text = f"FPS: {fps}"  # Texte à afficher
    texture_id, width, height = render_text_to_texture(
        text, font
    )  # Rendre le texte en texture
    glMatrixMode(GL_PROJECTION)  # Changer le mode de la matrice à la projection
    glPushMatrix()  # Sauvegarder la matrice
    glLoadIdentity()  # Réinitialiser la matrice
    gluOrtho2D(
        0, screenwidth, 0, screenheight
    )  # Appliquer la projection orthographique
    glMatrixMode(GL_MODELVIEW)  # Changer le mode de la matrice au modèle
    glPushMatrix()  # Sauvegarder la matrice
    glLoadIdentity()  # Réinitialiser la matrice
    glEnable(GL_TEXTURE_2D)  # Activer la texture
    glBindTexture(GL_TEXTURE_2D, texture_id)  # Lier la texture
    glColor3f(1, 1, 1)  # Couleur du texte
    glBegin(GL_QUADS)  # Commencer le dessin des quads
    glTexCoord2f(0, 0)
    glVertex2f(10, 560)  # Dessiner le quad
    glTexCoord2f(1, 0)
    glVertex2f(10 + width, 560)  # Dessiner le quad
    glTexCoord2f(1, 1)
    glVertex2f(10 + width, 560 + height)  # Dessiner le quad
    glTexCoord2f(0, 1)
    glVertex2f(10, 560 + height)  # Dessiner le quad
    glEnd()  # Terminer le dessin des quads
    glDisable(GL_TEXTURE_2D)  # Désactiver la texture
    glMatrixMode(GL_PROJECTION)  # Changer le mode de la matrice à la projection
    glPopMatrix()  # Restaurer la matrice
    glMatrixMode(GL_MODELVIEW)  # Changer le mode de la matrice au modèle
    glPopMatrix()  # Restaurer la matrice


# Fonction pour charger un fichier OBJ
def load_obj(filename):
    vertices = []  # Initialiser la liste des sommets
    texcoords = []  # Initialiser la liste des coordonnées de texture
    faces = []  # Initialiser la liste des faces
    with open(filename, "r") as file:  # Ouvrir le fichier en mode lecture
        for line in file:  # Lire chaque ligne du fichier
            if line.startswith("v "):  # Si la ligne commence par 'v'
                vertex = [
                    float(coord) for coord in line.strip().split()[1:4]
                ]  # Récupérer les coordonnées du sommet
                vertices.append(vertex)  # Ajouter le sommet à la liste
            elif line.startswith("vt "):  # Si la ligne commence par 'vt'
                texcoord = [
                    float(coord) for coord in line.strip().split()[1:3]
                ]  # Récupérer les coordonnées de texture
                texcoords.append(
                    texcoord
                )  # Ajouter les coordonnées de texture à la liste
            elif line.startswith("f "):  # Si la ligne commence par 'f'
                face_vertices = []  # Initialiser la liste des sommets de la face
                face_texcoords = (
                    []
                )  # Initialiser la liste des coordonnées de texture de la face
                for v in line.strip().split()[1:]:  # Lire chaque sommet de la face
                    v_split = v.split("/")  # Séparer les indices
                    face_vertices.append(
                        int(v_split[0]) - 1
                    )  # Ajouter l'indice du sommet
                    if (
                        len(v_split) >= 2 and v_split[1]
                    ):  # Si l'indice de la coordonnée de texture existe
                        face_texcoords.append(
                            int(v_split[1]) - 1
                        )  # Ajouter l'indice de la coordonnée de texture
                if len(face_vertices) >= 3:  # Si la face a au moins 3 sommets
                    faces.append(
                        (face_vertices[:3], face_texcoords[:3])
                    )  # Ajouter la face à la liste
    return (
        vertices,
        texcoords,
        faces,
    )  # Retourner les sommets, les coordonnées de texture et les faces


# Fonction pour charger une texture
def load_texture(filename):
    texture_surface = pygame.image.load(filename)  # Charger l'image
    texture_data = pygame.image.tostring(
        texture_surface, "RGBA", True
    )  # Convertir l'image en données
    width, height = texture_surface.get_size()  # Récupérer la taille de l'image

    texture_id = glGenTextures(1)  # Générer un identifiant de texture
    glBindTexture(GL_TEXTURE_2D, texture_id)  # Lier la texture
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA,
        width,
        height,
        0,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        texture_data,
    )  # Appliquer la texture
    glTexParameteri(
        GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR
    )  # Paramètres de la texture
    glTexParameteri(
        GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR
    )  # Paramètres de la texture
    return texture_id  # Retourner l'identifiant de la texture


# Fonction pour créer un modèle VBO
def create_model_vbo(vertices, texcoords, faces):
    vertex_data = []  # Initialiser les données des sommets
    texcoord_data = []  # Initialiser les données des coordonnées de texture
    for face in faces:  # Pour chaque face
        for vertex_idx, texcoord_idx in zip(
            face[0], face[1]
        ):  # Pour chaque sommet et coordonnée de texture
            vertex_data.extend(
                vertices[vertex_idx]
            )  # Ajouter les coordonnées du sommet
            texcoord_data.extend(
                texcoords[texcoord_idx]
            )  # Ajouter les coordonnées de texture

    vertex_data = np.array(
        vertex_data, dtype=np.float32
    )  # Convertir les données des sommets en tableau NumPy
    texcoord_data = np.array(
        texcoord_data, dtype=np.float32
    )  # Convertir les données des coordonnées de texture en tableau NumPy

    vbo = glGenBuffers(1)  # Générer un identifiant de VBO
    glBindBuffer(GL_ARRAY_BUFFER, vbo)  # Lier le VBO
    glBufferData(
        GL_ARRAY_BUFFER, vertex_data.nbytes + texcoord_data.nbytes, None, GL_STATIC_DRAW
    )  # Appliquer les données
    glBufferSubData(
        GL_ARRAY_BUFFER, 0, vertex_data.nbytes, vertex_data
    )  # Ajouter les données des sommets
    glBufferSubData(
        GL_ARRAY_BUFFER, vertex_data.nbytes, texcoord_data.nbytes, texcoord_data
    )  # Ajouter les données des coordonnées de texture

    return (
        vbo,
        len(vertex_data) // 3,
    )  # Retourner l'identifiant du VBO et le nombre de sommets


# Fonction pour dessiner un modèle
def draw_model(vbo, vertex_count):
    glBindBuffer(GL_ARRAY_BUFFER, vbo)  # Lier le VBO
    glEnableClientState(GL_VERTEX_ARRAY)  # Activer le tableau des sommets
    glVertexPointer(3, GL_FLOAT, 0, None)  # Pointer vers les sommets
    glEnableClientState(
        GL_TEXTURE_COORD_ARRAY
    )  # Activer le tableau des coordonnées de texture
    glTexCoordPointer(
        2, GL_FLOAT, 0, ctypes.c_void_p(vertex_count * 3 * 4)
    )  # Pointer vers les coordonnées de texture

    # Active le test de profondeur
    glEnable(GL_DEPTH_TEST)

    # Dessiner le modèle plein
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glColor3f(1.0, 1.0, 1.0)  # Couleur blanche pour que la texture soit visible
    glDrawArrays(GL_TRIANGLES, 0, vertex_count)  # Dessiner le modèle

    glDisableClientState(
        GL_TEXTURE_COORD_ARRAY
    )  # Désactiver le tableau des coordonnées de texture
    glDisableClientState(GL_VERTEX_ARRAY)  # Désactiver le tableau des sommets
    glDisable(GL_DEPTH_TEST)  # Désactiver le test de profondeur


# Initialisation de Pygame et de la police


version_text = "Version 1.0.0"  # Texte de la version
try:  # Essayer de charger la police par défaut
    version_font = pygame.font.Font(None, 24)  # Police par défaut
except:  # En cas d'erreur
    print(
        "Erreur lors de l'initialisation de la police, utilisation de la police par défaut."
    )
    version_font = pygame.font.SysFont(
        "Arial", 24
    )  # Si 'None' échoue, utiliser Arial comme fallback


def draw_crosshair(screen_width, screen_height):  # Fonction pour dessiner le viseur
    size = 6  # Taille du viseur
    gap = 2  # Espace au centre
    thickness = 2  # Épaisseur des lignes

    center_x = screen_width // 2  # Position X du centre
    center_y = screen_height // 2  # Position Y du centre

    glDisable(GL_DEPTH_TEST)  # Désactivation du test de profondeur

    glEnable(GL_BLEND)  # Activation du blending
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # Configuration du blending

    glMatrixMode(GL_PROJECTION)  # Changement en mode projection
    glPushMatrix()  # Sauvegarde de la matrice
    glLoadIdentity()  # Réinitialisation de la matrice
    glOrtho(
        0, screen_width, screen_height, 0, -1, 1
    )  # Configuration de la projection orthographique

    glMatrixMode(GL_MODELVIEW)  # Changement en mode vue
    glPushMatrix()  # Sauvegarde de la matrice
    glLoadIdentity()  # Réinitialisation de la matrice

    glColor4f(1.0, 1.0, 1.0, 1.0)  # Couleur blanche semi-transparente
    glLineWidth(thickness)  # Définition de l'épaisseur des lignes
    glBegin(GL_LINES)  # Début du dessin des lignes

    glVertex2f(center_x - size, center_y)  # Ligne horizontale gauche
    glVertex2f(center_x - gap / 2, center_y)
    glVertex2f(center_x + gap / 2, center_y)  # Ligne horizontale droite
    glVertex2f(center_x + size, center_y)

    glVertex2f(center_x, center_y - size)  # Ligne verticale haut
    glVertex2f(center_x, center_y - gap / 2)
    glVertex2f(center_x, center_y + gap / 2)  # Ligne verticale bas
    glVertex2f(center_x, center_y + size)

    glEnd()  # Fin du dessin des lignes

    glMatrixMode(GL_PROJECTION)  # Retour en mode projection
    glPopMatrix()  # Restauration de la matrice
    glMatrixMode(GL_MODELVIEW)  # Retour en mode vue
    glPopMatrix()  # Restauration de la matrice

    glEnable(GL_DEPTH_TEST)  # Réactivation du test de profondeur


# Fonction pour charger une vidéo locale
def load_local_video(file_path):
    try:
        if not os.path.exists(file_path):  # Si le fichier n'existe pas
            raise FileNotFoundError(
                f"Le fichier vidéo '{file_path}' n'existe pas."
            )  # Lever une exception
        return cv2.VideoCapture(file_path)  # Charger la vidéo
    except Exception as e:  # En cas d'erreur
        print(
            f"Erreur: Impossible de charger la vidéo depuis le fichier '{file_path}'. {e}"
        )  # Afficher l'erreur
        return None


# Classe pour gérer les boutons
class Button:
    def __init__(
        self,
        x,
        y,
        width,
        height,
        text,
        text_color,
        font,
        color,
        hover_color,
        shadow_color=(0, 0, 0),
        border_radius=10,
    ):
        self.rect = pygame.Rect(
            x, y, width, height
        )  # Créer un rectangle pour le bouton
        self.text = text  # Texte du bouton
        self.text_color = text_color  # Couleur du texte
        self.font = font  # Police du bouton
        self.color = color  # Couleur du bouton
        self.hover_color = hover_color  # Couleur du bouton survolé
        self.shadow_color = shadow_color  # Couleur de l'ombre
        self.border_radius = border_radius  # Rayon des bords

    # Dessiner le bouton
    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()  # Récupérer la position de la souris
        button_color = (
            self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        )  # Couleur du bouton

        # Dessiner l'ombre légèrement décalée
        shadow_rect = self.rect.move(5, 5)  # Décale l'ombre de 5 pixels sur x et y
        pygame.draw.rect(
            surface, self.shadow_color, shadow_rect, border_radius=self.border_radius
        )  # Dessiner l'ombre

        # Dessiner le bouton
        pygame.draw.rect(
            surface, button_color, self.rect, border_radius=self.border_radius
        )

        # Dessiner le texte sur le bouton
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)  # Centrer le texte
        surface.blit(text_surface, text_rect)  # Afficher le texte

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(
            event.pos
        )  # Vérifier si le bouton est cliqué


class tabButton:
    def __init__(self, x, y, width, height, text, font, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        button_color = (
            self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        )
        pygame.draw.rect(surface, button_color, self.rect, border_radius=10)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(
            event.pos
        )


# Déclaration de la variable de scroll globale
scroll_y = 0
is_dragging = False


def display_credits(screen, font, back_button_image, event=None):
    global scroll_y, is_dragging
    screen_width, screen_height = screen.get_size()

    # Création d'une surface semi-transparente pour un effet moderne
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((10, 10, 10, 200))  # Fond sombre semi-transparent
    screen.blit(overlay, (0, 0))

    # Charger et afficher l'image du bouton de retour avec effet de survol
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))
    back_rect = back_button_image.get_rect(topleft=(30, 30))
    mouse_pos = pygame.mouse.get_pos()
    if back_rect.collidepoint(mouse_pos):
        # Effet de survol : légère augmentation de la taille
        back_button_image = pygame.transform.scale(back_button_image, (55, 55))
        back_rect = back_button_image.get_rect(topleft=(27.5, 27.5))
    screen.blit(back_button_image, back_rect)

    # Diviser l'écran en deux colonnes
    column_width = screen_width // 2
    left_column_x = 0
    right_column_x = column_width

    # === PARTIE GAUCHE : CRÉDITS ===
    # Création de la surface pour les crédits avec un effet de gradient
    credits_surface = pygame.Surface((column_width, screen_height), pygame.SRCALPHA)
    for i in range(screen_height):
        alpha = int(230 - (i / screen_height) * 50)  # Gradient d'opacité
        pygame.draw.line(
            credits_surface, (30, 30, 30, alpha), (0, i), (column_width, i)
        )

    # Définition du texte des crédits avec plus de contenu
    credits_text = [
        ("Crédits", 32, (255, 255, 255)),  # (texte, taille, couleur)
        ("", 24, (180, 180, 180)),
        ("Développé par", 28, (200, 200, 200)),
        ("Albert Oscar", 24, (180, 180, 180)),
        ("Moors Michel", 24, (180, 180, 180)),
        ("Rinckenbach Yann", 24, (180, 180, 180)),
        ("", 24, (180, 180, 180)),
        ("Remerciements", 28, (200, 200, 200)),
        ("Musée du Louvre", 24, (180, 180, 180)),
        ("", 24, (180, 180, 180)),
        ("Merci d'avoir joué !", 32, (255, 255, 255)),
    ]

    # Position de départ du texte des crédits
    start_y = 50
    line_spacing = 35

    # Affichage des crédits avec un style amélioré
    for text, size, color in credits_text:
        text_font = pygame.font.Font(None, size)
        text_surface = text_font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(column_width // 2, start_y))
        credits_surface.blit(text_surface, text_rect)
        start_y += line_spacing

    # Afficher la surface des crédits
    screen.blit(credits_surface, (left_column_x, 0))

    # === PARTIE DROITE : COMMENT JOUER ===
    # Création de la surface pour "Comment jouer" avec un effet de gradient
    how_to_play_surface = pygame.Surface((column_width, screen_height), pygame.SRCALPHA)
    for i in range(screen_height):
        alpha = int(230 - (i / screen_height) * 50)
        pygame.draw.line(
            how_to_play_surface, (30, 30, 30, alpha), (0, i), (column_width, i)
        )

    # Texte "Comment jouer" avec style amélioré
    title_font = pygame.font.Font(None, 32)
    title_text = title_font.render("Comment jouer", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(column_width // 2, 30))
    how_to_play_surface.blit(title_text, title_rect)

    # Contenu défilant avec plus de détails
    content = [
        ("Bienvenue dans VirtuLouvre !", 28, (200, 200, 200)),
        ("", 24, (180, 180, 180)),
        ("Objectif", 28, (200, 200, 200)),
        ("Explorez le musée virtuel et découvrez", 24, (180, 180, 180)),
        ("les œuvres d'art de manière immersive.", 24, (180, 180, 180)),
        ("", 24, (180, 180, 180)),
        ("Contrôles principaux", 28, (200, 200, 200)),
        ("Z/S : Avancer/Reculer", 24, (180, 180, 180)),
        ("Q/D : Se déplacer à gauche/droite", 24, (180, 180, 180)),
        ("ESPACE : Voler", 24, (180, 180, 180)),
        ("SHIFT : Descendre", 24, (180, 180, 180)),
        ("G : Atterrir", 24, (180, 180, 180)),
        ("V : Sprint", 24, (180, 180, 180)),
        ("", 24, (180, 180, 180)),
        ("Contrôles supplémentaires", 28, (200, 200, 200)),
        ("ÉCHAP : Menu", 24, (180, 180, 180)),
        ("F11 : Plein écran", 24, (180, 180, 180)),
        ("", 24, (180, 180, 180)),
        ("Comment utiliser le programme", 28, (200, 200, 200)),
        ("1. Lancez le programme", 24, (180, 180, 180)),
        ("2. Utilisez le menu principal", 24, (180, 180, 180)),
        ("3. Personnalisez vos paramètres", 24, (180, 180, 180)),
        ("4. Commencez l'exploration !", 24, (180, 180, 180)),
        ("", 24, (180, 180, 180)),
        ("Astuces", 28, (200, 200, 200)),
        ("• Utilisez le sprint pour explorer plus rapidement", 24, (180, 180, 180)),
        ("• Le mode vol permet d'explorer sous tous les angles", 24, (180, 180, 180)),
        ("• N'oubliez pas de sauvegarder vos paramètres", 24, (180, 180, 180)),
    ]

    # Création de la surface de défilement
    scroll_area_height = screen_height - 100
    scroll_surface = pygame.Surface(
        (column_width - 40, scroll_area_height), pygame.SRCALPHA
    )
    scroll_surface.fill((40, 40, 40, 200))

    # Position de défilement
    line_height = 25
    total_height = len(content) * line_height
    visible_lines = scroll_area_height // line_height

    # Affichage du contenu avec style amélioré
    for i, (text, size, color) in enumerate(content):
        text_font = pygame.font.Font(None, size)
        text_surface = text_font.render(text, True, color)
        text_rect = text_surface.get_rect(x=20, y=i * line_height)
        scroll_surface.blit(text_surface, text_rect)

    # Barre de défilement améliorée
    scrollbar_width = 12
    scrollbar_height = max(30, scroll_area_height * (visible_lines / len(content)))
    scrollbar_x = column_width - 30
    scrollbar_y = 50
    scrollbar_track_height = scroll_area_height - scrollbar_height

    # Calcul de la position de la barre de défilement
    scrollbar_pos = (
        scrollbar_y
        + (scroll_y / (total_height - scroll_area_height)) * scrollbar_track_height
    )

    # Dessiner le track de la barre de défilement avec effet de gradient
    pygame.draw.rect(
        how_to_play_surface,
        (20, 20, 20),
        (scrollbar_x, scrollbar_y, scrollbar_width, scroll_area_height),
        border_radius=6,
    )

    # Dessiner la barre de défilement avec effet de survol
    scrollbar_color = (60, 60, 60) if is_dragging else (40, 40, 40)
    pygame.draw.rect(
        how_to_play_surface,
        scrollbar_color,
        (scrollbar_x + 2, scrollbar_pos, scrollbar_width - 4, scrollbar_height),
        border_radius=6,
    )

    # Afficher la surface de défilement
    how_to_play_surface.blit(
        scroll_surface, (20, 50), (0, scroll_y, column_width - 40, scroll_area_height)
    )

    # Afficher la surface "Comment jouer"
    screen.blit(how_to_play_surface, (right_column_x, 0))

    # Gestion du défilement avec la souris
    if event:
        # Molette de la souris
        if event.type == pygame.MOUSEWHEEL:
            scroll_y = max(
                0, min(total_height - scroll_area_height, scroll_y - event.y * 20)
            )

        # Vérifier si la souris est sur la barre de défilement
        mouse_x, mouse_y = pygame.mouse.get_pos()
        rel_x = mouse_x - right_column_x
        rel_y = mouse_y - 50

        if (
            scrollbar_x <= rel_x <= scrollbar_x + scrollbar_width
            and scrollbar_y <= rel_y <= scrollbar_y + scroll_area_height
        ):
            # Effet de survol sur la barre de défilement
            pygame.draw.rect(
                how_to_play_surface,
                (50, 50, 50),
                (scrollbar_x + 2, scrollbar_pos, scrollbar_width - 4, scrollbar_height),
                border_radius=6,
            )

            if (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            ):  # Clic gauche
                is_dragging = True
                drag_start_y = rel_y
                drag_start_scroll = scroll_y

            elif event.type == pygame.MOUSEBUTTONUP:
                is_dragging = False

        if event.type == pygame.MOUSEMOTION and is_dragging:
            delta_y = rel_y - drag_start_y
            scroll_y = drag_start_scroll + (delta_y / scrollbar_track_height) * (
                total_height - scroll_area_height
            )
            scroll_y = max(0, min(total_height - scroll_area_height, scroll_y))

    return back_rect


def quit_game():
    pygame.quit()
    sys.exit()


def size_screen():
    if os.name == "nt":  # Only for Windows
        from ctypes import windll

        user32 = windll.user32
        largeur = user32.GetSystemMetrics(0)
        hauteur = user32.GetSystemMetrics(1)
    else:
        largeur, hauteur = (
            pygame.display.Info().current_w,
            pygame.display.Info().current_h,
        )

    resolutions_16_9 = [
        (800, 600),
        (426, 240),
        (640, 360),
        (854, 480),
        (960, 540),
        (1280, 720),
        (1366, 768),
        (1600, 900),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160),
    ]

    return [(w, h) for w, h in resolutions_16_9 if w <= largeur and h <= hauteur] + [
        (0, 0)
    ]


pygame.init()
resolutions = size_screen()
current_resolution_index = 0


def change_resolution(index):
    global screen, current_resolution_index
    current_resolution_index = index
    width, height = resolutions[index]

    if width == 0 and height == 0:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | DOUBLEBUF | OPENGL)
        width, height = pygame.display.Info().current_w, pygame.display.Info().current_h
    else:
        screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)

    # Réinitialiser le contexte OpenGL
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width / height, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Charger les flèches de navigation
    arrow_left = pygame.image.load("src/Icons/arrow_left.png")
    arrow_right = pygame.image.load("src/Icons/arrow_right.png")
    arrow_size = (50, 50)
    arrow_left = pygame.transform.scale(arrow_left, arrow_size)
    arrow_right = pygame.transform.scale(arrow_right, arrow_size)


# Fonction pour afficher les paramètres
def display_settings(screen, font, back_button_image, current_tab, event=None):
    global slider_value, is_dragging, input_active, input_text, master_volume, controls, frame_x, frame_y, frame_width, frame_height, spacing

    # Initialiser les variables nécessaires
    back_rect = None
    tab_buttons = []
    left_rect = pygame.Rect(0, 0, 0, 0)  # Initialiser avec un rectangle vide
    right_rect = pygame.Rect(0, 0, 0, 0)  # Initialiser avec un rectangle vide
    volume_slider_rect = pygame.Rect(0, 0, 0, 0)
    reset_button_rect = pygame.Rect(0, 0, 0, 0)

    # Charger les images des flèches
    arrow_left = pygame.image.load("src/icons/arrow_left.png")
    arrow_right = pygame.image.load("src/icons/arrow_right.png")

    # Fond gris foncé pour tout l'écran
    screen.fill((20, 20, 20))

    # Utiliser la police par défaut si aucune n'est fournie
    if font is None:
        font = pygame.font.Font(None, 24)

    # Dessiner le bouton retour en haut à gauche
    back_button_rect = back_button_image.get_rect()
    back_button_rect.topleft = (10, 10)  # Position ajustée pour être plus près du bord
    screen.blit(back_button_image, back_button_rect)
    back_rect = back_button_rect

    # Créer les boutons d'onglets
    tabs = ["Vidéo", "Audio", "Touches"]
    tab_width, tab_height = 120, 30  # Réduit la largeur et la hauteur des onglets
    tab_spacing = 10  # Réduit l'espacement entre les onglets
    start_x = (
        screen.get_width() - (len(tabs) * (tab_width + tab_spacing) - tab_spacing)
    ) // 2
    start_y = 20

    for i, tab in enumerate(tabs):
        tab_buttons.append(
            tabButton(
                start_x + i * (tab_width + tab_spacing),
                start_y,
                tab_width,
                tab_height,
                tab,
                font,
                (40, 40, 40),
                (60, 60, 60),
            )
        )
        tab_buttons[i].draw(screen)

    if current_tab == "Vidéo":
        # Case pour les dimensions
        case_width = 300  # Réduit la largeur de la case
        case_height = 40  # Réduit la hauteur de la case
        case_x = (screen.get_width() - case_width) // 2
        case_y = 200

        # Dessiner la case gris clair
        pygame.draw.rect(
            screen,
            (60, 60, 60),
            (case_x, case_y, case_width, case_height),
            border_radius=10,
        )

        # Texte "Dimensions" à gauche
        dimensions_text = font.render("Dimensions", True, (255, 255, 255))
        dimensions_rect = dimensions_text.get_rect(
            midleft=(case_x + 20, case_y + case_height // 2)
        )
        screen.blit(dimensions_text, dimensions_rect)

        # Flèches de navigation et résolution alignés à droite
        arrow_size = (20, 20)  # Réduit la taille des flèches
        arrow_left_small = pygame.transform.scale(arrow_left, arrow_size)
        arrow_right_small = pygame.transform.scale(arrow_right, arrow_size)

        # Positionner d'abord la flèche droite
        right_rect = arrow_right_small.get_rect(
            midright=(case_x + case_width - 20, case_y + case_height // 2)
        )

        # Positionner la résolution à gauche de la flèche droite
        resolution_text = (
            "Plein écran"
            if resolutions[current_resolution_index] == (0, 0)
            else f"{resolutions[current_resolution_index][0]} x {resolutions[current_resolution_index][1]}"
        )
        resolution_surface = font.render(resolution_text, True, (255, 255, 255))
        resolution_rect = resolution_surface.get_rect(
            midright=(right_rect.left - 10, case_y + case_height // 2)
        )

        # Positionner la flèche gauche à gauche de la résolution
        left_rect = arrow_left_small.get_rect(
            midright=(resolution_rect.left - 10, case_y + case_height // 2)
        )

        # Afficher les éléments dans l'ordre
        screen.blit(arrow_left_small, left_rect)
        screen.blit(resolution_surface, resolution_rect)
        screen.blit(arrow_right_small, right_rect)

        # Case pour le FOV
        fov_case_y = case_y + case_height + 20  # 20 pixels de séparation
        pygame.draw.rect(
            screen,
            (60, 60, 60),
            (case_x, fov_case_y, case_width, case_height),
            border_radius=10,
        )

        # Texte "FOV" à gauche
        fov_text = font.render("FOV", True, (255, 255, 255))
        fov_rect = fov_text.get_rect(
            midleft=(case_x + 20, fov_case_y + case_height // 2)
        )
        screen.blit(fov_text, fov_rect)

        # Affichage numérique du FOV
        fov_number_text = font.render(f"{slider_value}°", True, (255, 255, 255))
        fov_number_rect = fov_number_text.get_rect(
            midright=(case_x + case_width - 20, fov_case_y + case_height // 2)
        )
        screen.blit(fov_number_text, fov_number_rect)

        # Barre de FOV
        fov_bar_width = 150  # Réduit la largeur de la barre
        fov_bar_height = 8  # Réduit la hauteur de la barre
        fov_bar_x = (
            case_x + case_width - fov_bar_width - 60
        )  # Ajusté pour laisser de la place au pourcentage
        fov_bar_y = fov_case_y + case_height // 2 - fov_bar_height // 2

        # Dessiner le fond de la barre
        pygame.draw.rect(
            screen,
            (40, 40, 40),
            (fov_bar_x, fov_bar_y, fov_bar_width, fov_bar_height),
            border_radius=5,
        )

        # Calculer la largeur de la barre de FOV (60° à 120°)
        fov_percentage = (slider_value - 60) / 60
        fov_width = int(fov_bar_width * fov_percentage)

        # Dessiner la barre de FOV
        pygame.draw.rect(
            screen,
            (0, 200, 255),
            (fov_bar_x, fov_bar_y, fov_width, fov_bar_height),
            border_radius=5,
        )

        # Rectangle pour la détection du clic sur la barre
        fov_slider_rect = pygame.Rect(
            fov_bar_x, fov_bar_y, fov_bar_width, fov_bar_height
        )

        # Rectangle pour la détection du clic sur le texte du FOV
        fov_number_click_rect = fov_number_rect.inflate(10, 10)

        # Gestion de la saisie de texte pour le FOV
        if event and event.type == pygame.MOUSEBUTTONDOWN:
            if fov_number_click_rect.collidepoint(event.pos):
                input_active = True
                input_text = ""
            else:
                input_active = False

        if event and event.type == pygame.KEYDOWN:
            if input_active:
                if event.key == pygame.K_RETURN:
                    try:
                        new_value = int(input_text)
                        if new_value > 120:
                            new_value = 120
                        elif new_value < 60:
                            new_value = 60
                        slider_value = new_value
                        save_controls()
                    except ValueError:
                        pass
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isdigit() and len(input_text) < 3:
                    input_text += event.unicode

        # Afficher le texte en cours de saisie si actif
        pygame.draw.rect(screen, (60, 60, 60), fov_number_rect)

        if input_active:
            input_surface = font.render(input_text + "°", True, (0, 200, 255))
            screen.blit(input_surface, fov_number_rect)
        else:
            fov_number_text = font.render(f"{slider_value}°", True, (255, 255, 255))
            screen.blit(fov_number_text, fov_number_rect)

        # Gestion du clic sur la barre de FOV
        if event and event.type == pygame.MOUSEBUTTONDOWN:
            if fov_slider_rect.collidepoint(event.pos):
                # Calculer la nouvelle valeur en fonction de la position du clic
                relative_x = event.pos[0] - fov_bar_x
                percentage = max(0, min(1, relative_x / fov_bar_width))
                slider_value = int(60 + (percentage * 60))  # 60° à 120°
                save_controls()

        # Gestion du glissement de la barre de FOV
        if event and event.type == pygame.MOUSEMOTION:
            if event.buttons[0] and fov_slider_rect.collidepoint(event.pos):
                relative_x = event.pos[0] - fov_bar_x
                percentage = max(0, min(1, relative_x / fov_bar_width))
                slider_value = int(60 + (percentage * 60))  # 60° à 120°
                save_controls()

    elif current_tab == "Audio":
        # Case pour le volume
        case_width = 300  # Réduit la largeur de la case
        case_height = 40  # Réduit la hauteur de la case
        case_x = (screen.get_width() - case_width) // 2
        case_y = 200

        # Dessiner la case gris clair
        pygame.draw.rect(
            screen,
            (60, 60, 60),
            (case_x, case_y, case_width, case_height),
            border_radius=10,
        )

        # Texte "Volume" à gauche
        volume_text = font.render("Volume", True, (255, 255, 255))
        volume_rect = volume_text.get_rect(
            midleft=(case_x + 20, case_y + case_height // 2)
        )
        screen.blit(volume_text, volume_rect)

        # Affichage numérique du volume
        volume_number_text = font.render(
            f"{int(master_volume)}%", True, (255, 255, 255)
        )
        volume_number_rect = volume_number_text.get_rect(
            midright=(case_x + case_width - 20, case_y + case_height // 2)
        )
        screen.blit(volume_number_text, volume_number_rect)

        # Barre de volume
        bar_width = 150  # Réduit la largeur de la barre
        bar_height = 8  # Réduit la hauteur de la barre
        bar_x = (
            case_x + case_width - bar_width - 60
        )  # Ajusté pour laisser de la place au pourcentage
        bar_y = case_y + case_height // 2 - bar_height // 2

        # Dessiner le fond de la barre
        pygame.draw.rect(
            screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height), border_radius=5
        )

        # Dessiner la barre de volume
        volume_width = int(bar_width * (master_volume / 100))
        pygame.draw.rect(
            screen,
            (0, 200, 255),
            (bar_x, bar_y, volume_width, bar_height),
            border_radius=5,
        )

        # Rectangle pour la détection du clic sur la barre
        volume_slider_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)

        # Rectangle pour la détection du clic sur le texte du volume
        volume_number_click_rect = volume_number_rect.inflate(10, 10)

        # Gestion de la saisie de texte pour le volume
        if event and event.type == pygame.MOUSEBUTTONDOWN:
            if volume_number_click_rect.collidepoint(event.pos):
                # Activer la saisie de texte et initialiser avec une chaîne vide
                input_active = True
                input_text = ""  # Initialiser avec une chaîne vide
            else:
                input_active = False

        if event and event.type == pygame.KEYDOWN:
            if input_active:
                if event.key == pygame.K_RETURN:
                    try:
                        new_value = int(input_text)
                        if new_value > 100:
                            new_value = 100
                        elif new_value < 0:
                            new_value = 0
                        master_volume = new_value
                        walk_sound_effect.set_volume(
                            master_volume / 100
                        )  # Mettre à jour le volume du son
                        save_controls()
                    except ValueError:
                        pass
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif (
                    event.unicode.isdigit() and len(input_text) < 3
                ):  # Limite à 3 chiffres
                    input_text += event.unicode

        # Afficher le texte en cours de saisie si actif
        pygame.draw.rect(screen, (60, 60, 60), volume_number_rect)

        if input_active:
            input_surface = font.render(input_text + "%", True, (0, 200, 255))
            screen.blit(input_surface, volume_number_rect)
        else:
            volume_number_text = font.render(
                f"{int(master_volume)}%", True, (255, 255, 255)
            )
            screen.blit(volume_number_text, volume_number_rect)

        # Gestion du glisser-déposer de la barre de volume
        if (
            event
            and event.type == pygame.MOUSEBUTTONDOWN
            and volume_slider_rect.collidepoint(event.pos)
        ):
            is_dragging = True
        elif event and event.type == pygame.MOUSEBUTTONUP:
            is_dragging = False
        elif event and event.type == pygame.MOUSEMOTION and is_dragging:
            relative_x = event.pos[0] - volume_slider_rect.x
            volume_percentage = max(
                0.0, min(1.0, relative_x / volume_slider_rect.width)
            )
            master_volume = int(volume_percentage * 100)  # Convertir en pourcentage
            walk_sound_effect.set_volume(
                master_volume / 100
            )  # Mettre à jour le volume du son
            save_controls()

    elif current_tab == "Touches":
        # Bouton de réinitialisation
        reset_button_width = 150  # Réduit la largeur du bouton
        reset_button_height = 30  # Réduit la hauteur du bouton
        reset_button_x = screen.get_width() // 2 - reset_button_width // 2
        reset_button_y = 200
        reset_button_rect = pygame.Rect(
            reset_button_x, reset_button_y, reset_button_width, reset_button_height
        )

        # Couleur du bouton
        reset_button_color = (200, 50, 50)
        reset_button_hover_color = (150, 30, 30)

        # Vérifier si la souris est sur le bouton
        mouse_pos = pygame.mouse.get_pos()
        button_color = (
            reset_button_hover_color
            if reset_button_rect.collidepoint(mouse_pos)
            else reset_button_color
        )

        # Dessiner le bouton
        pygame.draw.rect(screen, button_color, reset_button_rect, border_radius=10)
        reset_text = font.render("Par défaut", True, (255, 255, 255))
        reset_text_rect = reset_text.get_rect(center=reset_button_rect.center)
        screen.blit(reset_text, reset_text_rect)

        # Position de départ pour les contrôles
        start_y = 300
        frame_width = 400  # Réduit la largeur du cadre
        frame_height = len(controls) * spacing + 40
        frame_x = (screen.get_width() - frame_width) // 2
        frame_y = start_y - 20

        # Dessiner le cadre principal avec coins arrondis
        pygame.draw.rect(
            screen,
            (40, 40, 40),
            (frame_x, frame_y, frame_width, frame_height),
            border_radius=15,
        )

        # Ajouter un effet de bordure lumineuse
        pygame.draw.rect(
            screen,
            (60, 60, 60),
            (frame_x, frame_y, frame_width, frame_height),
            2,
            border_radius=15,
        )

        # Afficher chaque contrôle
        for i, (key, action) in enumerate(controls):
            # Créer un cadre individuel pour chaque contrôle
            control_frame_x = frame_x + 20
            control_frame_y = frame_y + 20 + i * spacing
            control_frame_width = frame_width - 40
            control_frame_height = 30

            # Dessiner le cadre individuel avec un effet de profondeur
            pygame.draw.rect(
                screen,
                (50, 50, 50),
                (
                    control_frame_x,
                    control_frame_y,
                    control_frame_width,
                    control_frame_height,
                ),
                border_radius=8,
            )

            # Ajouter un effet de surbrillance subtil
            pygame.draw.rect(
                screen,
                (70, 70, 70),
                (
                    control_frame_x,
                    control_frame_y,
                    control_frame_width,
                    control_frame_height,
                ),
                1,
                border_radius=8,
            )

            # Touche (à droite)
            key_text = font.render(
                "..." if waiting_for_key == i else key,
                True,
                (0, 200, 255) if key != "ÉCHAP" else (100, 100, 100),
            )
            key_rect = key_text.get_rect(
                center=(
                    control_frame_x + control_frame_width - 30,
                    control_frame_y + control_frame_height // 2,
                )
            )
            screen.blit(key_text, key_rect)

            # Action (à gauche)
            action_text = font.render(
                action, True, (255, 255, 255) if key != "ÉCHAP" else (150, 150, 150)
            )
            action_rect = action_text.get_rect(
                midleft=(
                    control_frame_x + 10,
                    control_frame_y + control_frame_height // 2,
                )
            )
            screen.blit(action_text, action_rect)

    return (
        back_rect,
        tab_buttons,
        left_rect,  # Toujours retourner le rectangle, même s'il est vide
        right_rect,  # Toujours retourner le rectangle, même s'il est vide
        volume_slider_rect,
        reset_button_rect,
    )


def draw_loading_screen(screen, progress, font):
    # Effacer l'écran
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Configurer la projection orthographique pour le texte
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, screen.get_width(), screen.get_height(), 0, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Désactiver le test de profondeur pour le texte
    glDisable(GL_DEPTH_TEST)

    # Activer le blending pour la transparence
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Dessiner le fond noir
    glColor4f(0.0, 0.0, 0.0, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(screen.get_width(), 0)
    glVertex2f(screen.get_width(), screen.get_height())
    glVertex2f(0, screen.get_height())
    glEnd()

    # Dessiner la barre de progression
    bar_width = screen.get_width() * 0.6
    bar_height = 20
    bar_x = (screen.get_width() - bar_width) / 2
    bar_y = screen.get_height() / 2

    # Fond de la barre
    glColor4f(0.3, 0.3, 0.3, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width, bar_y)
    glVertex2f(bar_x + bar_width, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()

    # Barre de progression
    glColor4f(0.0, 0.7, 1.0, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width * progress, bar_y)
    glVertex2f(bar_x + bar_width * progress, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()

    # Texte de chargement
    loading_text = f"Chargement : {int(progress * 100)}%"
    texture_id, width, height = render_text_to_texture(
        loading_text, font, (255, 255, 255)
    )

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor4f(1.0, 1.0, 1.0, 1.0)

    text_x = (screen.get_width() - width) / 2
    text_y = bar_y - 40

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(text_x, text_y)
    glTexCoord2f(1, 0)
    glVertex2f(text_x + width, text_y)
    glTexCoord2f(1, 1)
    glVertex2f(text_x + width, text_y + height)
    glTexCoord2f(0, 1)
    glVertex2f(text_x, text_y + height)
    glEnd()

    glDisable(GL_TEXTURE_2D)

    # Restaurer les états OpenGL
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

    pygame.display.flip()


def draw_rounded_rect(x, y, width, height, radius, color):
    """Dessine un rectangle arrondi rempli en OpenGL."""
    glColor4f(*color)

    # Dessiner le corps principal
    glBegin(GL_QUADS)
    glVertex2f(x + radius, y)
    glVertex2f(x + width - radius, y)
    glVertex2f(x + width - radius, y + height)
    glVertex2f(x + radius, y + height)
    glEnd()

    # Dessiner les coins arrondis
    segments = 32  # Nombre de segments pour chaque coin
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments

        # Coin supérieur gauche
        glBegin(GL_TRIANGLES)
        glVertex2f(x + radius, y + radius)
        glVertex2f(
            x + radius + radius * math.cos(angle), y + radius + radius * math.sin(angle)
        )
        glVertex2f(
            x + radius + radius * math.cos(angle + 2.0 * math.pi / segments),
            y + radius + radius * math.sin(angle + 2.0 * math.pi / segments),
        )
        glEnd()

        # Coin supérieur droit
        glBegin(GL_TRIANGLES)
        glVertex2f(x + width - radius, y + radius)
        glVertex2f(
            x + width - radius + radius * math.cos(angle),
            y + radius + radius * math.sin(angle),
        )
        glVertex2f(
            x + width - radius + radius * math.cos(angle + 2.0 * math.pi / segments),
            y + radius + radius * math.sin(angle + 2.0 * math.pi / segments),
        )
        glEnd()

        # Coin inférieur gauche
        glBegin(GL_TRIANGLES)
        glVertex2f(x + radius, y + height - radius)
        glVertex2f(
            x + radius + radius * math.cos(angle),
            y + height - radius + radius * math.sin(angle),
        )
        glVertex2f(
            x + radius + radius * math.cos(angle + 2.0 * math.pi / segments),
            y + height - radius + radius * math.sin(angle + 2.0 * math.pi / segments),
        )
        glEnd()

        # Coin inférieur droit
        glBegin(GL_TRIANGLES)
        glVertex2f(x + width - radius, y + height - radius)
        glVertex2f(
            x + width - radius + radius * math.cos(angle),
            y + height - radius + radius * math.sin(angle),
        )
        glVertex2f(
            x + width - radius + radius * math.cos(angle + 2.0 * math.pi / segments),
            y + height - radius + radius * math.sin(angle + 2.0 * math.pi / segments),
        )
        glEnd()


def draw_loading_bar(screen, font, progress):
    """Affiche une barre de chargement arrondie avec texte."""
    bar_x, bar_y = screen.get_width() * 0.2, screen.get_height() * 0.5
    bar_width, bar_height = screen.get_width() * 0.6, 30
    radius = 15  # Augmenté de 10 à 15 pour des coins plus arrondis

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glOrtho(0, screen.get_width(), screen.get_height(), 0, -1, 1)

    # Dessiner la barre de fond (grise)
    draw_rounded_rect(bar_x, bar_y, bar_width, bar_height, radius, (0.3, 0.3, 0.3, 1.0))

    # Dessiner la barre de progression (bleue)
    draw_rounded_rect(
        bar_x, bar_y, bar_width * progress, bar_height, radius, (0.0, 0.5, 1.0, 1.0)
    )

    # Afficher le texte "Chargement : ... %"
    percentage_text = f"Chargement : {int(progress * 100)}%"
    texture_id, text_width, text_height = render_text_to_texture(
        percentage_text, font, (255, 255, 255)
    )
    text_x = (screen.get_width() - text_width) / 2
    text_y = bar_y - 40

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor4f(1.0, 1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 1)
    glVertex2f(text_x, text_y)
    glTexCoord2f(1, 1)
    glVertex2f(text_x + text_width, text_y)
    glTexCoord2f(1, 0)
    glVertex2f(text_x + text_width, text_y + text_height)
    glTexCoord2f(0, 0)
    glVertex2f(text_x, text_y + text_height)
    glEnd()
    glDisable(GL_TEXTURE_2D)

    pygame.display.flip()


def start_game(screen, font, background_image, dimensions_possibles, current_state):
    global master_volume, video_capture, current_tab, waiting_for_key, slider_value, controls, frame_x, frame_y, frame_width, frame_height, spacing, is_dragging, input_active, input_text

    # Charger les paramètres sauvegardés avant l'initialisation
    load_controls()

    # Variables pour le menu de paramètres
    current_tab = "Vidéo"
    waiting_for_key = None
    frame_width = 600
    frame_height = 400
    spacing = 50
    is_dragging = False
    input_active = False
    input_text = ""

    # Chargement des ressources
    back_button_image = pygame.image.load("src/icons/back_arrow.png")
    back_button_image = pygame.transform.scale(back_button_image, (30, 30))

    pygame.init()  # Initialiser Pygame
    clock = pygame.time.Clock()
    # Charger la vidéo de fond
    local_video_path = "src/media/bg.mp4"
    video_capture = load_local_video(local_video_path)

    # Charger l'image du bouton retour
    back_button_image = pygame.image.load("src/icons/back_arrow.png").convert_alpha()
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))

    pygame.font.init()  # Initialiser la police
    display = dimensions_possibles[
        -2
    ]  # Récupérer les dimensions de l'écran et mettre une taille en dessous de la plus haute possible
    screen = pygame.display.set_mode(
        display, DOUBLEBUF | OPENGL
    )  # Créer la fenêtre Pygame
    pygame.display.set_caption("VirtuLouvre")  # Titre de la fenêtre
    start_time = time.time()
    loading_duration = 5

    vertices, texcoords, faces = [], [], []
    model_vbo, model_vertex_count, texture_id, floor_texture, sky_texture = (
        None,
        0,
        None,
        None,
        None,
    )

    while True:
        elapsed = time.time() - start_time
        progress = min(elapsed / loading_duration, 1.0)

        if progress >= 0.1 and not vertices:
            vertices, texcoords, faces = load_obj("src/models/Untitled.obj")
        if progress >= 0.3 and not model_vbo:
            model_vbo, model_vertex_count = create_model_vbo(vertices, texcoords, faces)
        if progress >= 0.5 and not texture_id:
            texture_id = load_texture("src/textures/texture.png")
        if progress >= 0.7 and not floor_texture:
            floor_texture = load_texture("src/textures/sol.png")
        if progress >= 0.9 and not sky_texture:
            sky_texture = load_texture("src/textures/sky.png")

        draw_loading_bar(screen, font, progress)

        if progress >= 1.0:
            break

    glMatrixMode(GL_MODELVIEW)  # Assure que nous sommes en mode ModelView
    glLoadIdentity()
    glScalef(-1, 1, 1)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glFrontFace(GL_CCW)

    glDisable(GL_CULL_FACE)
    menu_screen = pygame.Surface((display[0], display[1]), pygame.SRCALPHA)
    slider_value = 110
    is_dragging = False

    menu_width, menu_height = 600, 400
    menu_x = (display[0] - menu_width) // 2
    menu_y = (display[1] - menu_height) // 2

    bar_x, bar_y = 200, 300
    bar_width, bar_height = 420, 20

    player = Player(45, (display[0] / display[1]), 0.1, 200)
    player.apply_projection()
    glTranslatef(0.0, 0.0, -5)

    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glFrontFace(GL_CCW)

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)  # Mise à jour de la police ici aussi

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Configuration finale
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)

    # Boucle principale du jeu
    while True:
        delta_time = clock.tick(100) / 1000.0  # Calculer le temps écoulé
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():  # Pour chaque événement Pygame
            if event.type == pygame.QUIT:  # Si l'événement est de quitter
                pygame.quit()  # Quitter Pygame
                return

            if current_state == "settings":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if fov_slider_rect.collidepoint(event.pos):
                        is_dragging = True

                    elif event.type == pygame.MOUSEBUTTONUP:
                        is_dragging = False
                    elif event.type == pygame.MOUSEMOTION and is_dragging:
                        relative_x = event.pos[0] - fov_bar_x
                        fov_percentage = max(0.0, min(1.0, relative_x / fov_bar_width))
                        slider_value = int(60 + (fov_percentage * 60))
                        save_controls()
                    if back_rect.collidepoint(event.pos):
                        current_state = "settings"
                    for tab_button in tab_buttons:
                        if tab_button.is_clicked(event):
                            current_tab = tab_button.text
                    if current_tab == "Vidéo":
                        if left_rect.collidepoint(event.pos):
                            change_resolution(
                                (current_resolution_index - 1) % len(resolutions)
                            )
                            save_controls()
                        elif right_rect.collidepoint(event.pos):
                            change_resolution(
                                (current_resolution_index + 1) % len(resolutions)
                            )
                            save_controls()
                        # Gestion du FOV
                        fov_bar_x = (display[0] - 300) // 2 + 150
                        fov_bar_y = 240
                        fov_bar_width = 150
                        fov_bar_height = 8
                        fov_slider_rect = pygame.Rect(
                            fov_bar_x, fov_bar_y, fov_bar_width, fov_bar_height
                        )
                        # Rectangle pour la détection du clic sur le texte du FOV
                        fov_number_rect = pygame.Rect(
                            fov_bar_x + fov_bar_width + 20, fov_bar_y - 10, 60, 30
                        )
                        if fov_slider_rect.collidepoint(event.pos):
                            is_dragging = True
                            # Mettre à jour immédiatement la valeur du FOV au clic
                            relative_x = event.pos[0] - fov_bar_x
                            fov_percentage = max(
                                0.0, min(1.0, relative_x / fov_bar_width)
                            )
                            slider_value = int(60 + (fov_percentage * 60))
                            save_controls()
                        elif fov_number_rect.collidepoint(event.pos):
                            input_active = True
                            input_text = ""
                    elif current_tab == "Audio":
                        # Rectangle pour la détection du clic sur le texte du volume
                        volume_number_rect = pygame.Rect(
                            volume_slider_rect.right + 20,
                            volume_slider_rect.y - 10,
                            60,
                            30,
                        )
                        if volume_slider_rect.collidepoint(event.pos):
                            is_dragging = True
                            relative_x = event.pos[0] - volume_slider_rect.x
                            master_volume = int(
                                max(
                                    0.0, min(1.0, relative_x / volume_slider_rect.width)
                                )
                                * 100
                            )
                            walk_sound_effect.set_volume(master_volume / 100)
                            save_controls()
                        elif volume_number_rect.collidepoint(event.pos):
                            input_active = True
                            input_text = ""
                    elif current_tab == "Touches":
                        if reset_button_rect.collidepoint(event.pos):
                            controls = DEFAULT_CONTROLS.copy()
                            save_controls()
                        mouse_x, mouse_y = event.pos
                        for i, (key, action) in enumerate(controls):
                            control_frame_x = frame_x + 20
                            control_frame_y = frame_y + 20 + i * spacing
                            control_frame_width = frame_width - 40
                            control_frame_height = 30

                            if (
                                control_frame_x + control_frame_width - 60
                                <= mouse_x
                                <= control_frame_x + control_frame_width - 20
                                and control_frame_y
                                <= mouse_y
                                <= control_frame_y + control_frame_height
                            ) and key != "ÉCHAP":
                                waiting_for_key = i
                                break
                elif event.type == pygame.MOUSEBUTTONUP:
                    is_dragging = False
                elif event.type == pygame.MOUSEMOTION and is_dragging:
                    if current_tab == "Vidéo":
                        fov_bar_x = (display[0] - 300) // 2 + 150
                        fov_bar_y = 240
                        fov_bar_width = 150
                        relative_x = event.pos[0] - fov_bar_x
                        fov_percentage = max(0.0, min(1.0, relative_x / fov_bar_width))
                        slider_value = int(60 + (fov_percentage * 60))
                        save_controls()
                    elif current_tab == "Audio" and volume_slider_rect.collidepoint(
                        event.pos
                    ):
                        relative_x = event.pos[0] - volume_slider_rect.x
                        master_volume = int(
                            max(0.0, min(1.0, relative_x / volume_slider_rect.width))
                            * 100
                        )
                        walk_sound_effect.set_volume(master_volume / 100)
                        save_controls()
                elif event.type == pygame.KEYDOWN:
                    if input_active:
                        if event.key == pygame.K_RETURN:
                            try:
                                new_value = int(input_text)
                                if current_tab == "Vidéo":
                                    if new_value > 120:
                                        new_value = 120
                                    elif new_value < 60:
                                        new_value = 60
                                    slider_value = new_value
                                elif current_tab == "Audio":
                                    if new_value > 100:
                                        new_value = 100
                                    elif new_value < 0:
                                        new_value = 0
                                    master_volume = new_value
                                    walk_sound_effect.set_volume(master_volume / 100)
                                save_controls()
                            except ValueError:
                                pass
                            input_active = False
                        elif event.key == pygame.K_BACKSPACE:
                            input_text = input_text[:-1]
                        elif event.unicode.isdigit() and len(input_text) < 3:
                            input_text += event.unicode
            else:
                # Pour les autres états, on traite les événements normalement
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        current_state = (
                            "game_menu" if current_state != "game_menu" else "game"
                        )
                        pygame.event.set_grab(
                            current_state != "game_menu"
                        )  # Capturer la souris si menu ouvert
                        pygame.mouse.set_visible(
                            current_state == "game_menu"
                        )  # Afficher le curseur si menu ouvert
                    elif event.key == pygame.K_F11:  # Si la touche est F11
                        toggle_fullscreen()
                    elif input_active:
                        if event.key == pygame.K_RETURN:
                            try:
                                new_value = int(input_text)
                                if current_tab == "Vidéo":
                                    if new_value > 120:
                                        new_value = 120
                                    elif new_value < 60:
                                        new_value = 60
                                    slider_value = new_value
                                elif current_tab == "Audio":
                                    if new_value > 100:
                                        new_value = 100
                                    elif new_value < 0:
                                        new_value = 0
                                    master_volume = new_value
                                    walk_sound_effect.set_volume(master_volume / 100)
                                save_controls()
                            except ValueError:
                                pass
                            input_active = False
                        elif event.key == pygame.K_BACKSPACE:
                            input_text = input_text[:-1]
                        elif event.unicode.isdigit() and len(input_text) < 3:
                            input_text += event.unicode

                # Mettre à jour le joueur uniquement si on est dans l'état "game"
                if current_state == "game":
                    if event.type == pygame.MOUSEMOTION:
                        xoffset, yoffset = event.rel
                        player.process_mouse(xoffset, -yoffset)

        # Mise à jour du joueur
        if current_state == "game":
            player.process_keyboard(keys)
            player.update(delta_time)

        # Effacer le tampon
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Rendu de la scène 3D
        if current_state in ["game", "game_menu", "game_settings"]:
            player.apply()
            player.fov = slider_value
            player.apply_projection()

            glDisable(GL_CULL_FACE)
            draw_skybox(sky_texture)
            draw_textured_floor(floor_texture)

            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            draw_model(model_vbo, model_vertex_count)
            glDisable(GL_TEXTURE_2D)

            draw_crosshair(display[0], display[1])

        # Gestion des différents états
        if current_state == "game_menu":
            # Clear the menu overlay
            menu_screen.fill((0, 0, 0, 0))

            # Draw semi-transparent menu background
            pygame.draw.rect(
                menu_screen,
                (20, 20, 20, 180),
                (menu_x, menu_y, menu_width, menu_height),
                border_radius=15,
            )

            # Define buttons
            buttons = [
                Button(
                    display[0] // 2 - 100,
                    display[1] // 2 - 100,
                    200,
                    50,
                    "Resume",
                    (255, 255, 255),
                    font,
                    BLUE,
                    HOVER_BLUE,
                ),
                Button(
                    display[0] // 2 - 100,
                    display[1] // 2 - 20,
                    200,
                    50,
                    "Settings",
                    (255, 255, 255),
                    font,
                    BLUE,
                    HOVER_BLUE,
                ),
                Button(
                    display[0] // 2 - 100,
                    display[1] // 2 + 60,
                    200,
                    50,
                    "Quit",
                    (255, 255, 255),
                    font,
                    BLUE,
                    HOVER_BLUE,
                ),
            ]

            mouse_pos = pygame.mouse.get_pos()

            for button in buttons:
                button.draw(menu_screen)
                if pygame.mouse.get_pressed()[0]:
                    if button.rect.collidepoint(mouse_pos):
                        if button.text == "Resume":
                            current_state = "game"
                            pygame.event.set_grab(True)
                            pygame.mouse.set_visible(False)
                        elif button.text == "Settings":
                            current_state = "game_settings"
                        elif button.text == "Quit":
                            quit_game()

            # Now use the correct OpenGL method to overlay the 2D menu
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, display[0], display[1], 0, -1, 1)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            menu_texture_data = pygame.image.tostring(menu_screen, "RGBA", True)
            glWindowPos2d(0, 0)
            glDrawPixels(
                display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, menu_texture_data
            )

            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

            glEnable(GL_DEPTH_TEST)

        elif current_state == "game_settings":
            # Set up orthographic projection for 2D rendering
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, display[0], display[1], 0, -1, 1)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            settings_screen = pygame.Surface((display[0], display[1]), pygame.SRCALPHA)
            settings_screen.fill((0, 0, 0, 180))  # Récupérer tous les événements pygame
            (
                back_rect,
                tab_buttons,
                left_rect,
                right_rect,
                volume_slider_rect,
                reset_button_rect,
            ) = display_settings(settings_screen, font, back_button_image, current_tab)

            settings_texture_data = pygame.image.tostring(settings_screen, "RGBA", True)
            glWindowPos2d(0, 0)
            glDrawPixels(
                display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, settings_texture_data
            )

            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

            glEnable(GL_DEPTH_TEST)

            # Handle settings events
            if event.type == pygame.MOUSEBUTTONDOWN:
                if back_rect.collidepoint(event.pos):
                    current_state = "game_menu"
                for tab_button in tab_buttons:
                    if tab_button.is_clicked(event):
                        current_tab = tab_button.text
                if current_tab == "Vidéo":
                    if left_rect.collidepoint(event.pos):
                        change_resolution(
                            (current_resolution_index - 1) % len(resolutions)
                        )
                        save_controls()
                    elif right_rect.collidepoint(event.pos):
                        change_resolution(
                            (current_resolution_index + 1) % len(resolutions)
                        )
                        save_controls()
                    # Gestion du FOV
                    fov_bar_x = (display[0] - 300) // 2 + 150
                    fov_bar_y = 240
                    fov_bar_width = 150
                    fov_bar_height = 8
                    fov_slider_rect = pygame.Rect(
                        fov_bar_x, fov_bar_y, fov_bar_width, fov_bar_height
                    )
                    # Rectangle pour la détection du clic sur le texte du FOV
                    fov_number_rect = pygame.Rect(
                        fov_bar_x + fov_bar_width + 20, fov_bar_y - 10, 60, 30
                    )
                    if fov_slider_rect.collidepoint(event.pos):
                        is_dragging = True
                        # Mettre à jour immédiatement la valeur du FOV au clic
                        relative_x = event.pos[0] - fov_bar_x
                        fov_percentage = max(0.0, min(1.0, relative_x / fov_bar_width))
                        slider_value = int(60 + (fov_percentage * 60))
                        save_controls()
                    elif fov_number_rect.collidepoint(event.pos):
                        input_active = True
                        input_text = ""
                elif current_tab == "Audio":
                    # Rectangle pour la détection du clic sur le texte du volume
                    volume_number_rect = pygame.Rect(
                        volume_slider_rect.right + 20, volume_slider_rect.y - 10, 60, 30
                    )
                    if volume_slider_rect.collidepoint(event.pos):
                        is_dragging = True
                        relative_x = event.pos[0] - volume_slider_rect.x
                        master_volume = int(
                            max(0.0, min(1.0, relative_x / volume_slider_rect.width))
                            * 100
                        )
                        walk_sound_effect.set_volume(master_volume / 100)
                        save_controls()
                    elif volume_number_rect.collidepoint(event.pos):
                        input_active = True
                        input_text = ""
                elif current_tab == "Touches":
                    if reset_button_rect.collidepoint(event.pos):
                        controls = DEFAULT_CONTROLS.copy()
                        save_controls()
                    mouse_x, mouse_y = event.pos
                    for i, (key, action) in enumerate(controls):
                        control_frame_x = frame_x + 20
                        control_frame_y = frame_y + 20 + i * spacing
                        control_frame_width = frame_width - 40
                        control_frame_height = 30

                        if (
                            control_frame_x + control_frame_width - 60
                            <= mouse_x
                            <= control_frame_x + control_frame_width - 20
                            and control_frame_y
                            <= mouse_y
                            <= control_frame_y + control_frame_height
                        ) and key != "ÉCHAP":
                            waiting_for_key = i
                            break
            elif event.type == pygame.MOUSEBUTTONUP:
                is_dragging = False
            elif event.type == pygame.MOUSEMOTION and is_dragging:
                if current_tab == "Vidéo":
                    fov_bar_x = (display[0] - 300) // 2 + 150
                    fov_bar_y = 240
                    fov_bar_width = 150
                    relative_x = event.pos[0] - fov_bar_x
                    fov_percentage = max(0.0, min(1.0, relative_x / fov_bar_width))
                    slider_value = int(60 + (fov_percentage * 60))
                    save_controls()
                elif current_tab == "Audio" and volume_slider_rect.collidepoint(
                    event.pos
                ):
                    relative_x = event.pos[0] - volume_slider_rect.x
                    master_volume = int(
                        max(0.0, min(1.0, relative_x / volume_slider_rect.width)) * 100
                    )
                    walk_sound_effect.set_volume(master_volume / 100)
                    save_controls()
            elif event.type == pygame.KEYDOWN:
                if input_active:
                    if event.key == pygame.K_RETURN:
                        try:
                            new_value = int(input_text)
                            if current_tab == "Vidéo":
                                if new_value > 120:
                                    new_value = 120
                                elif new_value < 60:
                                    new_value = 60
                                slider_value = new_value
                            elif current_tab == "Audio":
                                if new_value > 100:
                                    new_value = 100
                                elif new_value < 0:
                                    new_value = 0
                                master_volume = new_value
                                walk_sound_effect.set_volume(master_volume / 100)
                            save_controls()
                        except ValueError:
                            pass
                        input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif event.unicode.isdigit() and len(input_text) < 3:
                        input_text += event.unicode

        pygame.display.flip()


# Modified afficher_parametres function to work with a surface paramete
# Fonction principale du menu
def main_menu():
    global controls, waiting_for_key, frame_x, frame_y, frame_width, frame_height, spacing
    pygame.init()

    # Charger les contrôles sauvegardés
    load_controls()

    # Paramètres d'écran - ajout du flag NOFRAME pour borderless
    screen_width, screen_height = 768, 768
    screen = pygame.display.set_mode(
        (screen_width, screen_height), pygame.RESIZABLE | pygame.NOFRAME
    )
    pygame.display.set_caption("Menu principal")

    # Variables pour le déplacement de la fenêtre
    dragging = False
    drag_offset_x = 0
    drag_offset_y = 0
    window_x = 0
    window_y = 0

    # Variable pour suivre la touche en cours de modification
    waiting_for_key = None

    # Créer des surfaces colorées au lieu de charger des images
    credits_background = pygame.Surface((screen_width, screen_height))
    credits_background.fill((40, 40, 40))  # Gris foncé

    game_background = pygame.Surface((screen_width, screen_height))
    game_background.fill((20, 20, 20))  # Presque noir

    # Charger la vidéo de fond pour le menu principal
    local_video_path = "src/media/bg.mp4"
    video_capture = load_local_video(local_video_path)

    # Variables pour le contrôle de la vidéo

    frame_delay = 1.0 / 35  # Temps entre chaque frame en secondes
    last_frame_time = time.time()

    # Charger l'image de la flèche pour le retour
    back_button_image = pygame.image.load(
        "src/icons/back_arrow.png"
    ).convert_alpha()  # Assurez-vous d'avoir cette image
    back_button_image = pygame.transform.scale(
        back_button_image, (50, 50)
    )  # Ajustez la taille selon votre besoin

    # Couleurs et police
    blue = (100, 200, 255)
    hover_blue = (50, 150, 255)
    font = pygame.font.Font(None, 24)  # Réduit de 36 à 24

    # Calculer la taille des boutons en fonction de la taille de la fenêtre
    button_width = int(screen_width * 0.3)  # 30% de la largeur de la fenêtre
    button_height = int(screen_height * 0.08)  # 8% de la hauteur de la fenêtre
    button_spacing = int(screen_height * 0.02)  # 2% de la hauteur de la fenêtre
    total_height = 4 * button_height + 3 * button_spacing

    start_y = (screen_height - total_height) // 2  # Centre verticalement

    buttons = [
        Button(
            screen_width // 2 - button_width // 2,
            start_y,
            button_width,
            button_height,
            "Visiter le site",
            WHITE,
            font,
            blue,
            hover_blue,
        ),
        Button(
            screen_width // 2 - button_width // 2,
            start_y + button_height + button_spacing,
            button_width,
            button_height,
            "Paramètres",
            WHITE,
            font,
            blue,
            hover_blue,
        ),
        Button(
            screen_width // 2 - button_width // 2,
            start_y + 2 * (button_height + button_spacing),
            button_width,
            button_height,
            "Crédits",
            WHITE,
            font,
            blue,
            hover_blue,
        ),
        Button(
            screen_width // 2 - button_width // 2,
            start_y + 3 * (button_height + button_spacing),
            button_width,
            button_height,
            "Quitter",
            WHITE,
            font,
            blue,
            hover_blue,
        ),
    ]

    clock = pygame.time.Clock()
    running = True
    current_state = "parametres"
    current_tab = "Vidéo"
    slider_value = 110
    is_dragging = False

    while running:
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Sauvegarder les contrôles avant de quitter
                save_controls()
                running = False

            # Gestion du déplacement de la fenêtre
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic gauche
                    mouse_x, mouse_y = event.pos
                    # Vérifier si le clic est dans la zone de titre (haut de la fenêtre)
                    if mouse_y < 30:  # Zone de titre de 30 pixels de haut
                        dragging = True
                        drag_offset_x = mouse_x
                        drag_offset_y = mouse_y

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Clic gauche
                    dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    # Calculer le déplacement
                    dx = event.pos[0] - drag_offset_x
                    dy = event.pos[1] - drag_offset_y
                    # Mettre à jour la position de la fenêtre
                    window_x += dx
                    window_y += dy
                    # Déplacer la fenêtre
                    if os.name == "nt":  # Windows
                        from ctypes import windll

                        hwnd = pygame.display.get_wm_info()["window"]
                        windll.user32.SetWindowPos(
                            hwnd, 0, window_x, window_y, 0, 0, 0x0001
                        )

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:  # Si la touche est F11
                    toggle_fullscreen()

            elif event.type == pygame.VIDEORESIZE:  # Détecte le redimensionnement
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height), pygame.RESIZABLE | pygame.NOFRAME
                )
                # Redimensionner les arrière-plans
                credits_background = pygame.transform.scale(
                    credits_background, (screen_width, screen_height)
                )
                game_background = pygame.transform.scale(
                    game_background, (screen_width, screen_height)
                )
                # Mettre à jour la position des boutons
                start_y = (screen_height - total_height) // 2
                buttons[0].rect.topleft = (
                    screen_width // 2 - button_width // 2,
                    start_y,
                )
                buttons[1].rect.topleft = (
                    screen_width // 2 - button_width // 2,
                    start_y + button_height + button_spacing,
                )
                buttons[2].rect.topleft = (
                    screen_width // 2 - button_width // 2,
                    start_y + 2 * (button_height + button_spacing),
                )
                buttons[3].rect.topleft = (
                    screen_width // 2 - button_width // 2,
                    start_y + 3 * (button_height + button_spacing),
                )

            if current_state == "parametres":
                for button in buttons:
                    if button.is_clicked(event):
                        if button.text == "Visiter le site":
                            current_state = "game"
                        elif button.text == "Paramètres":
                            current_state = "settings"
                        elif button.text == "Crédits":
                            current_state = "credits"
                        elif button.text == "Quitter":
                            pygame.quit()
                            sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    current_state = "parametres"
                elif event.key == pygame.K_LEFT:
                    current_state = "parametres"

            if current_state == "settings":
                (
                    back_rect,
                    tab_buttons,
                    left_rect,
                    right_rect,
                    volume_slider_rect,
                    reset_button_rect,
                ) = display_settings(
                    screen, font, back_button_image, current_tab, event
                )
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        current_state = "parametres"
                    for tab_button in tab_buttons:
                        if tab_button.is_clicked(event):
                            current_tab = tab_button.text
                    if current_tab == "Vidéo":
                        if left_rect.collidepoint(event.pos):
                            change_resolution(
                                (current_resolution_index - 1) % len(resolutions)
                            )
                        elif right_rect.collidepoint(event.pos):
                            change_resolution(
                                (current_resolution_index + 1) % len(resolutions)
                            )
                    elif current_tab == "Audio":
                        if volume_slider_rect.collidepoint(event.pos):
                            # Calculer le volume en fonction de la position du clic
                            global master_volume
                            relative_x = event.pos[0] - volume_slider_rect.x
                            master_volume = max(
                                0.0, min(1.0, relative_x / volume_slider_rect.width)
                            )
                            # Mettre à jour le volume de tous les sons
                            walk_sound_effect.set_volume(master_volume)
                            save_controls()
                    elif current_tab == "Touches":
                        if reset_button_rect.collidepoint(event.pos):
                            controls = DEFAULT_CONTROLS.copy()
                            save_controls()
                        # Vérifier si un clic a été fait sur une touche
                        mouse_x, mouse_y = event.pos
                        for i, (key, action) in enumerate(controls):
                            control_frame_x = frame_x + 20
                            control_frame_y = frame_y + 20 + i * spacing
                            control_frame_width = frame_width - 40
                            control_frame_height = 30

                            if (
                                control_frame_x + control_frame_width - 60
                                <= mouse_x
                                <= control_frame_x + control_frame_width - 20
                                and control_frame_y
                                <= mouse_y
                                <= control_frame_y + control_frame_height
                            ) and key != "ÉCHAP":
                                waiting_for_key = i
                                break
                elif event.type == pygame.KEYDOWN and waiting_for_key is not None:
                    # Si la touche est ÉCHAP, supprimer la touche assignée
                    if event.key == pygame.K_ESCAPE:
                        controls[waiting_for_key] = ("-", controls[waiting_for_key][1])
                        waiting_for_key = None
                        save_controls()
                    else:
                        # Convertir la touche en texte
                        key_name = pygame.key.name(event.key).upper()
                        if key_name == "ESCAPE":
                            key_name = "ÉCHAP"
                        elif key_name == "SPACE":
                            key_name = "ESPACE"
                        elif key_name == "LEFT SHIFT":
                            key_name = "SHIFT"

                        # Mettre à jour la touche
                        controls[waiting_for_key] = (
                            key_name,
                            controls[waiting_for_key][1],
                        )
                        waiting_for_key = None
                        save_controls()
                elif (
                    event.type == pygame.MOUSEMOTION and event.buttons[0]
                ):  # Si le bouton gauche est maintenu
                    if current_tab == "Audio" and volume_slider_rect.collidepoint(
                        event.pos
                    ):
                        # Mettre à jour le volume pendant le glissement
                        relative_x = event.pos[0] - volume_slider_rect.x
                        master_volume = max(
                            0.0, min(1.0, relative_x / volume_slider_rect.width)
                        )
                        # Mettre à jour le volume de tous les sons
                        walk_sound_effect.set_volume(master_volume)
                        save_controls()

        # Afficher l'état courant
        if current_state == "parametres":
            # Contrôle du framerate de la vidéo
            if current_time - last_frame_time >= frame_delay:
                if video_capture:
                    ret, frame = video_capture.read()
                    if ret:
                        frame = cv2.resize(frame, (screen_width, screen_height))
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_surface = pygame.surfarray.make_surface(frame)
                        screen.blit(pygame.transform.rotate(frame_surface, -90), (0, 0))
                    else:
                        video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                last_frame_time = current_time

            # Dessiner la barre de titre
            pygame.draw.rect(screen, (40, 40, 40), (0, 0, screen_width, 30))
            title_text = font.render("VirtuLouvre", True, (255, 255, 255))
            screen.blit(title_text, (10, 5))

            for button in buttons:
                button.draw(screen)
            # Afficher la version en bas à droite
            version_surface = version_font.render(version_text, True, (255, 255, 255))
            version_rect = version_surface.get_rect(
                bottomright=(screen_width - 10, screen_height - 10)
            )
            screen.blit(version_surface, version_rect)

        elif current_state == "credits":
            back_rect = display_credits(screen, font, back_button_image)
            if event.type == pygame.MOUSEBUTTONDOWN and back_rect.collidepoint(
                event.pos
            ):
                current_state = "parametres"
        elif current_state == "settings":
            display_settings(screen, font, back_button_image, current_tab)
        elif current_state == "game":
            start_game(
                screen, font, game_background, dimensions_possibles, current_state
            )
            pygame.display.flip()
        elif current_state == "quitter":
            quit_game()

        pygame.display.flip()  # Limiter le framerate global à 60 FPS

    if video_capture:
        video_capture.release()
    # Sauvegarder les contrôles avant de quitter
    save_controls()
    pygame.quit()


def save_controls():
    """Sauvegarde les contrôles dans le fichier de configuration."""
    config_dir = "config"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    config_file = os.path.join(config_dir, "settings.json")
    config_data = {
        "controls": controls,
        "master_volume": master_volume,
        "slider_value": slider_value,
    }

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=4)


def load_controls():
    """Charge les contrôles depuis le fichier de configuration."""
    global controls, master_volume, slider_value

    # S'assurer que controls a une valeur par défaut
    if controls is None:
        controls = DEFAULT_CONTROLS.copy()

    config_file = os.path.join("config", "settings.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
                if "controls" in config_data:
                    controls = config_data["controls"]
                if "master_volume" in config_data:
                    master_volume = config_data["master_volume"]
                    # Appliquer le volume aux effets sonores
                    if "walk_sound_effect" in globals():
                        walk_sound_effect.set_volume(master_volume)
                if "slider_value" in config_data:
                    slider_value = config_data["slider_value"]
        except Exception as e:
            print(f"Erreur lors du chargement des contrôles: {e}")
            # En cas d'erreur, utiliser les contrôles par défaut
            controls = DEFAULT_CONTROLS.copy()

    return controls  # Retourner les contrôles chargés ou par défaut


if __name__ == "__main__":
    main_menu()

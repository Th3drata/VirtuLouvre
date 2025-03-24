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

pygame.init()  # Initialiser Pygame
pygame.mixer.init()

walk_sound_effect = pygame.mixer.Sound("src/sound.wav")
walk_sound_effect.set_volume(0.5)
# Dimensions de l'écran
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
controls = [
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

# Variables globales pour le menu des contrôles
frame_x = 0
frame_y = 0
frame_width = 500
frame_height = 0
spacing = 40


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
        }

        # Activer/Désactiver le sprint avec la touche personnalisée
        sprint_key = key_mapping.get(
            controls[4][0], pygame.K_v
        )  # Touche "V" par défaut
        if keys[sprint_key]:
            self.is_sprinting = True
        else:
            self.is_sprinting = False

        # Gestion du vol et de l'atterrissage
        fly_key = key_mapping.get(
            controls[5][0], pygame.K_SPACE
        )  # Touche "ESPACE" par défaut
        land_key = key_mapping.get(controls[7][0], pygame.K_g)  # Touche "G" par défaut

        if keys[land_key]:
            self.is_flying = False
        elif keys[fly_key]:
            self.is_flying = True

        if self.is_flying:
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

        if keys[forward_key]:  # Forward
            forward_dir = np.array([self.front[0], 0, self.front[2]])
            if np.linalg.norm(forward_dir) > 0:
                forward_dir = forward_dir / np.linalg.norm(forward_dir)
                move_dir += forward_dir
                walk_sound()

        if keys[backward_key]:  # Backward
            backward_dir = np.array([self.front[0], 0, self.front[2]])
            if np.linalg.norm(backward_dir) > 0:
                backward_dir = backward_dir / np.linalg.norm(backward_dir)
                move_dir -= backward_dir
                walk_sound()

        if keys[left_key]:  # Left
            left_dir = np.array([self.right[0], 0, self.right[2]])
            if np.linalg.norm(left_dir) > 0:
                left_dir = left_dir / np.linalg.norm(left_dir)
                move_dir -= left_dir
                walk_sound()

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
        min_x, max_x = -30.0, 30.0  # Limites de la carte
        min_z, max_z = -30.0, 30.0  # Limites de la carte
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
        (256, 144),
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
    grid_size = 35  # Taille de la grille
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
    texture_id, grid_size=100, texture_width=0.5, texture_height=0.5
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
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(
            event.pos
        )


# Fonction pour afficher les crédits
def display_credits(screen, font, back_button_image):
    screen_width, screen_height = screen.get_size()

    # Définition du texte des crédits
    credits_text = [
        "Crédits",
        "Développé par",
        "Albert Oscar, Moors Michel, Rinckenbach Yann",
        "",
        "Merci d'avoir joué !",
    ]

    # Création d'une surface semi-transparente pour un effet moderne
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((10, 10, 10, 200))  # Fond sombre semi-transparent
    screen.blit(overlay, (0, 0))

    # Position de départ du texte
    start_y = screen_height // 2 - len(credits_text) * 20
    line_spacing = 50  # Espacement entre les lignes

    # Affichage des crédits avec un style épuré
    for i, line in enumerate(credits_text):
        text_color = (
            (255, 255, 255) if i == 0 else (180, 180, 180)
        )  # Le titre en blanc, le reste en gris clair
        text_surface = font.render(line, True, text_color)
        text_rect = text_surface.get_rect(
            center=(screen_width // 2, start_y + i * line_spacing)
        )
        screen.blit(text_surface, text_rect)

    # Charger et afficher l'image du bouton de retour
    back_button_image = pygame.transform.scale(
        back_button_image, (50, 50)
    )  # Redimensionner si nécessaire
    back_rect = back_button_image.get_rect(
        topleft=(30, 30)
    )  # Positionner en haut à gauche
    screen.blit(back_button_image, back_rect)

    return back_rect  # Retourne le rectangle du bouton pour détecter le clic


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
    global screen, current_resolution_index, settings_background
    current_resolution_index = index
    width, height = resolutions[index]

    if width == 0 and height == 0:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        width, height = pygame.display.Info().current_w, pygame.display.Info().current_h
    else:
        screen = pygame.display.set_mode((width, height))

    settings_background = pygame.transform.scale(
        pygame.image.load("src/settings_bg.jpg").convert(), (width, height)
    )


arrow_left = pygame.image.load("src/arrow_left.png")
arrow_right = pygame.image.load("src/arrow_right.png")
arrow_size = (50, 50)
arrow_left = pygame.transform.scale(arrow_left, arrow_size)
arrow_right = pygame.transform.scale(arrow_right, arrow_size)


# Fonction pour afficher les paramètres
def display_settings(screen, font, back_button_image, current_tab, settings_background):
    global master_volume, controls, frame_x, frame_y, frame_width, frame_height, spacing
    screen.blit(settings_background, (0, 0))
    tabs = ["Vidéo", "Audio", "Touches"]  # Remplacer "JSP" par "Touches"
    tab_buttons = []
    tab_width, tab_height, tab_spacing = 240, 40, -10
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
                (200, 200, 200),
                (150, 150, 150),
            )
        )
        tab_buttons[i].draw(screen)

    left_rect, right_rect = pygame.Rect(0, 0, 0, 0), pygame.Rect(0, 0, 0, 0)
    volume_slider_rect = pygame.Rect(0, 0, 0, 0)

    if current_tab == "Vidéo":
        resolution_text = (
            "Plein écran"
            if resolutions[current_resolution_index] == (0, 0)
            else f"{resolutions[current_resolution_index][0]} x {resolutions[current_resolution_index][1]}"
        )
        text_surface = font.render(resolution_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(screen.get_width() // 2, 200))
        screen.blit(text_surface, text_rect)
        left_rect = arrow_left.get_rect(midright=(text_rect.left - 20, 200))
        right_rect = arrow_right.get_rect(midleft=(text_rect.right + 20, 200))
        screen.blit(arrow_left, left_rect)
        screen.blit(arrow_right, right_rect)

    elif current_tab == "Audio":
        # Titre du volume
        volume_text = font.render("Volume Master", True, (255, 255, 255))
        volume_text_rect = volume_text.get_rect(center=(screen.get_width() // 2, 200))
        screen.blit(volume_text, volume_text_rect)

        # Barre de volume
        bar_width = 400
        bar_height = 20
        bar_x = (screen.get_width() - bar_width) // 2
        bar_y = 250

        # Fond de la barre
        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))

        # Barre de volume actuelle
        volume_width = int(bar_width * master_volume)
        pygame.draw.rect(
            screen, (0, 200, 255), (bar_x, bar_y, volume_width, bar_height)
        )

        # Curseur de volume
        cursor_x = bar_x + volume_width
        cursor_y = bar_y + bar_height // 2
        pygame.draw.circle(screen, (255, 255, 255), (cursor_x, cursor_y), 10)

        # Valeur du volume en pourcentage
        volume_value = int(master_volume * 100)
        value_text = font.render(f"{volume_value}%", True, (255, 255, 255))
        value_rect = value_text.get_rect(center=(screen.get_width() // 2, bar_y + 40))
        screen.blit(value_text, value_rect)

        # Rectangle pour la détection du clic sur la barre
        volume_slider_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)

    elif current_tab == "Touches":
        # Titre
        title_text = font.render("Contrôles du jeu", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(screen.get_width() // 2, 200))
        screen.blit(title_text, title_rect)

        # Position de départ
        start_y = 300
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
            control_frame_width = (
                frame_width - 40
            )  # Ajusté pour correspondre à la nouvelle largeur
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
                "..." if waiting_for_key == i else key, True, (0, 200, 255)
            )
            key_rect = key_text.get_rect(
                center=(
                    control_frame_x + control_frame_width - 40,
                    control_frame_y + control_frame_height // 2,
                )
            )
            screen.blit(key_text, key_rect)

            # Action (à gauche)
            action_text = font.render(action, True, (255, 255, 255))
            action_rect = action_text.get_rect(
                center=(
                    control_frame_x + 40,
                    control_frame_y + control_frame_height // 2,
                )
            )
            screen.blit(action_text, action_rect)

    back_rect = back_button_image.get_rect(center=(40, screen.get_height() - 30))
    screen.blit(back_button_image, back_rect)
    return back_rect, tab_buttons, left_rect, right_rect, volume_slider_rect


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
    glBegin(GL_POLYGON)

    # Dessiner le corps principal
    glVertex2f(x + radius, y)
    glVertex2f(x + width - radius, y)
    glVertex2f(x + width, y + radius)
    glVertex2f(x + width, y + height - radius)
    glVertex2f(x + width - radius, y + height)
    glVertex2f(x + radius, y + height)
    glVertex2f(x, y + height - radius)
    glVertex2f(x, y + radius)
    glEnd()


def draw_loading_bar(screen, font, progress):
    """Affiche une barre de chargement arrondie avec texte."""
    bar_x, bar_y = screen.get_width() * 0.2, screen.get_height() * 0.5
    bar_width, bar_height = screen.get_width() * 0.6, 30
    radius = 10

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


def display_menu():
    pygame.init()
    global screen, settings_background
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Menu principal")
    settings_background = pygame.image.load("src/settings_bg.jpg").convert()
    settings_background = pygame.transform.scale(settings_background, (800, 600))
    back_button_image = pygame.image.load("src/back_arrow.png").convert_alpha()
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))
    font = pygame.font.Font(None, 36)
    blue, hover_blue = (100, 200, 255), (50, 150, 255)
    buttons = [Button(350, 300, 200, 50, "Paramètres", font, blue, hover_blue)]
    clock = pygame.time.Clock()
    running, current_state, current_tab = True, "menu", "Vidéo"

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if current_state == "menu":
                for button in buttons:
                    if button.is_clicked(event):
                        current_state = "settings"
            elif current_state == "settings":
                back_rect, tab_buttons, left_rect, right_rect, volume_slider_rect = (
                    display_settings(screen, font, back_button_image, current_tab)
                )
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        current_state = "menu"
                    for tab_button in tab_buttons:
                        if tab_button.is_clicked(event):
                            current_tab = tab_button.text
                    if left_rect.collidepoint(event.pos):
                        change_resolution(
                            (current_resolution_index - 1) % len(resolutions)
                        )
                    elif right_rect.collidepoint(event.pos):
                        change_resolution(
                            (current_resolution_index + 1) % len(resolutions)
                        )

        screen.fill((0, 0, 0))
        if current_state == "menu":
            for button in buttons:
                button.draw(screen)
        elif current_state == "settings":
            display_settings(screen, font, back_button_image, current_tab)

        pygame.display.flip()
        clock.tick(35)
    pygame.quit()


def start_game(screen, font, background_image, dimensions_possibles, current_state):
    global master_volume
    pygame.init()  # Initialiser Pygame
    clock = pygame.time.Clock()

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
            vertices, texcoords, faces = load_obj("src/Untitled.obj")
        if progress >= 0.3 and not model_vbo:
            model_vbo, model_vertex_count = create_model_vbo(vertices, texcoords, faces)
        if progress >= 0.5 and not texture_id:
            texture_id = load_texture("src/texture.png")
        if progress >= 0.7 and not floor_texture:
            floor_texture = load_texture("src/sol.png")
        if progress >= 0.9 and not sky_texture:
            sky_texture = load_texture("src/sky.png")

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
    font = pygame.font.SysFont("Arial", 18)

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

            # Mettre à jour le joueur
            if current_state == "game":
                if event.type == pygame.MOUSEMOTION:
                    xoffset, yoffset = event.rel
                    player.process_mouse(xoffset, -yoffset)

            if event.type == pygame.QUIT:  # Si l'événement est de quitter
                pygame.quit()  # Quitter Pygame
                return

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

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:  # Si la touche est F11
                    toggle_fullscreen()
            # Handle slider interaction when menu is open

            if current_state == "bonjour":
                mouse_x, mouse_y = pygame.mouse.get_pos()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if (
                        bar_x <= mouse_x <= bar_x + bar_width
                        and bar_y <= mouse_y <= bar_y + bar_height
                    ):
                        is_dragging = True  # Activer le glissement du slider

                    elif event.type == pygame.MOUSEBUTTONUP:
                        is_dragging = False  # Désactiver le glissement

                    elif event.type == pygame.MOUSEMOTION and is_dragging:
                        relative_x = mouse_x - bar_x
                        slider_value = 70 + (relative_x / bar_width) * 80
                        slider_value = max(
                            70, min(150, slider_value)
                        )  # Clamp entre 70 et 150

                        # Appliquer immédiatement au joueur
                        player.fov = slider_value
                        player.apply_projection()

        if current_state == "game":
            player.process_keyboard(keys)
            player.update(delta_time)  # Mettre à jour le joueur

        glClear(
            GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT
        )  # Effacer le tampon de couleur et le tampon de profondeur

        if current_state == "game":
            player.apply()  # Appliquer la vue
            # Appliquer la nouvelle valeur de FOV
            player.fov = slider_value
            player.apply_projection()  # Affichage des paramètres FOV
            glDisable(GL_CULL_FACE)
            draw_skybox(sky_texture)
            draw_textured_floor(floor_texture)
            # grid() # Afficher la grille

            glEnable(GL_TEXTURE_2D)  # Activer la texture
            glBindTexture(GL_TEXTURE_2D, texture_id)  # Lier la texture
            draw_model(model_vbo, model_vertex_count)  # Dessiner le modèle
            glDisable(GL_TEXTURE_2D)  # Désactiver la texture

            # draw_fps(clock, font, screenwidth=2560, screenheight=1440)
            draw_crosshair(display[0], display[1])

        # If menu is open, render transparent menu overlay

        # Handle different states
        if current_state == "game_menu":
            # First render the 3D scene
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

            # Finish 3D rendering
            glFinish()

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
                            current_state = (
                                "bonjour" if current_state != "bonjour" else "game_menu"
                            )
                        elif button.text == "Quit":
                            pygame.quit()
                            return

            # Now use the correct OpenGL method to overlay the 2D menu
            # Set up orthographic projection for 2D rendering
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, display[0], display[1], 0, -1, 1)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            # Make sure depth testing is disabled for the overlay
            glDisable(GL_DEPTH_TEST)

            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # Convert the pygame surface to an OpenGL texture
            menu_texture_data = pygame.image.tostring(menu_screen, "RGBA", True)

            # Position the menu overlay at the correct viewport coordinates
            glWindowPos2d(0, 0)
            glDrawPixels(
                display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, menu_texture_data
            )

            # Restore previous OpenGL state
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

            # Re-enable depth testing for next frame
            glEnable(GL_DEPTH_TEST)

        elif current_state == "bonjour":
            if video_capture:
                ret, frame = video_capture.read()
                if ret:
                    frame = cv2.resize(frame, (screen_width, screen_height))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_surface = pygame.surfarray.make_surface(frame)
                    screen.blit(pygame.transform.rotate(frame_surface, -90), (0, 0))
                else:
                    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

            for button in buttons:
                button.draw(screen)
            # Afficher la version en bas à droite
            version_surface = version_font.render(version_text, True, (255, 255, 255))
            version_rect = version_surface.get_rect(
                bottomright=(screen_width - 10, screen_height - 10)
            )
            screen.blit(version_surface, version_rect)

            # Create a semi-transparent background for the menu area
            pygame.draw.rect(
                menu_screen,
                (20, 20, 20, 180),
                (menu_x, menu_y, menu_width, menu_height),
                border_radius=15,
            )
            # FOV Settings UI
            # Title
            title = font.render("FOV Camera Settings", True, (255, 255, 255))
            title_rect = title.get_rect(center=(screen.get_width() // 2, menu_y + 50))
            menu_screen.blit(title, title_rect)

            # Slider dimensions
            bar_width = int(menu_width * 0.7)
            bar_height = 20
            bar_x = menu_x + (menu_width - bar_width) // 2
            bar_y = menu_y + menu_height // 2

            # Slider background
            pygame.draw.rect(
                menu_screen,
                (30, 30, 30),
                (bar_x, bar_y, bar_width, bar_height),
                border_radius=10,
            )

            # Slider handle
            handle_x = bar_x + int((slider_value - 70) / 80 * bar_width)
            handle_y = max(bar_x, min(handle_x, bar_x + bar_width))
            pygame.draw.circle(
                menu_screen, (0, 200, 0), (handle_x, bar_y + bar_height // 2), 15
            )

            # Value display
            value_text = font.render(
                f"FOV: {int(slider_value)}°", True, (255, 255, 255)
            )
            value_rect = value_text.get_rect(
                center=(screen.get_width() // 2, bar_y - 30)
            )
            menu_screen.blit(value_text, value_rect)

            # Instructions
            instr_text = "Drag to adjust" if not is_dragging else "Adjusting..."
            instr = font.render(instr_text, True, (200, 200, 200))
            instr_rect = instr.get_rect(center=(screen.get_width() // 2, bar_y + 50))
            menu_screen.blit(instr, instr_rect)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                # Check if the mouse is near the slider handle
                if abs(mouse_x - handle_x) < 10 and abs(mouse_y - handle_y) < 10:
                    is_dragging = True
            elif event.type == pygame.MOUSEBUTTONUP:
                is_dragging = False
            elif event.type == pygame.MOUSEMOTION and is_dragging:
                mouse_x, _ = event.pos
                # Update the slider value based on mouse position
                slider_value = 70 + (mouse_x - bar_x) / bar_width * 80
                slider_value = max(
                    70, min(150, slider_value)
                )  # Clamp between 70 and 150

            # Now use the correct OpenGL method to overlay the 2D menu
            # Set up orthographic projection for 2D rendering
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, display[0], display[1], 0, -1, 1)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            # Make sure depth testing is disabled for the overlay
            glDisable(GL_DEPTH_TEST)

            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # Convert the pygame surface to an OpenGL texture
            menu_texture_data = pygame.image.tostring(menu_screen, "RGBA", True)

            # Position the menu overlay at the correct viewport coordinates
            glWindowPos2d(0, 0)
            glDrawPixels(
                display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, menu_texture_data
            )

            # Restore previous OpenGL state
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

            # Re-enable depth testing for next frame
            glEnable(GL_DEPTH_TEST)

        clock.tick(165)
        pygame.display.flip()


# Modified afficher_parametres function to work with a surface paramete
# Fonction principale du menu
def main_menu():
    global controls, waiting_for_key, frame_x, frame_y, frame_width, frame_height, spacing
    pygame.init()

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

    # Charger les images d'arrière-plan
    credits_background = pygame.image.load("src/credits_bg.jpg").convert()
    settings_background = pygame.image.load("src/settings_bg.jpg").convert()
    game_background = pygame.image.load("src/game_bg.jpg").convert()

    credits_background = pygame.transform.scale(
        credits_background, (screen_width, screen_height)
    )
    settings_background = pygame.transform.scale(
        settings_background, (screen_width, screen_height)
    )
    game_background = pygame.transform.scale(
        game_background, (screen_width, screen_height)
    )

    # Charger la vidéo de fond pour le menu principal
    local_video_path = "src/bg.mp4"
    video_capture = load_local_video(local_video_path)

    # Variables pour le contrôle de la vidéo

    frame_delay = 1.0 / 35  # Temps entre chaque frame en secondes
    last_frame_time = time.time()

    # Charger l'image de la flèche pour le retour
    back_button_image = pygame.image.load(
        "src/back_arrow.png"
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
                settings_background = pygame.transform.scale(
                    settings_background, (screen_width, screen_height)
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
                            quit_game()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    current_state = "parametres"
                elif event.key == pygame.K_LEFT:
                    current_state = "parametres"

            if current_state == "settings":
                back_rect, tab_buttons, left_rect, right_rect, volume_slider_rect = (
                    display_settings(
                        screen,
                        font,
                        back_button_image,
                        current_tab,
                        settings_background,
                    )
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
                    elif current_tab == "Touches":
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
                            ):
                                waiting_for_key = i
                                break
                elif event.type == pygame.KEYDOWN and waiting_for_key is not None:
                    # Convertir la touche en texte
                    key_name = pygame.key.name(event.key).upper()
                    if key_name == "ESCAPE":
                        key_name = "ÉCHAP"
                    elif key_name == "SPACE":
                        key_name = "ESPACE"
                    elif key_name == "LEFT SHIFT":
                        key_name = "SHIFT"

                    # Mettre à jour la touche
                    controls[waiting_for_key] = (key_name, controls[waiting_for_key][1])
                    waiting_for_key = None
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
            display_settings(
                screen, font, back_button_image, current_tab, settings_background
            )
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
    pygame.quit()


if __name__ == "__main__":
    main_menu()

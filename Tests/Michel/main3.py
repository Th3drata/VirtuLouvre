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
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Jeu avec menu intégré")
last_walk_sound_time = 0




# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 200, 255)
HOVER_BLUE = (50, 150, 255)
GREEN = (0, 255, 0)


# Police
FONT = pygame.font.Font(None, 36)
font = pygame.font.Font(None, 36)

# Taille de la fenêtre
screenwidth = 2560
screenheight = 1440

current_state = "game"  # États possibles: "game", "game_menu", "settings"
slider_value = 110  # Valeur initiale du FOV
is_dragging = False  # État du curseur


class Player:

    def __init__(self, fov, aspect, near, far, face_bboxes, vertices=None):
        self.face_bboxes = face_bboxes  # Store model's bounding boxes
        self.collision_radius = 0.8  # Player's collision radius
        self.fov = 110  # Champ de vision initial
        self.aspect = aspect  # Aspect ratio
        self.near = near  # Plan de vue proche
        self.far = 10000  # Plan de vue éloigné
        self.is_sprinting = False  # Initialiser le sprint à False
        self.base_speed = 0.1 # Vitesse de base
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
        new_position = self.position + self.velocity
        if not self.is_flying:
            new_position[1] -= self.gravity
            if new_position[1] < self.ground_level + self.initial_height:
                new_position[1] = self.ground_level + self.initial_height
                self.velocity[1] = 0

        if not self.check_collision(new_position):
            self.last_valid_position = new_position.copy()
            self.position = new_position
        else:
            self.position = self.last_valid_position.copy()
            self.velocity = np.zeros(3)

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
    # Replace the process_keyboard method in the Player class with this version:
    def process_keyboard(self, keys):
        current_speed = self.base_speed * (
            self.sprint_multiplier if self.is_sprinting else 1.0
        )  # Calculer la vitesse actuelle
        # Activer/Désactiver le sprint avec la touche "V"
        if keys[pygame.K_v]:
            self.is_sprinting = True
        else:
            self.is_sprinting = False
        if keys[pygame.K_g]:
            self.is_flying = False
        elif keys[pygame.K_SPACE]:
            self.is_flying = True
        if self.is_flying:
            if keys[pygame.K_SPACE]:
                self.position[1] += self.fly_speed
            if keys[pygame.K_LSHIFT]:
                self.position[1] -= self.fly_speed
        
        # Initialize movement direction vector
        move_dir = np.zeros(3, dtype=np.float32)
        
        # Calculate combined movement direction
        if keys[pygame.K_z]:  # Forward
            forward_dir = np.array([self.front[0], 0, self.front[2]])
            if np.linalg.norm(forward_dir) > 0:
                forward_dir = forward_dir / np.linalg.norm(forward_dir)
                move_dir += forward_dir
                walk_sound()
                
        if keys[pygame.K_s]:  # Backward
            backward_dir = np.array([self.front[0], 0, self.front[2]])
            if np.linalg.norm(backward_dir) > 0:
                backward_dir = backward_dir / np.linalg.norm(backward_dir)
                move_dir -= backward_dir
                walk_sound()
                
        if keys[pygame.K_q]:  # Left
            left_dir = np.array([self.right[0], 0, self.right[2]])
            if np.linalg.norm(left_dir) > 0:
                left_dir = left_dir / np.linalg.norm(left_dir)
                move_dir -= left_dir
                walk_sound()
                
        if keys[pygame.K_d]:  # Right
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

class BoundingBox:
    def __init__(self, min_point, max_point):
        self.min = np.array(min_point)
        self.max = np.array(max_point)

    def check_collision(self, point, radius):
        # Find closest point on box to player position
        closest = np.maximum(self.min, np.minimum(point, self.max))
        # Calculate distance to closest point
        distance = np.linalg.norm(point - closest)
        return distance < radius


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
        (7680, 4320),
    ]

    print("Dimensions possibles :")
    for w, h in dimensions_possibles:
        print(f"{w}, {h}")
    return dimensions_possibles


dimensions_possibles = size_screen()
display = dimensions_possibles[-2]


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

def draw_textured_floor(texture_id, grid_size=100, texture_width=0.5, texture_height=0.5):
    grid_height = -1.5  # Hauteur du sol

    # Calcul du nombre de répétitions en fonction de la taille de la grille et de la texture
    repeat_x = grid_size / texture_width
    repeat_y = grid_size / texture_height

    glEnable(GL_TEXTURE_2D)  # Activer les textures
    glBindTexture(GL_TEXTURE_2D, texture_id)  # Lier la texture du sol

    glBegin(GL_QUADS)
    glColor3f(1.0, 1.0, 1.0)  # Blanc pour afficher la texture correctement

    # Coordonnées de texture avec répétition pour le sol
    glTexCoord2f(0 * repeat_x, 0 * repeat_y); glVertex3f(-grid_size, grid_height, -grid_size)  # Coin bas-gauche
    glTexCoord2f(1 * repeat_x, 0 * repeat_y); glVertex3f(grid_size, grid_height, -grid_size)   # Coin bas-droit
    glTexCoord2f(1 * repeat_x, 1 * repeat_y); glVertex3f(grid_size, grid_height, grid_size)    # Coin haut-droit
    glTexCoord2f(0 * repeat_x, 1 * repeat_y); glVertex3f(-grid_size, grid_height, grid_size)   # Coin haut-gauche

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


def load_obj_with_bboxes(filename):
    vertices = []  # List to hold vertices
    texcoords = []  # List to hold texture coordinates
    faces = []  # List to hold faces
    face_bboxes = []  # List to hold bounding boxes for each face

    with open(filename, "r") as file:
        for line in file:
            if line.startswith("v "):  # Vertex data
                vertex = [float(coord) for coord in line.strip().split()[1:4]]
                vertices.append(vertex)
            elif line.startswith("vt "):  # Texture coordinate data
                texcoord = [float(coord) for coord in line.strip().split()[1:3]]
                texcoords.append(texcoord)
            elif line.startswith("f "):  # Face data
                face_vertices = []
                face_texcoords = []
                for v in line.strip().split()[1:]:
                    v_split = v.split("/")
                    face_vertices.append(int(v_split[0]) - 1)  # Convert to 0-based index
                    if len(v_split) >= 2 and v_split[1]:
                        face_texcoords.append(int(v_split[1]) - 1)

                if len(face_vertices) >= 3:  # Ensure there are at least 3 vertices
                    faces.append((face_vertices, face_texcoords))

                    # Calculate bounding box for the face
                    face_vertices_coords = np.array([vertices[i] for i in face_vertices])
                    min_point = np.min(face_vertices_coords, axis=0)
                    max_point = np.max(face_vertices_coords, axis=0)
                    face_bboxes.append(BoundingBox(min_point, max_point))

    return vertices, texcoords, faces, face_bboxes

def check_collision(self, new_position):
    # Check map boundaries
    x, y, z = new_position
    min_x, max_x = -30.0, 30.0
    min_z, max_z = -30.0, 30.0
    if x < min_x or x > max_x or z < min_z or z > max_z:
        return True

    # Check model collisions using bounding boxes
    for bbox in self.face_bboxes:
        if bbox.check_collision(new_position, self.collision_radius):
            return True
    return False
# Load the model and get its bounding boxes
# In your game initialization code
vertices, texcoords, faces, face_bboxes = load_obj_with_bboxes("src/your_model.obj")
player = Player(45, (display[0]/display[1]), 0.1, 200, face_bboxes)

# Now, face_bboxes contains the bounding boxes for each face
# The player's check_collision method can use these to detect collisions

def draw_bounding_boxes(face_bboxes):
    glColor3f(1.0, 0.0, 0.0)  # Color for the bounding boxes (red)
    glBegin(GL_LINES)
    for bbox in face_bboxes:
        # Draw the bounding box (6 lines for a rectangular box)
        for i in range(3):
            glVertex3f(bbox.min[i], bbox.min[(i+1)%3], bbox.min[(i+2)%3])
            glVertex3f(bbox.max[i], bbox.max[(i+1)%3], bbox.max[(i+2)%3])
    glEnd()


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
        button_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surface, button_color, self.rect, border_radius=10)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)


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
    
    settings_background = pygame.transform.scale(pygame.image.load("src/settings_bg.jpg").convert(), (width, height))

arrow_left = pygame.image.load("src/back_arrow.png")
arrow_right = pygame.image.load("src/back_arrow.png")
arrow_size = (50, 50)
arrow_left = pygame.transform.scale(arrow_left, arrow_size)
arrow_right = pygame.transform.scale(arrow_right, arrow_size)

# Fonction pour afficher les paramètres
def display_settings(screen, font, back_button_image, current_tab, settings_background):
    screen.blit(settings_background, (0, 0))
    tabs = ["Vidéo", "Audio", "JSP"]
    tab_buttons = []
    tab_width, tab_height, tab_spacing = 240, 40, -10
    start_x = (screen.get_width() - (len(tabs) * (tab_width + tab_spacing) - tab_spacing)) // 2
    start_y = 20

    for i, tab in enumerate(tabs):
        tab_buttons.append(tabButton(start_x + i * (tab_width + tab_spacing), start_y, tab_width, tab_height, tab, font, (200, 200, 200), (150, 150, 150)))
        tab_buttons[i].draw(screen)
    
    left_rect, right_rect = pygame.Rect(0, 0, 0, 0), pygame.Rect(0, 0, 0, 0)
    if current_tab == "Vidéo":
        resolution_text = "Plein écran" if resolutions[current_resolution_index] == (0, 0) else f"{resolutions[current_resolution_index][0]} x {resolutions[current_resolution_index][1]}"
        text_surface = font.render(resolution_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(screen.get_width() // 2, 200))
        screen.blit(text_surface, text_rect)
        left_rect = arrow_left.get_rect(midright=(text_rect.left - 20, 200))
        right_rect = arrow_right.get_rect(midleft=(text_rect.right + 20, 200))
        screen.blit(arrow_left, left_rect)
        screen.blit(arrow_right, right_rect)
    
    back_rect = back_button_image.get_rect(center=(40, screen.get_height() - 30))
    screen.blit(back_button_image, back_rect)
    return back_rect, tab_buttons, left_rect, right_rect


def start_game(screen, font, background_image, dimensions_possibles, current_state):
    pygame.init()  # Initialiser Pygame
    clock = pygame.time.Clock()
    
    pygame.font.init()  # Initialiser la police
      # Récupérer les dimensions de l'écran et mettre une taille en dessous de la plus haute possible
    screen = pygame.display.set_mode(
        display, DOUBLEBUF | OPENGL
    )  # Créer la fenêtre Pygame
    pygame.display.set_caption(
        "VirtuLouvre"
    )  # Titre de la fenêtre
    sky_texture = load_texture("src/sky.png")
    draw_skybox(sky_texture)
    glScalef(-1, 1, 1)  # Inverser la sphère pour voir la texture de l'intérieur
    glEnable(GL_CULL_FACE)  # Activer le culling
    glCullFace(GL_BACK)  # Cacher les faces arrière
    glFrontFace(GL_CCW)  # Sens des aiguilles d'une montre

    glDisable(GL_CULL_FACE)
    # Create a separate surface for the menu with alpha channel
    menu_screen = pygame.Surface((display[0], display[1]), pygame.SRCALPHA)  # Créer une surface pour le menu avec un canal alpha
    slider_value = 110  # Valeur du curseur
    is_dragging = False  # Initialiser le glissement à faux

    menu_width, menu_height = 600, 400
    menu_x = (display[0] - menu_width) // 2
    menu_y = (display[1] - menu_height) // 2

    # Add slider interaction variables
    bar_x, bar_y = 200, 300
    bar_width, bar_height = 420, 20  # Slider bar dimensions

    player = Player(45, (display[0] / display[1]), 0.1, 200)  # Initialiser le joueur
    player.apply_projection()  # Appliquer la projection
    glTranslatef(0.0, 0.0, -5)  # Translater la scène

    glEnable(GL_CULL_FACE)  # Activer le culling
    glCullFace(GL_BACK)  # Cacher les faces arrière
    glFrontFace(GL_CCW)  # Sens des aiguilles d'une montre

    clock = pygame.time.Clock()  # Initialiser l'horloge
    font = pygame.font.SysFont("Arial", 18)  # Initialiser la police

    # Enable blending for transparency
    glEnable(GL_BLEND)  # Activer le mélange
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # Fonction de mélange

    # Chargement du modèle 3D
    current_dir = os.path.dirname(
        os.path.abspath(__file__)
    )  # Récupérer le répertoire actuel
    model_path = os.path.join(current_dir, "src/Untitled.obj")  # Chemin du modèle 3D

    if not vertices or not faces:  # Si les sommets ou les faces sont vides
        print("Erreur: Impossible de charger le modèle 3D")
        pygame.quit()  # Quitter Pygame
        return

    model_vbo, model_vertex_count = create_model_vbo(
        vertices, texcoords, faces
    )  # Créer le VBO du modèle 3D
    texture_path = os.path.join(current_dir, "src/texture.png")  # Chemin de la texture
    texture_id = load_texture(texture_path)  # Charger la texture
    floor_texture = load_texture("src/sol.png")  # Remplace par ton chemin d'image

    # Set initial mouse state
    pygame.event.set_grab(True)  # Capturer la souris
    pygame.mouse.set_visible(False)  # Cacher le curseur

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
                    current_state = "game_menu" if current_state != "game_menu" else "game"
                    pygame.event.set_grab(current_state != "game_menu")  # Capturer la souris si menu ouvert
                    pygame.mouse.set_visible(current_state == "game_menu")  # Afficher le curseur si menu ouvert
                    

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:  # Si la touche est F11
                    toggle_fullscreen()  # Basculer en mode plein écran
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
                        player.fov = (slider_value)
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
            #grid() # Afficher la grille

            glEnable(GL_TEXTURE_2D)  # Activer la texture
            glBindTexture(GL_TEXTURE_2D, texture_id)  # Lier la texture
            draw_model(model_vbo, model_vertex_count)  # Dessiner le modèle
            glDisable(GL_TEXTURE_2D)  # Désactiver la texture

            draw_bounding_boxes(face_bboxes)

            draw_fps(clock, font, screenwidth= 2560, screenheight= 1440)

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
            pygame.draw.rect(menu_screen, (20, 20, 20, 180),
                        (menu_x, menu_y, menu_width, menu_height),
                        border_radius=15)
            
            # Define buttons
            buttons = [
                Button(display[0]//2-100, display[1]//2-100, 200, 50, "Resume", (255,255,255), font, BLUE, HOVER_BLUE),
                Button(display[0]//2-100, display[1]//2-20, 200, 50, "Settings", (255,255,255), font, BLUE, HOVER_BLUE),
                Button(display[0]//2-100, display[1]//2+60, 200, 50, "Quit", (255,255,255), font, BLUE, HOVER_BLUE),
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
                            current_state = "bonjour" if current_state != "bonjour" else "game_menu"
                        elif button.text == "Quit":
                            pygame.quit()
                            return "quit"
            
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
            glDrawPixels(display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, menu_texture_data)
            
            # Restore previous OpenGL state
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            
            # Re-enable depth testing for next frame
            glEnable(GL_DEPTH_TEST)
            
        elif current_state == "bonjour":
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
            glFinish()
            menu_screen.fill((0, 0, 0, 0))
            
            # Create a semi-transparent background for the menu area
            pygame.draw.rect(menu_screen, (20, 20, 20, 180), 
                        (menu_x, menu_y, menu_width, menu_height),
                        border_radius=15)
            # FOV Settings UI
            # Title
            title = font.render("FOV Camera Settings", True, (255,255,255))
            title_rect = title.get_rect(center=(screen.get_width()//2, menu_y + 50))
            menu_screen.blit(title, title_rect)

            # Slider dimensions
            bar_width = int(menu_width * 0.7)
            bar_height = 20
            bar_x = menu_x + (menu_width - bar_width) // 2
            bar_y = menu_y + menu_height//2

            # Slider background
            pygame.draw.rect(menu_screen, (30,30,30), (bar_x, bar_y, bar_width, bar_height), border_radius=10)
            
            # Slider handle
            handle_x = bar_x + int((slider_value - 70) / 80 * bar_width)
            handle_y = max(bar_x, min(handle_x, bar_x + bar_width))
            pygame.draw.circle(menu_screen, (0,200,0), (handle_x, bar_y + bar_height//2), 15)

            # Value display
            value_text = font.render(f"FOV: {int(slider_value)}°", True, (255,255,255))
            value_rect = value_text.get_rect(center=(screen.get_width()//2, bar_y - 30))
            menu_screen.blit(value_text, value_rect)

            # Instructions
            instr_text = "Drag to adjust" if not is_dragging else "Adjusting..."
            instr = font.render(instr_text, True, (200,200,200))
            instr_rect = instr.get_rect(center=(screen.get_width()//2, bar_y + 50))
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
                slider_value = max(70, min(150, slider_value))  # Clamp between 70 and 150

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
            glDrawPixels(display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, menu_texture_data)
            
            # Restore previous OpenGL state
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            
            # Re-enable depth testing for next frame
            glEnable(GL_DEPTH_TEST)


        clock.tick(60)
        pygame.display.flip()

# Fonction pour appliquer un flou gaussien sur la vidéo
def apply_blur(frame):
    # Applique un flou gaussien sur l'image
    return cv2.GaussianBlur(frame, (21, 21), 0)


# Fonction principale du menu
def main_menu():
    pygame.init()

    # Paramètres d'écran
    screen_width, screen_height = dimensions_possibles[-4]
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
    pygame.display.set_caption("Menu principal")

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
    font = pygame.font.Font(None, 36)

    button_width, button_height = 200, 50
    button_spacing = 30
    total_height = 3 * button_height + 2 * button_spacing

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
            screen_width // 2 - button_width //2, 
            start_y + 3 * (button_height + button_spacing), 
            button_width, 
            button_height, 
            "Quitter", 
            WHITE, 
            font, 
            blue, 
            hover_blue
        )
    ]

    clock = pygame.time.Clock()
    running = True
    current_state = "parametres"
    current_tab = "Vidéo"
    slider_value = 110
    is_dragging = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:  # Si la touche est F11
                    toggle_fullscreen()

            elif event.type == pygame.VIDEORESIZE:  # Détecte le redimensionnement
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height), pygame.RESIZABLE
                )
                start_y = (
                    screen_height - (3 * button_height + 2 * button_spacing)
                ) // 2
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

            if current_state == "parametres":
                for button in buttons:
                    if button.is_clicked(event):
                        if button.text == "Visiter le site":
                            current_state = "game"
                        elif button.text == "Paramètres":
                            current_state = "settings"
                        elif button.text == "Crédits":
                            current_state = "credits"
                        elif button.text == "Quitter":  # Ajout de la détection du bouton "Quitter"
                            quit_game()
            

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    current_state = "parametres"
                elif event.key == pygame.K_LEFT:  # Flèche gauche pour revenir au menu
                    current_state = "parametres"

            if current_state == "settings":
                back_rect, tab_buttons, left_rect, right_rect = display_settings(screen, font, back_button_image, current_tab, settings_background)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        current_state = "menu"
                    for tab_button in tab_buttons:
                        if tab_button.is_clicked(event):
                            current_tab = tab_button.text
                    if left_rect.collidepoint(event.pos):
                        change_resolution((current_resolution_index - 1) % len(resolutions))
                    elif right_rect.collidepoint(event.pos):
                        change_resolution((current_resolution_index + 1) % len(resolutions))

        # Afficher l'état courant
        if current_state == "parametres":
            if video_capture:
                ret, frame = video_capture.read()
                if ret:
                    frame = cv2.resize(frame, (screen_width, screen_height))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Appliquer le flou
                    frame = apply_blur(frame)

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

        elif current_state == "credits":
            back_rect = display_credits(screen, font, back_button_image)
            if event.type == pygame.MOUSEBUTTONDOWN and back_rect.collidepoint(
                event.pos
            ):
                current_state = "parametres"
        elif current_state == "settings":
            display_settings(screen, font, back_button_image, current_tab, settings_background)
        elif current_state == "game":
            start_game(screen, font, game_background, dimensions_possibles, current_state)
            pygame.display.flip()
        elif current_state == "quitter" :
            quit_game()

        pygame.display.flip()
        clock.tick(60)

    if video_capture:
        video_capture.release()
    pygame.quit()

if __name__ == "__main__":
    main_menu()

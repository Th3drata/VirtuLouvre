import pygame # Importer la bibliothèque Pygame
import os # Importer le module os
import cv2 # Importer la bibliothèque OpenCV
from pygame.locals import * # Importer les constantes Pygame
from OpenGL.GL import * # Importer les fonctions OpenGL 
from OpenGL.GLU import * # Importer les fonctions OpenGL Utility
import numpy as np # Importer la bibliothèque NumPy
import math # Importer le module math
import os  # Ajouter cet import au début du fichier

pygame.init() # Initialiser Pygame

# Dimensions de l'écran
os.environ['SDL_VIDEO_CENTERED'] = '1'
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Jeu avec menu intégré")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 200, 255)
HOVER_BLUE = (50, 150, 255)
GREEN = (0, 255, 0)

# Police
FONT = pygame.font.Font(None, 36)
font = pygame.font.Font(None, 36)

#Taille de la fenêtre
screenwidth = 2560
screenheight = 1440


class Player:

    def __init__(self, fov, aspect, near, far, vertices=None):
        self.fov = 110 # Champ de vision initial
        self.aspect = aspect # Aspect ratio
        self.near = near # Plan de vue proche
        self.far = 10000 # Plan de vue éloigné
        self.is_sprinting = False # Initialiser le sprint à False
        self.base_speed = 0.07 # Vitesse de base
        self.sprint_multiplier = 3.0 # Multiplicateur de sprint
        self.initial_height = 0.5 # Hauteur initiale
        self.position = np.array([0.0, self.initial_height, 5.0], dtype=np.float32) # Position initiale 
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=np.float32) # Vitesse initiale
        self.acceleration = 0.01 # Accélération
        self.deceleration = 1   # Décélération
        self.max_velocity = 0.5 # Vitesse maximale
        self.front = np.array([0.0, 0.0, -1.0], dtype=np.float32) # Vecteur de direction
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)  # Vecteur vertical
        self.right = np.array([1.0, 0.0, 0.0], dtype=np.float32) # Vecteur droit
        self.yaw = -90.0 # Angle de lacet
        self.pitch = 0.0 # Angle de tangage
        self.mouse_sensitivity = 0.1 # Sensibilité de la souris
        self.vertices = vertices or [] # Vertices
        self.last_valid_position = self.position.copy() # Dernière position valide
        self.fly_speed = 0.1 # Vitesse de vol
        self.gravity = 0.08 # Gravité
        self.is_flying = True # Initialiser le vol à True
        self.ground_level = 0.0 # Niveau du sol

    # Appliquer la projection
    def apply_projection(self):
        glMatrixMode(GL_PROJECTION) # Changer le mode de la matrice à la projection
        glLoadIdentity() # Réinitialiser la matrice
        gluPerspective(self.fov, self.aspect, self.near, self.far) # Appliquer la perspective
        glMatrixMode(GL_MODELVIEW) # Changer le mode de la matrice au modèle

    # Appliquer la vue
    def update_camera_vectors(self):
        self.front[0] = math.cos(math.radians(self.yaw)) * math.cos(math.radians(self.pitch)) # Calculer la direction x
        self.front[1] = math.sin(math.radians(self.pitch)) # Calculer la direction y
        self.front[2] = math.sin(math.radians(self.yaw)) * math.cos(math.radians(self.pitch)) # Calculer la direction z
        self.front = self.front / np.linalg.norm(self.front) # Normaliser le vecteur de direction
        self.right = np.cross(self.front, np.array([0.0, 1.0, 0.0])) # Calculer le vecteur droit
        self.right = self.right / np.linalg.norm(self.right) # Normaliser le vecteur droit
        self.up = np.cross(self.right, self.front)  # Calculer le vecteur vertical

    # Mettre à jour la position du joueur
    def update(self, delta_time):
        new_position = self.position + self.velocity # Calculer la nouvelle position
        if not self.is_flying: # Si le joueur ne vole pas
            new_position[1] -= self.gravity # Appliquer la gravité
            if new_position[1] < self.ground_level + self.initial_height: # Si le joueur est au sol
                new_position[1] = self.ground_level + self.initial_height # Mettre à jour la position y
                self.velocity[1] = 0  # Réinitialiser la vitesse y
        if not self.check_collision(new_position): # Si le joueur n'est pas en collision
            self.last_valid_position = new_position.copy() # Mettre à jour la dernière position valide
            self.position = new_position # Mettre à jour la position
        else:
            self.position = self.last_valid_position.copy() # Revenir à la dernière position valide
            self.velocity = np.zeros(3) # Réinitialiser la vitesse
        self.velocity *= (1 - self.deceleration) # Appliquer la décélération

    # Mettre à jour la souris
    def process_mouse(self, xoffset, yoffset):
        self.yaw += xoffset * self.mouse_sensitivity # Mettre à jour l'angle de lacet
        self.pitch += yoffset * self.mouse_sensitivity # Mettre à jour l'angle de tangage
        if self.pitch > 89.0: # Limiter l'angle de tangage
            self.pitch = 89.0 # Limiter l'angle de tangage
        if self.pitch < -89.0: # Limiter l'angle de tangage
            self.pitch = -89.0 # Limiter l'angle de tangage
        self.update_camera_vectors() # Mettre à jour les vecteurs de la cam

    # Mettre à jour le clavier    
    def process_keyboard(self, keys):
        current_speed = self.base_speed * (self.sprint_multiplier if self.is_sprinting else 1.0) # Calculer la vitesse actuelle
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
        if keys[pygame.K_z]: # Avancer
            move_dir = np.array([self.front[0], 0, self.front[2]]) # Calculer la direction de déplacement
            move_dir = move_dir / np.linalg.norm(move_dir) # Normaliser la direction de déplacement
            self.velocity += move_dir * current_speed # Appliquer la vitesse
        if keys[pygame.K_s]: # Reculer
            move_dir = np.array([self.front[0], 0, self.front[2]])
            move_dir = move_dir / np.linalg.norm(move_dir)
            self.velocity -= move_dir * current_speed
        if keys[pygame.K_q]: # Aller à gauche
            move_dir = np.array([self.right[0], 0, self.right[2]])
            move_dir = move_dir / np.linalg.norm(move_dir)
            self.velocity -= move_dir * current_speed
        if keys[pygame.K_d]: # Aller à droite
            move_dir = np.array([self.right[0], 0, self.right[2]])
            move_dir = move_dir / np.linalg.norm(move_dir)
            self.velocity += move_dir * current_speed

        velocity_length = np.linalg.norm(self.velocity) # Calculer la longueur de la vitesse
        if velocity_length > self.max_velocity: # Si la vitesse est supérieure à la vitesse maximale
            self.velocity = (self.velocity / velocity_length) * self.max_velocity # Limiter la vitesse

    # Vérifier la collision
    def check_collision(self, new_position, collision_radius=0.8):
        camera_pos = np.array(new_position) # Position de la caméra
        min_x, max_x = -30.0, 30.0 # Limites de la carte
        min_z, max_z = -30.0, 30.0 # Limites de la carte
        x, y, z = camera_pos     # Coordonnées de la caméra
        # Uniquement vérifier les limites de la carte
        if x < min_x or x > max_x or z < min_z or z > max_z:
            return True            
        return False
    
    # Appliquer la vue
    def apply(self):
        target = self.position + self.front # Calculer la cible
        glLoadIdentity() # Réinitialiser la matrice
        gluLookAt( # Appliquer la vue
            self.position[0], self.position[1], self.position[2], # Position de la caméra
            target[0], target[1], target[2], # Cible de la caméra
            self.up[0], self.up[1], self.up[2] # Vecteur vertical
        )


def size_screen():
    if os.name == 'nt':
        from ctypes import windll
        user32 = windll.user32
        largeur = user32.GetSystemMetrics(0)
        hauteur = user32.GetSystemMetrics(1)
    print(f"{largeur}x{hauteur}")
    resolutions_16_9 = [(256, 144),(426, 240),(640, 360),(854, 480),(960, 540),(1280, 720),(1366, 768),(1600, 900),(1920, 1080),(2560, 1440), (3840, 2160)]
    dimensions_possibles = [(w, h) for w, h in resolutions_16_9 if w <= largeur and h <= hauteur]

    print("Résolutions compatibles avec votre écran :")
    for w, h in dimensions_possibles:
        print(f"{w}, {h}")

    return dimensions_possibles 

size_screen()
dimensions_possibles = size_screen()

# Fonction pour afficher les crédits
def toggle_fullscreen():
    pygame.display.toggle_fullscreen() # Basculer en mode plein écran

# Fonction pour afficher les crédits
def grid(): 
    grid_size = 35 # Taille de la grille
    grid_step = 1 # Pas de la grille
    glBegin(GL_LINES) # Commencer le dessin des lignes
    glColor3f(0.5, 0.5, 0.5) # Couleur des lignes
    for i in range(-grid_size, grid_size + 1, grid_step):  # Dessiner les lignes horizontales
        glVertex3f(i, -1, -grid_size) # Dessiner la ligne
        glVertex3f(i, -1, grid_size) # Dessiner la ligne
    for i in range(-grid_size, grid_size + 1, grid_step): # Dessiner les lignes verticales
        glVertex3f(-grid_size, -1, i) # Dessiner la ligne
        glVertex3f(grid_size, -1, i) # Dessiner la ligne
    glEnd() # Terminer le dessin des lignes

# Fonction pour afficher les crédits
def render_text_to_texture(text, font, color=(255, 255, 0)):
    text_surface = font.render(text, True, color, (0, 0, 0)) # Rendre le texte
    text_data = pygame.image.tostring(text_surface, "RGBA", True) # Convertir le texte en données
    width, height = text_surface.get_size() # Récupérer la taille du texte
    texture_id = glGenTextures(1) # Générer un identifiant de texture
    glBindTexture(GL_TEXTURE_2D, texture_id) # Lier la texture
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data) # Appliquer la texture
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) # Paramètres de la texture
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR) # Paramètres de la texture
    return texture_id, width, height # Retourner l'identifiant de la texture, la largeur et la hauteur

# Fonction pour afficher les crédits
def draw_fps(clock, font, screenwidth, screenheight):
    fps = int(clock.get_fps()) # Calculer les FPS
    text = f"FPS: {fps}" # Texte à afficher
    texture_id, width, height = render_text_to_texture(text, font)  # Rendre le texte en texture
    glMatrixMode(GL_PROJECTION) # Changer le mode de la matrice à la projection
    glPushMatrix() # Sauvegarder la matrice
    glLoadIdentity() # Réinitialiser la matrice
    gluOrtho2D(0, screenwidth, 0, screenheight) # Appliquer la projection orthographique
    glMatrixMode(GL_MODELVIEW) # Changer le mode de la matrice au modèle
    glPushMatrix() # Sauvegarder la matrice
    glLoadIdentity() # Réinitialiser la matrice
    glEnable(GL_TEXTURE_2D) # Activer la texture
    glBindTexture(GL_TEXTURE_2D, texture_id) # Lier la texture
    glColor3f(1, 1, 1) # Couleur du texte
    glBegin(GL_QUADS) # Commencer le dessin des quads
    glTexCoord2f(0, 0); glVertex2f(10, 560) # Dessiner le quad
    glTexCoord2f(1, 0); glVertex2f(10 + width, 560) # Dessiner le quad
    glTexCoord2f(1, 1); glVertex2f(10 + width, 560 + height) # Dessiner le quad
    glTexCoord2f(0, 1); glVertex2f(10, 560 + height) # Dessiner le quad
    glEnd() # Terminer le dessin des quads
    glDisable(GL_TEXTURE_2D) # Désactiver la texture
    glMatrixMode(GL_PROJECTION) # Changer le mode de la matrice à la projection
    glPopMatrix() # Restaurer la matrice
    glMatrixMode(GL_MODELVIEW) # Changer le mode de la matrice au modèle
    glPopMatrix() # Restaurer la matrice

# Fonction pour charger un fichier OBJ
def load_obj(filename):
    vertices = [] # Initialiser la liste des sommets
    texcoords = [] # Initialiser la liste des coordonnées de texture
    faces = [] # Initialiser la liste des faces
    with open(filename, 'r') as file: # Ouvrir le fichier en mode lecture
        for line in file: # Lire chaque ligne du fichier
            if line.startswith('v '): # Si la ligne commence par 'v'
                vertex = [float(coord) for coord in line.strip().split()[1:4]] # Récupérer les coordonnées du sommet
                vertices.append(vertex) # Ajouter le sommet à la liste
            elif line.startswith('vt '): # Si la ligne commence par 'vt'
                texcoord = [float(coord) for coord in line.strip().split()[1:3]] # Récupérer les coordonnées de texture
                texcoords.append(texcoord) # Ajouter les coordonnées de texture à la liste
            elif line.startswith('f '): # Si la ligne commence par 'f'
                face_vertices = [] # Initialiser la liste des sommets de la face
                face_texcoords = [] # Initialiser la liste des coordonnées de texture de la face
                for v in line.strip().split()[1:]: # Lire chaque sommet de la face
                    v_split = v.split('/') # Séparer les indices
                    face_vertices.append(int(v_split[0]) - 1) # Ajouter l'indice du sommet
                    if len(v_split) >= 2 and v_split[1]: # Si l'indice de la coordonnée de texture existe
                        face_texcoords.append(int(v_split[1]) - 1) # Ajouter l'indice de la coordonnée de texture
                if len(face_vertices) >= 3: # Si la face a au moins 3 sommets
                    faces.append((face_vertices[:3], face_texcoords[:3])) # Ajouter la face à la liste
    return vertices, texcoords, faces # Retourner les sommets, les coordonnées de texture et les faces

# Fonction pour charger une texture
def load_texture(filename):
    texture_surface = pygame.image.load(filename)  # Charger l'image
    texture_data = pygame.image.tostring(texture_surface, "RGBA", True) # Convertir l'image en données
    width, height = texture_surface.get_size() # Récupérer la taille de l'image
    
    texture_id = glGenTextures(1) # Générer un identifiant de texture
    glBindTexture(GL_TEXTURE_2D, texture_id) # Lier la texture
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data) # Appliquer la texture
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) # Paramètres de la texture
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR) # Paramètres de la texture
    return texture_id # Retourner l'identifiant de la texture

# Fonction pour créer un modèle VBO
def create_model_vbo(vertices, texcoords, faces): 
    vertex_data = [] # Initialiser les données des sommets
    texcoord_data = [] # Initialiser les données des coordonnées de texture
    for face in faces: # Pour chaque face
        for vertex_idx, texcoord_idx in zip(face[0], face[1]): # Pour chaque sommet et coordonnée de texture
            vertex_data.extend(vertices[vertex_idx]) # Ajouter les coordonnées du sommet
            texcoord_data.extend(texcoords[texcoord_idx]) # Ajouter les coordonnées de texture
    
    vertex_data = np.array(vertex_data, dtype=np.float32) # Convertir les données des sommets en tableau NumPy
    texcoord_data = np.array(texcoord_data, dtype=np.float32) # Convertir les données des coordonnées de texture en tableau NumPy
    
    vbo = glGenBuffers(1) # Générer un identifiant de VBO
    glBindBuffer(GL_ARRAY_BUFFER, vbo) # Lier le VBO
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes + texcoord_data.nbytes, None, GL_STATIC_DRAW) # Appliquer les données
    glBufferSubData(GL_ARRAY_BUFFER, 0, vertex_data.nbytes, vertex_data) # Ajouter les données des sommets
    glBufferSubData(GL_ARRAY_BUFFER, vertex_data.nbytes, texcoord_data.nbytes, texcoord_data) # Ajouter les données des coordonnées de texture

    return vbo, len(vertex_data) // 3 # Retourner l'identifiant du VBO et le nombre de sommets

# Fonction pour dessiner un modèle
def draw_model(vbo, vertex_count):  
    glBindBuffer(GL_ARRAY_BUFFER, vbo) # Lier le VBO
    glEnableClientState(GL_VERTEX_ARRAY) # Activer le tableau des sommets
    glVertexPointer(3, GL_FLOAT, 0, None) # Pointer vers les sommets
    glEnableClientState(GL_TEXTURE_COORD_ARRAY) # Activer le tableau des coordonnées de texture
    glTexCoordPointer(2, GL_FLOAT, 0, ctypes.c_void_p(vertex_count * 3 * 4)) # Pointer vers les coordonnées de texture
    
    # Active le test de profondeur
    glEnable(GL_DEPTH_TEST)
    
    # Dessiner le modèle plein
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glColor3f(1.0, 1.0, 1.0)  # Couleur blanche pour que la texture soit visible
    glDrawArrays(GL_TRIANGLES, 0, vertex_count) # Dessiner le modèle
    
    glDisableClientState(GL_TEXTURE_COORD_ARRAY) # Désactiver le tableau des coordonnées de texture
    glDisableClientState(GL_VERTEX_ARRAY) # Désactiver le tableau des sommets
    glDisable(GL_DEPTH_TEST) # Désactiver le test de profondeur


# Initialisation de Pygame et de la police
pygame.init()

version_text = "Version 1.0.0" # Texte de la version
try: # Essayer de charger la police par défaut
    version_font = pygame.font.Font(None, 24)  # Police par défaut
except: # En cas d'erreur
    print("Erreur lors de l'initialisation de la police, utilisation de la police par défaut.")
    version_font = pygame.font.SysFont('Arial', 24)  # Si 'None' échoue, utiliser Arial comme fallback

# Fonction pour charger une vidéo locale
def load_local_video(file_path):
    try:
        if not os.path.exists(file_path): # Si le fichier n'existe pas
            raise FileNotFoundError(f"Le fichier vidéo '{file_path}' n'existe pas.") # Lever une exception
        return cv2.VideoCapture(file_path) # Charger la vidéo
    except Exception as e: # En cas d'erreur
        print(f"Erreur: Impossible de charger la vidéo depuis le fichier '{file_path}'. {e}") # Afficher l'erreur
        return None 

# Classe pour gérer les boutons
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color, shadow_color=(0, 0, 0), border_radius=10):
        self.rect = pygame.Rect(x, y, width, height) # Créer un rectangle pour le bouton
        self.text = text # Texte du bouton
        self.font = font # Police du bouton
        self.color = color # Couleur du bouton
        self.hover_color = hover_color # Couleur du bouton survolé
        self.shadow_color = shadow_color  # Couleur de l'ombre
        self.border_radius = border_radius # Rayon des bords

    # Dessiner le bouton
    def draw(self, surface): 
        mouse_pos = pygame.mouse.get_pos() # Récupérer la position de la souris
        button_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color # Couleur du bouton
        
        # Dessiner l'ombre légèrement décalée
        shadow_rect = self.rect.move(5, 5)  # Décale l'ombre de 5 pixels sur x et y
        pygame.draw.rect(surface, self.shadow_color, shadow_rect, border_radius=self.border_radius) # Dessiner l'ombre

        # Dessiner le bouton
        pygame.draw.rect(surface, button_color, self.rect, border_radius=self.border_radius)

        # Dessiner le texte sur le bouton
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center) # Centrer le texte
        surface.blit(text_surface, text_rect) # Afficher le texte

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos) # Vérifier si le bouton est cliqué

# Fonction pour afficher les crédits
def display_credits(screen, font, background_image, back_button_image):
    screen.blit(background_image, (0, 0)) # Afficher l'image d'arrière-plan

    credits_text = [
        "Crédits :",
        "Développé par",
        "Albert Oscar, Moors Michel, Rinckenbach Yann"
    ]

    start_y = 200 # Position de départ en y
    line_spacing = 40

    for i, line in enumerate(credits_text): # Pour chaque ligne de texte
        text_surface = font.render(line, True, (255, 255, 255)) # Rendre le texte
        text_rect = text_surface.get_rect(center=(400, start_y + i * line_spacing)) # Centrer le texte
        screen.blit(text_surface, text_rect) # Afficher le texte

    # Afficher la flèche pour revenir
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    
    return back_rect

# Fonction pour afficher les paramètres
def display_settings(screen, font, background_image, back_button_image):
    screen.blit(background_image, (0, 0)) # Afficher l'image d'arrière-plan
    text = font.render("Paramètres : Personnalisez votre jeu ici", True, (255, 255, 255)) # Rendre le texte
    text_rect = text.get_rect(center=(400, 300)) # Centrer le texte
    screen.blit(text, text_rect) # Afficher le texte

    # Afficher la flèche pour revenir
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect) 
    
    return back_rect

# Fonction pour démarrer le jeu
def start_game(screen, font, background_image, dimensions_possibles):
    pygame.init() # Initialiser Pygame
    pygame.font.init() # Initialiser la police
    display = (dimensions_possibles[-2]) # Récupérer les dimensions de l'écran
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL) # Créer la fenêtre Pygame
    pygame.display.set_caption("3D View - Press ESC to toggle menu") # Titre de la fenêtre

    # Create a separate surface for the menu with alpha channel
    menu_screen = pygame.Surface(display, pygame.SRCALPHA) # Créer une surface pour le menu avec un canal alpha
    menu_open = False # Initialiser le menu à fermé
    slider_value = 110 # Valeur du curseur
    is_dragging = False # Initialiser le glissement à faux
    
    # Add slider interaction variables
    bar_x, bar_y = 200, 300
    bar_width, bar_height = 420, 20 # Slider bar dimensions

    player = Player(45, (display[0] / display[1]), 0.1, 200) # Initialiser le joueur
    player.apply_projection() # Appliquer la projection
    glTranslatef(0.0, 0.0, -5) # Translater la scène

    glEnable(GL_CULL_FACE) # Activer le culling
    glCullFace(GL_BACK) # Cacher les faces arrière
    glFrontFace(GL_CCW) # Sens des aiguilles d'une montre

    clock = pygame.time.Clock() # Initialiser l'horloge
    font = pygame.font.SysFont("Arial", 18) # Initialiser la police

    # Enable blending for transparency
    glEnable(GL_BLEND) # Activer le mélange
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA) # Fonction de mélange

    # Chargement du modèle 3D
    current_dir = os.path.dirname(os.path.abspath(__file__)) # Récupérer le répertoire actuel
    model_path = os.path.join(current_dir, 'src/untitled.obj') # Chemin du modèle 3D
    vertices, texcoords, faces = load_obj(model_path) # Charger le modèle 3D
    
    if not vertices or not faces: # Si les sommets ou les faces sont vides
        print("Erreur: Impossible de charger le modèle 3D")
        pygame.quit() # Quitter Pygame
        return

    model_vbo, model_vertex_count = create_model_vbo(vertices, texcoords, faces) # Créer le VBO du modèle 3D
    texture_path = os.path.join(current_dir, 'src/texture.png') # Chemin de la texture
    texture_id = load_texture(texture_path) # Charger la texture
    
    # Set initial mouse state
    pygame.event.set_grab(True) # Capturer la souris
    pygame.mouse.set_visible(False) # Cacher le curseur

    while True:
        delta_time = clock.tick(60) / 1000.0 # Calculer le temps écoulé

        for event in pygame.event.get(): # Pour chaque événement Pygame
            if event.type == pygame.QUIT: # Si l'événement est de quitter
                pygame.quit() # Quitter Pygame
                return

            if event.type == pygame.KEYDOWN: # Si une touche est enfoncée
                if event.key == pygame.K_ESCAPE: # Si la touche est Echap
                    menu_open = not menu_open # Basculer le menu
                    # Toggle mouse visibility and grab
                    pygame.event.set_grab(not menu_open) # Capturer la souris
                    pygame.mouse.set_visible(menu_open) # Cacher le curseur
                elif event.key == pygame.K_F11: # Si la touche est F11
                    toggle_fullscreen() # Basculer en mode plein écran
            
            # Handle slider interaction when menu is open
            if menu_open: # Si le menu est ouvert
                if event.type == pygame.MOUSEBUTTONDOWN: # Si un bouton de la souris est enfoncé
                    mouse_x, mouse_y = pygame.mouse.get_pos() # Récupérer la position de la souris
                    # Check if click is near the slider
                    point_x = int(bar_x + (slider_value - 70) / 80 * bar_width) # Calculer la position du curseur
                    if abs(mouse_x - point_x) < 10 and abs(mouse_y - (bar_y + bar_height // 2)) < 10: # Si le clic est proche du curseur
                        is_dragging = True # Activer le glissement
                
                elif event.type == pygame.MOUSEBUTTONUP: # Si un bouton de la souris est relâché
                    is_dragging = False # Désactiver le glissement
                
                elif event.type == pygame.MOUSEMOTION and is_dragging: # Si la souris est en mouvement et que le glissement est activé
                    mouse_x, _ = pygame.mouse.get_pos()  # Récupérer la position de la souris
                    # Calculate new slider value based on mouse position
                    relative_x = mouse_x - bar_x # Calculer la position relative du curseur
                    slider_value = 70 + (relative_x / bar_width) * 80 # Calculer la valeur du curseur
                    slider_value = max(70, min(150, slider_value))  # Clamp between 70 and 150
                    # Update player FOV
                    player.fov = slider_value # Mettre à jour le champ de vision du joueur
                    player.apply_projection() # Appliquer la projection
            
            # Only process mouse motion for camera when menu is closed
            elif not menu_open and event.type == pygame.MOUSEMOTION: # Si la souris est en mouvement
                xoffset, yoffset = event.rel # Récupérer le décalage de la souris
                player.process_mouse(xoffset, -yoffset) # Mettre à jour la souris

        # Only process keyboard input when menu is closed
        if not menu_open: # Si le menu est fermé
            keys = pygame.key.get_pressed() # Récupérer les touches enfoncées
            player.process_keyboard(keys) # Mettre à jour le clavier
            player.update(delta_time) # Mettre à jour le joueur

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # Effacer le tampon de couleur et le tampon de profondeur
        player.apply() # Appliquer la vue
        
        #grid() # Afficher la grille
        
        glEnable(GL_TEXTURE_2D) # Activer la texture
        glBindTexture(GL_TEXTURE_2D, texture_id) # Lier la texture
        draw_model(model_vbo, model_vertex_count) # Dessiner le modèle 
        glDisable(GL_TEXTURE_2D) # Désactiver la texture
        
        #draw_fps(clock, font, screenwidth= 2560, screenheight= 1440)
        
        # If menu is open, render transparent menu overlay
        if menu_open: 
            # Get the OpenGL buffer
            glFinish() # Attendre que les commandes OpenGL soient terminées
            
            # Clear the menu surface with transparency
            menu_screen.fill((0, 0, 0, 0))  # Fill with transparent black
            
            # Draw semi-transparent menu background
            menu_width, menu_height = 600, 400 # Menu dimensions
            menu_x = (display[0] - menu_width) // 2 # Menu position
            menu_y = (display[1] - menu_height) // 2 # Menu position
            
            # Create a semi-transparent background for the menu area
            pygame.draw.rect(menu_screen, (20, 20, 20, 180), 
                           (menu_x, menu_y, menu_width, menu_height),
                           border_radius=15)
            
            # Draw menu content on the transparent surface
            afficher_parametres(menu_screen, slider_value, is_dragging)
            
            # Convert the surface to a string of pixels
            pixel_string = pygame.image.tostring(menu_screen, 'RGBA', True)
            
            # Draw the menu using OpenGL
            glWindowPos2d(0, 0)
            glDrawPixels(display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, pixel_string)

        pygame.display.flip()

# Modified afficher_parametres function to work with a surface parameter
def afficher_parametres(surface, slider_value, is_dragging):
    # Get the surface dimensions
    width, height = surface.get_width(), surface.get_height()
    
    # Calculate menu area
    menu_width, menu_height = 600, 400
    menu_x = (width - menu_width) // 2
    menu_y = (height - menu_height) // 2
    
    # Title with shadow effect
    title_text = "FOV Camera Settings"
    title = FONT.render(title_text, True, WHITE)
    title_shadow = FONT.render(title_text, True, (0, 0, 0, 128))
    
    # Center the title
    title_x = menu_x + (menu_width - title.get_width()) // 2
    surface.blit(title_shadow, (title_x + 2, menu_y + 32))
    surface.blit(title, (title_x, menu_y + 30))
    
    # Slider bar
    bar_x = menu_x + 90
    bar_y = menu_y + 200
    bar_width = 420
    bar_height = 20
    
    # Draw slider background with transparency
    pygame.draw.rect(surface, (30, 30, 30, 160), 
                    (bar_x-2, bar_y-2, bar_width+4, bar_height+4), 
                    border_radius=10)
    pygame.draw.rect(surface, (255, 255, 255, 200), 
                    (bar_x, bar_y, bar_width, bar_height), 
                    border_radius=10)
    
    # Slider handle
    point_x = int(bar_x + (slider_value - 70) / 80 * bar_width)
    pygame.draw.circle(surface, (0, 200, 0, 200), 
                      (point_x, bar_y + bar_height // 2), 12)
    pygame.draw.circle(surface, (0, 255, 0, 255), 
                      (point_x, bar_y + bar_height // 2), 10)
    
    # FOV value display
    value_text = f"FOV: {int(slider_value)}°"
    value = FONT.render(value_text, True, WHITE)
    value_x = menu_x + (menu_width - value.get_width()) // 2
    surface.blit(value, (value_x, bar_y - 40))
    
    # Instructions
    instruction_text = "Click and drag to adjust" if not is_dragging else "Adjusting..."
    instruction = FONT.render(instruction_text, True, (200, 200, 200, 220))
    instruction_x = menu_x + (menu_width - instruction.get_width()) // 2
    surface.blit(instruction, (instruction_x, bar_y + 50))
    
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

    credits_background = pygame.transform.scale(credits_background, (screen_width, screen_height))
    settings_background = pygame.transform.scale(settings_background, (screen_width, screen_height))
    game_background = pygame.transform.scale(game_background, (screen_width, screen_height))

    # Charger la vidéo de fond pour le menu principal
    local_video_path = "src/bg.mp4"
    video_capture = load_local_video(local_video_path)

    # Charger l'image de la flèche pour le retour
    back_button_image = pygame.image.load("src/back_arrow.png").convert_alpha()  # Assurez-vous d'avoir cette image
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))  # Ajustez la taille selon votre besoin

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
            "Jouer",
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
            font,
            blue,
            hover_blue,
        ),
    ]

    clock = pygame.time.Clock()
    running = True
    current_state = "parametres"
    slider_value = 110
    is_dragging = False
    menu_open = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:  # Détecte le redimensionnement
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
                start_y = (screen_height - (3 * button_height + 2 * button_spacing)) // 2
                buttons[0].rect.topleft = (screen_width // 2 - button_width // 2, start_y)
                buttons[1].rect.topleft = (screen_width // 2 - button_width // 2, start_y + button_height + button_spacing)
                buttons[2].rect.topleft = (screen_width // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing))

            if current_state == "parametres":
                for button in buttons:
                    if button.is_clicked(event):
                        if button.text == "Jouer":
                            current_state = "game"
                        elif button.text == "Paramètres":
                            current_state = "parametres"
                        elif button.text == "Crédits":
                            current_state = "credits"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    current_state = "parametres"
                elif event.key == pygame.K_LEFT:  # Flèche gauche pour revenir au menu
                    current_state = "parametres"
                elif event.key == pygame.K_ESCAPE and current_state == "game":
                    menu_open = not menu_open

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
            version_rect = version_surface.get_rect(bottomright=(screen_width - 10, screen_height - 10))
            screen.blit(version_surface, version_rect)

        elif current_state == "credits":
            back_rect = display_credits(screen, font, credits_background, back_button_image)
            if event.type == pygame.MOUSEBUTTONDOWN and back_rect.collidepoint(event.pos):
                current_state = "parametres"
        elif current_state == "settings":
            back_rect = display_settings(screen, font, settings_background, back_button_image)
            if event.type == pygame.MOUSEBUTTONDOWN and back_rect.collidepoint(event.pos):
                current_state = "parametres"
        elif current_state == "game":
            start_game(screen, font, game_background, dimensions_possibles)
            pygame.display.flip()
            if menu_open:
                afficher_parametres(slider_value, is_dragging)

        pygame.display.flip()
        clock.tick(30)

    if video_capture:
        video_capture.release()
    pygame.quit()

if __name__ == "__main__":
    main_menu()
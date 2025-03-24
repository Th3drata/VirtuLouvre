import pygame
import os
import cv2

from pygame.locals import *

from OpenGL.GL import *

from OpenGL.GLU import *

import numpy as np

import math

import os 

pygame.init()

# Dimensions de l'écran
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Projet Louvre   ")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 200, 255)
HOVER_BLUE = (50, 150, 255)
GREEN = (0, 255, 0)

FONT = pygame.font.Font(None, 36)
font = pygame.font.Font(None, 36)


class Player:

    def __init__(self, fov, aspect, near, far, vertices=None):

        self.fov = 110   

        self.aspect = aspect

        self.near = near

        self.far = 10000

        self.is_sprinting = False

        self.base_speed = 0.05

        self.sprint_multiplier = 2.0

        self.initial_height = 0.5

        self.position = np.array([0.0, self.initial_height, 5.0], dtype=np.float32)

        self.velocity = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        self.acceleration = 0.01

        self.deceleration = 1

        self.max_velocity = 0.5

        self.front = np.array([0.0, 0.0, -1.0], dtype=np.float32)

        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        self.right = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        self.yaw = -90.0

        self.pitch = 0.0

        self.mouse_sensitivity = 0.1

        self.vertices = vertices or []



        self.last_valid_position = self.position.copy()

        self.fly_speed = 0.1

        self.gravity = 0.08

        self.is_flying = True  

        self.ground_level = 0.0  

        
    def apply_projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, self.aspect, self.near, self.far)
        glMatrixMode(GL_MODELVIEW)


    def update_camera_vectors(self):

        self.front[0] = math.cos(math.radians(self.yaw)) * math.cos(math.radians(self.pitch))

        self.front[1] = math.sin(math.radians(self.pitch))

        self.front[2] = math.sin(math.radians(self.yaw)) * math.cos(math.radians(self.pitch))

        self.front = self.front / np.linalg.norm(self.front)

        

        self.right = np.cross(self.front, np.array([0.0, 1.0, 0.0]))

        self.right = self.right / np.linalg.norm(self.right)

        self.up = np.cross(self.right, self.front)

    

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

        

        

        self.velocity *= (1 - self.deceleration)

        

    def process_mouse(self, xoffset, yoffset):

        self.yaw += xoffset * self.mouse_sensitivity

        self.pitch += yoffset * self.mouse_sensitivity

        

        if self.pitch > 89.0:

            self.pitch = 89.0

        if self.pitch < -89.0:

            self.pitch = -89.0

            

        self.update_camera_vectors()

        

    def process_keyboard(self, keys):

        current_speed = self.base_speed * (self.sprint_multiplier if self.is_sprinting else 1.0)

        

        if keys[pygame.K_g]:

            self.is_flying = False

        elif keys[pygame.K_SPACE]:

            self.is_flying = True

            

        if self.is_flying:

            if keys[pygame.K_SPACE]:

                self.position[1] += self.fly_speed

            if keys[pygame.K_LSHIFT]:

                self.position[1] -= self.fly_speed



        if keys[pygame.K_z]:

            move_dir = np.array([self.front[0], 0, self.front[2]])

            move_dir = move_dir / np.linalg.norm(move_dir)

            self.velocity += move_dir * current_speed

        if keys[pygame.K_s]:

            move_dir = np.array([self.front[0], 0, self.front[2]])

            move_dir = move_dir / np.linalg.norm(move_dir)

            self.velocity -= move_dir * current_speed

        if keys[pygame.K_q]:

            move_dir = np.array([self.right[0], 0, self.right[2]])

            move_dir = move_dir / np.linalg.norm(move_dir)

            self.velocity -= move_dir * current_speed

        if keys[pygame.K_d]:

            move_dir = np.array([self.right[0], 0, self.right[2]])

            move_dir = move_dir / np.linalg.norm(move_dir)

            self.velocity += move_dir * current_speed



        velocity_length = np.linalg.norm(self.velocity)

        if velocity_length > self.max_velocity:

            self.velocity = (self.velocity / velocity_length) * self.max_velocity

            

    def check_collision(self, new_position, collision_radius=0.8):
        camera_pos = np.array(new_position)
        min_x, max_x = -30.0, 30.0
        min_z, max_z = -30.0, 30.0
        x, y, z = camera_pos
        
        # Uniquement vérifier les limites de la carte
        if x < min_x or x > max_x or z < min_z or z > max_z:
            return True
                
        return False

        

    def apply(self):

        target = self.position + self.front

        glLoadIdentity()

        gluLookAt(

            self.position[0], self.position[1], self.position[2],

            target[0], target[1], target[2],

            self.up[0], self.up[1], self.up[2]

        )

        

    def apply_projection(self):

        glMatrixMode(GL_PROJECTION)

        glLoadIdentity()

        gluPerspective(self.fov, self.aspect, self.near, self.far)

        glMatrixMode(GL_MODELVIEW)



def grid():

    grid_size = 35

    grid_step = 1
    glBegin(GL_LINES)
    glColor3f(0.5, 0.5, 0.5)
    for i in range(-grid_size, grid_size + 1, grid_step):
        glVertex3f(i, -1, -grid_size)
        glVertex3f(i, -1, grid_size)
    for i in range(-grid_size, grid_size + 1, grid_step):
        glVertex3f(-grid_size, -1, i)
        glVertex3f(grid_size, -1, i)
    glEnd()



def render_text_to_texture(text, font, color=(255, 255, 0)):
    text_surface = font.render(text, True, color, (0, 0, 0))
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    width, height = text_surface.get_size()
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return texture_id, width, height

def draw_fps(clock, font):

    fps = int(clock.get_fps())
    text = f"FPS: {fps}"
    texture_id, width, height = render_text_to_texture(text, font)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(10, 560)
    glTexCoord2f(1, 0); glVertex2f(10 + width, 560)
    glTexCoord2f(1, 1); glVertex2f(10 + width, 560 + height)
    glTexCoord2f(0, 1); glVertex2f(10, 560 + height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def load_obj(filename):
    vertices = []
    texcoords = []
    faces = []
    with open(filename, 'r') as file:
        for line in file:
            if line.startswith('v '):
                vertex = [float(coord) for coord in line.strip().split()[1:4]]
                vertices.append(vertex)
            elif line.startswith('vt '):
                texcoord = [float(coord) for coord in line.strip().split()[1:3]]
                texcoords.append(texcoord)
            elif line.startswith('f '):
                face_vertices = []
                face_texcoords = []
                for v in line.strip().split()[1:]:
                    v_split = v.split('/')
                    face_vertices.append(int(v_split[0]) - 1)
                    if len(v_split) >= 2 and v_split[1]:
                        face_texcoords.append(int(v_split[1]) - 1)
                if len(face_vertices) >= 3:
                    faces.append((face_vertices[:3], face_texcoords[:3]))
    return vertices, texcoords, faces
def load_texture(filename):
    texture_surface = pygame.image.load(filename)
    texture_data = pygame.image.tostring(texture_surface, "RGBA", True)
    width, height = texture_surface.get_size()
    
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    return texture_id

def create_model_vbo(vertices, texcoords, faces):
    vertex_data = []
    texcoord_data = []
    for face in faces:
        for vertex_idx, texcoord_idx in zip(face[0], face[1]):
            vertex_data.extend(vertices[vertex_idx])
            texcoord_data.extend(texcoords[texcoord_idx])
    
    vertex_data = np.array(vertex_data, dtype=np.float32)
    texcoord_data = np.array(texcoord_data, dtype=np.float32)
    
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes + texcoord_data.nbytes, None, GL_STATIC_DRAW)
    glBufferSubData(GL_ARRAY_BUFFER, 0, vertex_data.nbytes, vertex_data)
    glBufferSubData(GL_ARRAY_BUFFER, vertex_data.nbytes, texcoord_data.nbytes, texcoord_data)
    
    return vbo, len(vertex_data) // 3

def draw_model(vbo, vertex_count):
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(3, GL_FLOAT, 0, None)

    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glTexCoordPointer(2, GL_FLOAT, 0, ctypes.c_void_p(vertex_count * 3 * 4))
    
    # Active le test de profondeur
    glEnable(GL_DEPTH_TEST)
    
    # Dessiner le modèle plein
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glColor3f(1.0, 1.0, 1.0)  # Couleur blanche pour que la texture soit visible
    glDrawArrays(GL_TRIANGLES, 0, vertex_count)
    
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisable(GL_DEPTH_TEST)


# Initialisation de Pygame et de la police
pygame.init()

version_text = "Version 1.0.0"
try:
    version_font = pygame.font.Font(None, 24)  # Police par défaut
except:
    print("Erreur lors de l'initialisation de la police, utilisation de la police par défaut.")
    version_font = pygame.font.SysFont('Arial', 24)  # Si 'None' échoue, utiliser Arial comme fallback

# Fonction pour charger une vidéo locale
def load_local_video(file_path):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Le fichier vidéo '{file_path}' n'existe pas.")
        return cv2.VideoCapture(file_path)
    except Exception as e:
        print(f"Erreur: Impossible de charger la vidéo depuis le fichier '{file_path}'. {e}")
        return None

# Classe pour gérer les boutons
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color, shadow_color=(0, 0, 0), border_radius=10):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.shadow_color = shadow_color
        self.border_radius = border_radius

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        button_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        
        # Dessiner l'ombre légèrement décalée
        shadow_rect = self.rect.move(5, 5)  # Décale l'ombre de 5 pixels sur x et y
        pygame.draw.rect(surface, self.shadow_color, shadow_rect, border_radius=self.border_radius)

        # Dessiner le bouton
        pygame.draw.rect(surface, button_color, self.rect, border_radius=self.border_radius)

        # Dessiner le texte sur le bouton
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

# Fonction pour afficher les crédits
def display_credits(screen, font, background_image, back_button_image):
    screen.blit(background_image, (0, 0))

    credits_text = [
        "Crédits :",
        "Développé par",
        "Albert Oscar, Moors Michel, Rinckenbach Yann"
    ]

    start_y = 200
    line_spacing = 40

    for i, line in enumerate(credits_text):
        text_surface = font.render(line, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(400, start_y + i * line_spacing))
        screen.blit(text_surface, text_rect)

    # Afficher la flèche pour revenir
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    
    return back_rect

# Fonction pour afficher les paramètres
def display_settings(screen, font, background_image, back_button_image):
    screen.blit(background_image, (0, 0))
    text = font.render("Paramètres : Personnalisez votre jeu ici", True, (255, 255, 255))
    text_rect = text.get_rect(center=(400, 300))
    screen.blit(text, text_rect)

    # Afficher la flèche pour revenir
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    
    return back_rect

# Fonction pour démarrer le jeu
def start_game(screen, font, background_image):
    pygame.init()
    pygame.font.init()
    display = (800, 600)
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D View - Press ESC to toggle menu")

    # Create a separate surface for the menu with alpha channel
    menu_screen = pygame.Surface(display, pygame.SRCALPHA)
    menu_open = False
    slider_value = 110
    is_dragging = False
    
    # Add slider interaction variables
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

    # Enable blending for transparency
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Chargement du modèle 3D
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'untitled.obj')
    vertices, texcoords, faces = load_obj(model_path)
    
    if not vertices or not faces:
        print("Erreur: Impossible de charger le modèle 3D")
        pygame.quit()
        return

    model_vbo, model_vertex_count = create_model_vbo(vertices, texcoords, faces)
    texture_path = os.path.join(current_dir, 'texture.png')
    texture_id = load_texture(texture_path)
    
    # Set initial mouse state
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)

    while True:
        delta_time = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    menu_open = not menu_open
                    # Toggle mouse visibility and grab
                    pygame.event.set_grab(not menu_open)
                    pygame.mouse.set_visible(menu_open)
            
            # Handle slider interaction when menu is open
            if menu_open:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    # Check if click is near the slider
                    point_x = int(bar_x + (slider_value - 70) / 80 * bar_width)
                    if abs(mouse_x - point_x) < 10 and abs(mouse_y - (bar_y + bar_height // 2)) < 10:
                        is_dragging = True
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    is_dragging = False
                
                elif event.type == pygame.MOUSEMOTION and is_dragging:
                    mouse_x, _ = pygame.mouse.get_pos()
                    # Calculate new slider value based on mouse position
                    relative_x = mouse_x - bar_x
                    slider_value = 70 + (relative_x / bar_width) * 80
                    slider_value = max(70, min(150, slider_value))  # Clamp between 70 and 150
                    # Update player FOV
                    player.fov = slider_value
                    player.apply_projection()
            
            # Only process mouse motion for camera when menu is closed
            elif not menu_open and event.type == pygame.MOUSEMOTION:
                xoffset, yoffset = event.rel
                player.process_mouse(xoffset, -yoffset)

        # Only process keyboard input when menu is closed
        if not menu_open:
            keys = pygame.key.get_pressed()
            player.process_keyboard(keys)
            player.update(delta_time)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        player.apply()
        
        grid()
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        draw_model(model_vbo, model_vertex_count)
        glDisable(GL_TEXTURE_2D)
        
        draw_fps(clock, font)
        
        # If menu is open, render transparent menu overlay
        if menu_open:
            # Get the OpenGL buffer
            glFinish()
            
            # Clear the menu surface with transparency
            menu_screen.fill((0, 0, 0, 0))
            
            # Draw semi-transparent menu background
            menu_width, menu_height = 600, 400
            menu_x = (display[0] - menu_width) // 2
            menu_y = (display[1] - menu_height) // 2
            
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
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Menu principal")

    # Charger les images d'arrière-plan
    credits_background = pygame.image.load("credits_bg.jpg").convert()
    settings_background = pygame.image.load("settings_bg.jpg").convert()
    game_background = pygame.image.load("game_bg.jpg").convert()

    credits_background = pygame.transform.scale(credits_background, (screen_width, screen_height))
    settings_background = pygame.transform.scale(settings_background, (screen_width, screen_height))
    game_background = pygame.transform.scale(game_background, (screen_width, screen_height))

    # Charger la vidéo de fond pour le menu principal
    local_video_path = "bg.mp4"
    video_capture = load_local_video(local_video_path)

    # Charger l'image de la flèche pour le retour
    back_button_image = pygame.image.load("back_arrow.png").convert_alpha()  # Assurez-vous d'avoir cette image
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))  # Ajustez la taille selon votre besoin

    # Couleurs et police
    blue = (100, 200, 255)
    hover_blue = (50, 150, 255)
    font = pygame.font.Font(None, 36)

    buttons = [
        Button(screen_width // 2 - 100, 200, 200, 50, "Jouer", font, blue, hover_blue),
        Button(screen_width // 2 - 100, 300, 200, 50, "Paramètres", font, blue, hover_blue),
        Button(screen_width // 2 - 100, 400, 200, 50, "Crédits", font, blue, hover_blue),
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
            start_game(screen, font, game_background)
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
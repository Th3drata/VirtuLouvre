import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
import os  
import time

class Player:
    def __init__(self, fov, aspect, near, far, vertices=None):
        self.fov = 120
        self.aspect = aspect
        self.near = near
        self.far = far
        self.is_sprinting = False
        self.base_speed = 0.1
        self.sprint_multiplier = 2.0
        self.initial_height = 0.5
        self.position = np.array([0.0, self.initial_height, 6.0], dtype=np.float32)
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
        self.collision_radius = 0.1
        self.last_valid_position = self.position.copy()
        self.fly_speed = 0.1 
        self.gravity = 0.08
        self.is_flying = True  
        self.ground_level = 0.0  
        self.fullscreen = False

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
        if self.pitch > 90.0:
            self.pitch = 90.0
        if self.pitch < -90.0:
            self.pitch = -90.0
        self.update_camera_vectors()

    def process_keyboard(self, keys):
        current_speed = self.base_speed * (self.sprint_multiplier if self.is_sprinting else 1.0)
        if keys[pygame.K_g]:
            self.is_flying = False
        elif keys[pygame.K_SPACE]:
            self.is_flying = True
        if keys[pygame.K_e]:
            self.position = np.array([0.0, self.initial_height, 6.0], dtype=np.float32)
            self.yaw = 270.0
            self.pitch = 0.0
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
    faces = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('v '):  # Vertex
                    vertex = [float(coord) for coord in line.strip().split()[1:4]]
                    vertices.append(vertex)
                elif line.startswith('f '):  # Face
                    face_vertices = []
                    for v in line.strip().split()[1:]:
                        face_vertices.append(int(v.split('/')[0]) - 1)
                    if len(face_vertices) >= 3:
                        faces.append(face_vertices[:3])
        return vertices, faces
    except Exception as e:
        print(f"Erreur lors du chargement du fichier: {e}")
        return [], []

def create_model_vbo(vertices, faces):
    vertex_data = []
    for face in faces:
        for vertex_idx in face:
            vertex_data.extend(vertices[vertex_idx])
    vertex_data = np.array(vertex_data, dtype=np.float32)
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)
    return vbo, len(vertex_data) // 3

def draw_model(vbo, vertex_count):
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glColor3f(1, 1, 1)
    glDrawArrays(GL_POLYGON, 0, vertex_count)
    glDisable(GL_DEPTH_TEST)
    glLineWidth(0.01)
    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    glColor3f(0.2, 0.2, 0.2)
    glDrawArrays(GL_POLYGON, 0, vertex_count)
    glEnable(GL_DEPTH_TEST)
    glDisableClientState(GL_VERTEX_ARRAY)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

def place_model(vbo, vertex_count, x, y, z):
    glPushMatrix()
    glTranslatef(x, y, z)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glColor3f(1, 1, 1)
    glDrawArrays(GL_POLYGON, 0, vertex_count)
    glDisable(GL_DEPTH_TEST)
    glLineWidth(0.01)
    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    glColor3f(0.2, 0.2, 0.2)
    glDrawArrays(GL_POLYGON, 0, vertex_count)
    glEnable(GL_DEPTH_TEST)
    glDisableClientState(GL_VERTEX_ARRAY)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glPopMatrix()

def get_pos(self, font):
    pos = self.position
    text = f"Position: {pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}"
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
    glTexCoord2f(0, 0); glVertex2f(10, 530)
    glTexCoord2f(1, 0); glVertex2f(10 + width, 530)
    glTexCoord2f(1, 1); glVertex2f(10 + width, 530 + height)
    glTexCoord2f(0, 1); glVertex2f(10, 530 + height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def view_angle(self, font):
    viewy = self.yaw % 360
    viewp = self.pitch
    text = f"View Angle: {viewy:.2f}, {viewp:.2f}"
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
    glTexCoord2f(0, 0); glVertex2f(10, 500)
    glTexCoord2f(1, 0); glVertex2f(10 + width, 500)
    glTexCoord2f(1, 1); glVertex2f(10 + width, 500 + height)
    glTexCoord2f(0, 1); glVertex2f(10, 500 + height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def main():
    pygame.init()
    pygame.font.init() 
    windowed_size = (900, 700)
    fullscreen_size = (1920, 1080)
    current_size = windowed_size
    screen = pygame.display.set_mode(current_size, DOUBLEBUF|OPENGL)
    pygame.display.set_caption("3D View - Press ESC to toggle mouse lock")
    fullscreen = False
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    mouse_locked = True
    player = Player(45, (current_size[0]/current_size[1]), 0.1, 200)
    player.apply_projection()
    glTranslatef(0.0,0.0,-5)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18) 
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'modele.obj') 
    vertices, faces = load_obj(model_path)
    if not vertices or not faces:
        print("Erreur: Impossible de charger le modèle 3D")
        pygame.quit()
        return
    model_vbo, model_vertex_count = create_model_vbo(vertices, faces)
    model_position = [20.0, 0.0, -5.0] 
    while True:
        delta_time = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    mouse_locked = not mouse_locked
                    pygame.event.set_grab(mouse_locked)
                    pygame.mouse.set_visible(not mouse_locked)
                if event.key == pygame.K_F4:
                    pygame.quit()
                    quit() 
            elif event.type == pygame.MOUSEMOTION and mouse_locked:
                xoffset, yoffset = event.rel
                player.process_mouse(xoffset, -yoffset)
            elif event.type == pygame.ACTIVEEVENT:
                if event.state == 2:  
                    if not event.gain:  
                        mouse_locked = False
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                    else:  
                        mouse_locked = True
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
        keys = pygame.key.get_pressed()
        player.process_keyboard(keys)
        player.update(delta_time)
        player.apply()
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        grid()
        place_model(model_vbo, model_vertex_count, *model_position)
        get_pos(player, font)
        view_angle(player, font)
        draw_fps(clock, font) 
        pygame.display.flip()

if __name__ == "__main__":
    main()
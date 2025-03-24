import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
import os
import time
import ctypes

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

        for vertex in self.vertices:
            vertex_pos = np.array(vertex)
            distance = np.linalg.norm(camera_pos - vertex_pos)
            if distance < collision_radius:
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

def load_obj(filename):
    vertices = []
    tex_coords = []
    faces = []
    
    try:
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('v '):
                    vertices.append(list(map(float, line.split()[1:4])))
                elif line.startswith('vt '):
                    tex_coords.append(list(map(float, line.split()[1:3])))
                elif line.startswith('f '):
                    face_entries = [entry.split('/') for entry in line.split()[1:]]
                    face = []
                    for entry in face_entries:
                        v_idx = int(entry[0]) - 1
                        vt_idx = int(entry[1]) - 1 if entry[1] else 0
                        face.append((v_idx, vt_idx))
                    faces.append(face)
        return vertices, tex_coords, faces
    except Exception as e:
        print(f"Error loading OBJ file: {e}")
        return [], [], []

def load_texture(image_path):
    texture_surface = pygame.image.load(image_path)
    texture_data = pygame.image.tostring(texture_surface, "RGBA", 1)
    
    width = texture_surface.get_width()
    height = texture_surface.get_height()
    
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    
    return texture_id

def create_model_vbo(vertices, tex_coords, faces):
    vertex_data = []
    for face in faces:
        for v_idx, vt_idx in face:
            vertex = vertices[v_idx]
            tex_coord = tex_coords[vt_idx] if vt_idx < len(tex_coords) else [0, 0]
            vertex_data.extend(vertex)
            vertex_data.extend(tex_coord)
    
    vertex_data = np.array(vertex_data, dtype=np.float32)
    
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)
    
    return vbo, len(vertex_data)

def draw_model_vbo(vbo, vertex_count, texture_id):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(3, GL_FLOAT, 5 * 4, None)
    
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glTexCoordPointer(2, GL_FLOAT, 5 * 4, ctypes.c_void_p(3 * 4))
    
    glDrawArrays(GL_TRIANGLES, 0, vertex_count // 5)
    
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisable(GL_TEXTURE_2D)

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
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'cube.obj')
    texture_path = os.path.join(current_dir, 'textures.png')
    
    vertices, tex_coords, faces = load_obj(model_path)
    texture_id = load_texture(texture_path)
    
    player = Player(45, (current_size[0]/current_size[1]), 0.1, 200, vertices)
    player.apply_projection()
    glTranslatef(0.0,0.0,-5)
    
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18) 
    
    model_vbo, model_vertex_count = create_model_vbo(vertices, tex_coords, faces)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)

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
        draw_model_vbo(model_vbo, model_vertex_count, texture_id)
        get_pos(player, font)
        view_angle(player, font)
        pygame.display.flip()

if __name__ == "__main__":
    main()
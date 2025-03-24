import numpy as np
import math
from OpenGL.GL import *
from OpenGL.GLU import *
import pygame

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
        self.deceleration = 0.00390625
        self.max_velocity = 100000
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
        if not self.is_flying:
            self.velocity[1] -= self.gravity * delta_time  # Apply gravity over time

            # Prevent player from falling below ground level
            if self.position[1] < self.ground_level + self.initial_height:
                self.position[1] = self.ground_level + self.initial_height
                self.velocity[1] = 0  

        # Apply velocity to position
        new_position = self.position + self.velocity

        # Check for collision
        if not self.check_collision(new_position):
            self.last_valid_position = new_position.copy()
            self.position = new_position
        else:
            self.position = self.last_valid_position.copy()
            self.velocity = np.zeros(3)

        # Apply deceleration for movement
        self.velocity *= (1 - self.deceleration * delta_time)

        velocity_length = np.linalg.norm(self.velocity)


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
        if keys[pygame.K_t]:
            self.position = np.array([0.0, 20000, 6.0], dtype=np.float32)

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
        x, y, z = new_position
        min_x, max_x = -30.0, 30.0
        min_z, max_z = -30.0, 30.0
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

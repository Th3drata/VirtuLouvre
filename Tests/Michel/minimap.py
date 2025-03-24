import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math

# Initialize Pygame and OpenGL
pygame.init()
display_width, display_height = 800, 600
pygame.display.set_mode((display_width, display_height), DOUBLEBUF | OPENGL)
pygame.display.set_caption('3D Game with Minimap')

# Set up the 3D perspective
glMatrixMode(GL_PROJECTION)
gluPerspective(45, (display_width / display_height), 0.1, 50.0)
glMatrixMode(GL_MODELVIEW)
glEnable(GL_DEPTH_TEST)

# Player position and rotation
player_pos = [0, 0, 0]  # x, y, z
player_rot = 0  # rotation in degrees

# Map data - simple maze represented as a 2D grid
# 1 = wall, 0 = empty space
map_data = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    [1, 0, 1, 1, 0, 0, 1, 0, 0, 1],
    [1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 0, 1, 1, 1, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    [1, 1, 1, 0, 1, 0, 1, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]

# Create minimap surface with transparency
minimap_size = 150
minimap_surface = pygame.Surface((minimap_size, minimap_size), pygame.SRCALPHA)
minimap_scale = minimap_size / len(map_data)
minimap_pos = (display_width - minimap_size - 10, 10)  # top-right corner

# Function to draw the 3D world
def draw_world():
    global player_pos, player_rot
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # Position camera based on player position and rotation
    # Looking direction is calculated from player's rotation
    look_x = math.sin(math.radians(player_rot))
    look_z = -math.cos(math.radians(player_rot))
    
    gluLookAt(
        player_pos[0], 0.5, player_pos[2],  # Eye position
        player_pos[0] + look_x, 0.5, player_pos[2] + look_z,  # Look at point
        0, 1, 0  # Up vector
    )
    
    # Draw the floor
    glBegin(GL_QUADS)
    glColor3f(0.2, 0.2, 0.2)
    glVertex3f(-10, 0, -10)
    glVertex3f(-10, 0, 10)
    glVertex3f(10, 0, 10)
    glVertex3f(10, 0, -10)
    glEnd()
    
    # Draw walls from map_data
    for z in range(len(map_data)):
        for x in range(len(map_data[z])):
            if map_data[z][x] == 1:  # If it's a wall
                glPushMatrix()
                glTranslatef(x - len(map_data)/2, 0.5, z - len(map_data[0])/2)
                glColor3f(0.5, 0.5, 0.7)
                draw_cube()
                glPopMatrix()

# Function to draw a unit cube
def draw_cube():
    vertices = [
        [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5], [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5],
        [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5], [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5]
    ]
    
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7]
    ]
    
    faces = [
        [0, 1, 2, 3], [4, 5, 6, 7], [0, 4, 7, 3],
        [1, 5, 6, 2], [0, 1, 5, 4], [3, 2, 6, 7]
    ]
    
    glBegin(GL_QUADS)
    for face in faces:
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()

# Function to update the minimap
def update_minimap():
    global player_pos, player_rot
    
    minimap_surface.fill((0, 0, 0, 0))  # Clear with transparent background
    
    # Draw the map with transparency
    for z in range(len(map_data)):
        for x in range(len(map_data[z])):
            rect_x = x * minimap_scale
            rect_y = z * minimap_scale
            rect_w = minimap_scale
            rect_h = minimap_scale
            
            if map_data[z][x] == 1:  # Wall
                pygame.draw.rect(minimap_surface, (100, 100, 100, 200), (rect_x, rect_y, rect_w, rect_h))
            else:  # Floor - semi-transparent
                pygame.draw.rect(minimap_surface, (50, 50, 50, 100), (rect_x, rect_y, rect_w, rect_h))
    
    # Calculate player position on minimap
    map_center_offset = len(map_data) / 2
    mini_x = (player_pos[0] + map_center_offset) * minimap_scale
    mini_y = (player_pos[2] + map_center_offset) * minimap_scale
    
    # Draw player position (red dot)
    pygame.draw.circle(minimap_surface, (255, 0, 0, 255), (mini_x, mini_y), 3)
    
    # Draw player direction (line pointing in direction of view)
    direction_length = 10
    dir_x = mini_x + direction_length * math.sin(math.radians(player_rot))
    dir_y = mini_y + direction_length * math.cos(math.radians(player_rot))
    pygame.draw.line(minimap_surface, (0, 255, 0, 255), (mini_x, mini_y), (dir_x, dir_y), 2)

# Function to handle keyboard input
def handle_keys():
    global player_pos, player_rot
    
    keys = pygame.key.get_pressed()
    move_speed = 0.1
    rotate_speed = 2
    
    # Calculate forward direction vector
    forward_x = math.sin(math.radians(player_rot))
    forward_z = -math.cos(math.radians(player_rot))
    
    # Calculate right direction vector (perpendicular to forward)
    right_x = math.sin(math.radians(player_rot + 90))
    right_z = -math.cos(math.radians(player_rot + 90))
    
    new_x, new_z = player_pos[0], player_pos[2]
    
    if keys[K_z]:  # Forward
        new_x += forward_x * move_speed
        new_z += forward_z * move_speed
    if keys[K_s]:  # Backward
        new_x -= forward_x * move_speed
        new_z -= forward_z * move_speed
    if keys[K_q]:  # Strafe left
        new_x -= right_x * move_speed
        new_z -= right_z * move_speed
    if keys[K_d]:  # Strafe right
        new_x += right_x * move_speed
        new_z += right_z * move_speed
    if keys[K_LEFT]:  # Turn left
        player_rot -= rotate_speed
    if keys[K_RIGHT]:  # Turn right
        player_rot += rotate_speed
    
    # Check if the new position would collide with a wall
    map_x = int(new_x + len(map_data)/2)
    map_z = int(new_z + len(map_data[0])/2)
    
    if 0 <= map_x < len(map_data) and 0 <= map_z < len(map_data[0]):
        if map_data[map_z][map_x] != 1:  # Not a wall
            player_pos[0] = new_x
            player_pos[2] = new_z

# Main game loop
clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    handle_keys()
    draw_world()
    update_minimap()
    
    # Switch to 2D mode to draw the minimap
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, display_width, display_height, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    # Convert the Pygame surface to a texture and draw it
    minimap_data = pygame.image.tostring(minimap_surface, "RGBA", True)
    
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glEnable(GL_TEXTURE_2D)
    minimap_texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, minimap_texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, minimap_size, minimap_size, 0, GL_RGBA, GL_UNSIGNED_BYTE, minimap_data)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(minimap_pos[0], minimap_pos[1])
    glTexCoord2f(1, 0); glVertex2f(minimap_pos[0] + minimap_size, minimap_pos[1])
    glTexCoord2f(1, 1); glVertex2f(minimap_pos[0] + minimap_size, minimap_pos[1] + minimap_size)
    glTexCoord2f(0, 1); glVertex2f(minimap_pos[0], minimap_pos[1] + minimap_size)
    glEnd()
    
    glDeleteTextures(1, [minimap_texture])
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_BLEND)
    
    # Switch back to 3D mode
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
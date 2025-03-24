import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import os
from player import Player
from utils import grid, draw_fps, draw_position, draw_view_angle, load_obj, load_mtl, load_texture, create_model_vbo, draw_model_vbo, draw_velocity

def main():
    # Initialize Pygame and OpenGL
    pygame.init()
    pygame.font.init()
    windowed_size = (900, 700)
    screen = pygame.display.set_mode(windowed_size, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D View - Press ESC to toggle mouse lock")
    
    fullscreen = False
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    mouse_locked = True

    # Create Player object and apply initial projection
    player = Player(45, (windowed_size[0] / windowed_size[1]), 0.1, 10000000)
    player.apply_projection()

    # Initial OpenGL setup
    glTranslatef(0.0, 0.0, -5)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)
    
    # Load model and texture
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'modele.obj')
    texture_path = os.path.join(current_dir, 'texture.png')

    # Load texture for the model
    texture_id = load_texture(texture_path)
    if texture_id is None:
        print("Erreur: Impossible de charger la texture")
        pygame.quit()
        return

    vertices, textures, faces = load_obj(model_path)
    if not vertices or not faces:
        print("Erreur: Impossible de charger le modèle 3D")
        pygame.quit()
        return

    model_vbo, model_vertex_count = create_model_vbo(vertices, textures, faces)

    # Main game loop
    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    mouse_locked = not mouse_locked
                    pygame.event.set_grab(mouse_locked)
                    pygame.mouse.set_visible(not mouse_locked)
                if event.key == pygame.K_F4:
                    running = False
            elif event.type == pygame.MOUSEMOTION and mouse_locked:
                xoffset, yoffset = event.rel
                player.process_mouse(xoffset, -yoffset)
            elif event.type == pygame.ACTIVEEVENT:
                if event.state == 2:  # Window event
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
        
        # Clear screen and render scene
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        grid()
        glBindTexture(GL_TEXTURE_2D, texture_id)  # Bind the texture
        draw_model_vbo(model_vbo, model_vertex_count)  # Draw model with texture
        draw_position(player, font)
        draw_view_angle(player, font)
        draw_fps(clock, font)
        draw_velocity(player, font)
        
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
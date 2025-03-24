import pygame
import numpy as np

pygame.init()
size = (500, 500)
screen = pygame.display.set_mode(size, pygame.RESIZABLE)
ground_height = 50

ground = pygame.rect.Rect(0, size[1] - ground_height, size[0], ground_height)
player = pygame.rect.Rect(100, 400, 50, 50)

player_vel_y = 0
player_vel_x = 7

GRAVITY = 1
JUMP_STRENGTH = 20

ascii_chars = "@%#*+=-:. "
ascii_length = len(ascii_chars)

def grayscale_to_ascii(gray_value):
    index = int(gray_value / 255 * (ascii_length - 1))
    return ascii_chars[index]

def movement():
    global player_vel_y

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        player.x -= player_vel_x
    if keys[pygame.K_RIGHT]:
        player.x += player_vel_x
    
    if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and collisions():
        player_vel_y = -JUMP_STRENGTH

def collisions():
    global player_vel_y

    if player.colliderect(ground):
        player.y = ground.y - player.height
        player_vel_y = 0
        return True
    return False

def render_ascii():
    screen_array = pygame.surfarray.array3d(screen)
    gray_array = np.dot(screen_array[...,:3], [0.2989, 0.5870, 0.1140])
    ascii_screen = np.vectorize(grayscale_to_ascii)(gray_array)
    
    font = pygame.font.SysFont('Courier', 10)
    for y in range(0, size[1], 10):
        for x in range(0, size[0], 10):
            char = ascii_screen[x, y]
            text_surface = font.render(char, True, (255, 255, 255))
            screen.blit(text_surface, (x, y))

def main():
    global screen, size, player_vel_y, ground

    fps = 60
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        movement()
        player_vel_y += GRAVITY
        player.y += player_vel_y
        collisions()

        screen.fill((0, 0, 0))
        pygame.draw.rect(screen, (255, 0, 0), player)
        pygame.draw.rect(screen, (0, 255, 0), ground)
        
        render_ascii()

        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()

if __name__ == "__main__":
    main()
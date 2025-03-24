import pygame
import numpy as np
import pygame.surfarray as surfarray


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

ascii_chars = ".:'-~=<\\*({[%08O#@Q&"
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

def main():
    global screen, size, player_vel_y, ground

    fps = 60
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()

            if event.type == pygame.VIDEORESIZE:
                size = event.size
                screen = pygame.display.set_mode(size, pygame.RESIZABLE)
                ground = pygame.rect.Rect(0, size[1] - 50, size[0], 50)

        pixels = surfarray.pixels3d(screen)
        gray_values = np.dot(pixels[...,:3], [0.299, 0.587, 0.114])
        ascii_art = []

        for y in range(gray_values.shape[0]):
            line = ""
            for x in range(gray_values.shape[1]):
                gray_value = gray_values[y, x]
                ascii_char = grayscale_to_ascii(gray_value)
                line += ascii_char
            ascii_art.append(line)

        print("\n".join(ascii_art))


        player_vel_y += GRAVITY
        player.y += player_vel_y

        movement()
        collisions()

        screen.fill((255, 255, 255))
        pygame.draw.rect(screen, (255, 0, 0), ground)
        pygame.draw.rect(screen, (0, 0, 0), player)
        pygame.display.flip()

        clock.tick(fps)

if __name__ == "__main__":
    main()

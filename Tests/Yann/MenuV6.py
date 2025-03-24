import pygame
import os

# Initialisation de Pygame
pygame.init()

# Définition des résolutions disponibles
resolutions = [
    (800, 600),
    (1600, 900),
    (0, 0)  # 0,0 pour le plein écran
]

# Index de la résolution actuelle
current_resolution_index = 0

# Création de la fenêtre
screen = pygame.display.set_mode(resolutions[current_resolution_index])
pygame.display.set_caption("Changer la résolution")

# Chargement des images des flèches
arrow_left = pygame.image.load("src/arrow_left.png")
arrow_right = pygame.image.load("src/arrow_right.png")

# Redimensionnement des images des flèches
arrow_size = (50, 50)
arrow_left = pygame.transform.scale(arrow_left, arrow_size)
arrow_right = pygame.transform.scale(arrow_right, arrow_size)

# Police pour le texte
font = pygame.font.Font(None, 36)

# Fonction pour changer la résolution et recentrer la fenêtre
def change_resolution(index):
    global screen, current_resolution_index
    current_resolution_index = index
    width, height = resolutions[index]

    if width == 0 and height == 0:  # Plein écran
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((width, height))

# Boucle principale
running = True
while running:
    screen.fill((30, 30, 30))  # Fond gris foncé

    # Récupérer la taille actuelle de l'écran
    screen_width, screen_height = screen.get_size()

    # Affichage du texte de la résolution actuelle
    resolution_text = "Plein écran" if resolutions[current_resolution_index] == (0, 0) else f"{resolutions[current_resolution_index][0]} x {resolutions[current_resolution_index][1]}"
    text_surface = font.render(resolution_text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(screen_width // 2, screen_height // 2))

    # Positionnement des flèches
    left_rect = arrow_left.get_rect(midright=(text_rect.left - 20, screen_height // 2))
    right_rect = arrow_right.get_rect(midleft=(text_rect.right + 20, screen_height // 2))

    # Dessiner les éléments
    pygame.draw.rect(screen, (50, 50, 50), (left_rect.left - 10, left_rect.top - 10, right_rect.right - left_rect.left + 20, left_rect.height + 20), border_radius=10)
    screen.blit(arrow_left, left_rect)
    screen.blit(arrow_right, right_rect)
    screen.blit(text_surface, text_rect)

    # Gestion des événements
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Clic gauche
            if left_rect.collidepoint(event.pos):
                new_index = (current_resolution_index - 1) % len(resolutions)
                change_resolution(new_index)
            elif right_rect.collidepoint(event.pos):
                new_index = (current_resolution_index + 1) % len(resolutions)
                change_resolution(new_index)

    pygame.display.flip()

pygame.quit()

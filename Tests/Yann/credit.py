import pygame
import sys

def display_credits():
    pygame.init()

    # Paramètres de l'écran
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Crédits")

    # Couleurs et police
    white = (255, 255, 255)
    black = (0, 0, 0)
    font = pygame.font.Font(None, 36)

    # Texte des crédits
    credits = [
        "Développeur principal: Nom du développeur",
        "Graphismes: Nom de l'artiste",
        "Musique: Nom du compositeur",
        "Merci de jouer à notre jeu!",
    ]

    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False  # Retour au menu principal

        screen.fill(black)

        # Afficher les crédits ligne par ligne
        for i, line in enumerate(credits):
            text_surface = font.render(line, True, white)
            screen.blit(text_surface, (50, 100 + i * 50))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

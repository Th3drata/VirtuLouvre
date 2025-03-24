import pygame
import sys

# Initialisation de Pygame
pygame.init()

# Dimensions de la fenêtre
WIDTH, HEIGHT = 800, 600

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 0, 255)

# Configuration de l'écran
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jeu avec Menu Paramètres")

# Charger une image de fond pour le menu
menu_background = pygame.image.load("settings_bg.jpg").convert()

# Création d'une surface pour afficher le jeu en arrière-plan
game_surface = pygame.Surface((WIDTH, HEIGHT))

# Initialisation de la FOV
class GameSettings:
    def __init__(self):
        self.fov = 160

settings = GameSettings()

def draw_game():
    # Dessiner le jeu sur la surface dédiée
    game_surface.fill((100, 150, 200))
    pygame.draw.circle(game_surface, (255, 0, 0), (WIDTH // 2, HEIGHT // 2), 50)

# Fonction pour dessiner le menu des paramètres
def draw_settings_menu():
    # Dessiner le jeu en arrière-plan
    screen.blit(game_surface, (0, 0))

    # Dessiner l'arrière-plan du menu
    screen.blit(pygame.transform.scale(menu_background, (WIDTH, HEIGHT)), (0, 0))

    font = pygame.font.Font(None, 40)
    title = font.render("Menu Paramètres", True, BLACK)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 4))

    # Afficher la barre de réglage de la FOV
    fov_label = font.render(f"FOV: {settings.fov}", True, BLACK)
    screen.blit(fov_label, (WIDTH // 2 - fov_label.get_width() // 2, HEIGHT // 2 - 50))

    # Dessiner la barre
    bar_x = WIDTH // 4
    bar_y = HEIGHT // 2
    bar_width = WIDTH // 2
    bar_height = 20

    # Fond de la barre
    pygame.draw.rect(screen, GRAY, (bar_x, bar_y, bar_width, bar_height))
    
    # Curseur en fonction de la valeur actuelle de la FOV
    cursor_width = 10
    cursor_x = bar_x + int((settings.fov - 50) / 100 * (bar_width - cursor_width))
    pygame.draw.rect(screen, BLUE, (cursor_x, bar_y, cursor_width, bar_height))

    back_text = font.render("Appuyez sur Echap pour revenir.", True, BLACK)
    screen.blit(back_text, (WIDTH // 2 - back_text.get_width() // 2, HEIGHT - 100))

# Boucle principale
def main():
    clock = pygame.time.Clock()
    running = True
    in_settings_menu = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    in_settings_menu = not in_settings_menu

        # Modifier la FOV avec les touches gauche et droite
        if in_settings_menu:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                settings.fov = max(50, settings.fov - 1)
            if keys[pygame.K_RIGHT]:
                settings.fov = min(150, settings.fov + 1)

        # Toujours dessiner le jeu, même si le menu est actif
        draw_game()

        if in_settings_menu:
            draw_settings_menu()
        else:
            # Dessiner le jeu sur l'écran principal
            screen.blit(game_surface, (0, 0))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
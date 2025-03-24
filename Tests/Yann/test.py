import pygame
import sys

# Initialisation de Pygame
pygame.init()

# Dimensions de la fenêtre
WIDTH, HEIGHT = 300, 200
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Barre arrondie avec point mobile")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)

# Propriétés de la barre
BAR_START_X = 60
BAR_END_X = 160
BAR_Y = HEIGHT // 2
BAR_HEIGHT = 10
BAR_COLOR = GRAY
BAR_RADIUS = BAR_HEIGHT // 2

# Propriétés du point
POINT_RADIUS = 8
point_x = (BAR_START_X + BAR_END_X) // 2  # Position initiale du point (milieu)
point_y = BAR_Y

# Variable pour stocker la valeur associée au point
value = int((point_x - BAR_START_X) / (BAR_END_X - BAR_START_X) * 50 + 110)

# Police pour afficher le nombre
font = pygame.font.Font(None, 36)

# État du menu
menu_active = False

# Fonction pour afficher le menu
def draw_menu():
    # Dessiner l'écran
    screen.fill(WHITE)

    # Dessiner la barre (avec extrémités arrondies)
    pygame.draw.rect(screen, BAR_COLOR, (BAR_START_X, BAR_Y - BAR_RADIUS, BAR_END_X - BAR_START_X, BAR_HEIGHT))
    pygame.draw.circle(screen, BAR_COLOR, (BAR_START_X, BAR_Y), BAR_RADIUS)
    pygame.draw.circle(screen, BAR_COLOR, (BAR_END_X, BAR_Y), BAR_RADIUS)

    # Dessiner le point
    pygame.draw.circle(screen, RED, (point_x, point_y), POINT_RADIUS)

    # Afficher la position du point au-dessus
    text_surface = font.render(str(value), True, BLACK)
    text_rect = text_surface.get_rect(center=(point_x, point_y - 20))
    screen.blit(text_surface, text_rect)

# Boucle principale
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                menu_active = not menu_active
        elif menu_active and event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            # Vérifie si la souris clique sur le point
            if (mouse_x - point_x) ** 2 + (mouse_y - point_y) ** 2 <= POINT_RADIUS ** 2:
                dragging = True
        elif menu_active and event.type == pygame.MOUSEBUTTONUP:
            dragging = False
        elif menu_active and event.type == pygame.MOUSEMOTION and 'dragging' in locals() and dragging:
            # Déplace le point avec la souris (limité à la barre)
            point_x = min(max(BAR_START_X, event.pos[0]), BAR_END_X)
            # Met à jour la valeur associée
            value = int((point_x - BAR_START_X) / (BAR_END_X - BAR_START_X) * 50 + 110)

    # Dessiner le menu si actif
    if menu_active:
        draw_menu()

    # Mettre à jour l'écran
    pygame.display.flip()

    # Limiter le framerate
    pygame.time.Clock().tick(60)

# Quitter Pygame
pygame.quit()
sys.exit()

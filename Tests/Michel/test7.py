import pygame

# Initialisation de Pygame
pygame.init()

# Dimensions de l'écran
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Jeu avec menu intégré")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 200, 255)
HOVER_BLUE = (50, 150, 255)
GREEN = (0, 255, 0)

# Police
FONT = pygame.font.Font(None, 36)

# Classe pour gérer les boutons
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        button_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surface, button_color, self.rect)
        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

def afficher_menu(buttons):
    for button in buttons:
        button.draw(screen)

def afficher_parametres(slider_value, is_dragging):

    pygame.draw.rect(screen, (50, 50, 50), (100, 100, 600, 400))  # Fond du menu
    text = FONT.render("Paramètres : Déplacez le point sur la barre", True, WHITE)
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 150))

    # Dessin de la barre arrondie (plus longue)
    bar_x, bar_y, bar_width, bar_height = 200, 300, 420, 20
    pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), border_radius=80)

    # Calcul de la position du point mobile
    point_x = int(bar_x + (slider_value - 70) / 80 * bar_width)
    pygame.draw.circle(screen, GREEN, (point_x, bar_y + bar_height // 2), 10)

    label_text = FONT.render("Valeur :", True, WHITE)
    screen.blit(label_text, (SCREEN_WIDTH // 2 - 75, 250))
    
    value_text = FONT.render(f"{slider_value}", True, WHITE)
    screen.blit(value_text, (SCREEN_WIDTH // 2 + 20, 250))

    drag_text = "Glissement : ON" if is_dragging else "Glissement : OFF"
    drag_surface = FONT.render(drag_text, True, WHITE)
    screen.blit(drag_surface, (SCREEN_WIDTH // 2 - drag_surface.get_width() // 2, 400))

# Fonction principale du jeu
def game_loop():
    running = True
    menu_open = False
    slider_value = 110
    is_dragging = False
    clock = pygame.time.Clock()
    buttons = [Button(SCREEN_WIDTH//2 - 100, 200, 200, 50, "Jouer", FONT, BLUE, HOVER_BLUE),
               Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "Paramètres", FONT, BLUE, HOVER_BLUE),
               Button(SCREEN_WIDTH//2 - 100, 400, 200, 50, "Crédits", FONT, BLUE, HOVER_BLUE)]
    
    buttons1 = [Button(SCREEN_WIDTH//2 - 100, 200, 200, 50, "Reprendre", FONT, BLUE, HOVER_BLUE),
               Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "Settings", FONT, BLUE, HOVER_BLUE),
               Button(SCREEN_WIDTH//2 - 100, 400, 200, 50, "Quit", FONT, BLUE, HOVER_BLUE)]
    
    current_state = "parametres"
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if current_state == "parametres":
                for button in buttons:
                    if button.is_clicked(event):
                        if button.text == "Jouer":
                            current_state = "game"
                        elif button.text == "Paramètres":
                            current_state = "parametres"
                        elif button.text == "Crédits":
                            current_state = "credits"

        if current_state == "parametres":
            screen.fill(BLACK)
            for button in buttons:
                button.draw(screen)

        elif current_state == "game":
            screen.fill(BLUE)
            text = FONT.render("Appuyez sur Échap pour ouvrir le menu", True, WHITE)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                current_state = "game_menu"

        elif current_state == "game_menu":
            afficher_menu(buttons1)
            for button in buttons1:
                if button.is_clicked(event):
                    if button.text == "Reprendre":
                        current_state = "game"
                    elif button.text == "Settings":
                        current_state = "settings"
                    elif button.text == "Quit":
                        current_state = "quit"

        elif current_state == "settings":
            afficher_parametres(slider_value, is_dragging)
            bar_x, bar_y, bar_width, bar_height = 200, 300, 420, 20
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if bar_x <= mouse_x <= bar_x + bar_width and bar_y <= mouse_y <= bar_y + bar_height:
                    is_dragging = True
            elif event.type == pygame.MOUSEBUTTONUP:
                is_dragging = False
            elif event.type == pygame.MOUSEMOTION and is_dragging:
                mouse_x, _ = event.pos
                slider_value = int((mouse_x - bar_x) / bar_width * 80) + 70
                slider_value = max(70, min(150, slider_value))
            
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    game_loop()
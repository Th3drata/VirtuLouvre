import pygame
import os
import cv2

# Initialisation de Pygame
pygame.init()

# Définition des constantes
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 200, 255)
HOVER_BLUE = (50, 150, 255)
GREEN = (0, 255, 0)

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FONT = pygame.font.Font(None, 36)

version_text = "Version 1.0.0"
version_font = pygame.font.Font(None, 24)

# Charger la vidéo locale
def load_local_video(file_path):
    if not os.path.exists(file_path):
        print(f"Erreur : le fichier '{file_path}' est introuvable.")
        return None
    return cv2.VideoCapture(file_path)

# Appliquer un flou à une image (utilisé pour les vidéos)
def apply_blur(frame):
    return cv2.GaussianBlur(frame, (21, 21), 0)

# Classe Button
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color, shadow_color=BLACK, border_radius=10):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.shadow_color = shadow_color
        self.border_radius = border_radius

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        shadow_rect = self.rect.move(5, 5)
        pygame.draw.rect(surface, self.shadow_color, shadow_rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, color, self.rect, border_radius=self.border_radius)
        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

# Affichage des paramètres
def display_settings(screen, slider_value, is_dragging):
    screen.fill((50, 50, 50))
    text = FONT.render("Paramètres : Déplacez le point sur la barre", True, WHITE)
    text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, 100))
    screen.blit(text, text_rect)

    bar_x, bar_y, bar_width, bar_height = 200, 300, 400, 20
    pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), border_radius=10)

    point_x = int(bar_x + (slider_value - 70) / 80 * bar_width)
    pygame.draw.circle(screen, GREEN, (point_x, bar_y + bar_height // 2), 10)

    value_text = FONT.render(f"Valeur : {slider_value}", True, WHITE)
    value_text_rect = value_text.get_rect(center=(SCREEN_WIDTH // 2, 350))
    screen.blit(value_text, value_text_rect)

    drag_text = "Glissement : ON" if is_dragging else "Glissement : OFF"
    drag_surface = FONT.render(drag_text, True, WHITE)
    drag_rect = drag_surface.get_rect(center=(SCREEN_WIDTH // 2, 400))
    screen.blit(drag_surface, drag_rect)

# Affichage des crédits
def display_credits(screen, font):
    screen.fill(BLACK)
    credits = [
        "Crédits :",
        "Développé par",
        "Albert Oscar, Moors Michel, Rinckenbach Yann"
    ]
    start_y = 200
    for i, line in enumerate(credits):
        text = font.render(line, True, WHITE)
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * 40))
        screen.blit(text, text_rect)

# Lancer le jeu
def start_game(screen, font):
    screen.fill((30, 30, 30))
    text = font.render("Jeu en cours... Appuyez sur Retour pour revenir", True, WHITE)
    text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(text, text_rect)

# Fonction principale
def main_menu():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Menu principal")
    clock = pygame.time.Clock()

    buttons = [
        Button(300, 200, 200, 50, "Jouer", FONT, BLUE, HOVER_BLUE),
        Button(300, 300, 200, 50, "Paramètres", FONT, BLUE, HOVER_BLUE),
        Button(300, 400, 200, 50, "Crédits", FONT, BLUE, HOVER_BLUE),
    ]

    current_state = "menu"
    slider_value = 110
    is_dragging = False
    video_capture = load_local_video("bg.mp4")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if current_state == "menu":
                for i, button in enumerate(buttons):
                    if button.is_clicked(event):
                        if i == 0:
                            current_state = "game"
                        elif i == 1:
                            current_state = "settings"
                        elif i == 2:
                            current_state = "credits"

            elif current_state == "settings":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos
                    bar_x, bar_y, bar_width, bar_height = 200, 300, 400, 20
                    if bar_x <= mouse_x <= bar_x + bar_width and bar_y <= mouse_y <= bar_y + bar_height:
                        is_dragging = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    is_dragging = False
                elif event.type == pygame.MOUSEMOTION and is_dragging:
                    mouse_x, _ = event.pos
                    slider_value = int((mouse_x - 200) / 400 * 80) + 70
                    slider_value = max(70, min(150, slider_value))
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                    current_state = "menu"

            elif current_state in ["credits", "game"]:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                    current_state = "menu"

        # Affichage selon l'état
        if current_state == "menu":
            if video_capture:
                ret, frame = video_capture.read()
                if ret:
                    frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = apply_blur(frame)
                    frame_surface = pygame.surfarray.make_surface(frame)
                    screen.blit(pygame.transform.rotate(frame_surface, -90), (0, 0))
                else:
                    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            for button in buttons:
                button.draw(screen)
            version_surface = version_font.render(version_text, True, WHITE)
            screen.blit(version_surface, (10, SCREEN_HEIGHT - 30))

        elif current_state == "settings":
            display_settings(screen, slider_value, is_dragging)

        elif current_state == "credits":
            display_credits(screen, FONT)

        elif current_state == "game":
            start_game(screen, FONT)

        pygame.display.flip()
        clock.tick(30)

    if video_capture:
        video_capture.release()
    pygame.quit()

if __name__ == "__main__":
    main_menu()

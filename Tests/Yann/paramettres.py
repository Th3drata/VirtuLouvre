import pygame
import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

def size_screen():
    if os.name == 'nt':  # Only for Windows
        from ctypes import windll
        user32 = windll.user32
        largeur = user32.GetSystemMetrics(0)
        hauteur = user32.GetSystemMetrics(1)
    else:
        largeur, hauteur = pygame.display.Info().current_w, pygame.display.Info().current_h
    
    resolutions_16_9 = [ (800, 600), (426, 240), (640, 360), (854, 480), (960, 540), 
                        (1280, 720), (1366, 768), (1600, 900), (1920, 1080), 
                        (2560, 1440), (3840, 2160)]
    
    return [(w, h) for w, h in resolutions_16_9 if w <= largeur and h <= hauteur] + [(0, 0)]

pygame.init()
resolutions = size_screen()
current_resolution_index = 0

def change_resolution(index):
    global screen, current_resolution_index, settings_background
    current_resolution_index = index
    width, height = resolutions[index]

    if width == 0 and height == 0:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        width, height = pygame.display.Info().current_w, pygame.display.Info().current_h
    else:
        screen = pygame.display.set_mode((width, height))
    
    settings_background = pygame.transform.scale(pygame.image.load("src/settings_bg.jpg").convert(), (width, height))

arrow_left = pygame.image.load("src/arrow_left.png")
arrow_right = pygame.image.load("src/arrow_right.png")
arrow_size = (50, 50)
arrow_left = pygame.transform.scale(arrow_left, arrow_size)
arrow_right = pygame.transform.scale(arrow_right, arrow_size)

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
        pygame.draw.rect(surface, button_color, self.rect, border_radius=10)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

def display_settings(screen, font, back_button_image, current_tab):
    screen.blit(settings_background, (0, 0))
    tabs = ["Vidéo", "Audio", "JSP"]
    tab_buttons = []
    tab_width, tab_height, tab_spacing = 240, 40, -10
    start_x = (screen.get_width() - (len(tabs) * (tab_width + tab_spacing) - tab_spacing)) // 2
    start_y = 20

    for i, tab in enumerate(tabs):
        tab_buttons.append(Button(start_x + i * (tab_width + tab_spacing), start_y, tab_width, tab_height, tab, font, (200, 200, 200), (150, 150, 150)))
        tab_buttons[i].draw(screen)
    
    left_rect, right_rect = pygame.Rect(0, 0, 0, 0), pygame.Rect(0, 0, 0, 0)
    if current_tab == "Vidéo":
        resolution_text = "Plein écran" if resolutions[current_resolution_index] == (0, 0) else f"{resolutions[current_resolution_index][0]} x {resolutions[current_resolution_index][1]}"
        text_surface = font.render(resolution_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(screen.get_width() // 2, 200))
        screen.blit(text_surface, text_rect)
        left_rect = arrow_left.get_rect(midright=(text_rect.left - 20, 200))
        right_rect = arrow_right.get_rect(midleft=(text_rect.right + 20, 200))
        screen.blit(arrow_left, left_rect)
        screen.blit(arrow_right, right_rect)
    
    back_rect = back_button_image.get_rect(center=(40, screen.get_height() - 30))
    screen.blit(back_button_image, back_rect)
    return back_rect, tab_buttons, left_rect, right_rect

def main_menu():
    pygame.init()
    global screen, settings_background
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Menu principal")
    settings_background = pygame.image.load("src/settings_bg.jpg").convert()
    settings_background = pygame.transform.scale(settings_background, (800, 600))
    back_button_image = pygame.image.load("src/back_arrow.png").convert_alpha()
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))
    font = pygame.font.Font(None, 36)
    blue, hover_blue = (100, 200, 255), (50, 150, 255)
    buttons = [Button(350, 300, 200, 50, "Paramètres", font, blue, hover_blue)]
    clock = pygame.time.Clock()
    running, current_state, current_tab = True, "menu", "Vidéo"
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if current_state == "menu":
                for button in buttons:
                    if button.is_clicked(event):
                        current_state = "settings"
            elif current_state == "settings":
                back_rect, tab_buttons, left_rect, right_rect = display_settings(screen, font, back_button_image, current_tab)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        current_state = "menu"
                    for tab_button in tab_buttons:
                        if tab_button.is_clicked(event):
                            current_tab = tab_button.text
                    if left_rect.collidepoint(event.pos):
                        change_resolution((current_resolution_index - 1) % len(resolutions))
                    elif right_rect.collidepoint(event.pos):
                        change_resolution((current_resolution_index + 1) % len(resolutions))
        
        screen.fill((0, 0, 0))
        if current_state == "menu":
            for button in buttons:
                button.draw(screen)
        elif current_state == "settings":
            display_settings(screen, font, back_button_image, current_tab)
        
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()

if __name__ == "__main__":
    main_menu() 
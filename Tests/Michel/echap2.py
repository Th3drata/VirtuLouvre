import pygame
import sys
from OpenGL.GL import *
from pygame.locals import *
import numpy as np
import random

pygame.init()
FPS = 60
window_size = (800, 600)
pygame.display.set_mode(window_size, OPENGL | DOUBLEBUF)

# OpenGL setup
glViewport(0, 0, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;791,&quot;end_index&quot;&#58;794,&quot;number&quot;&#58;0,&quot;url&quot;&#58;&quot;https&#58;//www.pygame.org/docs/tut/PygameIntro.html?highlight=blit&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/KiE6f4Y66LNpzXm3ymMWRJMBYp4fc2KmSY1C8jMmVdc/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvYmRmYmZlMzEy/NGM4OTAyMTE3NWNl/OTNkYmYyZGNmZDg3/OWEyYTlhNDRiMzQ3/NTNlOWJiMGM0ZWQ5/OWM3Y2E3Yi93d3cu/cHlnYW1lLm9yZy8&quot;,&quot;snippet&quot;&#58;&quot;sndarray&#58;&#32;manipulate&#32;sounds&#32;with&#32;numpy…&quot;&#125;&#93;"}, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;807,&quot;end_index&quot;&#58;810,&quot;number&quot;&#58;1,&quot;url&quot;&#58;&quot;https&#58;//stackoverflow.com/questions/61396799/how-can-i-blit-my-pygame-game-onto-an-opengl-surface&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/4WRMec_wn8Q9LO6DI43kkBvIL6wD5TYCXztC9C9kEI0/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvNWU3Zjg0ZjA1/YjQ3ZTlkNjQ1ODA1/MjAwODhiNjhjYWU0/OTc4MjM4ZDJlMTBi/ODExYmNiNTkzMjdh/YjM3MGExMS9zdGFj/a292ZXJmbG93LmNv/bS8&quot;,&quot;snippet&quot;&#58;&quot;This&#32;started&#32;from&#32;the&#32;example&#32;provided&#32;by&#32;@Kingsley.\nSo&#32;this&#32;is&#32;supposed&#32;to&#32;be&#32;an&#32;addition&#32;or&#32;variant,&#32;not&#32;a&#32;replacement&#32;or&#32;competing&#32;with&#32;the&#32;original&#32;answer.\nI&#32;was&#32;trying&#32;to&#32;remove&#32;the&#32;use&#32;of&#32;the&#32;\&quot;tostring\&quot;.\nIt&#32;also&#32;prints&#32;some&#32;info&#32;about&#32;OpenGL&#32;and&#32;removes&#32;unnecessary&#32;state&#32;changes.\nAlso&#32;removed&#32;glGenerateMipmap&#32;as&#32;we&#32;do&#32;not&#32;need&#32;it&#32;for&#32;2D&#32;(nothing&#32;is&#32;far).\nWe&#32;also&#32;do&#32;not&#32;need&#32;blending&#32;for&#32;this…&quot;&#125;&#93;"})
glMatrixMode(GL_PROJECTION)
glLoadIdentity()
glOrtho(0, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;879,&quot;end_index&quot;&#58;882,&quot;number&quot;&#58;0,&quot;url&quot;&#58;&quot;https&#58;//www.pygame.org/docs/tut/PygameIntro.html?highlight=blit&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/KiE6f4Y66LNpzXm3ymMWRJMBYp4fc2KmSY1C8jMmVdc/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvYmRmYmZlMzEy/NGM4OTAyMTE3NWNl/OTNkYmYyZGNmZDg3/OWEyYTlhNDRiMzQ3/NTNlOWJiMGM0ZWQ5/OWM3Y2E3Yi93d3cu/cHlnYW1lLm9yZy8&quot;,&quot;snippet&quot;&#58;&quot;sndarray&#58;&#32;manipulate&#32;sounds&#32;with&#32;numpy…&quot;&#125;&#93;"}, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;895,&quot;end_index&quot;&#58;898,&quot;number&quot;&#58;1,&quot;url&quot;&#58;&quot;https&#58;//stackoverflow.com/questions/61396799/how-can-i-blit-my-pygame-game-onto-an-opengl-surface&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/4WRMec_wn8Q9LO6DI43kkBvIL6wD5TYCXztC9C9kEI0/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvNWU3Zjg0ZjA1/YjQ3ZTlkNjQ1ODA1/MjAwODhiNjhjYWU0/OTc4MjM4ZDJlMTBi/ODExYmNiNTkzMjdh/YjM3MGExMS9zdGFj/a292ZXJmbG93LmNv/bS8&quot;,&quot;snippet&quot;&#58;&quot;This&#32;started&#32;from&#32;the&#32;example&#32;provided&#32;by&#32;@Kingsley.\nSo&#32;this&#32;is&#32;supposed&#32;to&#32;be&#32;an&#32;addition&#32;or&#32;variant,&#32;not&#32;a&#32;replacement&#32;or&#32;competing&#32;with&#32;the&#32;original&#32;answer.\nI&#32;was&#32;trying&#32;to&#32;remove&#32;the&#32;use&#32;of&#32;the&#32;\&quot;tostring\&quot;.\nIt&#32;also&#32;prints&#32;some&#32;info&#32;about&#32;OpenGL&#32;and&#32;removes&#32;unnecessary&#32;state&#32;changes.\nAlso&#32;removed&#32;glGenerateMipmap&#32;as&#32;we&#32;do&#32;not&#32;need&#32;it&#32;for&#32;2D&#32;(nothing&#32;is&#32;far).\nWe&#32;also&#32;do&#32;not&#32;need&#32;blending&#32;for&#32;this…&quot;&#125;&#93;"}, 0, -1, 1)  # Top-left origin
glMatrixMode(GL_MODELVIEW)
glLoadIdentity()
glDisable(GL_DEPTH_TEST)
glDisable(GL_LIGHTING)

# Setup GL texture
texId = glGenTextures(1)
glBindTexture(GL_TEXTURE_2D, texId)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;1284,&quot;end_index&quot;&#58;1287,&quot;number&quot;&#58;0,&quot;url&quot;&#58;&quot;https&#58;//www.pygame.org/docs/tut/PygameIntro.html?highlight=blit&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/KiE6f4Y66LNpzXm3ymMWRJMBYp4fc2KmSY1C8jMmVdc/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvYmRmYmZlMzEy/NGM4OTAyMTE3NWNl/OTNkYmYyZGNmZDg3/OWEyYTlhNDRiMzQ3/NTNlOWJiMGM0ZWQ5/OWM3Y2E3Yi93d3cu/cHlnYW1lLm9yZy8&quot;,&quot;snippet&quot;&#58;&quot;sndarray&#58;&#32;manipulate&#32;sounds&#32;with&#32;numpy…&quot;&#125;&#93;"}, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;1300,&quot;end_index&quot;&#58;1303,&quot;number&quot;&#58;1,&quot;url&quot;&#58;&quot;https&#58;//stackoverflow.com/questions/61396799/how-can-i-blit-my-pygame-game-onto-an-opengl-surface&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/4WRMec_wn8Q9LO6DI43kkBvIL6wD5TYCXztC9C9kEI0/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvNWU3Zjg0ZjA1/YjQ3ZTlkNjQ1ODA1/MjAwODhiNjhjYWU0/OTc4MjM4ZDJlMTBi/ODExYmNiNTkzMjdh/YjM3MGExMS9zdGFj/a292ZXJmbG93LmNv/bS8&quot;,&quot;snippet&quot;&#58;&quot;This&#32;started&#32;from&#32;the&#32;example&#32;provided&#32;by&#32;@Kingsley.\nSo&#32;this&#32;is&#32;supposed&#32;to&#32;be&#32;an&#32;addition&#32;or&#32;variant,&#32;not&#32;a&#32;replacement&#32;or&#32;competing&#32;with&#32;the&#32;original&#32;answer.\nI&#32;was&#32;trying&#32;to&#32;remove&#32;the&#32;use&#32;of&#32;the&#32;\&quot;tostring\&quot;.\nIt&#32;also&#32;prints&#32;some&#32;info&#32;about&#32;OpenGL&#32;and&#32;removes&#32;unnecessary&#32;state&#32;changes.\nAlso&#32;removed&#32;glGenerateMipmap&#32;as&#32;we&#32;do&#32;not&#32;need&#32;it&#32;for&#32;2D&#32;(nothing&#32;is&#32;far).\nWe&#32;also&#32;do&#32;not&#32;need&#32;blending&#32;for&#32;this…&quot;&#125;&#93;"}, 0, GL_RGB, GL_UNSIGNED_BYTE, None)

# Function to convert Pygame surface to OpenGL texture
def surfaceToTexture(pygame_surface, texId):
    width, height = pygame_surface.get_size()
    surface_array = pygame.surfarray.pixels3d(pygame_surface)
    rgb_surface = surface_array.swapaxes(0, 1).astype(np.uint8).tobytes()
    glBindTexture(GL_TEXTURE_2D, texId)
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, rgb_surface)
    glBindTexture(GL_TEXTURE_2D, 0)

# Main loop
clock = pygame.time.Clock()
offscreen_surface = pygame.Surface(window_size)
text_font = pygame.font.Font(None, 30)

done = False
while not done:
    for event in pygame.event.get():
        if event.type == QUIT:
            done = True

    offscreen_surface.fill((15, 0, 100))
    time_text = f"TICKS: {pygame.time.get_ticks()}"
    words = text_font.render(time_text, True, (255, 245, 100))
    offscreen_surface.blit(words, (50, 250))

    surfaceToTexture(offscreen_surface, texId)

    glBindTexture(GL_TEXTURE_2D, texId)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(0, 0)  # Top-left corner
    glTexCoord2f(1, 0); glVertex2f(window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;2466,&quot;end_index&quot;&#58;2469,&quot;number&quot;&#58;0,&quot;url&quot;&#58;&quot;https&#58;//www.pygame.org/docs/tut/PygameIntro.html?highlight=blit&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/KiE6f4Y66LNpzXm3ymMWRJMBYp4fc2KmSY1C8jMmVdc/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvYmRmYmZlMzEy/NGM4OTAyMTE3NWNl/OTNkYmYyZGNmZDg3/OWEyYTlhNDRiMzQ3/NTNlOWJiMGM0ZWQ5/OWM3Y2E3Yi93d3cu/cHlnYW1lLm9yZy8&quot;,&quot;snippet&quot;&#58;&quot;sndarray&#58;&#32;manipulate&#32;sounds&#32;with&#32;numpy…&quot;&#125;&#93;"}, 0)  # Top-right corner
    glTexCoord2f(1, 1); glVertex2f(window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;2540,&quot;end_index&quot;&#58;2543,&quot;number&quot;&#58;0,&quot;url&quot;&#58;&quot;https&#58;//www.pygame.org/docs/tut/PygameIntro.html?highlight=blit&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/KiE6f4Y66LNpzXm3ymMWRJMBYp4fc2KmSY1C8jMmVdc/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvYmRmYmZlMzEy/NGM4OTAyMTE3NWNl/OTNkYmYyZGNmZDg3/OWEyYTlhNDRiMzQ3/NTNlOWJiMGM0ZWQ5/OWM3Y2E3Yi93d3cu/cHlnYW1lLm9yZy8&quot;,&quot;snippet&quot;&#58;&quot;sndarray&#58;&#32;manipulate&#32;sounds&#32;with&#32;numpy…&quot;&#125;&#93;"}, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;2556,&quot;end_index&quot;&#58;2559,&quot;number&quot;&#58;1,&quot;url&quot;&#58;&quot;https&#58;//stackoverflow.com/questions/61396799/how-can-i-blit-my-pygame-game-onto-an-opengl-surface&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/4WRMec_wn8Q9LO6DI43kkBvIL6wD5TYCXztC9C9kEI0/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvNWU3Zjg0ZjA1/YjQ3ZTlkNjQ1ODA1/MjAwODhiNjhjYWU0/OTc4MjM4ZDJlMTBi/ODExYmNiNTkzMjdh/YjM3MGExMS9zdGFj/a292ZXJmbG93LmNv/bS8&quot;,&quot;snippet&quot;&#58;&quot;This&#32;started&#32;from&#32;the&#32;example&#32;provided&#32;by&#32;@Kingsley.\nSo&#32;this&#32;is&#32;supposed&#32;to&#32;be&#32;an&#32;addition&#32;or&#32;variant,&#32;not&#32;a&#32;replacement&#32;or&#32;competing&#32;with&#32;the&#32;original&#32;answer.\nI&#32;was&#32;trying&#32;to&#32;remove&#32;the&#32;use&#32;of&#32;the&#32;\&quot;tostring\&quot;.\nIt&#32;also&#32;prints&#32;some&#32;info&#32;about&#32;OpenGL&#32;and&#32;removes&#32;unnecessary&#32;state&#32;changes.\nAlso&#32;removed&#32;glGenerateMipmap&#32;as&#32;we&#32;do&#32;not&#32;need&#32;it&#32;for&#32;2D&#32;(nothing&#32;is&#32;far).\nWe&#32;also&#32;do&#32;not&#32;need&#32;blending&#32;for&#32;this…&quot;&#125;&#93;"})  # Bottom-right corner
    glTexCoord2f(0, 1); glVertex2f(0, window_size:inlineRefs{references="&#91;&#123;&quot;type&quot;&#58;&quot;inline_reference&quot;,&quot;start_index&quot;&#58;2633,&quot;end_index&quot;&#58;2636,&quot;number&quot;&#58;1,&quot;url&quot;&#58;&quot;https&#58;//stackoverflow.com/questions/61396799/how-can-i-blit-my-pygame-game-onto-an-opengl-surface&quot;,&quot;favicon&quot;&#58;&quot;https&#58;//imgs.search.brave.com/4WRMec_wn8Q9LO6DI43kkBvIL6wD5TYCXztC9C9kEI0/rs&#58;fit&#58;32&#58;32&#58;1&#58;0/g&#58;ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvNWU3Zjg0ZjA1/YjQ3ZTlkNjQ1ODA1/MjAwODhiNjhjYWU0/OTc4MjM4ZDJlMTBi/ODExYmNiNTkzMjdh/YjM3MGExMS9zdGFj/a292ZXJmbG93LmNv/bS8&quot;,&quot;snippet&quot;&#58;&quot;This&#32;started&#32;from&#32;the&#32;example&#32;provided&#32;by&#32;@Kingsley.\nSo&#32;this&#32;is&#32;supposed&#32;to&#32;be&#32;an&#32;addition&#32;or&#32;variant,&#32;not&#32;a&#32;replacement&#32;or&#32;competing&#32;with&#32;the&#32;original&#32;answer.\nI&#32;was&#32;trying&#32;to&#32;remove&#32;the&#32;use&#32;of&#32;the&#32;\&quot;tostring\&quot;.\nIt&#32;also&#32;prints&#32;some&#32;info&#32;about&#32;OpenGL&#32;and&#32;removes&#32;unnecessary&#32;state&#32;changes.\nAlso&#32;removed&#32;glGenerateMipmap&#32;as&#32;we&#32;do&#32;not&#32;need&#32;it&#32;for&#32;2D&#32;(nothing&#32;is&#32;far).\nWe&#32;also&#32;do&#32;not&#32;need&#32;blending&#32;for&#32;this…&quot;&#125;&#93;"})  # Bottom-left corner
    glEnd()
    glBindTexture(GL_TEXTURE_2D, 0)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
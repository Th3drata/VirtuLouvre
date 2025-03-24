import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

def grid():
    grid_size = 35
    grid_step = 1
    glBegin(GL_LINES)
    glColor3f(0.5, 0.5, 0.5)
    for i in range(-grid_size, grid_size + 1, grid_step):
        glVertex3f(i, -1, -grid_size)
        glVertex3f(i, -1, grid_size)
    for i in range(-grid_size, grid_size + 1, grid_step):
        glVertex3f(-grid_size, -1, i)
        glVertex3f(grid_size, -1, i)
    glEnd()

def render_text_to_texture(text, font, color=(255, 255, 0)):

    text_surface = font.render(text, True, color, (0, 0, 0))
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    width, height = text_surface.get_size()
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return texture_id, width, height

def draw_textured_floor(texture_id):
    """Dessine un plan texturé au sol."""
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-10.0, -1.0, -10.0)
    glTexCoord2f(1.0, 0.0); glVertex3f(10.0, -1.0, -10.0)
    glTexCoord2f(1.0, 1.0); glVertex3f(10.0, -1.0, 10.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-10.0, -1.0, 10.0)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)

def draw_fps(clock, font):
    fps = int(clock.get_fps())
    text = f"FPS: {fps}"
    texture_id, width, height = render_text_to_texture(text, font)
    

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(10, 560)
    glTexCoord2f(1, 0); glVertex2f(10 + width, 560)
    glTexCoord2f(1, 1); glVertex2f(10 + width, 560 + height)
    glTexCoord2f(0, 1); glVertex2f(10, 560 + height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
 
    glDeleteTextures([texture_id])

def draw_position(player, font):

    pos = player.position
    text = f"Position: {pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}"
    texture_id, width, height = render_text_to_texture(text, font)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(10, 530)
    glTexCoord2f(1, 0); glVertex2f(10 + width, 530)
    glTexCoord2f(1, 1); glVertex2f(10 + width, 530 + height)
    glTexCoord2f(0, 1); glVertex2f(10, 530 + height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glDeleteTextures([texture_id])

def draw_view_angle(player, font):

    view_yaw = player.yaw % 360
    view_pitch = player.pitch
    text = f"View Angle: {view_yaw:.2f}, {view_pitch:.2f}"
    texture_id, width, height = render_text_to_texture(text, font)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(10, 500)
    glTexCoord2f(1, 0); glVertex2f(10 + width, 500)
    glTexCoord2f(1, 1); glVertex2f(10 + width, 500 + height)
    glTexCoord2f(0, 1); glVertex2f(10, 500 + height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glDeleteTextures([texture_id])

def load_obj(filename):
    """Charge un fichier OBJ et renvoie les sommets, les coordonnées de texture et les faces."""
    vertices = []
    textures = []
    faces = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('v '):  # Déclaration d'un vertex
                    vertex = [float(coord) for coord in line.strip().split()[1:4]]
                    vertices.append(vertex)
                elif line.startswith('vt '):  # Déclaration d'une coordonnée de texture
                    texture = [float(coord) for coord in line.strip().split()[1:3]]
                    textures.append(texture)
                elif line.startswith('f '):  # Déclaration d'une face
                    face_vertices = []
                    face_textures = []
                    for v in line.strip().split()[1:]:
                        vertex_data = v.split('/')
                        face_vertices.append(int(vertex_data[0]) - 1)
                        if len(vertex_data) > 1 and vertex_data[1]:
                            face_textures.append(int(vertex_data[1]) - 1)
                    if len(face_vertices) >= 3:
                        faces.append((face_vertices[:3], face_textures[:3]))
        return vertices, textures, faces
    except Exception as e:
        print(f"Erreur lors du chargement du fichier OBJ: {e}")
        return [], [], []
    
    
def load_mtl(filename):

    materials = {}
    current_material = None
    try:
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('newmtl'):
                    current_material = line.split()[1]
                    materials[current_material] = {}
                elif line.startswith('Kd') and current_material:
                    kd = [float(value) for value in line.split()[1:4]]
                    materials[current_material]['Kd'] = kd
                elif line.startswith('Ka') and current_material:
                    ka = [float(value) for value in line.split()[1:4]]
                    materials[current_material]['Ka'] = ka
                elif line.startswith('Ks') and current_material:
                    ks = [float(value) for value in line.split()[1:4]]
                    materials[current_material]['Ks'] = ks
                elif line.startswith('Ns') and current_material:
                    ns = float(line.split()[1])
                    materials[current_material]['Ns'] = ns
                elif line.startswith('d') and current_material:
                    d = float(line.split()[1])
                    materials[current_material]['d'] = d
                elif line.startswith('map_Kd') and current_material:
                    map_kd = line.split()[1]
                    materials[current_material]['map_Kd'] = map_kd
        return materials
    except Exception as e:
        print(f"Erreur lors du chargement du fichier MTL: {e}")
        return {}

def load_texture(filename):
    try:
        texture_surface = pygame.image.load(filename)
        texture_data = pygame.image.tostring(texture_surface, "RGBA", True)
        width, height = texture_surface.get_size()
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return texture_id
    except Exception as e:
        print(f"Erreur lors du chargement de la texture: {e}")
        return None

def create_model_vbo(vertices, textures, faces):
    """Crée un VBO pour le modèle à partir des vertices, textures et faces."""
    vertex_data = []
    texture_data = []
    for face in faces:
        face_vertices, face_textures = face
        for i, vertex_idx in enumerate(face_vertices):
            vertex_data.extend(vertices[vertex_idx])
            if face_textures:
                texture_data.extend(textures[face_textures[i]])
            else:
                texture_data.extend([0.0, 0.0])  # Coordonnées de texture par défaut

    vertex_data = np.array(vertex_data, dtype=np.float32)
    texture_data = np.array(texture_data, dtype=np.float32)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes + texture_data.nbytes, None, GL_STATIC_DRAW)
    glBufferSubData(GL_ARRAY_BUFFER, 0, vertex_data.nbytes, vertex_data)
    glBufferSubData(GL_ARRAY_BUFFER, vertex_data.nbytes, texture_data.nbytes, texture_data)

    return vbo, len(vertex_data) // 3  # Chaque vertex contient 3 coordonnées

def draw_model_vbo(vbo, vertex_count):
    """Dessine le modèle à partir du VBO."""
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(3, GL_FLOAT, 0, None)

    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glTexCoordPointer(2, GL_FLOAT, 0, ctypes.c_void_p(vertex_count * 3 * 4))

    glEnable(GL_TEXTURE_2D)
    glDrawArrays(GL_TRIANGLES, 0, vertex_count)

    glDisable(GL_TEXTURE_2D)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisableClientState(GL_VERTEX_ARRAY)
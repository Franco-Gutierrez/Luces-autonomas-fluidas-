import pygame
import numpy as np
import colorsys
import sys

# --- CONFIGURACIÓN ---
WIDTH, HEIGHT = 1200, 800
NUM_PARTICLES = 4000
FPS = 60

class Sculptor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)
        pygame.display.set_caption("ESCULTOR DE FLUJO INTERACTIVO - EDICIÓN MAGIA")
        self.clock = pygame.time.Clock()
        
        # Partículas: [x, y, vx, vy]
        self.pos = np.random.rand(NUM_PARTICLES, 2) * [WIDTH, HEIGHT]
        self.vel = np.random.randn(NUM_PARTICLES, 2) * 2
        
        self.particle_size = 1
        self.color_mode = 0 # 0: Neon, 1: Fuego, 2: Hielo
        self.hue_base = 0
        self.running = True
        
        # --- NUEVAS VARIABLES PARA EL TRUCO DE MAGIA ---
        self.mouse_pressed_time = 0
        self.hyper_space_active = False

    def get_color(self, dist_to_mouse):
        """Genera colores basados en la distancia al mouse y el modo elegido"""
        self.hue_base += 0.001
        
        if self.hyper_space_active:
            # En hiperespacio se vuelven blancas/brillantes antes de estallar
            return (255, 255, 255)
        
        if self.color_mode == 0: # NEON
            h = (self.hue_base + dist_to_mouse * 0.0005) % 1.0
            s, v = 0.9, 1.0
        elif self.color_mode == 1: # FUEGO
            h = (0.02 + dist_to_mouse * 0.0001) % 1.0
            s, v = 0.9, 1.0
        else: # HIELO
            h = (0.6 + dist_to_mouse * 0.0002) % 1.0
            s, v = 0.7, 1.0
            
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

    def run(self):
        while self.running:
            # 1. CAPA DE RASTRO (Trail effect)
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(18) 
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

            m_pos = np.array(pygame.mouse.get_pos())
            m_pressed = pygame.mouse.get_pressed()

            # 2. EVENTOS
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: self.color_mode = 0
                    if event.key == pygame.K_2: self.color_mode = 1
                    if event.key == pygame.K_3: self.color_mode = 2 # Corregido el error de PIANO_3
                    if event.key == pygame.K_SPACE: self.screen.fill((0,0,0))
                    if event.key == pygame.K_UP: self.particle_size = min(10, self.particle_size + 1)
                    if event.key == pygame.K_DOWN: self.particle_size = max(1, self.particle_size - 1)

            # --- LÓGICA DEL TEMPORIZADOR (Mete el dedo 3 segundos) ---
            if m_pressed[0]: # Si mantienes el dedo puesto
                self.mouse_pressed_time += 1
                # 3 segundos a 60 FPS son 180 vueltas del bucle
                if self.mouse_pressed_time >= 180:
                    self.hyper_space_active = True
            else:
                # Si quitas el dedo, el contador se reinicia
                if self.hyper_space_active:
                    # ¡PUM! EFECTO MAGIA: Desaparece todo y renace en el centro
                    self.screen.fill((0, 0, 0)) # Pantalla negra absoluta
                    pygame.draw.circle(self.screen, (255, 255, 255), (WIDTH // 2, HEIGHT // 2), 6) # Puntito blanco
                    
                    # Reiniciamos todas las partículas al centro exacto
                    self.pos = np.ones((NUM_PARTICLES, 2)) * [WIDTH // 2, HEIGHT // 2]
                    # Salen disparadas en direcciones aleatorias como un Big Bang
                    self.vel = np.random.randn(NUM_PARTICLES, 2) * 5
                    
                    self.hyper_space_active = False
                self.mouse_pressed_time = 0

            # 3. FÍSICA CON NUMPY
            diff = m_pos - self.pos
            dist = np.linalg.norm(diff, axis=1)[:, np.newaxis]
            dist = np.maximum(dist, 1.0) 
            unit_diff = diff / dist
            
            # Interacción con Mouse modificada por el hiperespacio
            if m_pressed[0]: 
                if self.hyper_space_active:
                    force = -unit_diff * 25.0 # ¡FUERZA BRUTAL! Va a explotar
                else:
                    force = -unit_diff * 2.0 # Repeler normal
            else: 
                force = unit_diff * 0.5 # Atraer sutilmente
            
            # Campo de flujo de fondo
            flow_x = np.sin(self.pos[:, 1] * 0.105 + self.hue_base * 10)
            flow_y = np.cos(self.pos[:, 0] * 0.005 + self.hue_base * 10)
            flow_force = np.column_stack((flow_x, flow_y)) * 0.3
            
            # Aplicar todo a la velocidad
            self.vel += force + flow_force
            
            # En hiperespacio la fricción casi no los frena para que se vuelva loco
            if self.hyper_space_active:
                self.vel *= 0.98
            else:
                self.vel *= 0.95 
                
            self.pos += self.vel
            self.pos %= [WIDTH, HEIGHT]

            # 4. DIBUJO DE FIGURAS
            color = self.get_color(np.mean(dist))
            
            for i in range(0, NUM_PARTICLES, 2): 
                p = self.pos[i]
                speed = np.linalg.norm(self.vel[i])
                if speed > 5:
                    pygame.draw.line(self.screen, color, p, p - self.vel[i] * 2, 1)
                else:
                    pygame.draw.circle(self.screen, color, p.astype(int), self.particle_size)

            # Info en pantalla
            font = pygame.font.SysFont("Arial", 14)
            txt = font.render("Manten presionado 3s para HIPERESPACIO y suelta para MAGIA", True, (100, 100, 100))
            self.screen.blit(txt, (20, HEIGHT - 30))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    Sculptor().run()

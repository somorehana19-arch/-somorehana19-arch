import cv2
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
import threading
import time

 # CONFIGURATION & INITIALIZATION
WIDTH, HEIGHT = 1000, 700
NUM_PARTICLES = 1500

lock = threading.Lock()
shared_data = {
    "mode": 1,
    "target_x": 0.0,
    "target_y": 0.0,
    "target_z": -12.0,
    "frame": None,
    "running": True
}

 # SHAPE DATA GENERATION (3D PARTICLES)
pos_space = np.random.uniform(-4.0, 4.0, (NUM_PARTICLES, 3))

pos_planet = np.zeros((NUM_PARTICLES, 3))
NUM_SPHERE = 700
for i in range(NUM_SPHERE):
    phi = np.random.uniform(0, 2 * np.pi)
    costheta = np.random.uniform(-1, 1)
    theta = np.arccos(costheta)
    r = 1.3
    pos_planet[i, 0] = r * np.sin(theta) * np.cos(phi)
    pos_planet[i, 1] = r * np.sin(theta) * np.sin(phi)
    pos_planet[i, 2] = r * np.cos(theta)

for i in range(NUM_SPHERE, NUM_PARTICLES):
    theta = np.random.uniform(0, 2 * np.pi)
    r = np.random.uniform(1.8, 3.8)
    pos_planet[i, 0] = r * np.cos(theta)
    pos_planet[i, 1] = r * np.sin(theta)
    pos_planet[i, 2] = np.random.uniform(-0.05, 0.05)

text_img = np.zeros((200, 800), dtype=np.uint8)
cv2.putText(text_img, "I LOVE YOU", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 3.2, 255, 6, cv2.LINE_AA)
y_indices, x_indices = np.where(text_img > 0)
x_text = (x_indices - 400) / 70.0
y_text = -(y_indices - 100) / 70.0
z_text = np.random.uniform(-0.1, 0.1, len(x_text))
text_points = np.stack((x_text, y_text, z_text), axis=-1)
pos_text = np.zeros((NUM_PARTICLES, 3))
chosen_indices = np.random.choice(len(text_points), NUM_PARTICLES)
pos_text = text_points[chosen_indices]

pos_heart = np.zeros((NUM_PARTICLES, 3))
for i in range(NUM_PARTICLES):
    t = np.random.uniform(-np.pi, np.pi)
    p = np.random.uniform(-np.pi, np.pi)
    x = 2.0 * (np.sin(t) ** 3)
    y = 2.0 * np.cos(t) - 0.7 * np.cos(2*t) - 0.3 * np.cos(4*t) - 0.1 * np.cos(4*t)
    z = np.sin(p) * 0.4
    pos_heart[i, 0] = x * 0.85
    pos_heart[i, 1] = (y * 0.85) + 0.5
    pos_heart[i, 2] = z

current_pos = np.copy(pos_space)
target_pos = np.copy(pos_space)

 # CAMERA & LIGHT/COLOR OBJECT TRACKING
def camera_thread_func():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    
    while shared_data["running"]:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
            
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Track the brightest spot (like a colored card or phone light)
        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(gray)
        
        local_x, local_y, local_z = 0.0, 0.0, -12.0
        
        # If a valid object/light threshold is met, track it
        if maxVal > 200: 
            cx, cy = maxLoc
            cv2.circle(frame, (cx, cy), 15, (0, 255, 0), 2)
            local_x = ((cx / 480.0) - 0.5) * 10.0
            local_y = -((cy / 360.0) - 0.5) * 7.0
            
        with lock:
            shared_data["target_x"] = local_x
            shared_data["target_y"] = local_y
            shared_data["frame"] = frame
            
    cap.release()

camera_thread = threading.Thread(target=camera_thread_func)
camera_thread.daemon = True
camera_thread.start()

 # MAIN THREAD: 3D RENDERING (Pygame)
pygame.init()
pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
pygame.display.set_caption("Object Tracker Simulation")

glMatrixMode(GL_PROJECTION)
glLoadIdentity()
gluPerspective(45, (WIDTH / HEIGHT), 0.1, 50.0)
glMatrixMode(GL_MODELVIEW)
glEnable(GL_DEPTH_TEST)

clock = pygame.time.Clock()
rotation_angle = 0.0
current_mode = 1
hand_x, hand_y, hand_z = 0.0, 0.0, -12.0

while shared_data["running"]:
    pygame.event.pump()
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
            shared_data["running"] = False
        if event.type == KEYDOWN:
            if event.key == K_1: current_mode = 1
            if event.key == K_2: current_mode = 2
            if event.key == K_3: current_mode = 3
            if event.key == K_4: current_mode = 4
                
    with lock:
        target_hand_x = shared_data["target_x"]
        target_hand_y = shared_data["target_y"]
        frame = shared_data["frame"]
        
    if frame is not None:
        cv2.putText(frame, "Hold up a bright item/light to move particles!", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.imshow("Tracking Window", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            shared_data["running"] = False

    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    hand_x += (target_hand_x - hand_x) * 0.1
    hand_y += (target_hand_y - hand_y) * 0.1
    
    if current_mode == 1:
        target_pos = pos_space
        rotation_angle += 0.5
    elif current_mode == 2:
        target_pos = pos_planet
        rotation_angle += 1.5
    elif current_mode == 3:
        target_pos = pos_text
        rotation_angle = 0.0
    elif current_mode == 4:
        target_pos = pos_heart
        rotation_angle += 1.2
        
    current_pos += (target_pos - current_pos) * 0.15
    
    glTranslate(hand_x, hand_y, hand_z)
    if current_mode == 2:
        glRotate(25, 1.0, 0.0, 0.5)
    glRotate(rotation_angle, 0.0, 1.0, 0.0)
    
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glPointSize(4.0)
    
    glBegin(GL_POINTS)
    for i in range(NUM_PARTICLES):
        if current_mode == 3: glColor4f(0.0, 0.8, 1.0, 0.9)
        elif current_mode == 4: glColor4f(1.0, 0.1, 0.4, 0.95)
        elif current_mode == 2 and i < NUM_SPHERE: glColor4f(1.0, 0.7, 0.3, 0.6)
        elif current_mode == 2 and i >= NUM_SPHERE: glColor4f(1.0, 0.5, 0.0, 0.85)
        else: glColor4f(0.1, 0.5, 1.0, 0.8)
        glVertex3f(current_pos[i, 0], current_pos[i, 1], current_pos[i, 2])
    glEnd()
    
    pygame.display.flip()
    clock.tick(60)

cv2.destroyAllWindows()
pygame.quit()
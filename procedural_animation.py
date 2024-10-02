import numpy as np
import pygame
import random


WIDTH, HEIGHT = 800,800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Procedural Animation')

FPS=120

def angle(pos1, pos2):
    diff = (pos2[0] - pos1[0], pos2[1] - pos1[1])
    return np.rad2deg(np.arctan2(diff[1],diff[0]))

def distance(pos1,pos2):
    return np.sqrt(abs(np.power(pos1[0] - pos2[0],2) + np.power(pos1[1] - pos2[1],2)))

def addVector(v1,v2):
    return (v1[0]+v2[0], v1[1]+v2[1])

def subVector(v1,v2):
    return (v1[0]-v2[0], v1[1]-v2[1])

def multVector(v, value):
    return (v[0]*value, v[1]*value)

def averageVector(v1,v2):
    return ((v1[0]+v2[0])/2,(v1[1]+v2[1])/2)

def setMagnitude(v1, mag):
    oldMag = np.sqrt(v1[0]*v1[0] + v1[1]*v1[1])	
    v1 = (v1[0]*mag/oldMag, v1[1]*mag/oldMag)
    return v1

def lerp(a,b,t):
    return a + (b-a) * t

def lerp2d(v1,v2,t):
    return (lerp(v1[0],v2[0],t), lerp(v1[1],v2[1],t))

def rotateTo(anchorPoint, localLength, deg):
    deg = np.deg2rad(deg)
    offsetX = np.cos(deg) * localLength
    offsetY = np.sin(deg) * localLength
    NewPos = (anchorPoint[0] + offsetX, anchorPoint[1] + offsetY)
    return NewPos

def rotate(anchorPoint, point, localLength, degOffset):
    angleOff = angle(point,anchorPoint) + degOffset
    return rotateTo(anchorPoint, localLength, angleOff)

def isOutOfBounds(pos, bounds):
    return pos[0] > bounds[0] or pos[0] < 0 or pos[1] > bounds[1] or pos[1] < 0

class anchor():
    
    def __init__(self, pos, color, radius, distance, nextAnchor = None):
        self.nextAnchor = nextAnchor
        self.pos = pos
        self.color = color
        self.distance = distance
        self.radius = radius
        self.angle = 0
        self.speed = 3
        self.drawPoints = []
        
    def update(self):
        if self.nextAnchor:
            vec_next = subVector(self.nextAnchor.pos, self.pos)
            vec_next = setMagnitude(vec_next, self.distance)
            
            self.nextAnchor.setPos(addVector(self.pos, vec_next))
            self.drawPoints = [rotate(self.pos, self.nextAnchor.pos, self.radius, 90), rotate(self.pos, self.nextAnchor.pos, self.radius, -90)]
    
    def setPos(self, newPos):
        self.pos = newPos

    def draw(self):
        pygame.draw.circle(WIN, self.color, self.pos, self.radius, 3)
        if self.nextAnchor:
            pygame.draw.circle(WIN, (200,40,40), self.drawPoints[0], 3)
            pygame.draw.circle(WIN, (200,40,40), self.drawPoints[1], 3)
    
    def getHead(self):
        points = [
            rotate(self.pos, self.nextAnchor.pos, self.radius, -90),
            rotate(self.pos, self.nextAnchor.pos, self.radius+3, -55),
            rotate(self.pos, self.nextAnchor.pos, self.radius+10, -25),
            rotate(self.pos, self.nextAnchor.pos, self.radius+11, 0),
            rotate(self.pos, self.nextAnchor.pos, self.radius+10, 25),
            rotate(self.pos, self.nextAnchor.pos, self.radius+3, 55),
            rotate(self.pos, self.nextAnchor.pos, self.radius, 90)
                  ]
        return points
    
    def randomWalk(self):
        step = subVector(rotateTo(self.pos, self.speed, self.angle), self.pos)
        self.pos = addVector(self.pos, step)
        
        if not isOutOfBounds(addVector(self.pos, multVector(step, 15)), (WIDTH, HEIGHT)): 
            self.angle += random.randint(-7, 7)
            self.angle = self.angle%360
        else:
            a = angle(self.pos, (400,400)) - self.angle
            self.angle += a/5
        
        neckAngle = angle(self.nextAnchor.pos, self.pos)%360
        self.angle = np.clip(self.angle, neckAngle-50, neckAngle+50)
        
cont = 0

clock = pygame.time.Clock()
pygame.mouse.set_visible(False)

instances = []

body_thickness = [30, 34, 25, 18, 27, 32, 34, 31, 25, 15, 9, 5, 5, 5, 5][::-1]

total_length = 350

resolution = 20


for i in range(resolution):
    
    bt_index = (i/resolution)*(len(body_thickness)-1)
    bt_index_round = int(round((i/resolution)*(len(body_thickness)-1)))
    
    closest_bt = body_thickness[bt_index_round]
    
    bt_index_error = bt_index - bt_index_round
    
    second_closest_bt = body_thickness[int(bt_index_round + np.sign(bt_index_error))]
    
    body_thickness_interpolated = lerp(closest_bt, second_closest_bt, np.abs(bt_index_error))
    
    if i > 0:
        instances.append(anchor((400+i,400+i), (255,255,255), body_thickness_interpolated, total_length/resolution, instances[i-1]))
    else:
        instances.append(anchor((400,400), (255,255,255), body_thickness_interpolated, total_length/resolution))

instances[0].nextAnchor = instances[1]
        
run = True

selected_anchor = None
dragging = False
random_walk = True

while run:
    clock.tick(120)
    cont = cont+1%360
    mousePos = pygame.mouse.get_pos()
    

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            pygame.mouse.set_visible(True)
            run = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pressed = pygame.mouse.get_pressed()
            mouse_pos = pygame.mouse.get_pos()

            if mouse_pressed[0]:
                distances = list(map(lambda i: distance(mouse_pos, i.pos), instances))
                closest = distances.index(min(distances))
                if distances[closest] < 20:
                    dragging = True
                    selected_anchor = closest
            if mouse_pressed[2]:
                random_walk = not random_walk
        elif event.type == pygame.MOUSEBUTTONUP:
            mouse_pressed = pygame.mouse.get_pressed()

            if not mouse_pressed[0]:
                dragging = False

    WIN.fill((10,10,30))
    
    if dragging:
        instances[selected_anchor].setPos(pygame.mouse.get_pos())
    elif random_walk:
        instances[-1].randomWalk()
    
    for i in instances[::-1]:
        i.update()

    for i in instances:
        i.draw()


    #pygame.draw.polygon(WIN, (100,100,200), list(map(lambda x: x.drawPoints[0], instances)) + instances[-1].getHead() + list(map(lambda x: x.drawPoints[1], instances))[::-1]) 

    
    pygame.draw.circle(WIN, (200,40,40), pygame.mouse.get_pos(), 2)
    #draw


    pygame.display.update()

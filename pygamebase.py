import numpy as np
import pygame

WIDTH, HEIGHT = 800,800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('game')

FPS=120

def angle(pos1, pos2):
	diff = (pos2[0] - pos1[0], pos2[1] - pos1[1])
	return np.rad2deg(np.arctan2(diff[1],diff[0]))

def distance(pos1,pos2):
	return np.sqrt(abs(np.power(pos1[0] - pos2[0],2) + np.power(pos1[1] - pos2[1],2)))

def addVector(v1,v2):
	return (v1[0]+v2[0], v1[1]+v2[1])

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

def rotateTo(anchorPoint, point, localLength, deg):
	deg = np.deg2rad(deg)
	offsetX = np.cos(deg) * localLength
	offsetY = np.sin(deg) * localLength
	NewPos = (anchorPoint[0] + offsetX, anchorPoint[1] + offsetY)
	return NewPos

def rotate(anchorPoint, point, localLength, degOffset):
	angleOff = angle(point,anchorPoint) + degOffset
	return rotateTo(anchorPoint, point, localLength, angleOff)

class obj():
	
	def __init__(self):
		pass
	
	def update(self):
		pass

cont = 0

clock = pygame.time.Clock()
pygame.mouse.set_visible(False)

run = True
while run:
	clock.tick(120)
	cont = cont+1%360
	mousePos = pygame.mouse.get_pos()

	for event in pygame.event.get():

		if event.type == pygame.QUIT:
			pygame.mouse.set_visible(True)
			run = False
		elif event.type == pygame.MOUSEBUTTONDOWN:
			pass

	WIN.fill((255,255,255))


	#draw


	pygame.display.update()

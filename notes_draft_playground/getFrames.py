import io
import sys
import os
import numpy as np
import cv2 #need to install: sudo apt-get install python-opencv
from PIL import Image #need to install: pip install pillow
import imagehash #need to install: sudo pip install imagehash
import os


videoFile='/home/ubuntu/playground/Superman_s_True_Power-yWyj9ORkj8w.mp4'
def getFrames(videoFile):
    vidcap = cv2.VideoCapture(videoFile)
    success,image = vidcap.read()
    frameNum = 0
    success = True
    while success:
        success,image = vidcap.read()
        frameNum=vidcap.get(1) #gets the frame number
        if ((frameNum % 5)==0):
			cv2.imwrite("/home/ubuntu/playground/frame%d.jpg" % frameNum, image)     # save frame as JPEG file. This keeps printing "True for some reason"
        	hashValue=imagehash.phash(Image.fromarray(image)) #used to be Image.read, wasn't working. http://stackoverflow.com/questions/22906394/numpy-ndarray-object-has-no-attribute-read
        	#print("hashValue: ", hashValue, " frameNum: ", frameNum)
    return videoFile

getFrames(videoFile)



########## older stuff below #############

#hasing according to https://pypi.python.org/pypi/ImageHash
import cv2
vidcap = cv2.VideoCapture('/home/ubuntu/playground/Superman_s_True_Power-yWyj9ORkj8w.mp4')
success,image = vidcap.read()
frameNum = 0
success = True
while success:
	success,image = vidcap.read()
	frameNum=vidcap.get(1) #gets the frame number
	print 'Read a new frame: ',frameNum, success
	if ((frameNum % 5) ==0):
		cv2.imwrite("/home/ubuntu/playground/frame%d.jpg" % frameNum, image)     # save frame as JPEG file. This keeps printing "True for some reason"
  #if cv2.waitKey(10) == 27:                     # exit if Escape is hit
  #	break


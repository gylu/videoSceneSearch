import io
import sys
import os
import numpy as np
import cv2 #need to install: sudo apt-get install python-opencv
from PIL import Image #need to install: pip install pillow
import os
import math

#videoFile='/home/ubuntu/playground/Superman_s_True_Power-yWyj9ORkj8w.mp4'

#videoFile="/home/ubuntu/playground/fix/videos_fix/JOHN_WICK_Trailer_Keanu_Reeves_-_Action_Movie_-_2014-kuQo4xHqCww.mp4"

videoFolder="/Users/gyl/Desktop/insight_projects/godzillaFrames"

#bin sizing. This is the number bins the histogram values are broken into. E.g. hue, which has a value from 0 to 180, would be broken in 8 bins
#http://stackoverflow.com/questions/24725224/how-to-choose-the-number-of-bins-when-creating-hsv-histogram
bins = [4, 8, 3]

videoFile="/Users/gyl/Desktop/insight_projects/youtubeDLtest/godzilla.mp4"
videoFile="/Users/gyl/Desktop/insight_projects/test_image_proc/Superman_s_True_Power-yWyj9ORkj8w.mp4"
def getFrames(videoFile):
    vidcap = cv2.VideoCapture(videoFile)
    success,image = vidcap.read()
    frameNum = 0
    myVects=[]
    while success:
        frameNum=vidcap.get(1) #gets the frame number
        frameTime=vidcap.get(0)/1000 #gets the frame time, in seconds
        if ((int(frameNum) % 5)==0):
            hsv = cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1, 2], None, bins, [0, 180, 0, 256, 0, 256])
            hist = cv2.normalize(hist).flatten()
            myVects.append(hist)
            #print(hist)
            #print(frameNum)
        success,image = vidcap.read()
    return myVects


results=getFrames(videoFile)

mypic="/Users/gyl/Desktop/insight_projects/test_image_proc/superman_frames5370.jpg"
mypic="/Users/gyl/Desktop/insight_projects/test_image_proc/superman_frame5370png.png"
image=cv2.imread(mypic)
hsv2 = cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, bins, [0, 180, 0, 256, 0, 256])
hist2 = cv2.normalize(hist2).flatten()

def cosine_similarity(v1,v2):
    "compute cosine similarity of v1 to v2: (v1 dot v2)/{||v1||*||v2||)"
    sumxx, sumxy, sumyy = 0, 0, 0
    for i in range(len(v1)):
        x = v1[i]; y = v2[i]
        sumxx += x*x
        sumyy += y*y
        sumxy += x*y
    return sumxy/math.sqrt(sumxx*sumyy)

a=[]
for vect in results:
    a.append(cosine_similarity(vect,hist2))
indicies_of_most_similar=sorted(range(len(a)), key=lambda i: a[i])[-5:]

#results of running this in python shell:
#using a frame screen show of a shrinked and .png version o my frame, it was still able to return the closest result
#mypic="/Users/gyl/Desktop/insight_projects/test_image_proc/superman_frame5370png.png"
#using bins = [4,8,3] #using these bins seemed to perform better
#>>> indicies_of_most_similar
#[531, 530, 528, 529, 1073]
#note that index 1073 is my frame 5365 (since i only get the 5th frames). in this index, 1073 is the highest liklihood

#using bins = [8, 4, 3]
# >>> indicies_of_most_similar=sorted(range(len(a)), key=lambda i: a[i])[-5:]
# >>> indicies_of_most_similar
# [676, 677, 678, 1007, 1113]
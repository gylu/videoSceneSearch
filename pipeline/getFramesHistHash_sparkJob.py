from pyspark import SparkContext
from pyspark import SparkConf
from pyspark import StorageLevel
import pyspark_cassandra
import time
import os

import io #question: it seems like none of these would work if I imported them in a different function?
import sys
import os
import numpy as np
import cv2 #need to install: sudo apt-get install python-opencv
from PIL import Image #need to install: pip install pillow
import imagehash #need to install: sudo pip install imagehash
import pyspark_cassandra
import math
import pickle

conf = SparkConf().setAppName("getFramesHist")
sc = SparkContext(conf=conf)
#keyspace="vss"
keyspace="vss_hist"



S3_BUCKET="videoscenesearch"
S3_FOLDER="videos_orig/" #as of 10/18/2016, videos_orig has 10.12GB of videos
videoLocation = "s3a://%s/%s" % (S3_BUCKET, S3_FOLDER)

rdd=sc.binaryFiles(videoLocation) #question, what's the difference between this and binaryFiles? #Note very wierd bug, when changed to take(5), sc.wholeTextFiles stopped working
rdd=rdd.repartition(36)

#bin sizing. This is the number bins the histogram values are broken into. E.g. hue, which has a value from 0 to 180, would be broken in 8 bins
#http://stackoverflow.com/questions/24725224/how-to-choose-the-number-of-bins-when-creating-hsv-histogram
histogram_bins = [4, 8, 3]

def getFrames(inputFile):
    videoFilePath=inputFile[0] #sc.wholeTextFiles and sc.binaryFiles have key value pair, with key being name, value being the content
    videoNameOnly = videoFilePath.rsplit('/', 1)[-1] #Split get name part after the last slash
    #videoNameOnly=videonNameOnly.rsplit('.')[0] #Split for part before .mp4
    print("videoNameOnly: ",videoNameOnly)
    ### Note to self: seem to need to do the following to write it back to itself ###    
    videoContent=inputFile[1]
    with open(videoNameOnly, 'wb') as wfile:
        wfile.write(videoContent)
    vidcap = cv2.VideoCapture(videoNameOnly)
    success,image = vidcap.read()
    frameNum = 0
    tempList=[]
    while success:
        frameNum=vidcap.get(1) #gets the frame number
        frameTime=vidcap.get(0)/1000 #gets the frame time, in seconds
        if ((frameNum % 5)==0): #gets every 5th frame
            hashValue=imagehash.phash(Image.fromarray(image)) #Note: Image.read wasn't working, so instead using Image.fromarray. http://stackoverflow.com/questions/22906394/numpy-ndarray-object-has-no-attribute-read
            hashValueStr=str(hashValue) 
            youtubeLink='www.youtube.com/watch?v='+videoNameOnly.split('.mp4')[0][-11:] #videoNameOnly.split('-')[-1].split('.mp4')[0] #videoId=str.split('-')[-1].split('.mp4')[0]
            hsvImg = cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsvImg], [0, 1, 2], None, histogram_bins, [0, 180, 0, 256, 0, 256])
            histflat = cv2.normalize(hist).flatten()           
            histstring=pickle.dumps(histflat)
            outputDict={"hashvalue": hashValueStr, "framenumber": frameNum, "videoname": videoNameOnly, "frametime":frameTime, "youtubelink":youtubeLink, "histogramvector":histstring}
            tempList.append(outputDict)
            #print(outputDict)
        success,image = vidcap.read()
    return tempList


def main():
    output=rdd.flatMap(getFrames).saveToCassandra(keyspace,"vname")

if __name__ == '__main__':
    main()


""""
$SPARK_HOME/bin/spark-submit \
--master spark://ip-172-31-0-173:7077 \
--executor-memory 12000M \
--driver-memory 12000M \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/getFramesHistHash_sparkJob.py

#questions: kept getting this issue: WARN TaskSchedulerImpl: Initial job has not accepted any resources; check your cluster UI to ensure that workers are registered and have sufficient resources

$SPARK_HOME/bin/spark-submit \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/getFramesHistHash_sparkJob.py

#for starting a distributed pyspark shell
$SPARK_HOME/bin/pyspark \
--master spark://ip-172-31-0-173:7077 \
--executor-memory 12000M \
--driver-memory 12000M \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12

#for starting a local shell
$SPARK_HOME/bin/pyspark \
--executor-memory 12000M \
--driver-memory 12000M \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12
"""

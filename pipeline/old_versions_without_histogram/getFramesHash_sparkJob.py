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

conf = SparkConf().setAppName("getFramesHash")
sc = SparkContext(conf=conf)
#keyspace="vss"
keyspace="vss_large"

#logFile = "YOUR_SPARK_HOME/README.md"  # Should be some file on your system #Question, what the hell is this
#logData = sc.textFile(logFile).cache()

#rdd=sc.textFile("/home/ubuntu/playground/Superman_s_True_Power-yWyj9ORkj8w.mp4")
#rdd=sc.textFile("/Users/gyl/Desktop/insight_projects/test_image_proc/Superman_s_True_Power-yWyj9ORkj8w.mp4")
#hdfsVideoLocation="hdfs://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9000/videos"

#videoFilePath="/home/ubuntu/playground/fix/videos_fix/JOHN_WICK_Trailer_Keanu_Reeves_-_Action_Movie_-_2014-kuQo4xHqCww.mp4"


AWS_ACCESS_KEY_ID=os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY=os.environ['AWS_SECRET_ACCESS_KEY']
AWS_DEFAULT_REGION=os.environ['AWS_DEFAULT_REGION']
S3_BUCKET="videoscenesearch"
S3_FOLDER="videos/"


#videoLocation="hdfs://ec2-52-11-6-165.us-west-2.compute.amazonaws.com:9000/videos"
#public_dns = os.environ["PUBLIC_DNS"]
#videoLocation="hdfs://{}:9000/videos_orig".format(public_dns)
#videoLocation="hdfs://{}:9000/videos_long".format(public_dns)
#videoLocation = "s3a://%s:%s@%s/%s" % (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET, S3_FOLDER) #No need to do this. Also don't do this, because on public DNS spark UI, it'll appear
S3_BUCKET="videoscenesearch"
S3_FOLDER="videos/"
S3_FOLDER="videos_orig/"
videoLocation = "s3a://%s/%s" % (S3_BUCKET, S3_FOLDER)


rdd=sc.binaryFiles(videoLocation) #question, what's the difference between this and binaryFiles? #Note very wierd bug, when changed to take(5), sc.wholeTextFiles stopped working
rdd=rdd.repartition(36)


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
        if ((frameNum % 5)==0):
            #cv2.imwrite("/home/ubuntu/playground/fix/images/jwick_frame%d.jpg" % frameNum, image)     # save frame as JPEG file. This keeps printing "True for some reason"
            #cv2.imwrite("/home/ubuntu/playground/vid_%s_frame%d.jpg" % (videoNameOnly, frameNum), image)     # save frame as JPEG file. This keeps printing "True for some reason"
            #cv2.imwrite("hdfs://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9000/frames/vid_%s_frame%d.jpg" % (videoNameOnly, frameNum), image)     #Todo: this still isn't working
            hashValue=imagehash.phash(Image.fromarray(image)) #Note: Image.read wasn't working, so instead using Image.fromarray. http://stackoverflow.com/questions/22906394/numpy-ndarray-object-has-no-attribute-read
            hashValueStr=str(hashValue)
            # hashValueInt=int(hashValueStr,16)
            # s1=bin(hashValueInt)
            # s2=bin(int('aaaaaaaaaaaaaaaa',16))
            # hammingDistBetweenHexA=sum(c1 != c2 for c1, c2 in zip(s1, s2))
            # partitionby=bin(hashValueInt).count("1")
            #stringToOutput="videoName: %s, hashValue: %s, frameNumber: %d" % (videoNameOnly, hashValueStr, frameNum)
            #outputDict={"partitionby":hammingDistBetweenHexA, "hashvalue": hashValueStr, "framenumber": frameNum, "videoname": videoNameOnly, "frametime":frameTime, "youtubelink":youtubeLink}
            youtubeLink='www.youtube.com/watch?v='+videoNameOnly.split('.mp4')[0][-11:] #videoNameOnly.split('-')[-1].split('.mp4')[0] #videoId=str.split('-')[-1].split('.mp4')[0]
            outputDict={"hashvalue": hashValueStr, "framenumber": frameNum, "videoname": videoNameOnly, "frametime":frameTime, "youtubelink":youtubeLink}
            tempList.append(outputDict)
            print(outputDict)
        success,image = vidcap.read()
    #print(tempList)
    return tempList

#Note that when this take is higher than 1, it breaks, and then the top needs to be reset to sc.binaryFiles 
#Note, for it to work when it's higher than one, it needs to be sc.binaryFiles AND the re-write "with open(videoNameOnly, 'wb') as wfile:" needs to be uncommented
#sc.wholeTextFiles with a wfile uncommented with take higher than 1 doesn't work
#sc.wholeTextFiles with a wfile commented with take higher than 1 doesn't work
#sc.textFile doesn't work at all
#Then after it brakes, going back to sc.wholeTextFiles doesn't work, even with take 1
#rdd.flatMap(getFrames).take(1)
#rdd.flatMap(getFrames).saveAsTextFile("hdfs://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9000/outputExample.txt")
#rdd.flatMap(getFrames).saveToCassandra("vss","hval") #what worked the first time
#output=rdd.flatMap(getFrames).collect()
output=rdd.flatMap(getFrames).saveToCassandra(keyspace,"vname")
#output=rdd.flatMap(getFrames).persist(StorageLevel.MEMORY_ONLY)
#output.saveToCassandra("vss","hval") #thehval table sucks because bad prefix
#output.saveToCassandra("vss","vname2") #can't do .saveToCassandra().saveToCassandra() results in AttributeError: 'NoneType' object has no attribute 'saveToCassandra'
#question: got this error: WARN QueuedThreadPool: 1 threads could not be stopped

#for some reason, if i use flatmap, take(4) only does take(1)?

#Note, spark should be running on the service, and then you can submit with this:
#Note that you need to use the private IP, and also use port 7077

""""
$SPARK_HOME/bin/spark-submit \
--master spark://ip-172-31-0-173:7077 \
--executor-memory 12000M \
--driver-memory 12000M \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/getFramesHash_sparkJob.py

#questions: kept getting this issue: WARN TaskSchedulerImpl: Initial job has not accepted any resources; check your cluster UI to ensure that workers are registered and have sufficient resources

$SPARK_HOME/bin/spark-submit \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/getFramesHash_sparkJob.py

$SPARK_HOME/bin/pyspark \
--master spark://ip-172-31-0-173:7077 \
--executor-memory 12000M \
--driver-memory 12000M \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12

$SPARK_HOME/bin/pyspark \
--executor-memory 12000M \
--driver-memory 12000M \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12
"""

# #### Question - This doesn't seem to work, because the RDD forgets it...? ####
# def importStuff (x):
#     import io
#     import sys
#     import os
#     import numpy as np
#     import cv2 #need to install: sudo apt-get install python-opencv
#     from PIL import Image #need to install: pip install pillow
#     import imagehash #need to install: sudo pip install imagehash
#     import os
#     return x

# rdd.map(importStuff).take(1)
# #### Question - The above doesn't seem to work, because the RDD forgets it...? /####


#For testing function in a nonMR way. For local testing only. 
#videoFile='/home/ubuntu/playground/Superman_s_True_Power-yWyj9ORkj8w.mp4'
#getFrames(videoFile)


##### Testing how map reduce works  #####
#The following test function works
#def myTestFunc(x):
#    x=x+100
#    return x
#
#rdd_forTestFunc=sc.parallelize([1,2,3,4,10,50])
#rdd2_forTestFunc=rdd_forTestFunc.map(myTestFunc)
#rdd2_forTestFunc.take(6)
##### Testing how map reduce works / #####



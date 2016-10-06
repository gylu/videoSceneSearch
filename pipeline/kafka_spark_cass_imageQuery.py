#from __future__ import print_function
"""
The plan:
1. Read RDD from cassandra
2. Search for top 3 matches closest to target image
3. Pull entire video that each match belongs to
4. Calculate distance on each frame on the video
5. Plot distance vs time
6. Push plots to client

Questions:
Do I query cassandra through CQL?
Do I query cassandra through python?
Or do I get spark to read the cassandra as an RDD first, and then query through spark?

how do i access one rdd from another?
how do i push the data back to flask, back to the client end?
what's up with the casandra errors when I start this guy?
"""



"""
Takes requests from kafka, runs spark streaming processing query to get results, then pushes results to cassandra
Usage: kafka_spark_cass_imageQuery.py <zk> <kafka topic> <more kafka topic if exist>
"""


from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from pyspark_cassandra import streaming
import pyspark_cassandra, sys
from pyspark_cassandra import CassandraSparkContext, Row
import json

from pyspark import StorageLevel

from pyspark.sql.functions import sum
from pyspark.sql.types import *
from pyspark.sql import Window
from pyspark.sql import SQLContext 
from pyspark.sql import functions


##my stuff
from pyspark import SparkConf
import time

import io
import os

import numpy as np
from PIL import Image
import imagehash

import pdb
from kafka import KafkaProducer
import time
##
db_table=0 #global rdd
producer = KafkaProducer(bootstrap_servers = 'ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092', value_serializer=lambda v: json.dumps(v).encode('ascii'))
# Kafka and Spark Streaming specific vars
batch_interval = 5 #question, why is batch interval of 5 so much better than 3? 3 seemed like needed to wait a long time
sc = CassandraSparkContext(appName="PythonStreamingVSS") #http://www.slideshare.net/JonHaddad/intro-to-py-spark-and-cassandra
ssc = StreamingContext(sc, batch_interval)


"""
Example usages:
db_table.select("hashvalue", "partitionby","videoname").map(lambda x: x['hashvalue']).take(3)
will resule in
[u'6daab6a32cb6b209', u'77a888d7aa2f882b', u'571d23371cc358d5']
"""

def main():
    global db_table;
    global producer;
    if len(sys.argv) != 3:
        #print("Usage: thisfile.py <zk> <topic>", file=sys.stderr) #i get an error about file=sys.stderr for some reason
        print("Usage: thisfile.py <zk> <topic>")
        exit(-1)


    #ssc.checkpoint("hdfs://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9000/imgSrchRqstCkpts")


    #example of what can be done
    #db_table=sc.cassandraTable("vss","vname") #doesn't work
    db_table=sc.cassandraTable("vss","vname").select("hashvalue","youtubelink","videoname",'framenumber','frametime').persist(StorageLevel.MEMORY_ONLY)

    zkQuorum, myTopic = sys.argv[1:]
    # Specify all the nodes you are running Kafka on
    kafkaBrokers = {"metadata.broker.list": "52.33.155.170:9092,54.69.1.84:9092,52.41.224.1:9092"}
    streamFromKafka = KafkaUtils.createDirectStream(ssc, [myTopic], kafkaBrokers)
    
    print("hi")
    print("stream fm kafka:", streamFromKafka)

    #streamFromKafka.transform(lambda rdd: rdd.map(lambda x: (1,x[1])).join(db_table.map(lambda x: (1,x)))).map(addDistanceInfo).foreachRDD(takeTop) #to do , need to debug this function, this is the original one causing a lot of issues as of 2am on oct 5, 2016
    #streamFromKafka.foreachRDD(lambda rdd: rdd.map(lambda x: (1,x[1])).join(db_table.map(lambda x: (1,x))).map(addDistanceInfo)) #broken
    streamFromKafka.foreachRDD(doEverything) #wi think this works similar to the line above, but still super slow, maybe slightly faster than the other one

    producer.send('searchReturns',"Hello, producer is working. Time is: " + str(time.time()))
    print("here")
    ssc.start()
    ssc.awaitTermination()


def doEverything(rdd):
    taken=rdd.take(1)
    print("take 1 off: ",taken)
    if taken!=[]:
        starttime=time.time()
        print("taken 1 of rdd inside loop: ",taken)
        print("=====here0, just inside if stmt: ",time.time()-starttime)
        temp=rdd.map(lambda x: (1,x[1])).join(db_table.map(lambda x: (1,x))).map(addDistanceInfo).cache() #this works, but is still super slow
        #temp=db_table.map(lambda x: (1,x)).join(rdd.map(lambda x: (1,x[1]))).map(addDistanceInfo).cache() #uhhh, this breaks
        print("=====here1, after map: ",time.time()-starttime)
        nothing=temp.take(3)
        print("=====here2, after take(): ",time.time()-starttime)
        framesfound=temp.takeOrdered(3,key=lambda x: (x['distance']))
        print("=====here3 after takeOrdered(): ", time.time()-starttime)
        producer.send('searchReturns',framesfound)
        print("=====here4, after send to kafka: ", time.time()-starttime)
        sc.parallelize(framesfound).saveToCassandra("vss","queryresults")
        print("=====here5, after 1st db write: ", time.time()-starttime)
        uniqueNames=set(item['videoname'] for item in framesfound)
        temp.filter(lambda x: (x['videoname'] in uniqueNames)).saveToCassandra("vss","distances")
        print("=====here6, after 2nd db write: ", time.time()-starttime)


#example of framesfound:
#[{'youtubelink': 'www.youtube.com/watch?v=gHWjwGRlrNo', 'targetimagehash': '5919a6e6791986e6', 'frametime': 46.08770751953125, 'framehash': '5959a6a6795986a6', 'distance': 4, 'videoname': 'MISSION_IMPOSSIBLE_5_Rogue_Nation_Trailer-gHWjwGRlrNo.mp4', 'framenumber': 1105, 'imagename': 'Screen_Shot_2016-09-28_at_9.47.49_PM.png'}, {'youtubelink': 'www.youtube.com/watch?v=gHWjwGRlrNo', 'targetimagehash': '5919a6e6791986e6', 'frametime': 46.504791259765625, 'framehash': '5959a6a65959a6a6', 'distance': 6, 'videoname': 'MISSION_IMPOSSIBLE_5_Rogue_Nation_Trailer-gHWjwGRlrNo.mp4', 'framenumber': 1115, 'imagename': 'Screen_Shot_2016-09-28_at_9.47.49_PM.png'}, {'youtubelink': 'www.youtube.com/watch?v=gHWjwGRlrNo', 'targetimagehash': '5919a6e6791986e6', 'frametime': 58.6002082824707, 'framehash': '1999e6e619398ec6', 'distance': 8, 'videoname': 'MISSION_IMPOSSIBLE_5_Rogue_Nation_Trailer-gHWjwGRlrNo.mp4', 'framenumber': 1405, 'imagename': 'Screen_Shot_2016-09-28_at_9.47.49_PM.png'}]
#[{"distance": 16, "framenumber": 250, "videoname": "Bunraku_Trailer_HD-jVabHVw4dMc.mp4", "framehash": "8725ec7a7ada1a82", "youtubelink": "www.youtube.com/watch?v=jVabHVw4dMc", "frametime": 10.0, "imagename": "Screen_Shot_2016-09-30_at_3.24.47_AM.png", "targetimagehash": "8568787a787a3a5a"}, {"distance": 16, "framenumber": 1375, "videoname": "New_World_Movie_Clip_RED_BAND-axRTL8yvXtI.mp4", "framehash": "8585f27a78585ad6", "youtubelink": "www.youtube.com/watch?v=axRTL8yvXtI", "frametime": 57.34895706176758, "imagename": "Screen_Shot_2016-09-30_at_3.24.47_AM.png", "targetimagehash": "8568787a787a3a5a"}, {"distance": 16, "framenumber": 3085, "videoname": "FAST_and_FURIOUS_7_Official_Trailer-KBhXp1gqZRo.mp4", "framehash": "9783407c78f83ada", "youtubelink": "www.youtube.com/watch?v=KBhXp1gqZRo", "frametime": 128.6702117919922, "imagename": "Screen_Shot_2016-09-30_at_3.24.47_AM.png", "targetimagehash": "8568787a787a3a5a"}]
def takeTop(rdd):
    global producer;
    framesfound= rdd.takeOrdered(3,key=lambda x: (x['distance'])) #this is a python list, can't save this to cassandra #making this a take(3) doens't do any better either, so the issue isn't in the takeOrdered
    framesfound=framesfound[:3] #this is to only get 3, even if there are ties
    uniqueNames=set(item['videoname'] for item in framesfound)
    print("stream job, frames found:", framesfound)
    print("stream job, output out take top:", uniqueNames)
    #rdd.map(lambda x: set(x['videoname']))
    producer.send('searchReturns',framesfound)
    sc.parallelize(framesfound).saveToCassandra("vss","queryresults") #this doesn't seem to be the bottle neck, as soon as prints happen, I get the frames
    #distancesOfCloseVids=rdd.filter(lambda x: (x['videoname'] in uniqueNames)).collect()
    #sc.parallelize(distancesOfCloseVids).saveToCassandra("vss","distances")
    rdd.filter(lambda x: (x['videoname'] in uniqueNames)).saveToCassandra("vss","distances") #this does not seem to be the bottleneck, as soon as prints happen, i get the frames
    #return framesfound #uncommenting this breaks the hell out of it, that's because foreach rdd isn't supposed to return anything



def addDistanceInfo(x):
    #x is of the form (1, ({dict in string format},row()) )
    print("in stream job, add distance info")
    targetImageDict=json.loads(x[1][0]) #Need to have json.loads. Because print(x[1][0][0]) returns just the { char as a string. #this is the dictionary from the kafka topic 
    #returns {"imgName": "Kafka.jpeg", "hash": "f1b9094e06b13dce", "time": 1475035317.596829}
    rowFromDatabase=x[1][1] #this is the row item
    distance=calcDistStr(targetImageDict['hash'],rowFromDatabase['hashvalue']) #this does not seem to be the bottleneck, still took long time when I made this constant
    result={'distance':distance,'youtubelink':rowFromDatabase['youtubelink'], 'imagename':targetImageDict['imgName'], "targetimagehash":targetImageDict['hash'], 'framehash':rowFromDatabase['hashvalue'] ,"videoname":rowFromDatabase['videoname'], "frametime":rowFromDatabase['frametime'], "framenumber":rowFromDatabase['framenumber']}
    #print("stream job, add distance info in stream: ", result) #won't work, break
    #producer.send('searchReturns',"hi") #won't work, breaks
    return result



def calcDistStr (targetHashStr, databaseRowHashStr):
    targetHashInt=int(targetHashStr,16)
    targetHashBinStr=format(targetHashInt,'064b')
    databaseRowHashInt=int(databaseRowHashStr,16)
    databaseRowHashBinStr=format(databaseRowHashInt,'064b')   
    compareThese = zip(targetHashBinStr, databaseRowHashBinStr)
    distance=64
    for a,b in compareThese:
        if a==b:
            distance=distance-1
    return distance


if __name__ == '__main__':
  main()


# def raw_data_tojson (input):
#     #tuple looks like: (None, u'{"imgName": "volleyball_block.jpg", "hash": "17e81e97e01fe815", "time": 1474613689.301628}')
#     print("json input: ", input)
#     output=json.loads(input[1])
#     print("json output: ", output)
#     print("json imgName: ", output['imgName'])
#     print("json hash: ", output['hash'])
#     return {'imgName':output['imgName'],'imgHash':output['hash']};




"""
$SPARK_HOME/bin/spark-submit \
--master spark://ip-172-31-0-172:7077 \
--executor-memory 8000M \
--driver-memory 8000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Running on single node
$SPARK_HOME/bin/spark-submit \
--executor-memory 2000M \
--driver-memory 2000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,\
TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Running spark shell with cassandra
$SPARK_HOME/bin/pyspark \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12
"""
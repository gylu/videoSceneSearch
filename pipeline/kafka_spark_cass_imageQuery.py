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

$SPARK_HOME/bin/spark-submit \
--master spark://ip-172-31-0-174:7077 \
--executor-memory 2000M \
--driver-memory 2000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,\
TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.35.12.160,52.33.155.170,54.69.1.84,52.41.224.1 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Running on single node
$SPARK_HOME/bin/spark-submit \
--executor-memory 2000M \
--driver-memory 2000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,\
TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.35.12.160,52.33.155.170,54.69.1.84,52.41.224.1 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Running spark shell with cassandra
$SPARK_HOME/bin/pyspark \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.35.12.160,52.33.155.170,54.69.1.84,52.41.224.1
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
hval_table=0 #global rdd
producer = KafkaProducer(bootstrap_servers = 'ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092', value_serializer=lambda v: json.dumps(v).encode('ascii'))
   


def hamming2(s1, s2):
    """Calculate the Hamming distance between two bit strings"""
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))

# Delete this later, i'm 90% sure that it's useless
#conf = SparkConf().setAppName("vss")
#sc = SparkContext(conf=conf)

#hashValueStr=str(hashValue)
#hashValueInt=int(hashValueStr,16)
#hashPrefixStr=hashValueStr[0:6]
#hashPrefixInt=int(hashPrefixStr,16)


def calcDist (rowInFramesDatabase, targetHashValBinStr):
    hashValfmDatabase=rowInFramesDatabase['hashvalue']
    hashValfmDatabaseInt=int(hashValfmDatabase,16)
    hashValfmDatabaseBinStr=format(hashValfmDatabaseInt,'064b')
    #dist=sum(c1 != c2 for c1, c2 in zip(hashValfmDatabaseBinStr, targetHashValBinStr)) #this doesn't seem to work
    #return dist
    compareThese = zip(hashValfmDatabaseBinStr, targetHashValBinStr)
    distance=0
    for a,b in compareThese:
        if a==b:
            distance=distance+1
    return distance

def calcDistStr (targetHashStr, databaseRowHashStr):
    targetHashInt=int(targetHashStr,16)
    targetHashBinStr=format(targetHashInt,'064b')
    databaseRowHashInt=int(databaseRowHashStr,16)
    databaseRowHashBinStr=format(databaseRowHashInt,'064b')   
    #dist=sum(c1 != c2 for c1, c2 in zip(hashValfmDatabaseBinStr, targetHashValBinStr)) #this doesn't seem to work
    #return dist
    compareThese = zip(targetHashBinStr, databaseRowHashBinStr)
    distance=0
    for a,b in compareThese:
        if a==b:
            distance=distance+1
    return distance


"""
Example usages:
hval_table.select("hashvalue", "partitionby","videoname").map(lambda x: x['hashvalue']).take(3)
will resule in
[u'6daab6a32cb6b209', u'77a888d7aa2f882b', u'571d23371cc358d5']
"""
def findClosestMatches (input):
    global hval_table;
    #tuple looks like: (None, u'{"imgName": "volleyball_block.jpg", "hash": "17e81e97e01fe815", "time": 1474613689.301628}')
    output=json.loads(input[1])
    print("Here, json input: ", input)
    targetHashValInt=int(output['hash'],16)
    #targetHashValInt=int("17e81e97e01fe815",16) #example hash value to try on. Comment this out
    targetHashValBinStr=format(targetHashValInt,'064b')
    #closestFrames=hval_table.select("hashvalue", "partitionby","videoname",'framenumber').map(lambda j: (j['videoname'],j['framenumber'],calcDist(j,targetHashValBinStr))).takeOrdered(5,key=lambda x: x[2])
    closestFrames=hval_table.map(lambda j: (j['videoname'],j['framenumber'],calcDist(j,targetHashValBinStr))).takeOrdered(5,key=lambda x: x[2])
    producer.send('searchReturns', {output:closestFrames})  #fix this, need to figure out what to send back
    return closestFrames;

def raw_data_tojson (input):
    #tuple looks like: (None, u'{"imgName": "volleyball_block.jpg", "hash": "17e81e97e01fe815", "time": 1474613689.301628}')
    print("json input: ", input)
    output=json.loads(input[1])
    print("json output: ", output)
    print("json imgName: ", output['imgName'])
    print("json hash: ", output['hash'])
    return {'imgName':output['imgName'],'imgHash':output['hash']};

def main():
    global hval_table;
    if len(sys.argv) != 3:
        #print("Usage: thisfile.py <zk> <sensor_topic>", file=sys.stderr) #i get an error about file=sys.stderr for some reason
        print("Usage: thisfile.py <zk> <sensor_topic>")
        exit(-1)

    # Kafka and Spark Streaming specific vars
    batch_interval = 3
    window_length = 50
    sc = CassandraSparkContext(appName="PythonStreamingVSS") #http://www.slideshare.net/JonHaddad/intro-to-py-spark-and-cassandra
    ssc = StreamingContext(sc, batch_interval)
    #ssc.checkpoint("hdfs://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9000/imgSrchRqstCkpts")


    #example of what can be done
    #hval_table=sc.cassandraTable("vss","hval") #doesn't work
    hval_table=sc.cassandraTable("vss","hval").select("hashvalue", "partitionby","videoname",'framenumber','frametime').persist(StorageLevel.MEMORY_ONLY)
    #a=hval_table.select('videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()
    #a=hval_table.select("hashvalue","partitionby",'videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()
    #print(a) #this works

    zkQuorum, myTopic = sys.argv[1:]
    # Specify all the nodes you are running Kafka on
    kafkaBrokers = {"metadata.broker.list": "52.35.12.160:9092,52.33.155.170:9092,54.69.1.84:9092,52.41.224.1:9092"}
    streamFromKafka = KafkaUtils.createDirectStream(ssc, [myTopic], kafkaBrokers)
    
    print("hi")
    print("stream fm kafka:", streamFromKafka)

    """
    Breaks
    #doSomething = streamFromKafka.foreach(raw_data_tojson).pprint() #this DOESNT work, KafkaDStream has no attribute 'foreach'
    #doSomething = streamFromKafka.foreachRDD(raw_data_tojson) #this DOESNT work. Returns RDDs. Whereas a simple .map maps to all items in RDD
    #imageFindRequests = streamFromKafka.foreachRDD(lambda x: x.foreach(findClosestMatches)) #doesn't work
    #streamFromKafka.map(raw_data_tojson).map(lambda x: ({"joinKey":1,x})).joinWithCassandraTable("vss", "hval_table", [],['id'])
    streamFromKafka.map(lambda x: (1,x)).join(hval_table.map(lambda x: (1,x))) #AttributeError: 'PipelinedRDD' object has no attribute '_jdstream'
    streamFromKafka.transform(lambda rdd: rdd.map(lambda x: (1,x) ).join(hval_table.map(lambda x: (1,x)))).foreach() #AttributeError: 'KafkaTransformedDStream' object has no attribute 'foreach'
    
    #Breaks due to RDD scope issue
    #imageFindRequests = streamFromKafka.map(lambda rdd: rdd.map(lambda row: findClosestMatches(row))).pprint() #question: is this the correct syntax? I just want my findClosestMatches to run
    #imageFindRequests = streamFromKafka.map(findClosestMatches).pprint() #question: is this the correct syntax? I just want my findClosestMatches to run

    #Breaks for some other reason
    #streamFromKafka.map(lambda x: (1,x)).join(hval_table.map(lambda x:(1,x))) #doesn't work, AttributeError: 'PipelinedRDD' object has no attribute '_jdstream'
    #streamFromKafka.map(lambda x: (json.loads(x[1]))).cartesian(hval_table)
    #hval_table.cartesian(streamFromKafka.map(raw_data_tojson)) #doesn't work

    Doesn't crash
    #hval_table.filter(lambda x:(x['hashvalue']=='038bffff40008af3')).map(lambda x: (1,x)).join(hval_table.filter(lambda x:(x['partitionby']==25)).map(lambda x: (1,x))).collect() #this works

    """
    #streamFromKafka.map(raw_data_tojson).pprint() #this works BUT I DONT KNOW WHY. SEEMS LIKE MAP IS APPLIED DIRECTLY DOWN TO LOWEST FILE? (SKIPPED AN RDD?)
    #streamFromKafka.map(printMe).pprint() #this works..
    #streamFromKafka.map(lambda x: (1,x)).map(printMe).pprint() #This works, results in: (1, (None, u'{"imgName": "Flask.png", "hash": "5141bde30ef3833a", "time": 1475016832.642927}'))
    #streamFromKafka.map(lambda x: (1,x)).foreachRDD(lambda rdd: rdd.join(hval_table.map(lambda x: (1,x)))).map(printMe).pprint() #AttributeError: 'NoneType' object has no attribute 'map'
    #streamFromKafka.foreachRDD(lambda rdd: (rdd.map(lambda x: (1,x))) ).map(printMe).pprint()
    #streamFromKafka.transform(lambda rdd: rdd.map(lambda x: (1,x) ).join(hval_table.map(lambda x: (1,x)))).pprint() #this seems to work, 
    #outputs rows of the following:
    #(1, ((None, u'{"imgName": "Kafka.jpeg", "hash": "f1b9094e06b13dce", "time": 1475023909.082745}'), Row(framenumber=135, frametime=5630.625, hashvalue=u'6daab6a32cb6b209', partitionby=42, videoname=u'TERMINATOR_GENISYS_Clip_War_of_the_Machines-vjZDU_WldAw.mp4')))
    streamFromKafka.transform(lambda rdd: rdd.map(lambda x: (1,x[1]) ).join(hval_table.map(lambda x: (1,x)))).pprint() #this seems to work, 
    streamFromKafka.transform(lambda rdd: rdd.map(lambda x: (1,x[1]) ).join(hval_table.map(lambda x: (1,x)))).map(findClosest).pprint() #this seems to work, 

    #streamFromKafka.foreachRDD(lambda rdd: rdd.map(lambda x: (1,x))).join(hval_table.map(lambda x: (1,x)))).map(printMe).pprint() 
    #streamFromKafka.map(lambda x: (1,x)).join(hval_table.map(lambda x: (1,x))).map(printMe).pprint() #AttributeError: 'PipelinedRDD' object has no attribute '_jdstream'
    print("here")


    ssc.start()
    ssc.awaitTermination()

def findClosest(x):
    distance=calcDistStr(x[1][0][1]['hash'],x[1][1][0]['hashvalue'])
    return distance

def printMe(x):
    return x

if __name__ == '__main__':
  main()

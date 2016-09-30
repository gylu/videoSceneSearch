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

##
hval_table=0 #global rdd
producer = KafkaProducer(bootstrap_servers = 'ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092', value_serializer=lambda v: json.dumps(v).encode('ascii'))
# Kafka and Spark Streaming specific vars
batch_interval = 5 #question, why is batch interval of 5 so much better than 3? 3 seemed like needed to wait a long time
sc = CassandraSparkContext(appName="PythonStreamingVSS") #http://www.slideshare.net/JonHaddad/intro-to-py-spark-and-cassandra
ssc = StreamingContext(sc, batch_interval)


"""
Example usages:
hval_table.select("hashvalue", "partitionby","videoname").map(lambda x: x['hashvalue']).take(3)
will resule in
[u'6daab6a32cb6b209', u'77a888d7aa2f882b', u'571d23371cc358d5']
"""

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
    global producer;
    if len(sys.argv) != 3:
        #print("Usage: thisfile.py <zk> <sensor_topic>", file=sys.stderr) #i get an error about file=sys.stderr for some reason
        print("Usage: thisfile.py <zk> <sensor_topic>")
        exit(-1)


    #ssc.checkpoint("hdfs://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9000/imgSrchRqstCkpts")


    #example of what can be done
    #hval_table=sc.cassandraTable("vss","hval") #doesn't work
    hval_table=sc.cassandraTable("vss","hval").select("hashvalue","youtubelink", "partitionby","videoname",'framenumber','frametime').persist(StorageLevel.MEMORY_ONLY)
    #a=hval_table.select('videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()
    #a=hval_table.select("hashvalue","partitionby",'videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()
    #print(a) #this works

    zkQuorum, myTopic = sys.argv[1:]
    # Specify all the nodes you are running Kafka on
    kafkaBrokers = {"metadata.broker.list": "52.35.12.160:9092,52.33.155.170:9092,54.69.1.84:9092,52.41.224.1:9092"}
    streamFromKafka = KafkaUtils.createDirectStream(ssc, [myTopic], kafkaBrokers)
    
    print("hi")
    print("stream fm kafka:", streamFromKafka)

    streamFromKafka.transform(lambda rdd: rdd.map(lambda x: (1,x[1])).join(hval_table.map(lambda x: (1,x)))).map(addDistanceInfo).foreachRDD(takeTop) #works once then breaks AttributeError: 'list' object has no attribute '_jrdd'
    producer.send('searchReturns',"Hello, producer is working. Time is: " + str(time.time()))
    print("here")
    ssc.start()
    ssc.awaitTermination()


def takeTop(rdd):
    global producer;
    output= rdd.takeOrdered(3,key=lambda x: (x['distance'])) #this is a python list, can't save this to cassandra
    producer.send('searchReturns',output)
    sc.parallelize(output).saveToCassandra("vss","queryresults")
    #return output


def addDistanceInfo(x):
    #x is of the form (1, ({dict in string format},row()) )
    targetImageDict=json.loads(x[1][0]) #Need to have json.loads. Because print(x[1][0][0]) returns just the { char as a string. #this is the dictionary from the kafka topic 
    #returns {"imgName": "Kafka.jpeg", "hash": "f1b9094e06b13dce", "time": 1475035317.596829}
    rowFromDatabase=x[1][1] #this is the row item
    distance=calcDistStr(targetImageDict['hash'],rowFromDatabase['hashvalue'])
    result={'distance':distance,'youtubelink':rowFromDatabase['youtubelink'], 'imagename':targetImageDict['imgName'], "targetimagehash":targetImageDict['hash'], 'framehash':rowFromDatabase['hashvalue'] ,"videoname":rowFromDatabase['videoname'], "frametime":rowFromDatabase['frametime'], "framenumber":rowFromDatabase['framenumber']}
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

def printMe(x):
    return x

if __name__ == '__main__':
  main()


"""
$SPARK_HOME/bin/spark-submit \
--master spark://ip-172-31-0-174:7077 \
--executor-memory 3200M \
--driver-memory 1700M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.41.224.1,52.35.12.160,52.33.155.170,54.69.1.84 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

$SPARK_HOME/bin/spark-submit \
--master spark://ip-172-31-0-174:7077 \
--executor-memory 4000M \
--driver-memory 2000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1, TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.41.224.1,52.35.12.160,52.33.155.170,54.69.1.84 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Running on single node
$SPARK_HOME/bin/spark-submit \
--executor-memory 2000M \
--driver-memory 2000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,\
TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.41.224.1,52.35.12.160,52.33.155.170,54.69.1.84 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Running spark shell with cassandra
$SPARK_HOME/bin/pyspark \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.41.224.1,52.35.12.160,52.33.155.170,54.69.1.84
"""
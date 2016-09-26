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


$SPARK_HOME/bin/spark-submit \
--executor-memory 2000M \
--driver-memory 2000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,\
TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.35.12.160,52.33.155.170,54.69.1.84,52.41.224.1 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests
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

"""
Example usages:
hval_table.select("hashvalue", "partitionby","videoname").map(lambda x: x['hashvalue']).take(3)
will resule in
[u'6daab6a32cb6b209', u'77a888d7aa2f882b', u'571d23371cc358d5']
"""
def findClosestMatches (input):
    #input looks like: (None, u'{"imgName": "volleyball_block.jpg", "hash": "17e81e97e01fe815", "time": 1474613689.301628}')
    output=json.loads(input[1])
    print("Here, json input: ", input)
    targetHashValInt=int(output['hash'],16)
    #targetHashValInt=int("17e81e97e01fe815",16) #example hash value to try on. Comment this out
    targetHashValBinStr=format(targetHashValInt,'064b')
    closestFrames=hval_table.select("hashvalue", "partitionby","videoname",'framenumber').map(lambda j: (j['videoname'],j['framenumber'],calcDist(j,targetHashValBinStr))).takeOrdered(5,key=lambda x: x[2])
    producer.send('searchReturns', {output:closestFrames})  #fix this, need to figure out what to send back
    return closestFrames;

def raw_data_tojson (input):
    #input looks like: (None, u'{"imgName": "volleyball_block.jpg", "hash": "17e81e97e01fe815", "time": 1474613689.301628}')
    output=json.loads(input[1])
    print("json input: ", input)
    print("json output: ", output)
    print("json imgName: ", output['imgName'])
    print("json hash: ", output['hash'])
    return output;

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
    hval_table=sc.cassandraTable("vss","hval");
    #a=hval_table.select('videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()
    #a=hval_table.select("hashvalue","partitionby",'videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()
    #print(a) #this works

    zkQuorum, myTopic = sys.argv[1:]
    # Specify all the nodes you are running Kafka on
    kafkaBrokers = {"metadata.broker.list": "52.35.12.160:9092,52.33.155.170:9092,54.69.1.84:9092,52.41.224.1:9092"}
    streamFromKafka = KafkaUtils.createDirectStream(ssc, [myTopic], kafkaBrokers)
    
    print("hi")
    print("stream fm kafka:", streamFromKafka)
    #doSomething = streamFromKafka.map(raw_data_tojson).pprint() #this works
    imageFindRequests = streamFromKafka.map(lambda rdd: rdd.map(lambda row: findClosestMatches(row))).pprint() #question: is this the correct syntax? I just want my findClosestMatches to run

    print("here")


    ssc.start()
    ssc.awaitTermination()

if __name__ == '__main__':
  main()












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
"""
The plan:
1. Read RDD from cassandra
2. Get DStream RDD from kafka
3. Search for top 3 matches closest to target image by calculating distances on each frame
4. Pull entire video that each match belongs to
5. Push plots to client
6. Have client plot distance vs time

Takes requests from kafka, runs spark streaming processing query to get results, then pushes results to cassandra
Usage: kafka_spark_cass_imageQuery.py <zk> <kafka topic> <more kafka topic if exist>

#Ways of running this
$SPARK_HOME/bin/spark-submit \
--master spark://ip-172-31-0-173:7077 \
--executor-memory 12000M \
--driver-memory 12000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Running on single node
$SPARK_HOME/bin/spark-submit \
--executor-memory 8000M \
--driver-memory 8000M \
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,\
TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12 \
/home/ubuntu/pipeline/kafka_spark_cass_imageQuery.py localhost:2181 imgSearchRequests

#Opening spark shell with cassandra
$SPARK_HOME/bin/pyspark \
--master spark://ip-172-31-0-173:7077 \
--packages TargetHolding/pyspark-cassandra:0.3.5 \
--conf spark.cassandra.connection.host=52.32.192.156,52.32.200.206,54.70.213.12
"""


db_table=0 #global rdd
producer = KafkaProducer(bootstrap_servers = 'ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092', value_serializer=lambda v: json.dumps(v).encode('ascii'))
# Kafka and Spark Streaming specific vars
batch_interval = 5 #question, why is batch interval of 5 so much better than 3? 3 seemed like needed to wait a long time
sc = CassandraSparkContext(appName="PythonStreamingVSS") #http://www.slideshare.net/JonHaddad/intro-to-py-spark-and-cassandra
ssc = StreamingContext(sc, batch_interval)
keyspace="vss_hist"

"""
Example usages:
db_table.select("hashvalue", "partitionby","videoname").map(lambda x: x['hashvalue']).take(3)
will result in
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
    print("about to do map and persist")
    db_table=sc.cassandraTable(keyspace,"vname").select("hashvalue","youtubelink","videoname",'framenumber','frametime','histogramvector').persist(StorageLevel.MEMORY_ONLY)
    db_table.repartition(36)
    print("about to take")
    tempTake1=db_table.take(1);
    print("take 1 of db_table: ", tempTake1)
    zkQuorum, myTopic = sys.argv[1:]
    # Specify all the nodes you are running Kafka on
    kafkaBrokers = {"metadata.broker.list": "52.33.155.170:9092,54.69.1.84:9092,52.41.224.1:9092"}
    streamFromKafka = KafkaUtils.createDirectStream(ssc, [myTopic], kafkaBrokers)
    print("stream fm kafka:", streamFromKafka)
    streamFromKafka.foreachRDD(doEverything)
    producer.send('searchReturns',"Hello, producer is working. Time is: " + str(time.time()))
    print("starting")
    ssc.start()
    ssc.awaitTermination()



def doEverything(rdd):
    taken=rdd.take(1)
    print("rdd taken: ",taken) #('rdd taken: ', [(None, u'{"imgName": "Screen_Shot_2016-10-10_at_11.07.01_PM.png", "hash": "4d63933393239b6c", "time": 1476166026.925404}')])
    if taken!=[]:
        starttime=time.time()
        temp=db_table.map(lambda x: (1,x)).join(rdd.coalesce(3).map(lambda x: (1,x[1]))).map(addDistanceInfo).cache() #joining big table with small table, works but is STILL super slow. ~45sec
        framesfound=temp.takeOrdered(30,key=lambda x: (x['distance']))
        seen = set()
        framesfound = [seen.add(obj['videoname']) or obj for obj in framesfound if obj['videoname'] not in seen] #get unique videos only 
        framesfound=framesfound[:3] #just get 3 at most
        producer.send('searchReturns',framesfound)
        sc.parallelize(framesfound).saveToCassandra(keyspace,"queryresults")
        uniqueNames=set(item['videoname'] for item in framesfound)
        temp.filter(lambda x: (x['videoname'] in uniqueNames)).saveToCassandra(keyspace,"distances")
        print("=====here5, after 2nd db write: ", time.time()-starttime)



def addDistanceInfo(x):
    #x is of the form (1, ({dict in string format}, row()) ) if I do dstreamRDD.join(movie table)
    #targetImageDict=json.loads(x[1][0]) #Need to have json.loads. Because print(x[1][0][0]) returns just the { char as a string. #this is the dictionary from the kafka topic. #returns {"imgName": "Kafka.jpeg", "hash": "f1b9094e06b13dce", "time": 1475035317.596829}
    #rowFromDatabase=x[1][1] #this is the row item
    ##### Alternative for doing db_table.join(dstream RDD)
    #x is of the form (1, (row(), {dict in string format}) ) if I do db_table.join(dstream RDD)
    targetImageDict=json.loads(x[1][1])
    rowFromDatabase=x[1][0]
    #doing stuff with the histogram
    histogramvector=pickle.loads(rowFromDatabase['histogramvector'])
    
    ####
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


# references:
#regarding how data is recieved by spark 
#Data is read directly by the executors
#http://stackoverflow.com/questions/35942148/spark-streaming-data-dissemination-in-kafka-and-textsocket-stream
#tips about sizing executors
#http://www.slideshare.net/cloudera/top-5-mistakes-to-avoid-when-writing-apache-spark-applications
#joining dstream with static RDD. I'm doing the same thing as this. Super slow...
#https://docs.cloud.databricks.com/docs/latest/databricks_guide/07%20Spark%20Streaming/14%20Joining%20DStreams%20With%20Static%20Datasets.html
#http://permalink.gmane.org/gmane.comp.lang.scala.spark.user/13195
#could try something like this for broadcasting an RDD. But this won't work for broadcasting a dstream rdd
#http://stackoverflow.com/questions/28847962/how-to-join-two-tables-big-and-small-ones-effectively
#number of partitions spark streaming creates per dstream rdd batch (Ans: about 5 partitions created per second)
#https://forums.databricks.com/questions/778/how-many-partitions-does-spark-streaming-create-pe.html
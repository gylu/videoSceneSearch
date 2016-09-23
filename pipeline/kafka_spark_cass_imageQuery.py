#from __future__ import print_function
"""
The plan:
1. Read RDD from cassandra
2. Search for top 3 matches closest to targetImage
3. Pull entire video that each match belongs to
4. Calculate distance on each frame on the video
5. Plot distance vs time
6. Push plots to client

Questions:
Do I query cassandra through CQL?
Do I query cassandra through python?
Or do I get spark to read the cassandra as an RDD first, and then query through spark?

is it at all possible to write 
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

##



def hamming2(s1, s2):
    """Calculate the Hamming distance between two bit strings"""
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))

# Delete this later, i'm 90% sure that it's useless
#conf = SparkConf().setAppName("vss")
#sc = SparkContext(conf=conf)

#targetImage = "/path/to/target/image"
#hashValue=imagehash.phash(Image.fromarray(targetImage)) #Note: Image.read wasn't working, so instead using Image.fromarray. http://stackoverflow.com/questions/22906394/numpy-ndarray-object-has-no-attribute-read
#hashValueStr=str(hashValue)
#hashValueInt=int(hashValueStr,16)
#hashPrefixStr=hashValueStr[0:6]
#hashPrefixInt=int(hashPrefixStr,16)

def raw_data_tojson (input):
    #input looks like: (None, u'{"imgName": "volleyball_block.jpg", "hash": "17e81e97e01fe815", "time": 1474613689.301628}')
    output=json.loads(input[1])
    print("json input: ", input)
    print("json output: ", output)
    print("json imgName: ", output['imgName'])
    print("json hash: ", output['hash'])
    return output;


def main():
    if len(sys.argv) != 3:
        #print("Usage: thisfile.py <zk> <sensor_topic>", file=sys.stderr) #i get an error about file=sys.stderr for some reason
        print("Usage: thisfile.py <zk> <sensor_topic>")
        exit(-1)

    # Kafka and Spark Streaming specific vars
    batch_interval = 3
    window_length = 50

    sc = CassandraSparkContext(appName="PythonStreamingVSS")
    ssc = StreamingContext(sc, batch_interval)
    #ssc.checkpoint("hdfs://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9000/imgSrchRqstCkpts")

    zkQuorum, myTopic = sys.argv[1:]
    # Specify all the nodes you are running Kafka on
    kafkaBrokers = {"metadata.broker.list": "52.35.12.160:9092,52.33.155.170:9092,54.69.1.84:9092,52.41.224.1:9092"}
    
    streamFromKafka = KafkaUtils.createDirectStream(ssc, [myTopic], kafkaBrokers)

    print("hi")
    print(streamFromKafka)

    doSomething = streamFromKafka.map(raw_data_tojson).pprint()

    #example of what can be done
    hval_table=sc.cassandraTable("vss","hval");
    #a=hval_table.select('videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()
    #print(a) #this works
    a=hval_table.select("hashvalue","partitionby",'videoname').map(lambda r: (r['videoname'],1)).reduceByKey(lambda a, b: a+b).collect()


    print("here")
    #pdb.set_trace()    
    #Do something with batch_interval and window_length
    #windowed_user_rate = user_rate_values.groupByKeyAndWindow(window_length, batch_interval).map(lambda x : (x[0], list(x[1]))).map(lambda x: {"user_id": x[0], "timestamp": max(x[1])[0], "sum_rate": costum_add(list(filter_list(x[1])), sum_time_window)})
    #windowed_user_rate.saveToCassandra("rate_data", "user_sum")

    ssc.start()
    ssc.awaitTermination()

if __name__ == '__main__':
  main()











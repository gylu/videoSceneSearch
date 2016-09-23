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
Usage: kafka_spark_cass.py <zk> <topic1> <topic2>
/usr/local/spark/bin/spark-submit --master spark://ip-172-31-1-101:7077 --executor-memory 4000M --driver-memory 4000M 
--packages org.apache.spark:spark-streaming-kafka_2.10:1.6.1,TargetHolding/pyspark-cassandra:0.3.5 --conf spark.cassandra.connection.host=52.41.123.24,52.36.29.21,52.41.189.217 kafka_spark_cass.py localhost:2181 drate_18 loc_18
"""

from __future__ import print_function

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from pyspark_cassandra import streaming
import pyspark_cassandra, sys
import json

from pyspark import StorageLevel

from pyspark.sql.functions import sum
from pyspark.sql.types import *
from pyspark.sql import Window
from pyspark.sql import SQLContext 
from pyspark.sql import functions


##my stuff
from pyspark import SparkContext
from pyspark import SparkConf
import pyspark_cassandra
import time

import io
import sys
import os
import numpy as np
from PIL import Image
import imagehash
##



def hamming2(s1, s2):
    """Calculate the Hamming distance between two bit strings"""
    #assert len(s1) == len(s2)
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))

# Delete this later, i'm 90% sure that it's useless
#conf = SparkConf().setAppName("vss")
#sc = SparkContext(conf=conf)

targetImage = "/path/to/target/image"
hashValue=imagehash.phash(Image.fromarray(targetImage)) #Note: Image.read wasn't working, so instead using Image.fromarray. http://stackoverflow.com/questions/22906394/numpy-ndarray-object-has-no-attribute-read
hashValueStr=str(hashValue)
hashValueInt=int(hashValueStr,16)
hashPrefixStr=hashValueStr[0:6]
hashPrefixInt=int(hashPrefixStr,16)



def raw_data_tojson(sensor_data):
  """ Parse input json stream """
  # The Kafka messages arrive as a tuple (None, {"room":{"uid": 42, "time": 1, "loc": 32}})
  # this first line grabs the nested json (second element) 
  raw_sensor = sensor_data.map(lambda k: json.loads(k[1]))
  # .keys() finds all keys of the json - this case there is only one: "room"
  # the value of the key "room" is returned as a json
  return(raw_sensor.map(lambda x: json.loads(x[x.keys()[0]])))
 

def costum_add(l, sum_time_window):
  """ List sum, scaled if not enough datapoints are received """
  result, length = 0, 0
  for i in l:
    result = result + i
    length = length + 1
  if length:
    result = float(result)/length*sum_time_window
  return result 
 

def main():

    if len(sys.argv) != 3:
        print("Usage: thisfile.py <zk> <sensor_topic>", file=sys.stderr)
        exit(-1)

    # Kafka and Spark Streaming specific vars
    batch_length = 5
    window_length = 50

    sc = SparkContext(appName="PythonStreamingVSS")
    ssc = StreamingContext(sc, batch_length)
    ssc.checkpoint("hdfs://ec2-52-24-174-234.us-west-2.compute.amazonaws.com:9000/usr/sp_data")

    zkQuorum, topic1, topic2 = sys.argv[1:]
    # Specify all the nodes you are running Kafka on
    kafkaBrokers = {"metadata.broker.list": "52.35.6.29:9092, 52.41.24.92:9092, 52.41.26.121:9092, 52.24.174.234:9092"}
    
    # Get the sensor and location data streams - they have separate Kafka topics
    sensor_data = KafkaUtils.createDirectStream(ssc, [topic1], kafkaBrokers)
    loc_data = KafkaUtils.createDirectStream(ssc, [topic2], kafkaBrokers)

  
    ##### Merge streams and push rates to Cassandra #####

    # Get location (room) info for users
    raw_loc = raw_data_tojson(loc_data)

    # Get sensor rate info for users
    raw_sensor = raw_data_tojson(sensor_data)
    
    # Map the 2 streams to ((userid, time), value) then join the streams
    # 
    s1 = raw_loc.map(lambda x: ((x["room"]["uid"], x["room"]["t"]) , x["room"]["nl"]))
    s2 = raw_sensor.map(lambda x: ((x["sens"]["uid"], x["sens"]["t"]), x["sens"]["dr"]))

    combined_info = s1.join(s2).persist(StorageLevel.MEMORY_ONLY)

    # Group stream by room and calc average rate signal 
    room_rate_gen = combined_info.map(lambda x: ((x[1][0],x[0][1]), x[1][1])).groupByKey().\
                              map(lambda x : (x[0][0], (x[0][1], reduce(lambda x, y: x + y, list(x[1]))/float(len(list(x[1])))))).persist(StorageLevel.MEMORY_ONLY)
  
    room_rate = room_rate_gen.map(lambda x: {"room_id": x[0], "timestamp": x[1][0], "rate": x[1][1]})
    room_rate.saveToCassandra("rate_data", "room_rate")

    # Find which users are at a certain room
    room_users = combined_info.map(lambda x: ((x[1][0],x[0][1]), x[0][0])).groupByKey().\
                               map(lambda x : {"room_id": x[0][0], "timestamp": x[0][1], "users": list(x[1])})    
    room_users.saveToCassandra("rate_data", "room_users")
  

    # Save all user info (id, time, rate, room) to Cassandra
    user_rate = combined_info.map(lambda x: { "user_id": x[0][0], "timestamp": x[0][1],  "rate": x[1][1], "room": x[1][0]})
    user_rate.saveToCassandra("rate_data", "user_rate")

    
    ##### Calculate sums for the user_rate and room_rate streams
    # Data points to sum   
    sum_time_window = 20

    # Selects all data points in window, if less than limit, calcs sum based on available average 
    def filter_list(points):
      max_time = max(points)[0]
      valid_points = [(point[1]) for point in points if (max_time - point[0]) < sum_time_window]

      return(valid_points)

    ### Find the max time for each user in the past xxx time and sum the latest sum_time_window points
    user_rate_values = combined_info.map(lambda x: (x[0][0], (x[0][1], x[1][1]))) 

    # Calculate user dose in sliding window
    windowed_user_rate = user_rate_values.groupByKeyAndWindow(window_length, batch_length).map(lambda x : (x[0], list(x[1]))).\
                         map(lambda x: {"user_id": x[0], "timestamp": max(x[1])[0], "sum_rate": costum_add(list(filter_list(x[1])), sum_time_window)})
    windowed_user_rate.saveToCassandra("rate_data", "user_sum")

    # Calculate room dose in sliding window
    windowed_room_rate = room_rate_gen.groupByKeyAndWindow(window_length, batch_length).map(lambda x : (x[0], list(x[1]))).\
                         map(lambda x: {"room_id": x[0], "timestamp": max(x[1])[0], "sum_rate": costum_add(list(filter_list(x[1])), sum_time_window)})
    windowed_room_rate.saveToCassandra("rate_data", "room_sum")


    ssc.start()
    ssc.awaitTermination()

if __name__ == '__main__':
  main()











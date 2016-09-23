#!/bin/bash

# Copyright 2015 Insight Data Science
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

PEG_ROOT=$(dirname ${BASH_SOURCE})/../..

CLUSTER_NAME=spark-cluster

peg up ${PEG_ROOT}/examples/spark/nodeconfigs_master_20160914.yaml &
peg up ${PEG_ROOT}/examples/spark/nodeconfigs_worker_20160914.yaml &

wait

peg fetch ${CLUSTER_NAME}

peg install ${CLUSTER_NAME} ssh
peg install ${CLUSTER_NAME} aws
peg install ${CLUSTER_NAME} hadoop
peg install ${CLUSTER_NAME} zookeeper
peg install ${CLUSTER_NAME} kafka
peg install ${CLUSTER_NAME} kafka-manager
peg install ${CLUSTER_NAME} spark
peg install ${CLUSTER_NAME} cassandra
peg service ${CLUSTER_NAME} hadoop start
peg service ${CLUSTER_NAME} zookeeper start
peg service ${CLUSTER_NAME} kafka-manager start
peg service ${CLUSTER_NAME} cassandra start
peg service george-cluster spark start



#Note that using pegasus to install zookeeper pretty much did everything here:
#https://github.com/InsightDataScience/data-engineering-ecosystem/wiki/zookeeper. 
#Except: need to uncomment lines about auto-purging in zookeeper to prevent running out of memory

#Note: Using pegasus to install kafka automatically does everything here: 
#https://github.com/InsightDataScience/data-engineering-ecosystem/wiki/Kafka
#Can check whether kafka started: usr/local/kafka/bin/kafka-topics.sh --list --zookeeper localhost:2181
#Kafka manager running at: http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9001/
#/usr/local/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 --topic imgSearchRequests --partitions 4 --replication-factor 2

#Note to self about messages that appeared when hadoop cluster started
#HDFS WebUI is running at http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:50070
#Hadoop Job Tracker WebUI is running at http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:8088
#Hadoop Job History WebUI is running at http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:19888


#### Notes about monitoring:
#For Spark
#http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:8080/
#For Hadoop
#http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:50070/

#for SCP
#peg scp to-rem george-cluster 1 /Users/gyl/Desktop/insight_projects/videoSceneSearch/getFramesHash_sparkJob.py /home/ubuntu/playground/


######## Notes about stuff not related to the above 

##Trying to get youtube videos into and out of kafka
#youtube-dl https://www.youtube.com/playlist?list=PLBDA074E6B463154D | /usr/local/kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic myVideos
#/usr/local/kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic myVideos << youtube-dl https://www.youtube.com/playlist?list=PLBDA074E6B463154D

#Restrict filenames, and ignore errors
#Download from a url to a folder called videoFiles. Removing spaces from filenames and ignoring errors. Seems to work locally only
#youtube-dl -i --restrict-filenames -o "videoFiles/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/watch?v=yWyj9ORkj8w
#into HDFS directly
#youtube-dl -i --restrict-filenames -o - https://www.youtube.com/watch?v=yWyj9ORkj8w | hdfs dfs -put - "/videoFiles/%(title)s-%(id)s.%(ext)s"

#FFmpeg local usage (quality still seems to be smaller image size):
#./ffmpeg -i Superman_s_True_Power-yWyj9ORkj8w.mp4 -q:v 1 ./frames_superman_ffmpeg/filename%03d.jpg
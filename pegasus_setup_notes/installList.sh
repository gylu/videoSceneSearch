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
peg service ${CLUSTER_NAME} spark start

#george4
#install hadoop, didn't have to start it
#install spark, start spark


#george-db
#install cassandra, start cassandra

#george-cluster
#kafka, started
#flask


#Additional installs
#On all nodes
#sudo apt-get install python-opencv
#sudo pip install pillow
#sudo pip install imagehash
#sudo pip install kafka-python
#
#On webserver node
#sudo pip install Flask
#sudo pip install cassandra-driver

#Note, refer to here for the kafka-python install
#http://kafka-python.readthedocs.io/en/master/install.html
#for the datastax cassandra driver
#note that sudo pip install cassandra-driver is from datastax #https://datastax.github.io/python-driver/installation.html

#Note that using pegasus to install zookeeper pretty much did everything here:
#https://github.com/InsightDataScience/data-engineering-ecosystem/wiki/zookeeper. 
#Except: need to uncomment lines about auto-purging in zookeeper to prevent running out of memory

#Note: Using pegasus to install kafka automatically does everything here: 
#https://github.com/InsightDataScience/data-engineering-ecosystem/wiki/Kafka
#Can check whether kafka started: usr/local/kafka/bin/kafka-topics.sh --list --zookeeper localhost:2181
#Kafka manager running at: http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9001/
#/usr/local/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 --topic imgSearchRequests --partitions 4 --replication-factor 3
#the only other thing I did was update retention policy at /usr/local/kafka/config/server.properties to become 24hrs instead of 168

#Note to self about messages that appeared when hadoop cluster started
#HDFS WebUI is running at http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:50070
#Hadoop Job Tracker WebUI is running at http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:8088
#Hadoop Job History WebUI is running at http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:19888


#### Notes about monitoring:
#For Spark
#http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:8080/
#http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:4040/
#For Hadoop
#http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com:50070/

#for SCP
#peg scp to-rem george-cluster 1 /Users/gyl/Desktop/insight_projects/videoSceneSearch/getFramesHash_sparkJob.py /home/ubuntu/playground/


######## Notes about stuff not related to the above 


###############Notes about memory usage############
#du -sh ~/videos showed 7.4G used
#du -sh ~/ showed 8.6G used
#du -sh / showed 12G used, with msgs about how it couldn't access/read some of my files
# ubuntu@ip-172-31-0-174:~$ df -h
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/xvda1      158G   12G  139G   8% /
# none            4.0K     0  4.0K   0% /sys/fs/cgroup
# udev            3.9G   12K  3.9G   1% /dev
# tmpfs           799M  380K  799M   1% /run
# none            5.0M     0  5.0M   0% /run/lock
# none            3.9G     0  3.9G   0% /run/shm
# none            100M   20K  100M   1% /run/user

#####Notes about free -m memory usage:
#2455 free before stopping spark (just the service, already didn't have batch nor stream running), aftewards, had 2970 free
#before
# ubuntu@ip-172-31-0-174:~$ free -m
#              total       used       free     shared    buffers     cached
# Mem:          7983       7681        302          0         89       2230
# -/+ buffers/cache:       5361       2622
# Swap:            0          0          0
#Then stopping kafka manager
# ubuntu@ip-172-31-0-174:~$ free -m
#              total       used       free     shared    buffers     cached
# Mem:          7983       7422        561          0         89       2231
# -/+ buffers/cache:       5100       2883
# Swap:            0          0          0
#Then stopping kafka
# ubuntu@ip-172-31-0-174:~$ free -m
#              total       used       free     shared    buffers     cached
# Mem:          7983       6284       1699          0         89       2233
# -/+ buffers/cache:       3961       4022
# Swap:            0          0          0
#Then stopping hadoop
# ubuntu@ip-172-31-0-174:~$ free -m
#              total       used       free     shared    buffers     cached
# Mem:          7983       5141       2842          0         92       2233
# -/+ buffers/cache:       2815       5168
# Swap:            0          0          0
#Then stopping cassandra:
# ubuntu@ip-172-31-0-174:~$ free -m
#              total       used       free     shared    buffers     cached
# Mem:          7983       2734       5249          0         94       2251
# -/+ buffers/cache:        389       7594
# Swap:            0          0          0
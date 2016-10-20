import os
import sys
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, stream_with_context, Response, jsonify
from app import app
from werkzeug import secure_filename 
import pdb

import numpy as np
from PIL import Image
import imagehash
import time
import json
from kafka import KafkaProducer
from cassandra.cluster import Cluster #datastax

import cv2 #need to install: sudo apt-get install python-opencv
import math
import pickle

#producer = KafkaProducer(bootstrap_servers =  kafka_node_dns + ':9092')
producer = KafkaProducer(bootstrap_servers = 'ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092', value_serializer=lambda v: json.dumps(v).encode('ascii'))


app.config['UPLOAD_FOLDER'] = 'app/static/uploads' # This is the path to the upload directory
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'png', 'jpg', 'jpeg', 'gif']) # These are the extension that we are accepting to be uploaded
app.config['CASSANDRA_NODES'] = ['52.32.192.156','52.32.200.206','54.70.213.12']  # can be a string or list of nodes

keyspace='vss_hist'
#Cassandra cluster using datastax
cluster = Cluster(app.config['CASSANDRA_NODES'])
#session = cluster.connect('vss_large')
session = cluster.connect(keyspace)

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']




# something like this
# cqlsh:vss> select * from distances where videoname = 'PIXELS_Peter_Dinklage_Character_TRAILER-t_wS7kG8Cec.mp4' and targetimagehash='095adad95741eacc' and frametime>0;
# InvalidRequest: code=2200 [Invalid query] message="PRIMARY KEY column "targetimagehash" cannot be restricted (preceding column "frametime" is restricted by a non-EQ relation)"
@app.route('/_getallframes')
def getallframes():
    videoname = request.args.get('videoname', 0, type=str)
    targetimagehash = request.args.get('targetimagehash', 0, type=str)
    imagename = request.args.get('imagename', 0, type=str)
    print("here in _getallframes request: ", request, "videoname: ", videoname,"targetimagehash: ", targetimagehash, "imagename: ", imagename)
    cql = "SELECT frametime, distance, cosinesimilarity FROM distances WHERE videoname = '"+videoname+"' and targetimagehash='"+targetimagehash+"' and imagename='"+imagename+"'"
    print("cql printed: ",cql)
    #cql = "SELECT * FROM queryresults LIMIT 1"
    cqlresult=0
    frameresults=[]
    times=[]
    hammdistances=[]
    cosinedistances=[]
    starttime=time.time()
    printcounter=0
    elapsed=0    
    while elapsed<60:
        elapsed=time.time()-starttime
        cqlresult = session.execute(cql)
        if cqlresult:
            print("cqlresult: ", cqlresult)
            break
    for row in cqlresult:
        frameresults.append(row)
        times.append(row.frametime)
        hammdistances.append(row.distance)
        cosinedistances.append(row.cosinesimilarity)
    print('got all frames and returning')
    graphdata=jsonify(times=times,distances=hammdistances,cosinedistances=cosinedistances)
    return graphdata


#ec2-52-41-224-1.us-west-2.compute.amazonaws.com:80
@app.route('/')
def home():
    title = "VSS"
    listOfImageNames=os.listdir('./app/static/uploads')
    return render_template('home.html', title=title, listOfImageNames=listOfImageNames)


@app.route('/about')
def about():
    title="VSS"
    return render_template('about.html', title=title)

def findSimilar(imagename):
    #cql = "SELECT * FROM queryresults WHERE targetimagehash='"+str(hashValue) +"' ALLOW FILTERING"
    filepath=os.path.join(app.config['UPLOAD_FOLDER'], imagename)
    hashValue=imagehash.phash(Image.open(filepath))
    image=cv2.imread(filepath)
    hsvImg = cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    histogram_bins = [4, 8, 3]
    hist = cv2.calcHist([hsvImg], [0, 1, 2], None, histogram_bins, [0, 180, 0, 256, 0, 256])
    histflat = cv2.normalize(hist).flatten()
    histstring=pickle.dumps(histflat)
    jsonToShow={"imgName":imagename,"hash":str(hashValue),"time":time.time()}    
    jsonToSend={"imgName":imagename,"hash":str(hashValue),"time":time.time(), "histogramvector":histstring}    
    cql = "SELECT * FROM queryresults WHERE targetimagehash='"+str(hashValue) +"' and imagename='"+imagename+"'"
    print("cql printed: ",cql)    
    cqlresult=0
    cqlresult = session.execute(cql)
    if not cqlresult:
        print("json being sent: ",jsonToSend)
        producer.send('imgSearchRequests', jsonToSend)
    starttime=time.time()
    printcounter=0
    elapsed=0
    while elapsed<600: #allow waiting for 600 seconds for the spark streaming job to finish and write to the database
        elapsed=time.time()-starttime
        printcounter=printcounter+1
        if printcounter==10000: #will print about every 15 seconds
            printcounter=0
            print("querying cassandra for: ",imagename, "time: ", elapsed)
        cqlresult = session.execute(cql)
        if cqlresult:
            print("cqlresult: ", cqlresult)
            print("cqlresult.current_rows: ", cqlresult.current_rows) #note that cqlresult is an iterator, so you can't
            break
    arrayOfMessages=[]
    arrayOfYoutubeIDs=[]
    arrayOfYoutubeTimes=[]
    for row in cqlresult:
        arrayOfMessages.append(row)
        arrayOfYoutubeIDs.append(str(row.youtubelink)[-11:]) #get the youtube video id
        arrayOfYoutubeTimes.append(int(float(str(row.frametime)))-3) #get the youtube video time, 2 seconds before
    arrayOfMessages=arrayOfMessages[:3]
    arrayOfYoutubeIDs=arrayOfYoutubeIDs[:3]
    arrayOfYoutubeTimes=arrayOfYoutubeTimes[:3]
    return render_template('results.html', jsontoshow=jsonToShow, results=zip(arrayOfMessages,arrayOfYoutubeIDs, arrayOfYoutubeTimes), imagename=imagename)


@app.route('/runprovided' , methods=['POST'])
def runprovided():
    print('Hello world also!')
    filename=request.form['uploadFile']
    print("request: ",request)
    print("file: ",filename)
    return findSimilar(imagename=filename)


# Route that will process the file upload
@app.route('/upload', methods=['POST'])
def upload():
    print('Hello world!')
    # Get the name of the uploaded file
    #file = request.files['uploadFile']
    file = request.files['uploadFile']
    # Check if the file is one of the allowed types/extensions
    if file and allowed_file(file.filename):
        # Make the filename safe, remove unsupported chars
        filename = secure_filename(file.filename)
        # Move the file form the temporal folder to
        # the upload folder we setup
        print("filename: ", filename)
        print("file: ", file)
        filepath=os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return findSimilar(imagename=filename)
        

# This route is expecting a parameter containing the name
# of a file. Then it will locate that file on the upload
# directory and show it on the browser, so if the user uploads
# an image, that image is going to be show after the upload

#@app.route('/uploads/<filename>')
#def get_uploadedFile(filename):
#    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# @app.route('/uploads')
# def uploads():
#     return render_template('uploads.html')

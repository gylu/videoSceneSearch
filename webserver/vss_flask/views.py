import os
import sys
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, stream_with_context, Response, jsonify
from vss_flask import app
from werkzeug import secure_filename 
import pdb

import numpy as np
from PIL import Image
import imagehash
import time
import json
from kafka import KafkaProducer
from cassandra.cluster import Cluster #datastax


#producer = KafkaProducer(bootstrap_servers =  kafka_node_dns + ':9092')
producer = KafkaProducer(bootstrap_servers = 'ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092', value_serializer=lambda v: json.dumps(v).encode('ascii'))


app.config['UPLOAD_FOLDER'] = 'vss_flask/static/uploads' # This is the path to the upload directory
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'png', 'jpg', 'jpeg', 'gif']) # These are the extension that we are accepting to be uploaded
app.config['CASSANDRA_NODES'] = ['52.32.192.156','52.32.200.206','54.70.213.12']  # can be a string or list of nodes

#Cassandra cluster using datastax
cluster = Cluster(app.config['CASSANDRA_NODES'])
session = cluster.connect('vss')

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@app.route('/_add_numbers')
def add_numbers():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    print("here in add numbers: ", request, "a: ", a,"b: ", b)
    result=jsonify(result=a + b)
    print('result: ',result)
    return result


#ec2-52-41-224-1.us-west-2.compute.amazonaws.com:80
@app.route('/')
def home():
    title = "VSS"
    listOfImageNames=os.listdir('./vss_flask/static/uploads')
    return render_template('home.html', title=title, listOfImageNames=listOfImageNames)


@app.route('/about')
def about():
    title="VSS"
    message="work in progress..."
    return render_template('about.html', title=title, message=message)


@app.route('/runprovided' , methods=['POST'])
def runprovided():
    print('Hello world also!')
    file=request.form['uploadFile']
    imageName=file
    print("request: ",request)
    print("file: ",file)
    filepath=os.path.join(app.config['UPLOAD_FOLDER'], file)
    print("filepath: ", filepath)
    hashValue=imagehash.phash(Image.open(filepath))
    jsonToSend={"imgName":file,"hash":str(hashValue),"time":time.time()}
    print("json being sent: ",jsonToSend)
    producer.send('imgSearchRequests', jsonToSend)
    cql = "SELECT * FROM queryresults WHERE targetimagehash='"+str(hashValue) +"' ALLOW FILTERING"
    print("cql printed: ",cql)
    #cql = "SELECT * FROM queryresults LIMIT 1"
    cqlresult=0
    while True:
        cqlresult = session.execute(cql)
        if cqlresult:
            print("cqlresult: ", cqlresult)
            if cqlresult.current_rows>2: #this is so that all 3 top results will appear before this returns #this isn't working.. still returning just 1 sometimes
                break
    arrayOfResults=[]
    arrayOfYoutubeIDs=[]
    arrayOfYoutubeTimes=[]
    for row in cqlresult:
        arrayOfResults.append(row)
        arrayOfYoutubeIDs.append(str(row.youtubelink)[-11:]) #get the youtube video id
        arrayOfYoutubeTimes.append(int(float(str(row.frametime)))-2) #get the youtube video id
    arrayOfResults=arrayOfResults[:3]
    arrayOfYoutubeIDs=arrayOfYoutubeIDs[:3]
    arrayOfYoutubeTimes=arrayOfYoutubeTimes[:3]
    # oneYoutubeID=arrayOfYoutubeIDs[0]
    return render_template('results.html', jsonSent=jsonToSend, results=zip(arrayOfResults,arrayOfYoutubeIDs, arrayOfYoutubeTimes), imageName=imageName)


# Route that will process the file upload
@app.route('/upload', methods=['POST'])
def upload():
    print('Hello world!')
    # Get the name of the uploaded file
    file = request.files['uploadFile']
    # Check if the file is one of the allowed types/extensions
    if file and allowed_file(file.filename):
        # Make the filename safe, remove unsupported chars
        filename = secure_filename(file.filename)
        # Move the file form the temporal folder to
        # the upload folder we setup
        filepath=os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        #pdb.set_trace()
        hashValue=imagehash.phash(Image.open(filepath))
        jsonToSend={"imgName":filename,"hash":str(hashValue),"time":time.time()}
        print("json being sent: ",jsonToSend)
        producer.send('imgSearchRequests', jsonToSend)
        #keep pinging until get result
        print(hashValue)
        # Redirect the user to the uploaded_file route, which
        # will basicaly show on the browser the uploaded file
        return render_template('results.html', jsonSent=jsonToSend, message="Wait for it...")

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

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from vss_flask import app
from werkzeug import secure_filename 
import pdb

import numpy as np
from PIL import Image
import imagehash
import time
import json

from kafka import KafkaProducer
#kafka_node_dns="http://ec2-52-41-224-1.us-west-2.compute.amazonaws.com"
kafka_node_dns1='ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092'
kafka_node_dns2='ec2-52-33-155-170.us-west-2.compute.amazonaws.com:9092'
kafka_node_dns3='ec2-54-69-1-84.us-west-2.compute.amazonaws.com:9092'
kafka_node_dns4='ec2-52-35-12-160.us-west-2.compute.amazonaws.com:9092'

#producer = KafkaProducer(bootstrap_servers =  kafka_node_dns + ':9092')
producer = KafkaProducer(bootstrap_servers = 'ec2-52-41-224-1.us-west-2.compute.amazonaws.com:9092', value_serializer=lambda v: json.dumps(v).encode('ascii'))


# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = 'uploads/'
# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']



#ec2-52-41-224-1.us-west-2.compute.amazonaws.com:80
@app.route('/')
def home():
	title = "VSS"
	return render_template('home.html', title=title)
 
@app.route('/about')
def about():
	title="VSS"
	message="work in progress..."
	return render_template('about.html', title=title, message=message)


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
        #return redirect(url_for('get_uploadedFile', filename=filename))

# This route is expecting a parameter containing the name
# of a file. Then it will locate that file on the upload
# directory and show it on the browser, so if the user uploads
# an image, that image is going to be show after the upload
@app.route('/uploads/<filename>')
def get_uploadedFile(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# @app.route('/uploads')
# def uploads():
#     return render_template('uploads.html')

#! /usr/bin/env python
from app import app
app.run(host='0.0.0.0', port=80, debug = True, threaded=True) 

#Note about the using threaded option, not for production
#http://stackoverflow.com/questions/14814201/can-i-serve-multiple-clients-using-just-flask-app-run-as-standalone

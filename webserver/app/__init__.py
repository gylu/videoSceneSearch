from flask import Flask, render_template

app = Flask(__name__)
#app = Flask(__name__, static_folder='static', static_url_path='')

from app import views

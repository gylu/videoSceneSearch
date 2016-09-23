from flask import Flask, render_template
app = Flask(__name__)

from vss_flask import views

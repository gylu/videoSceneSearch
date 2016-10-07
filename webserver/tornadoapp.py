#! /usr/bin/env python

from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler, RequestHandler, Application
from app import app
from tornado.httpserver import HTTPServer
from tornado import gen

# http_server = HTTPServer(WSGIContainer(app))
# http_server.listen(80)
# IOLoop.instance().start()

class MainHandler(RequestHandler):
 def get(self):
   self.write("This message comes from Tornado ^_^")

tr = WSGIContainer(app)

application = Application([
(r"/tornado", MainHandler),
(r".*", FallbackHandler, dict(fallback=tr)),
])

if __name__ == "__main__":
 application.listen(80)
 IOLoop.instance().start()
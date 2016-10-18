#Note, this is heavily copied from this stack overflow site:
#http://stackoverflow.com/questions/34809795/tensorflow-return-similar-images

#What i found though was that it was taking too long to describe an image using inception
#and then when I tried to using the pool3 layer to find similar images, it found too many that were similar that didn't appear to be similar
#i ultimately abandoned trying to move this to the cluster


# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
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
# ==============================================================================

"""Simple image classification with Inception.

Run image classification with Inception trained on ImageNet 2012 Challenge data
set.

This program creates a graph from a saved GraphDef protocol buffer,
and runs inference on an input JPEG image. It outputs human readable
strings of the top 5 predictions along with their probabilities.

Change the --image_file argument to any jpg image to compute a
classification of that image.

Please see the tutorial and website for a detailed description of how
to use this script to perform image recognition.

https://tensorflow.org/tutorials/image_recognition/
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os.path
import re
import sys
import tarfile

import numpy as np
from six.moves import urllib
import tensorflow as tf

#from scipy import spatial #ADDED
import math
import glob

FLAGS = tf.app.flags.FLAGS

# classify_image_graph_def.pb:
#   Binary representation of the GraphDef protocol buffer.
# imagenet_synset_to_human_label_map.txt:
#   Map from synset ID to a human readable string.
# imagenet_2012_challenge_label_map_proto.pbtxt:
#   Text representation of a protocol buffer mapping a label to synset ID.
tf.app.flags.DEFINE_string(
    'model_dir', '/tmp/imagenet',
    """Path to classify_image_graph_def.pb, """
    """imagenet_synset_to_human_label_map.txt, and """
    """imagenet_2012_challenge_label_map_proto.pbtxt.""")
tf.app.flags.DEFINE_string('image_file', '',
                           """Absolute path to image file.""")
tf.app.flags.DEFINE_integer('num_top_predictions', 5,
                            """Display this many predictions.""")

# pylint: disable=line-too-long
DATA_URL = 'http://download.tensorflow.org/models/image/imagenet/inception-2015-12-05.tgz'
#DATA_URL = 'http://download.tensorflow.org/models/image/imagenet/inception-v3-2016-03-01.tar.gz'
# pylint: enable=line-too-long



def create_graph():
  """Creates a graph from saved GraphDef file and returns a saver."""
  # Creates graph from saved graph_def.pb.
  with tf.gfile.FastGFile(os.path.join(
      FLAGS.model_dir, 'classify_image_graph_def.pb'), 'rb') as f:
    graph_def = tf.GraphDef()
    graph_def.ParseFromString(f.read())
    _ = tf.import_graph_def(graph_def, name='')


def run_inference_on_image(image):
  if not tf.gfile.Exists(image):
    tf.logging.fatal('File does not exist %s', image)
  image_data = tf.gfile.FastGFile(image, 'rb').read()
  create_graph()
  with tf.Session() as sess:
    feature_tensor = sess.graph.get_tensor_by_name('pool_3:0') #ADDED
    feature_set = sess.run(feature_tensor,{'DecodeJpeg/contents:0': image_data}) #ADDED
    feature_set = np.squeeze(feature_set) #ADDED
    print(feature_set) #ADDED
  return feature_set


def getVect(filepath):
  results=[]
  create_graph()
  with tf.Session() as sess:
    feature_tensor = sess.graph.get_tensor_by_name('pool_3:0') #ADDED
    for image in glob.glob(os.path.join(filepath,"*.jpg")):
      # if not tf.gfile.Exists(image):
      #   tf.logging.fatal('File does not exist %s', image)
      # else:
      image_data = tf.gfile.FastGFile(image, 'rb').read()
      feature_set = sess.run(feature_tensor,{'DecodeJpeg/contents:0': image_data}) #ADDED
      feature_set = np.squeeze(feature_set) #ADDED
      results.append(feature_set)
      #print("feature_set: ", feature_set) #ADDED
  return results


def maybe_download_and_extract():
  """Download and extract model tar file."""
  dest_directory = FLAGS.model_dir
  if not os.path.exists(dest_directory):
    os.makedirs(dest_directory)
  filename = DATA_URL.split('/')[-1]
  filepath = os.path.join(dest_directory, filename)
  if not os.path.exists(filepath):
    def _progress(count, block_size, total_size):
      sys.stdout.write('\r>> Downloading %s %.1f%%' % (
          filename, float(count * block_size) / float(total_size) * 100.0))
      sys.stdout.flush()
    filepath, _ = urllib.request.urlretrieve(DATA_URL, filepath, _progress)
    print()
    statinfo = os.stat(filepath)
    print('Succesfully downloaded', filename, statinfo.st_size, 'bytes.')
  tarfile.open(filepath, 'r:gz').extractall(dest_directory)


def cosine_similarity(v1,v2):
    "compute cosine similarity of v1 to v2: (v1 dot v2)/{||v1||*||v2||)"
    sumxx, sumxy, sumyy = 0, 0, 0
    for i in range(len(v1)):
        x = v1[i]; y = v2[i]
        sumxx += x*x
        sumyy += y*y
        sumxy += x*y
    return sumxy/math.sqrt(sumxx*sumyy)



def main(_):
  maybe_download_and_extract()
  #image = (FLAGS.image_file if FLAGS.image_file else os.path.join(FLAGS.model_dir, 'cropped_panda.jpg'))
  #run_inference_on_image(image)
  results=getVect("frames")
  oneImage="explosion_fm_online.jpg"
  oneImage="frame1505.jpg"
  abc=run_inference_on_image(oneImage)
  a=[]
  for vect in results:
    a.append(cosine_similarity(vect,abc))
  indicies_of_most_similar=sorted(range(len(a)), key=lambda i: a[i])[-5:]

  # vectOneImage=run_inference_on_image(oneImage)
  # dictAllFiles={}
  # for file in os.listdir('frames'):
  #   if not file ==".DS_Store":
  #     print("file: ", file)
  #     vect=run_inference_on_image(os.path.join("frames/",file))
  #     #print("vect len: ", len(vect))
  #     #print("vect: ", vect)
  #     dictAllFiles[file]=vect
  #     result = cosine_similarity(vectOneImage, vect)
  #     print("resut: ", result)

if __name__ == '__main__':
  tf.app.run()

# error ValueError: GraphDef cannot be larger than 2GB
#http://stackoverflow.com/questions/36349049/overcome-graphdef-cannot-be-larger-than-2gb-in-tensorflow

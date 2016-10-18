# Video Scene Search

[Video Scene Search](https://vss.rocks)

See presentation at http://bit.do/georgelu


## Table of contents
1. [Introduction](README.md#introduction)
2. [Data Pipeline](README.md#data-pipeline)
3. [Performance](README.md#performance)
4. [Challenges and Future Improvements](README.md#challenges-and-future-improvements)


## Introduction 


[Video Scene Search](http://vss.rocks) lets you perform an image search for video scenes that are similar. The user uploads an image and VSS will return with video recommendations and time in the video where a similar scene was found.

The contents of this readme can be seen as slides at https://bit.do/georgelu/. Demo [video](https://www.youtube.com/watch?v=XtXn3fWwENI).

## Data Pipeline

Overview of Pipeline
* Takes videos stored in HDFS and runs a Spark Batch job on it
 * Spark batch job extracts frames from each video, then hashes each frame, stores it in Cassandra database. A perceptual hash is used
* Users submit images they want to search for
 * The Flask front end hashes the image, and then attempts to find the most similar image(s) in the existing Cassandra database
 * Similarity is determined by hamming distance
 * Information about the most similar frames, the video the belong time, and the time of their occurence in the video is returned to the user
 * For the most similar frames, distance similarity against all the frames of the entire video that the closest frame belongs to is also sent back to the user

The image below depicts the underlying data pipeline and cluster size.

![Alt text](content_for_readme/pipeline.png?raw=true "Pipeline")

### Data source
Data source consists of ~8gb of youtube videos (mostly trailers, ~12.5hrs of video time), downloaded using the youtube-dl tool.



## Performance

* Batch Processing: Approx 38minutes to hash 270,000 frames. (Every 5th frame was hashed)
* Stream processing: For new image queries, approximately 50 seconds to return with recommendations
* Accuracy: Not very good except for black-screen scenes or credit scenes. (Due to perceptual hashing algorithm not being very good for describing/fingerprinting image)


## Challenges and Future Improvements

What doesn't work very well:
* Need to reduce search space. Doing the "all pairs" distance calculation through each row in the existing frames database to find the most similar frame is not scalable. Need to find a way search only a partition and not the whole database
 * Find some way to cluster and partition the database
* Need to speed up the similarity searching
 * Currently, the project does a join of a DStream RDD against the large static RDD that has all the existing frames. This join is extremeley slow (Takes about 45 seconds when Dstream RDD has 1 item, and the static RDD has ~400k rows). dstreamRDD.join(staticRDD) and staticRDD.join(dstreamRDD) are both the same slowness. Maybe a bottle neck in the join (or something) is also causing things to run super slow (and maybe on one node?)
  * Broadcasting the large static RDD (to avoid the join) was not done because this is also not as scalable, in case more videos are added to the database, each video results in thousands of frames, so thousands of additional rows to the database. There is a limit to what can be broadcasted. Most forums are saying only 2^31 rows can be broadcasted (2 billion rows? or 2 GB?), due to some java int size thing within Spark. At 30 frames per second, this is about 20,000hrs of videos, or approx 10,000 2hr long videos. See here: http://apache-spark-user-list.1001560.n3.nabble.com/Is-it-common-in-spark-to-broadcast-a-10-gb-variable-td2604.html  Note that the number of movies made in history is >100k
* Perceptual hash sucks. It's only good for finding duplicates, not really good for finding similaries. Maybe alternatives to perceptual hashing can be tried:
 * Color histogram. Because currently, perceptual hash discards all color information as it only quantifies "image frequency" using discrete cosine transform
 * Try Tensor Flow's trained Inception V3
  * Run Inception v3 on each image to get a vector of detected/recognized objects, then do cosine similarity to compare images. See here: http://stackoverflow.com/questions/34809795/tensorflow-return-similar-images. I briefly attempted this, but it was taking about 5 seconds per image to classify (return the pool_3:0 tensor). Other users online have optimized it to about 1 second per image, but since i have ~400k images, this would still take a hundred hours (about a week), and this project is only 4 weeks long
* Other thoughts
 * Perhaps use Elastic Search instead of using Spark to do the comparison in attempt to search for the most similar image?
 * For the batch phase, be able to distributedly process a single video

[Back to Table of contents](README.md#table-of-contents)

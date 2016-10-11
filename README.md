# videoSceneSearch

What this project does:
* Takes videos stored in HDFS and runs a Spark Batch job on it
** Spark batch job extracts frames from each video, then hashes each frame, stores it in Cassandra database. A perceptual hash is used
* Users submit images they want to search for
** The Flask front end hashes the image, and then attempts to find the most similar image(s) in the existing Cassandra database
** Similarity is determined by hamming distance
** Information about the most similar frames, the video the belong time, and the time of their occurence in the video is returned to the user
** For the most similar frames, distance similarity against all the frames of the entire video that the closest frame belongs to is also sent back to the user

See presentation at http://bit.do/georgelu

Future work:
* Need to reduce search space. Doing the "all pairs" distance calculation through each row in the existing frames database to find the most similar frame is not scalable. Need to find a way search only a partition and not the whole database
** Find some way to cluster and partition the database
* Need to speed up the similarity searching
** Currently, the project does a join of a DStream RDD against the large static RDD that has all the existing frames. This join is extremeley slow (Takes about 45 seconds when Dstream RDD has 1 item, and the static RDD has ~400k rows). dstreamRDD.join(staticRDD) and staticRDD.join(dstreamRDD) are both the same slowness.
*** Broadcasting the large static RDD (to avoid the join) was not done because this is also not as scalable, in case more videos are added to the database, each video results in thousands of frames, so thousands of additional rows to the database. There is a limit to what can be broadcasted. Most forums are saying only 2^31 rows can be broadcasted (2 billion rows? or 2 GB?), due to some java int size thing within Spark. At 30 frames per second, this is about 20,000hrs of videos, or approx 10,000 2hr long videos. See here: http://apache-spark-user-list.1001560.n3.nabble.com/ Is-it-common-in-spark-to-broadcast-a-10-gb-variable-td2604.html  Note that the number of movides made in history is >100k
** Currently, for some reason, a bottle neck in the join (or something) is also causing things to run super slow (and maybe on one node?)
* Perceptual hash sucks. It's only good for finding duplicates, not really good for finding similaries. 
*** In the future, use Tensor Flow's trained Inception V3
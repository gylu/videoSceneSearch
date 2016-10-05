#!/bin/bash      

#kung fury, 30 minutes
youtube-dl -i --restrict-filenames -o "/home/ubuntu/videos_long/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/watch?v=bS5P_LAqiVg
#mongol, 2hrs
youtube-dl -i --restrict-filenames -o "/home/ubuntu/videos_long/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/watch?v=NxoBfbhoEmo
#wesley snipes, the marksman 1.5hr
youtube-dl -i --restrict-filenames -o "/home/ubuntu/videos_long/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/watch?v=lLr7d88-BT0
#ayrton sena the marksman 1hr 45min
youtube-dl -i --restrict-filenames -o "/home/ubuntu/videos_long/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/watch?v=76sEQnqKesM
#documentary playlist, 200 movies, some 2hrs long
youtube-dl -i --restrict-filenames -o "/home/ubuntu/videos_long/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/playlist?list=PLi4lYGGXHIkODAkKFIXtLZpAjMptl-xSl

##Trying to get youtube videos into and out of kafka
#youtube-dl https://www.youtube.com/playlist?list=PLBDA074E6B463154D | /usr/local/kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic myVideos

#/usr/local/kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic myVideos << youtube-dl https://www.youtube.com/playlist?list=PLBDA074E6B463154D

#Restrict filenames, and ignore errors
#Download from a url to a folder called videoFiles. Removing spaces from filenames and ignoring errors. Seems to work locally only
#youtube-dl -i --restrict-filenames -o "videoFiles/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/watch?v=yWyj9ORkj8w

#into HDFS directly by using std out? (doesn't work)
#youtube-dl -i --restrict-filenames -o - https://www.youtube.com/watch?v=yWyj9ORkj8w | hdfs dfs -put - "/videoFiles/%(title)s-%(id)s.%(ext)s"

#into HDFS directly?
#youtube-dl -i --restrict-filenames -o "/videoFiles/%(title)s-%(id)s.%(ext)s" https://www.youtube.com/watch?v=yWyj9ORkj8w | hdfs dfs -put - "/videoFiles/%(title)s-%(id)s.%(ext)s"

#Onto s3?
#youtube-dl -i --restrict-filenames -o - https://www.youtube.com/watch?v=yWyj9ORkj8w | aws s3 mv - s3://videoscenesearch/videoFiles/%(title)s-%(id)s.%(ext)s

#FFmpeg local usage (quality still seems to be smaller image size):
#./ffmpeg -i Superman_s_True_Power-yWyj9ORkj8w.mp4 -q:v 1 ./frames_superman_ffmpeg/filename%03d.jpg

# videoSceneSearch


See presentation at http://bit.do/georgelu

When cassandra database is at a size of approx 211,000 rows (derived from ~400 youtube videos, totaling ~8gigs), querying for an image took up to 400 seconds, because of this line:

streamFromKafka.transform(lambda rdd: rdd.map(lambda x: (1,x[1])).join(db_table.map(lambda x: (1,x)))).map(addDistanceInfo).foreachRDD(takeTop)

What I believe I'm doing wrong is I am joining a big table onto a small table, and that is causing me to move the entire contents of the big table


Takes 100 seconds if I don't do a collect
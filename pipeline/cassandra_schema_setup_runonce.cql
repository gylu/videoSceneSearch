//CassandraCQL shell
CREATE KEYSPACE test WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 3};
USE test;
DROP TABLE ages;
CREATE TABLE ages (
	name text,
	age int, 
	PRIMARY KEY (name)
);

INSERT INTO ages (name, age) VALUES ('name1', 23);
INSERT INTO ages (name, age) VALUES ('name2', 23);
INSERT INTO ages (name, age) VALUES ('name3', 23);
INSERT INTO ages (name, age) VALUES ('name4', 23);
SELECT * FROM ages;


//test on pyspark with cassandra: 
/*
import pyspark_cassandra
rdd=sc.parallelize([{"name":"john","age":23},{"name":"tom","age":24}, {"name":"matt","age":24},{"name":"gary","age":24}])
rdd=sc.parallelize([{"name":"john3","age":23}])
rdd.saveToCassandra("test","ages");
*/


////////////////////////////////////////////////////////////
//Create tables 
CREATE KEYSPACE vss WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 3};

USE vss;
DROP TABLE hval;
CREATE TABLE hval (
	partitionby int,
	hashvalue text,
	videoname text,
	framenumber int,
	frametime float,
	youtubelink text,
	PRIMARY KEY (partitionby, hashvalue)
) WITH CLUSTERING ORDER BY (hashvalue ASC);

//do I need time if all I am going to do with it is used to avoiding duplicate primary key?
//is it ok to have everything as primary key?
//using blog because Cassandra doesn't support unsigned 64bit int

//timestamp is used as a primary key in case user uploads a video with the same name
DROP TABLE vname;
CREATE TABLE vname (
	hashvalue text,
	videoname text,
	framenumber int,
	time timestamp,
	youtubelink text,
	PRIMARY KEY (videoname, framenumber, time)
) WITH CLUSTERING ORDER BY (framenumber ASC);

/////////////////////////////////////////////////////////////////////

//To note regarding blobs and storing them as hex
//http://stackoverflow.com/questions/31994880/why-cassandra-cql-query-with-hexadecimal-literal-works-but-textasbinary-does-not

INSERT INTO hval (videoName, partitionby, hashValue, frameNumber) VALUES ('testVidName', 23, 'hashvdalaaaa', 24);

//test on pyspark with cassandra: 
/*
import pyspark_cassandra
rdd=sc.parallelize([{'partitionby':233, 'hashvalue':'asfd', 'videoname':'vidnameeee2', 'framenumber':234}])
rdd.saveToCassandra('vss','hval')
*/

SELECT * FROM hval;


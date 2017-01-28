//CassandraCQL shell

////////////////////////////////////////////////////////////
//Create tables 
CREATE KEYSPACE vss WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 3};
USE vss;

/////////////////////////////////////////////////////////////////////
DROP TABLE vname;


/////////////////////////////////////////////////////////////////////

CREATE TABLE vname (
	hashvalue text,
	videoname text,
	framenumber int,
	frametime float,
	youtubelink text,
	PRIMARY KEY (videoname, framenumber)
) WITH CLUSTERING ORDER BY (framenumber ASC);

/////////////////////////////////////////////////////////////////////


DROP TABLE queryresults;
CREATE TABLE queryresults (
	imagename text,
	targetimagehash text,
	framehash text,
	videoname text,
	framenumber int,
	distance int,
	frametime float,
	youtubelink text,
	PRIMARY KEY (targetimagehash, distance, framenumber)
) WITH CLUSTERING ORDER BY (distance ASC);

/////////////////////////////////////////////////////////////////////

//this table stores the distances of a target image against all the frames of a particular video

DROP TABLE distances;
CREATE TABLE distances (
	imagename text,
	targetimagehash text,
	framehash text,
	videoname text,
	framenumber int,
	distance int,
	frametime float,
	PRIMARY KEY (videoname, targetimagehash, frametime)
);

/////////////////////////////////////////////////////////////////////
















//this table hval was not needed or used. the original intention was to use it for partitioning based on the hash value. But I ultimatley couldn't figure out a good way to do that.

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


//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
////// another keyspace using histograms, in addition to hamming distance ////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
CREATE KEYSPACE vss_hist WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 3};
USE vss_hist;

/////////////////////////////////////////////////////////////////////
//thoughts on using blob storage vs string storage http://stackoverflow.com/questions/31339150/what-are-the-pros-or-cons-of-storing-json-as-text-vs-blob-in-cassandra
drop table vname;

CREATE TABLE vname (
	hashvalue text,
	videoname text,
	framenumber int,
	frametime float,
	youtubelink text,
	histogramvector text,
	PRIMARY KEY (videoname, framenumber)
) WITH CLUSTERING ORDER BY (framenumber ASC);

/////////////////////////////////////////////////////////////////////

DROP TABLE queryresults;
CREATE TABLE queryresults (
	imagename text,
	targetimagehash text,
	framehash text,
	videoname text,
	framenumber int,
	distance int,
	frametime float,
	youtubelink text,
	cosinesimilarity float,
	PRIMARY KEY ((targetimagehash, imagename), cosinesimilarity)
) WITH CLUSTERING ORDER BY (cosinesimilarity ASC);

/////////////////////////////////////////////////////////////////////

DROP TABLE distances;
CREATE TABLE distances (
	imagename text,
	targetimagehash text,
	framehash text,
	videoname text,
	framenumber int,
	distance int,
	frametime float,
	cosinesimilarity float,
	PRIMARY KEY ((videoname, targetimagehash, imagename), frametime)
);

/////////////////////////////////////////////////////////////////////





//To note regarding blobs and storing them as hex
//http://stackoverflow.com/questions/31994880/why-cassandra-cql-query-with-hexadecimal-literal-works-but-textasbinary-does-not



/////////// Example usages//////////////
CREATE KEYSPACE mykeyspace WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 3};

USE mykeyspace;

CREATE TABLE ages (
	id int,
	name text,
	age int,
	PRIMARY KEY (id)
);

INSERT INTO ages (id, name, age) VALUES (800, 'name1', 23);
INSERT INTO ages (id, name) VALUES (801, 'name2');

cqlsh:mykeyspace> INSERT INTO ages (id, name, age) VALUES (800, 'name1', 23);
cqlsh:mykeyspace> INSERT INTO ages (id, name) VALUES (801, 'name2');
cqlsh:mykeyspace> select * from ages;

 id  | age  | name
-----+------+-------
 801 | null | name2
 800 |   23 | name1


//Using allow filtering
cqlsh:mykeyspace> select * from ages where name='name2';
InvalidRequest: code=2200 [Invalid query] message="Cannot execute this query as it might involve data filtering and thus may have unpredictable performance. If you want to execute this query despite the performance unpredictability, use ALLOW FILTERING"

cqlsh:mykeyspace> select * from ages where name='name2' ALLOW FILTERING;

 id  | age  | name
-----+------+-------
 801 | null | name2


cqlsh:mykeyspace> select * from ages where id>799;
InvalidRequest: code=2200 [Invalid query] message="Only EQ and IN relation are supported on the partition key (unless you use the token() function)"
cqlsh:mykeyspace> select * from ages where id>799;

//another example
DROP TABLE ages;
CREATE TABLE ages2 (
	id int,
	name text,
	age int,
	PRIMARY KEY (age, name)
);


INSERT INTO ages2 (id, name, age) VALUES (801, 'jim', 23);
INSERT INTO ages2 (id, name, age) VALUES (802, 'jake', 23);
INSERT INTO ages2 (id, name, age) VALUES (803, 'jim', 23);
INSERT INTO ages2 (id, name, age) VALUES (804, 'jake', 24);
INSERT INTO ages2 (id, name, age) VALUES (805, 'jake', 24);


CREATE TABLE ages3 (
	id int,
	name text,
	age int,
	gpa float,
	PRIMARY KEY ((age, name), gpa)
);


INSERT INTO ages3 (id, name, age, gpa) VALUES (801, 'jim', 23, 3.5);
INSERT INTO ages3 (id, name, age, gpa) VALUES (801, 'jim', 23, 1.2);
INSERT INTO ages3 (id, name, age, gpa) VALUES (801, 'jim', 23, 4.3);
INSERT INTO ages3 (id, name, age, gpa) VALUES (801, 'jim', 23, 2.1);




//////////test on pyspark with cassandra: 
/*
import pyspark_cassandra
rdd=sc.parallelize([{"name":"john","age":23},{"name":"tom","age":24}, {"name":"matt","age":24},{"name":"gary","age":24}])
rdd=sc.parallelize([{"name":"john3","age":23}])
rdd.saveToCassandra("test","ages");
*/




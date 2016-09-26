/usr/local/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 3 --partitions 2 --topic imgSearchRequests
/usr/local/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 3 --partitions 2 --topic searchReturns



#For monitoring:
/usr/local/kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic imgSearchRequests

/usr/local/kafka/bin/kafka-console-consumer.sh --zookeeper localhost:2181 --from-beginning --topic imgSearchRequests

/usr/local/kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic searchReturns

/usr/local/kafka/bin/kafka-console-consumer.sh --zookeeper localhost:2181 --from-beginning --topic searchReturns
from confluent_kafka import SerializingProducer, DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer
from confluent_kafka.serialization import StringSerializer, StringDeserializer

import requests

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

SCHEMA_REGISTRY = 'http://schema-registry:8080'

class KafkaProducer:

    def __init__(self, topic):
        self.topic = topic

        schema_registry_client = SchemaRegistryClient({'url': SCHEMA_REGISTRY})
        schema = None
        while not schema:
            try:
                schema = schema_registry_client.get_latest_version(topic).schema
            except requests.exceptions.ConnectionError:
                pass
            except confluent_kafka.schema_registry.error.SchemaRegistryError:
                pass
            except Exception as e:
                print("Kafka Messenger", e)
        avro_serializer = AvroSerializer(schema_registry_client, schema.schema_str)
        string_serializer = StringSerializer('utf_8')

        producer_conf = {
            'bootstrap.servers': 'kafka:9092',
            'key.serializer': string_serializer,
            'value.serializer': avro_serializer
        }

        self.producer = SerializingProducer(producer_conf)

    def produce(self, key, value):
        self.producer.produce(topic=self.topic, key=key, value=value)

    def flush(self):
        self.producer.flush()


class KafkaConsumer:

    def __init__(self, topic):
        self.topic = topic
        schema_registry_client = SchemaRegistryClient({'url': SCHEMA_REGISTRY})
        avro_deserializer = AvroDeserializer(schema_registry_client)
        string_deserializer = StringDeserializer('utf_8')

        consumer_conf = {
            'bootstrap.servers': 'kafka:9092',
            'key.deserializer': string_deserializer,
            'value.deserializer': avro_deserializer,
            'group.id': 'integration',
            'auto.offset.reset': 'earliest'
        }

        self.consumer = DeserializingConsumer(consumer_conf)
        self.consumer.subscribe([self.topic])

    def consume(self):
        return self.consumer.poll(10)
from confluent_kafka import Producer
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class KafkaProducerClient:
    def __init__(self, bootstrap_servers="localhost:9092"):
        """
        Initialize Kafka Producer with specified bootstrap servers.
        """
        self.producer = Producer({'bootstrap.servers': bootstrap_servers})

    def send(self, topic, message, key=None):
        """
        Send a message to a Kafka topic with optional key.
        """
        try:
            self.producer.produce(topic, key=key, value=json.dumps(message).encode('utf-8'))
            self.producer.flush()  # Ensure message is delivered
            logger.info(f"Message sent successfully to topic: {topic}")
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}")

    def close(self):
        """
        Close the Kafka Producer.
        """
        self.producer.flush()
        logger.info("Kafka Producer closed.")

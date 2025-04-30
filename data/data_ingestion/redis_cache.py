import redis
import json

class RedisCache:
    def __init__(self):
        self.redis_client = redis.Redis(host="localhost", port=6379, db=0)

    def store_data(self, key, data):
        self.redis_client.set(key, json.dumps(data))

    def fetch_data(self, key):
        raw_data = self.redis_client.get(key)
        return json.loads(raw_data) if raw_data else None

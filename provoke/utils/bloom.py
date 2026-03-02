import redis
import logging
from provoke.config import config

logger = logging.getLogger(__name__)


class RedisBloomFilter:
    """
    A persistent, distributed Bloom Filter backed by Redis.
    Requires the RedisBloom module to be installed on the Redis server.
    Falls back to a regular Redis Set if the Bloom module is not available
    (though this is less space-efficient).
    """

    def __init__(
        self,
        name=None,
        host=None,
        port=None,
        db=None,
        capacity=None,
        error_rate=None,
    ):
        self.name = name or config.BLOOM_FILTER_NAME
        self.host = host or config.REDIS_HOST
        self.port = port or config.REDIS_PORT
        self.db = db or config.REDIS_DB
        self.capacity = capacity or config.BLOOM_FILTER_CAPACITY
        self.error_rate = error_rate or config.BLOOM_FILTER_ERROR_RATE

        self.redis = redis.Redis(
            host=self.host, port=self.port, db=self.db, decode_responses=True
        )

        self._use_bloom = True
        self._initialized = False
        self._provision_filter()

    def _provision_filter(self):
        """Create the bloom filter if it doesn't exist."""
        try:
            # Check if the Bloom module is available by trying to INFO the filter
            # or just try to create it.
            self.redis.execute_command(
                "BF.RESERVE", self.name, self.error_rate, self.capacity
            )
            logger.info(
                f"Created Redis Bloom Filter '{self.name}' with capacity {self.capacity}"
            )
            self._initialized = True
        except redis.exceptions.ResponseError as e:
            if "item already exists" in str(e).lower():
                self._initialized = True
                logger.debug(f"Bloom Filter '{self.name}' already exists.")
            else:
                logger.warning(
                    f"RedisBloom module not detected or error creating filter: {e}. Falling back to Redis SET."
                )
                self._use_bloom = False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}. Bloom Filter disabled.")
            self._use_bloom = False

    def add(self, item: str) -> bool:
        """Add an item to the filter. Returns True if successful."""
        try:
            if self._use_bloom:
                # BF.ADD returns 1 if item was added, 0 if it already existed
                return bool(self.redis.execute_command("BF.ADD", self.name, item))
            else:
                # Fallback to SADD
                return bool(self.redis.sadd(f"{self.name}:set", item))
        except Exception as e:
            logger.debug(f"Error adding to Bloom Filter: {e}")
            return False

    def exists(self, item: str) -> bool:
        """Check if an item exists in the filter."""
        try:
            if self._use_bloom:
                # BF.EXISTS returns 1 if item exists, 0 if not
                return bool(self.redis.execute_command("BF.EXISTS", self.name, item))
            else:
                # Fallback to SISMEMBER
                return bool(self.redis.sismember(f"{self.name}:set", item))
        except Exception as e:
            logger.debug(f"Error checking Bloom Filter: {e}")
            return False

    def __contains__(self, item: str) -> bool:
        return self.exists(item)

    def clear(self):
        """Delete the filter."""
        try:
            if self._use_bloom:
                self.redis.delete(self.name)
            else:
                self.redis.delete(f"{self.name}:set")
            self._provision_filter()
        except Exception as e:
            logger.error(f"Error clearing Bloom Filter: {e}")

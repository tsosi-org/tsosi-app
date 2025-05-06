import logging
import time

import pandas as pd
import redis
import redis.exceptions
from tsosi.app_settings import app_settings

logger = logging.getLogger(__name__)
console_logger = logging.getLogger("console_only")


REDIS_CLIENT = redis.StrictRedis(
    host=app_settings.REDIS_HOST,
    port=app_settings.REDIS_PORT,
    db=app_settings.REDIS_DB,
)


class TokenBucket:
    """
    Implement the token bucket algorithm to handle rate limited tasks.
    The bucket is automatically refilled if necessary before every token
    consumption request.
    This should be set as a periodic task instead if the number of
    consumption request grows significantly.
    """

    # KEYS[1] - token bucket name
    # KEYS[2] - last refill time name
    # KEYS[3] - first consumption time name
    # ARGV[1] - desired number of tokens
    # ARGV[2] - current time
    # Consume/decrease the token bucket with
    # the minimum of (available tokens, desired tokens), then
    # update the bucket's first consumption time
    LUA_CONSUME_TOKEN_SCRIPT = """
        local current_tokens = tonumber(redis.call('GET', KEYS[1]))
        if not current_tokens then return 0 end
        local tokens_to_consume = math.min(current_tokens, tonumber(ARGV[1]))
        if tokens_to_consume > 0 then
            redis.call('DECRBY', KEYS[1], tokens_to_consume)
        end

        local last_refill_time = tonumber(redis.call('GET', KEYS[2]))
        local first_consumption_time = tonumber(redis.call('GET', KEYS[3]))
        local current_time = tonumber(ARGV[2])

        if not last_refill_time then
            return tokens_to_consume
        end
        if not first_consumption_time or first_consumption_time < last_refill_time then
            redis.call('SET', KEYS[3], math.max(last_refill_time, current_time))
        end

        return tokens_to_consume
    """
    # KEYS[1] - token bucket name
    # KEYS[2] - last refill time name
    # KEYS[3] - first consumption time name
    # ARGV[1] - token number
    # ARGV[2] - refill time
    # Refill the bucket and refresh associated variables.
    LUA_REFILL_TOKEN_SCRIPT = """
        redis.call('SET', KEYS[1], ARGV[1])
        redis.call('SET', KEYS[2], ARGV[2])
        redis.call('DEL', KEYS[3])
        return 1
    """

    def __init__(
        self,
        redis: redis.Redis,
        bucket_name: str,
        max_tokens: int,
        refill_period: int,
    ):
        """
        :params redis:          The redis.Redis client.
        :params bucket_name:    The name of the bucket to be used in Redis.
        :params max_tokens:     The maximum number of tokens the bucket can hold.
        :params refill_period:  The number of seconds before the bucket should
                                be replenished.
        """
        cls = self.__class__
        self.redis = redis
        self.bucket_name = bucket_name
        self.max_tokens = max_tokens
        self.refill_period = refill_period
        # Redis keys
        self.token_count_key = f"{bucket_name}:token_count"
        self.last_refill_time_key = f"{bucket_name}:last_refill_time"
        self.first_consumption_time_key = (
            f"{bucket_name}:first_consumption_time"
        )
        # Lua scripts
        self.lua_token_consume = self.redis.register_script(
            cls.LUA_CONSUME_TOKEN_SCRIPT
        )
        self.lua_refill_token = self.redis.register_script(
            cls.LUA_REFILL_TOKEN_SCRIPT
        )

    def _refill(self):
        """
        Refill the token bucket if it's time.
        """
        last_refill_time: bytes | None = self.redis.get(
            self.last_refill_time_key
        )
        first_consumption_time: bytes | None = self.redis.get(
            self.first_consumption_time_key
        )
        last_refill_time = (
            None
            if last_refill_time is None
            else float(last_refill_time.decode("utf-8"))
        )
        first_consumption_time = (
            None
            if first_consumption_time is None
            else float(first_consumption_time.decode("utf-8"))
        )
        c_time = time.time()
        # Bucket initialization or enough time since first tokens were consumed
        # or since last refill
        if (
            last_refill_time is None
            or (
                first_consumption_time is None
                and c_time - last_refill_time > self.refill_period
            )
            or (
                first_consumption_time is not None
                and first_consumption_time
                and c_time - first_consumption_time > self.refill_period
            )
        ):
            logger.info(
                f"Refilled {self.max_tokens} tokens in bucket {self.bucket_name}"
            )
            self.lua_refill_token(
                keys=[
                    self.token_count_key,
                    self.last_refill_time_key,
                    self.first_consumption_time_key,
                ],
                args=[self.max_tokens, c_time],
                client=self.redis,
            )

    def consume(self, token_number: int, retry=0) -> int:
        """
        Consume the minimum of the given number of token and the number of
        available tokens.
        """
        self._refill()
        tokens_consumed = int(
            self.lua_token_consume(
                keys=[
                    self.token_count_key,
                    self.last_refill_time_key,
                    self.first_consumption_time_key,
                ],
                args=[token_number, time.time()],
                client=self.redis,
            )
        )
        logger.info(
            f"Consumed {tokens_consumed} tokens from bucket {self.bucket_name}."
        )
        return tokens_consumed

    def consume_for_df(self, df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
        """
        Try to consume 1 token of the bucket per row of the given dataframe.
        Return the truncated dataframe for wich a token was consumed.
        """
        tokens_number = len(df)
        if tokens_number == 0:
            return df, False

        tokens_consumed = self.consume(tokens_number)
        if tokens_consumed == tokens_number:
            return df, False
        elif tokens_consumed == 0:
            return pd.DataFrame(), True
        else:
            return df.iloc[0:tokens_consumed].copy(), True


# https://ror.readme.io/v2/docs/rest-api 2000 requests / 5 minutes
ROR_TOKEN_BUCKET = TokenBucket(REDIS_CLIENT, "ror", 2000, 5 * 60)
# The SPARQL service is limited to 60s of query calculation every 60s
# We translate this to 2000 records per minute as a raw approximation.
WIKIDATA_TOKEN_BUCKET = TokenBucket(REDIS_CLIENT, "wikidata", 2000, 60)
# https://en.wikipedia.org/api/rest_v1/#/ The rate limit is 200 requests/s
WIKIPEDIA_TOKEN_BUCKET = TokenBucket(REDIS_CLIENT, "wikipedia", 200, 5)
# It's not clear whether there's a rate limit for downloading files from wikimedia
# We use a "safe" option of 100 files per minute.
# Previous limit of 500/min ended reaching a HTTP 429 status code when
# trying to fetch 447 files at "once". The limit is probably 400/something
WIKIMEDIA_TOKEN_BUCKET = TokenBucket(REDIS_CLIENT, "wikimedia", 200, 60)

TOKEN_BUCKETS = [
    ROR_TOKEN_BUCKET,
    WIKIDATA_TOKEN_BUCKET,
    WIKIPEDIA_TOKEN_BUCKET,
    WIKIMEDIA_TOKEN_BUCKET,
]

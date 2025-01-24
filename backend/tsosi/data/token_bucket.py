import logging
import time
from asyncio import sleep

import pandas as pd
import redis
import redis.exceptions
from tsosi.app_settings import app_settings

logger = logging.getLogger(__name__)
console_logger = logging.getLogger("console_only")
SHARED_BUCKET = "shared"
MAX_RETRY = 3
TOKEN_SCRIPT_SHA_KEY = f"{SHARED_BUCKET}:token_script_sha"
# This script consumes the minimum
TOKEN_LUA_SCRIPT = """
    local current_tokens = tonumber(redis.call('GET', KEYS[1]))
    if not current_tokens then return 0 end
    local tokens_to_consume = math.min(current_tokens, tonumber(ARGV[1]))
    if tokens_to_consume > 0 then
        redis.call('DECRBY', KEYS[1], tokens_to_consume)
    end
    return tokens_to_consume
    """


class TokenBucket:
    """
    Implement the token bucket algorithm to handle rate limited tasks.
    """

    def __init__(self, bucket_name: str, max_tokens: int, refill_period: int):
        """
        :params bucket_name:    The name of the bucket to be used in Redis.
        :params max_tokens:     The maximum number of tokens the bucket can hold.
        :params refill_period:  The number of seconds before the bucket should
                                be replenished.
        """
        self.redis = redis.StrictRedis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
            db=app_settings.REDIS_DB,
        )
        self.bucket_name = bucket_name
        self.max_tokens = max_tokens
        self.refill_period = refill_period
        self.last_refill_time_key = f"{bucket_name}:last_refill_time"
        self.token_count_key = f"{bucket_name}:token_count"

    def refill(self):
        """
        Refill the token bucket if it's time.
        """
        c_time = time.time()
        last_refill_time: bytes | None = self.redis.get(
            self.last_refill_time_key
        )
        if last_refill_time is None:
            last_refill_time = time.time()
            self.redis.set(self.token_count_key, self.max_tokens)
            self.redis.set(self.last_refill_time_key, last_refill_time)
            return
        if (
            c_time - float(last_refill_time.decode("utf-8"))
            > self.refill_period
        ):
            self.redis.set(self.token_count_key, self.max_tokens)

    def _load_script(self) -> str:
        """
        Load the token getter script and store its SHA.
        """
        script_sha = self.redis.script_load(TOKEN_LUA_SCRIPT)
        self.redis.set(TOKEN_SCRIPT_SHA_KEY, script_sha)
        return script_sha

    def _get_script_sha(self) -> str:
        """
        Return the token getter script's SHA.
        """
        script_sha: bytes | str | None = self.redis.get(TOKEN_SCRIPT_SHA_KEY)
        if script_sha is None:
            # The result of script_load is a string
            script_sha = self._load_script()
        else:
            script_sha = script_sha.decode("utf-8")

        return script_sha

    def consume(self, token_number: int, retry=0) -> int:
        """
        Consume the minimum of the given number of token and the number of
        available tokens.
        """
        try:
            script_sha = self._get_script_sha()

            tokens_consumed = self.redis.evalsha(
                script_sha,
                1,
                self.token_count_key,
                token_number,
            )
            logger.info(
                f"Consumed {tokens_consumed} tokens from bucket {self.bucket_name}."
            )
            return int(tokens_consumed)
        except redis.exceptions.NoScriptError as e:
            console_logger.info(f"Error while evaluating Lua script:\n{e}")
            if retry >= MAX_RETRY:
                logger.error(
                    f"Max retries ({MAX_RETRY}) reached while trying "
                    f"to consume {token_number} from bucket {self.bucket_name}"
                )
                raise RecursionError("Max retries reached.")
            # Reload script after a few seconds if it does not exist
            sleep(0.2)
            script_sha = self._get_script_sha()
            scripts_exist = self.redis.script_exists(script_sha)
            if not scripts_exist[0]:
                self._load_script()
            return self.consume(token_number, retry=retry + 1)

    def consume_for_df(self, df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
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
ROR_TOKEN_BUCKET = TokenBucket("ror", 2000, 5 * 60)
# The SPARQL service is limited to 60s of query calculation every 60s
# We translate this to 2000 records per minute as a raw approximation.
WIKIDATA_TOKEN_BUCKET = TokenBucket("wikidata", 2000, 60)
# https://en.wikipedia.org/api/rest_v1/#/ The rate limit is 200 requests/s
WIKIPEDIA_TOKEN_BUCKET = TokenBucket("wikipedia", 200, 5)
# It's not clear whether there's a rate limit for downloading files from wikimedia
# We use a "safe" option of 500 files per minute.
WIKIMEDIA_TOKEN_BUCKET = TokenBucket("wikimedia", 500, 60)

TOKEN_BUCKETS = [
    ROR_TOKEN_BUCKET,
    WIKIDATA_TOKEN_BUCKET,
    WIKIPEDIA_TOKEN_BUCKET,
    WIKIMEDIA_TOKEN_BUCKET,
]

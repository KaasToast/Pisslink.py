import random
from typing import Optional

class Backoff:
    """An implementation of an Exponential Backoff.

    Parameters
    ----------
    base: int
        The base time to multiply exponentially. Defaults to 1.
    maximum_time: float
        The maximum wait time. Defaults to 30.0
    maximum_tries: Optional[int]
        The amount of times to backoff before resetting. Defaults to 5. If set to None, backoff will run indefinitely.
    """

    def __init__(self, *, base: int = 1, maximum_time: float = 30.0, maximum_tries: Optional[int] = 5):
        self._base = base
        self._maximum_time = maximum_time
        self._maximum_tries = maximum_tries
        self._retries: int = 1

        rand = random.Random()
        rand.seed()

        self._rand = rand.uniform

        self._last_wait: float = 0

    def calculate(self) -> float:
        exponent = min((self._retries ** 2), self._maximum_time)
        wait = self._rand(0, (self._base * 2) * exponent)

        if wait <= self._last_wait:
            wait = self._last_wait * 2

        self._last_wait = wait

        if wait > self._maximum_time:
            wait = self._maximum_time
            self._retries = 0
            self._last_wait = 0

        if self._maximum_tries and self._retries >= self._maximum_tries:
            self._retries = 0
            self._last_wait = 0

        self._retries += 1

        return wait
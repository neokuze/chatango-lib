"""
Utility module
"""
import functools
import asyncio
import random
import typing


def virtual(func: typing.Callable) -> typing.Callable:
    """
    Used for virtual functions.
    A call to the wrapped function will always
    raise NotImplementedError.
    Works for both coroutines and normal functions.
    """
    if asyncio.iscoroutinefunction(func):
        async def wrapper(*args, **kwargs):
            raise NotImplementedError
    else:
        def wrapper(*args, **kwargs):
            raise NotImplementedError

    wrapper = functools.wraps(func)(wrapper)
    return wrapper


def gen_uid() -> str:
    """
    Generate an uid
    """
    return str(random.randrange(10 ** 15, 10 ** 16))

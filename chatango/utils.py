"""
Utility module
"""
import functools
import asyncio
import random
import typing

def has_flag(flags: str or int, flag: int) -> bool:
    assert type(flags) in (str, int), "Invalid flags"
    assert type(flag) is int, "Invalid flag"
    return int(flags) & flag

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
    print(func, wrapper)
    return wrapper


def gen_uid() -> str:
    """
    Generate an uid
    """
    return str(random.randrange(10 ** 15, 10 ** 16))

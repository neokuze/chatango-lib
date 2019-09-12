"""
Utility module
"""
import functools
import asyncio
import random
import typing

def gen_uid() -> str:
    """
    Generate an uid
    """
    return str(random.randrange(10 ** 15, 10 ** 16))

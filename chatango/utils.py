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

def parse_flags(FlagInterator, flags):
    _flags = {}
    FLAGS = [flag for flag in dir(FlagInterator) if flag[:2] != "__"]
    for flag in FLAGS:
        if hasattr(FlagInterator(flags), f"{flag}"):
            active_flag = getattr(FlagInterator(flags), f"{flag}")
            if active_flag in FlagInterator(flags):
                _flags[f"{flag}"] = True
            else:
                _flags[f"{flag}"] = False
    return _flags

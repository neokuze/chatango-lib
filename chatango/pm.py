"""
Module for pm related stuff
"""
import asyncio


class PM(Connection):
    """
    Represents a PM Connection
    """
    def __init__(self, client): #clean
        super().__init__(client)
        pass
    
    def __repr__(self):
        return "<PM>"

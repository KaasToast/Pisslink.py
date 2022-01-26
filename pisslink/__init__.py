'''
Pisslink
Minimalistic lavalink wrapper based on wavelink. Made for Pycord.
'''

__title__ = 'Pisslink'
__author__ = 'KaasToast'
__license__ = 'MIT'
__copyright__ = 'Copyright 2019-2021 (c) Pythonista, EvieePy | Copyright 2022-present (c) KaasToast'
__version__ = 'V1'

from . import abc
from .player import Player
from .backoff import Backoff
from .stats import Stats
from .enums import *
from .errors import *
from .pool import *
from .tracks import *
from discord.enums import try_enum
from .enums import ErrorSeverity

__all__ = (
    'PisslinkError',
    'AuthorizationFailure',
    'LavalinkException',
    'LoadTrackError',
    'BuildTrackError',
    'NodeOccupied',
    'InvalidIDProvided',
    'ZeroConnectedNodes',
    'NoMatchingNode',
)

class PisslinkError(Exception):
    pass

class AuthorizationFailure(PisslinkError):
    pass

class LavalinkException(PisslinkError):
    pass

class LoadTrackError(LavalinkException):

    def __init__(self, data):
        exception = data['exception']
        self.severity: ErrorSeverity = try_enum(ErrorSeverity, exception['severity'])
        super().__init__(exception['message'])

class BuildTrackError(LavalinkException):

    def __init__(self, data):
        super().__init__(data['error'])

class NodeOccupied(PisslinkError):
    pass

class InvalidIDProvided(PisslinkError):
    pass

class ZeroConnectedNodes(PisslinkError):
    pass

class NoMatchingNode(PisslinkError):
    pass
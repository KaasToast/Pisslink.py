from .enums import ErrorSeverity

__all__ = (
    "PisslinkError",
    "AuthorizationFailure",
    "LavalinkException",
    "LoadTrackError",
    "BuildTrackError",
    "NodeOccupied",
    "InvalidIDProvided",
    "ZeroConnectedNodes",
    "NoMatchingNode",
)

class PisslinkError(Exception):
    """Base Pisslink Exception"""

class AuthorizationFailure(PisslinkError):
    """Exception raised when an invalid password is provided toa node."""

class LavalinkException(PisslinkError):
    """Exception raised when an error occurs talking to Lavalink."""

class LoadTrackError(LavalinkException):
    """Exception raised when an error occurred when loading a track."""

    def __init__(self, data):
        exception = data["exception"]
        self.severity: ErrorSeverity
        super().__init__(exception["message"])

class BuildTrackError(LavalinkException):
    """Exception raised when a track is failed to be decoded and re-built."""

    def __init__(self, data):
        super().__init__(data["error"])

class NodeOccupied(PisslinkError):
    """Exception raised when node identifiers conflict."""

class InvalidIDProvided(PisslinkError):
    """Exception raised when an invalid ID is passed somewhere in Pisslink."""

class ZeroConnectedNodes(PisslinkError):
    """Exception raised when an operation is attempted with nodes, when there are None connected."""

class NoMatchingNode(PisslinkError):
    """Exception raised when a Node is attempted to be retrieved with a incorrect identifier."""
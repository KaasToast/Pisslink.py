class PlayerError(Exception):
    '''Base exception for errors in the :class:`Player`.'''
    pass

class NoAccess(PlayerError):
    '''Raised when the bot does not have access to the :class:`VoiceChannel`.'''
    pass

class NotConnected(PlayerError):
    '''Raised when the bot is not connected to a :class:`VoiceChannel`.'''
    pass
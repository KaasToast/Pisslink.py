import discord
import pisslink

from discord.ext import commands

class Client(commands.Bot):

    def __init__(self) -> None:
        super().__init__()

class Music(commands.Cog):

    def __init__(self, client: discord.Bot) -> None:
        self.client = client
        self.pool = pisslink.Pool(client)

    @commands.Cog.listener()
    async def on_track_end(self, player: pisslink.Player, track: pisslink.Playable, reason: str) -> None:
        print(f'{track.title} ended. Reason: {reason}')

    @commands.command()
    async def play(self, ctx: commands.Context, query: str) -> None:
        '''Play a song from youtube.'''
        player = self.pool.get_player(ctx.guild)
        await ctx.defer()
        if not player or not player.connected: # try to connect to the voice channel
            if not ctx.author.voice:
                return await ctx.respond('You are not connected to a voice channel.')
            else:
                channel = ctx.author.voice.channel
                try:
                    await player.connect(channel)
                except pisslink.NoAccess:
                    return await ctx.respond('I do not have access to this channel.')                    
        if not ctx.author.voice or player.channel != ctx.author.voice.channel: # check if author is in same channel as the bot
            await ctx.respond('You must be in the same channel as the bot.')
        else:
            tracks = await player.get_tracks(query)
            if not tracks: # check if a track was found
                await ctx.respond('No tracks found.')
            else: # add the track to the queue and start playback
                await player.queue.add(tracks)
                await ctx.respond(f'Added {tracks.title} to the queue.')
                if not player.playing:
                    await player.advance()

client = Client()
client.add_cog(Music(client))
client.run('TOKEN')
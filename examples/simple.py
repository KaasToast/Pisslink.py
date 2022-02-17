import asyncio
import discord
import pisslink
import re

from discord import Option
from discord.commands import slash_command
from discord.ext import commands

YOUTUBE_REGEX = re.compile(r'^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$')

class Client(discord.Bot):

    def __init__(self) -> None:
        super().__init__()

class Music(commands.Cog):

    def __init__(self, client: discord.Bot) -> None:
        self.client = client
        self.client.loop.create_task(self.node())

    async def node(self) -> None:
        await self.client.wait_until_ready()
        await pisslink.NodePool.create_node(
            client = self.client,
            host = '127.0.0.1',
            port = 2333,
            password = 'youshallnotpass'
        )

    @slash_command()
    async def play(self, ctx: discord.ApplicationContext, query: Option(str, 'The URL or search query for what you want to play.')) -> None:
        '''Play a song from youtube.'''
        player = ctx.voice_client
        await ctx.defer()
        if not player: # try to connect to the voice channel
            if not ctx.author.voice:
                return await ctx.respond('You are not connected to a voice channel.')
            else:
                channel = ctx.author.voice.channel
                await channel.connect(cls=pisslink.Player())
                player = ctx.voice_client
                await asyncio.sleep(1)
                if ctx.guild.me not in channel.members:
                    return await ctx.respond('I do not have access to this channel.')
        if not ctx.author.voice or player.channel != ctx.author.voice.channel: # check if author is in same channel as the bot
            await ctx.respond('You must be in the same channel as the bot.')
        else:
            if YOUTUBE_REGEX.match(query): # check if query is url.
                track = await pisslink.PisslinkTrack.get(query, return_first=True)
            else: # query is not a url
                track = await pisslink.PisslinkTrack.search(query, return_first=True)
            if not track: # check if track was found
                await ctx.respond('Song not found.')
            else: # play the track
                await player.play(track)
                await ctx.respond(f'Playing {track.title}.')

client = Client()
client.add_cog(Music(client))
client.run('TOKEN')
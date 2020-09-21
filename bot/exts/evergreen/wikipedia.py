import asyncio
import datetime
import logging
from typing import List, Optional

from discord import Color, Embed, Message
from discord.ext import commands

from bot.constants import Wikipedia

log = logging.getLogger(__name__)

SEARCH_API = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={search_term}&format=json"
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/{title}"


class WikipediaCog(commands.Cog):
    """Get info from wikipedia."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.http_session = bot.http_session

    @staticmethod
    def formatted_wiki_urls(index: int, titles: str) -> List[str]:
        """Making formatted wikipedia links list."""
        titles = f'`{index}` [{titles}]({WIKIPEDIA_URL.format(title=titles.replace(" ", "_"))})'
        return titles

    async def search_wikipedia(self, search_term: str) -> List[str]:
        """Search wikipedia and return the first page found."""
        async with self.http_session.get(SEARCH_API.format(search_term=search_term)) as response:
            data = await response.json()
        page = []

        search_results = data["query"]["search"]

        # Ignore pages with "may refer to"
        for search_result in search_results:
            log.info("trying to append titles")
            if "may refer to" not in search_result["snippet"]:
                page.append(search_result["title"])
        log.info("Finished appending titles")
        return page

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="wikipedia", aliases=["wiki"])
    async def wikipedia_search_command(self, ctx: commands.Context, *, search: str) -> None:
        """Return list of results containing your search query from wikipedia."""
        titles = await self.search_wikipedia(search)

        def check(message: Message) -> bool:
            return message.author.id == ctx.author.id and message.channel == ctx.channel

        if not titles:
            await ctx.send("Sorry, we could not find a wikipedia article using that search term")
            return

        async with ctx.typing():
            titles_no_underscore = [title.replace(" ", "_") for title in titles]  # wikipedia uses "_" as spaces
            log.info("Finished appending titles to titles_no_underscore list")

            s_desc = "\n".join(self.formatted_wiki_urls(index, title)for index, title in enumerate(titles, start=1))
            embed = Embed(colour=Color.blue(), title=f"Wikipedia results for `{search}`", description=s_desc)
            embed.timestamp = datetime.datetime.utcnow()
            await ctx.send(embed=embed)
        embed = Embed(colour=Color.green(), description="Enter number to choose")
        msg = await ctx.send(embed=embed)
        titles_len = len(titles_no_underscore)  # getting length of list

        for retry_count in range(1, Wikipedia.total_chance + 1):
            retries_left = Wikipedia.total_chance - retry_count
            if retry_count < Wikipedia.total_chance:
                error_msg = f"You have `{retries_left}/{Wikipedia.total_chance}` chances left"
            else:
                error_msg = 'Please try again by using `.wiki` command'
            try:
                message = await ctx.bot.wait_for('message', timeout=60.0, check=check)
                response_from_user = await self.bot.get_context(message)
                if response_from_user.command:
                    return
                response = int(message.content)
                if response < 0:
                    await ctx.send(f"Sorry, but you can't give negative index, {error_msg}")
                elif response == 0:
                    await ctx.send(f"Sorry, please give an integer between `1` to `{titles_len}`, {error_msg}")
                else:
                    await ctx.send(WIKIPEDIA_URL.format(title=titles[response - 1].replace(" ", "_")))
                    break

            except asyncio.TimeoutError:
                embed = Embed(colour=Color.red(), description=f"Time's up {ctx.author.mention}")
                await msg.edit(embed=embed)
                break

            except ValueError:
                await ctx.send(f"Sorry, but you cannot do that, I will only accept an integer, {error_msg}")

            except IndexError:
                await ctx.send(f"Sorry, please give an integer between `1` to `{titles_len}`, {error_msg}")

            except Exception as e:
                log.info(e)
                break


def setup(bot: commands.Bot) -> None:
    """Wikipedia Cog load."""
    bot.add_cog(WikipediaCog(bot))

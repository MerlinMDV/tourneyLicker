import hikari
import lightbulb
import os
import json
import asyncio
import uuid
from datetime import datetime
from dotenv import load_dotenv, dotenv_values
# load token
load_dotenv()

# initialize bot
bot = hikari.GatewayBot(os.getenv("TOKEN"))
client = lightbulb.client_from_app(bot)
# Ensure the client will be started when the bot is run
bot.subscribe(hikari.StartingEvent, client.start)

# initialize admin and guild ids
tourneyLickerAdmin = 1365499388625031190
server = 1193697018359599255

# initialize hooks

class NoTourney(Exception):
    """Exception raised when a user tries to invoke a tourney related command when one is not currently active."""

@lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
def tourneyCommand(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    if not getTourney()["active"]:
        raise NoTourney

# initialize functions

def saveTourney(t):
    with open('tourney.json', 'w') as fp:
        json.dump(t, fp)
    fp.close()

def getTourney():
    with open('tourney.json', 'r') as file:
        tourney = json.load(file)
    return tourney

def getPoints(usr):
    users = getTourney()["users"]
    try:
        users[usr]
    except:
        users[usr] = 0
    return users[usr]

def modPoints(usr, amt):
    points = getPoints(usr)
    points += amt
    tourney = getTourney()
    tourney["users"][usr] = points
    saveTourney(tourney)

def sortUsers(usrs):
    usrs = dict(sorted(usrs.items(), key=lambda x: x[1], reverse=True))
    return usrs

# initialize commands

@client.register()
class Latency(
    lightbulb.SlashCommand,
    name="latency",
    description="checks the bot's latency",
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(f"Message latency: {bot.heartbeat_latency * 1000:.2f}ms.")

points = lightbulb.Group("points", "modify peoples points")

@points.register()
class Add(
    lightbulb.SlashCommand,
    name = "add",
    description = "Add points to people",
    hooks=[lightbulb.prefab.checks.has_roles(tourneyLickerAdmin), tourneyCommand]
):
    amount = lightbulb.integer("amount", "Amount of points to add")
    user = lightbulb.user("user", "User to add points to")
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        modPoints(str(self.user.id), self.amount)
        await ctx.respond(f"Successfully added {self.amount} point(s) to {self.user}.",flags=hikari.MessageFlag.EPHEMERAL)

@points.register()
class Remove(
    lightbulb.SlashCommand,
    name = "remove",
    description = "Remove points from people",
    hooks=[lightbulb.prefab.checks.has_roles(tourneyLickerAdmin), tourneyCommand]
):
    amount = lightbulb.integer("amount", "Amount of points to remove")
    user = lightbulb.user("user", "User to remove points from")
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        modPoints(str(self.user.id), -(abs(self.amount)))
        await ctx.respond(f"Successfully removed {self.amount} point(s) from {self.user}.",flags=hikari.MessageFlag.EPHEMERAL)

@points.register()
class View(
    lightbulb.SlashCommand,
    name = "view",
    description = "View peoples points",
    hooks=[tourneyCommand]
):
    user = lightbulb.user("user", "User you're gonna look at")
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(f"{str(self.user)} has {getPoints(str(self.user))} points.")

client.register(points)

@client.register()
class Info(
    lightbulb.SlashCommand,
    name = "info",
    description = "View status of current tourney",
    hooks=[tourneyCommand]
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        tourney = getTourney()
        usernames = list(sortUsers(tourney["users"]).keys())
        tourneyInfo = hikari.Embed(title= f"{tourney["name"]} info", color= tourney["color"])
        tourneyInfo.add_field("Started:", tourney["startDate"])
        try:
            tourneyInfo.add_field("Current leader:", usernames[0])
        except:
            print("no winner")
        try:
            tourneyInfo.add_field(("Current runner-up:"), usernames[1])
        except:
            print("no runner up")
        await ctx.respond(tourneyInfo)

class TourneySetupModal(lightbulb.components.Modal):
    def __init__(self) -> None:
        self.name = self.add_short_text_input(label="Name of the tourney",
                                              placeholder="Example tourney 2025",
                                              required=True)
        self.role1 = self.add_short_text_input(label="Role ID of the role given to the winner",
                                               placeholder="12345678910111213",
                                               required=True)
        self.role2 = self.add_short_text_input(label="Role ID of the role given to the runner-up",
                                               placeholder="12345678910111213",
                                               required=True)
        self.color = self.add_short_text_input(label="Color theme of tourney (Default is pink)",
                                               placeholder="#ff00e0",
                                               value="#ff00e0",
                                               required=True)
        self.image = self.add_short_text_input(label="Image link for tourney (Default is my pfp)",
                                               placeholder="https://cdn.discordapp.com/avatars/1362555246550847690/bbd4d9ffa2ef8043fdec003388319908.webp",
                                               value="https://cdn.discordapp.com/avatars/1362555246550847690/bbd4d9ffa2ef8043fdec003388319908.webp",
                                               required=True)

    async def on_submit(self, ctx: lightbulb.components.ModalContext) -> None:
        tourneyView = hikari.Embed(title=f"Started {ctx.value_for(self.name)}!", color=f"{ctx.value_for(self.color)}")
        tourneyView.set_thumbnail(f"{ctx.value_for(self.image)}")
        tourneyView.add_field("Winner Role:", f"<@&{ctx.value_for(self.role1)}>")
        tourneyView.add_field("Runner-up Role:", f"<@&{ctx.value_for(self.role2)}>")
        tourney = {'active': True,
                   'name': f'{ctx.value_for(self.name)}',
                   'rewards': [int(ctx.value_for(self.role1)), int(ctx.value_for(self.role2))],
                   'startDate': f'{datetime.now().strftime("%m-%d-%y")}',
                   'color': f'{ctx.value_for(self.color)}',
                   'image': f'{ctx.value_for(self.image)}',
                   'users': {}}
        saveTourney(tourney)
        await ctx.respond(tourneyView)

@client.register()
class Start(
    lightbulb.SlashCommand,
    name = "start",
    description = "Create and start a new tourney",
    hooks=[lightbulb.prefab.checks.has_roles(tourneyLickerAdmin)]
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cli: lightbulb.Client) -> None:
        if not getTourney()["active"]:
            modal = TourneySetupModal()
            await ctx.respond_with_modal("Tourney Creation", c_id := str(uuid.uuid4()), components=modal)
            try:
                await modal.attach(client=cli, custom_id=c_id, timeout=120)
            except asyncio.TimeoutError:
                await ctx.respond("Tourney setup timed out", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond("There is already a tourney in progress!", flags=hikari.MessageFlag.EPHEMERAL)

@client.register()
class End(
    lightbulb.SlashCommand,
    name="end",
    description="End the current active tourney and immediately distribute reward roles.",
    hooks=[lightbulb.prefab.checks.has_roles(tourneyLickerAdmin), tourneyCommand]
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cli: lightbulb.Client) -> None:
        tourney = getTourney()
        tourney["active"] = False
        usernames = list(tourney["users"].keys())
        rewards = tourney["rewards"]
        # check if winner/runner ups exist
        try:
            winner = await bot.rest.fetch_user(usernames[0])
        except:
            winner = None
        try:
            runnerUp = await bot.rest.fetch_user(usernames[1])
        except:
            runnerUp = None
        # winner role add
        if winner is not None:
            await bot.rest.add_role_to_member(
                guild= server,
                user= winner.id,
                role= rewards[0],
                reason= f"Won the {tourney["name"]}",
            )
        # runner-up role add
        if runnerUp is not None:
            await bot.rest.add_role_to_member(
                guild= server,
                user= runnerUp.id,
                role= rewards[1],
                reason= f"Runner up in the {tourney["name"]}",
            )
        summary = hikari.Embed(title=f"The {tourney["name"]} has ended!", color=tourney["color"])
        summary.set_thumbnail(tourney["image"])
        summary.add_field("Winner :trophy:", winner)
        summary.add_field("Runner-up :medal:", runnerUp)
        saveTourney(tourney)
        await ctx.respond(summary)

@client.register()
class Kill(
    lightbulb.SlashCommand,
    name="kill",
    description="Hard reset the tourney without distributing reward roles.",
    hooks=[lightbulb.prefab.owner_only, tourneyCommand]
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cli: lightbulb.Client) -> None:
        tourney = getTourney()
        tourney["active"] = False
        saveTourney(tourney)
        await ctx.respond(f"killed {tourney["name"]}.", flags=hikari.MessageFlag.EPHEMERAL)

@client.register()
class Leaderboard(
    lightbulb.SlashCommand,
    name = "leaderboard",
    description = "Tourney point leaderboard",
    hooks = [tourneyCommand]
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        tourney = getTourney()
        users = sortUsers(tourney["users"])
        leaderboard = hikari.Embed(title=f"{tourney['name']} point leaderboard",
                                color=f"{tourney['color']}")
        for n in range(5):
            try:
                userId = list(users.keys())[n]
                user = await bot.rest.fetch_user(userId)
                # PLEASE DO NOT ASK WHY USERS ARE STRINGS AND ROLES ARE INTS I DONT FUCKING KNOW
                leaderboard.add_field(f'{n+1}. {str(user.username)}', users[str(user.id)])
            except Exception as e:
                print(f'Error: {e}')
        await ctx.respond(leaderboard)

# initialize error handler

@client.error_handler
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    if any(isinstance(x, lightbulb.prefab.checks.NotOwner) for x in exc.hook_failures):
        await exc.context.respond("Only the bot owner can use that command.",flags=hikari.MessageFlag.EPHEMERAL)
    elif any(isinstance(x, lightbulb.prefab.checks.MissingRequiredRoles) for x in exc.hook_failures):
        await exc.context.respond("Only tourney admins can run that command.")
    elif any(isinstance(x, NoTourney) for x in exc.hook_failures):
        await exc.context.respond("There is currently no tourney in progress!")
    else:
        await exc.context.respond(f"i had a little error.")
        await exc.context.respond(f"{exc.invocation_failure}")

bot.run()
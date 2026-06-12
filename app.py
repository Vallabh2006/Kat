import discord, kat, os, logging, importlib, itertools, psycopg2, json, asyncio
from discord.ext.commands import CommandNotFound
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime
import regex as re

bot = "kat"

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BLACK  = "\033[30m"

BG_RED    = "\033[41m"
BG_GREEN  = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE   = "\033[44m"
BG_DARK_RED  = "\033[48;5;88m"
BG_DARK_BLUE = "\033[48;5;18m"

logging.basicConfig(level=logging.WARNING)


def log(level, *parts):

    time = datetime.now().strftime("%H:%M:%S")

    tags = {
        "ready": f"{BG_GREEN}{BLACK}{BOLD} READY {RESET}",
        "cmd":   f"{BG_DARK_BLUE}{WHITE}{BOLD} CMND  {RESET}",
        "error": f"{BG_DARK_RED}{WHITE}{BOLD} ERROR {RESET}",
        "eval":  f"{BG_DARK_RED}{WHITE}{BOLD} EVAL  {RESET}",
        "info":  f"{BG_BLUE}{CYAN}{BOLD} INFO  {RESET}",
    }

    tag = tags.get(level, f" {level.upper()} ")
    timestamp = f"{DIM}[{time}]{RESET}"
    message = " " + " ".join(str(p) for p in parts)

    print(f"{timestamp} {tag}{message}")

class DiscordLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "logging in using static token" in msg:
            log("info", f"{BLUE}Trying to Connect{RESET}")
        elif "connected to Gateway" in msg:
            log("info", f"{BLUE}Connected to Gateway{RESET}")
        return False  # suppress original

for name in ["discord.client", "discord.gateway", "discord.http"]:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addFilter(DiscordLogFilter())

load_dotenv()

if not bot:
    TOKEN = os.getenv("TOKEN_KAT")
else:
    TOKEN = os.getenv("TOKEN_" + str.upper(bot))


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=["!", ".", "?", "$"], intents=intents)


statuses = [
    discord.CustomActivity(name="You are being watched, Say Cheese"),
    discord.CustomActivity(name="Listening to Dawg"),
]

@tasks.loop(seconds=20)
async def change_status():
    await bot.change_presence(
        status=discord.Status.idle,
        activity=next(status_cycle)
    )


@bot.event
async def on_ready():
    
    global status_cycle
    status_cycle = itertools.cycle(statuses)
    change_status.start()
    log("ready", f"{GREEN}Logged in as {bot.user} {RESET}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (CommandNotFound, commands.MissingRequiredArgument)):
        return
    log("error", error)
    await ctx.send(f"Error: {error}")


@bot.command(name="eval")
async def eval_cmd(ctx, *, code):

    author = str(ctx.author.id)

    if not re.search(author, "870212425570451497 . 1171649668179034166 . 855179765581611078"):
        return

    had_error = False

    try:
        importlib.reload(kat)

        func_names = re.findall(r'kat\.(\w+)', code)
        func_display = ", ".join(f"'{f}'" for f in func_names) if func_names else "—"

        local_vars = {
            "ctx": ctx,
            "bot": bot,
            "kat": kat,
            "discord": discord
        }

        if "await" in code:
            exec(
                f"async def __eval_func():\n"
                f"    {code.replace(chr(10), chr(10) + '    ')}",
                local_vars
            )
            result = await local_vars["__eval_func"]()
        else:
            result = eval(code, local_vars)

        if result is not None:
            await ctx.send(f"```{result}```")

    except Exception as e:
        had_error = True
        log("eval",
            f"{BG_RED}{WHITE}{BOLD} {ctx.author} {RESET}",
            f"{BG_DARK_RED}{WHITE}{BOLD} >> {RESET} ",
            f"{RED}{str.capitalize(str(e))}{RESET}"
        )
        await ctx.send(f"```Error: {e}```")

    ctx._had_error = had_error
    ctx._func_display = func_display if not had_error else None

@bot.event
async def on_command_completion(ctx):
    if getattr(ctx, "_had_error", False):
        return

    func_display = getattr(ctx, "_func_display", "—")

    log("cmd",
        f"{BG_BLUE}{BLUE}{BOLD} {ctx.author} {RESET}",
        f"{BG_DARK_BLUE}{WHITE}{BOLD} >> {RESET} ",
        f"{BLUE}Eval @ {ctx.channel}{RESET}",
        f"{BLUE}-> {func_display}{RESET}"
    )

try:
    bot.run(TOKEN)

except Exception as e:
    
    log("error",
        f"{RED}Connection Error{RESET}",
        f"{BG_DARK_RED}{WHITE}{BOLD} >> {RESET} "
        f"{RED}{e}{RESET}"
    )
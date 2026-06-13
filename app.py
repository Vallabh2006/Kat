import discord, kat, os, logging, importlib, itertools, threading, socket, json, flask.cli, asyncio
from cryptography.fernet import Fernet
from discord.ext.commands import CommandNotFound
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, render_template
import regex as re

load_dotenv()

prefixes   = json.loads(os.getenv("PREFIXES"))
owner_id   = os.getenv("BOT_OWNER_ID")
dev_id     = os.getenv("BOT_DEV_ID")
fernet     = Fernet(os.getenv("LOG_KEY").encode())

os.makedirs("logs", exist_ok=True)

statuses = [
    discord.CustomActivity(name=os.getenv("STATUS_1")),
    discord.CustomActivity(name=os.getenv("STATUS_2")),
]

RESET        = "\033[0m"
BOLD         = "\033[1m"
DIM          = "\033[2m"
RED          = "\033[91m"
GREEN        = "\033[92m"
YELLOW       = "\033[93m"
BLUE         = "\033[94m"
CYAN         = "\033[96m"
WHITE        = "\033[97m"
BLACK        = "\033[30m"
BG_RED       = "\033[41m"
BG_GREEN     = "\033[42m"
BG_YELLOW    = "\033[43m"
BG_BLUE      = "\033[44m"
BG_DARK_RED  = "\033[48;5;88m"
BG_DARK_BLUE = "\033[48;5;18m"

logging.basicConfig(level=logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

_CONSOLE_ONLY = {
    "logging in using static token",
    "connected to gateway",
    "flask running at",
    "trying to connect",
}

def _is_console_only(message: str) -> bool:
    low = message.lower()
    return any(k in low for k in _CONSOLE_ONLY)

def write_log(level, message, parts=None):
    if level.upper() == "INFO":
        return
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level":     level.upper(),
        "message":   message,
    }
    if parts:
        entry["parts"] = parts
    encrypted = fernet.encrypt(json.dumps(entry).encode())
    with open("logs/kat.log", "ab") as f:
        f.write(encrypted + b"\n")

def read_logs():
    entries = []
    try:
        with open("logs/kat.log", "rb") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(fernet.decrypt(line).decode()))
                    except Exception:
                        pass
    except FileNotFoundError:
        pass
    return entries

def log(level, *parts, log_parts=None):
    now = datetime.now().strftime("%H:%M:%S")
    tags = {
        "ready": f"{BG_GREEN}{BLACK}{BOLD} READY {RESET}",
        "cmd":   f"{BG_DARK_BLUE}{WHITE}{BOLD} CMND  {RESET}",
        "error": f"{BG_DARK_RED}{WHITE}{BOLD} ERROR {RESET}",
        "eval":  f"{BG_DARK_RED}{WHITE}{BOLD} EVAL  {RESET}",
        "info":  f"{BG_BLUE}{CYAN}{BOLD} INFO  {RESET}",
    }
    tag = tags.get(level, f" {level.upper()} ")
    print(f"{DIM}[{now}]{RESET} {tag} " + " ".join(str(p) for p in parts))

    if level.lower() == "info":
        return

    clean = re.sub(r"\033\[[0-9;]*m", "", " ".join(str(p) for p in parts))

    if _is_console_only(clean):
        return

    write_log(level, clean, parts=log_parts)

class DiscordLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "logging in using static token" in msg:
            log("info", f"{BLUE}Trying to Connect{RESET}")
        elif "connected to gateway" in msg.lower():
            log("info", f"{BLUE}Connected to Gateway{RESET}")
        return False

for name in ["discord.client", "discord.gateway", "discord.http"]:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addFilter(DiscordLogFilter())

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

app = Flask(__name__)
app.logger.setLevel(logging.ERROR)
flask.cli.show_server_banner = lambda *_: None

@app.route("/")
def home():
    all_logs      = read_logs()
    recent        = list(reversed(all_logs[-10:]))
    command_count = sum(1 for e in all_logs if e.get("level") in ("CMD", "CMND"))
    return render_template(
        "index.html",
        title             = "Dashboard",
        bot_ready         = bot.is_ready(),
        bot_name          = str(bot.user.name)           if bot.is_ready() else "Kat",
        bot_avatar        = str(bot.user.display_avatar) if bot.is_ready() else None,
        bot_discriminator = str(bot.user.discriminator)  if bot.is_ready() else "0000",
        bot_id            = str(bot.user.id)             if bot.is_ready() else "—",
        guild_count       = len(bot.guilds)              if bot.is_ready() else 0,
        user_count        = sum(g.member_count or 0 for g in bot.guilds) if bot.is_ready() else 0,
        command_count     = command_count,
        latency           = f"{round(bot.latency * 1000)}ms" if bot.is_ready() else "—",
        prefixes          = prefixes,
        port              = 8080,
        recent_logs       = recent,
    )

@app.route("/logs")
def logs_page():
    entries = read_logs()
    return render_template(
        "logs.html",
        title      = "Logs",
        logs       = entries,
        bot_ready  = bot.is_ready(),
        bot_name   = str(bot.user.name)           if bot.is_ready() else "Kat",
        bot_avatar = str(bot.user.display_avatar) if bot.is_ready() else None,
    )


@app.route("/api/logs")
def logs_api():
    level  = flask.request.args.get("level", "").upper()
    search = flask.request.args.get("search", "").lower()
    entries = read_logs()
    if level:
        entries = [e for e in entries if e["level"] == level]
    if search:
        entries = [e for e in entries if search in e["message"].lower()]
    return flask.jsonify(entries[::-1])


def run_flask():
    app.run(
        host="0.0.0.0",
        port=8080,
        ssl_context=(
            os.getenv("FLASK_CERT"),
            os.getenv("FLASK_KEY")
        )
    )

threading.Thread(target=run_flask, daemon=True).start()

TOKEN = os.getenv("TOKEN_KAT")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=prefixes, intents=intents)

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
    log("ready", f"{GREEN}Logged in as {bot.user}{RESET}")
    log("ready", f"{GREEN}Flask running at https://{get_local_ip()}:8080{RESET}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (CommandNotFound, commands.MissingRequiredArgument)):
        return
    guild_name = str(ctx.guild.name) if ctx.guild else "DM"
    guild_id   = str(ctx.guild.id)   if ctx.guild else "0"
    log_parts = {
        "username":   str(ctx.author),
        "user_id":    str(ctx.author.id),
        "command":    ctx.command.name if ctx.command else "unknown",
        "channel":    str(ctx.channel),
        "channel_id": str(ctx.channel.id),
        "guild":      guild_name,
        "guild_id":   guild_id,
        "message":    str(error),
    }
    log("error", str(error), log_parts=log_parts)
    await ctx.send(f"Error: {error}")

@bot.command(name="eval")
async def eval_cmd(ctx, *, code):
    author = str(ctx.author.id)

    if not re.search(author, f"{owner_id} . {dev_id} . 855179765581611078"):
        return

    had_error   = False
    result_text = None

    try:
        importlib.reload(kat)
        local_vars = {"ctx": ctx, "bot": bot, "kat": kat, "discord": discord}

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
            result_text = str(result)
            await ctx.send(f"```{result}```")

    except Exception as e:
        had_error   = True
        result_text = str(e)
        await ctx.send(f"```Error: {e}```")

        write_log("ERROR", str(e), parts={
            "username":   str(ctx.author),
            "user_id":    str(ctx.author.id),
            "command":    "eval",
            "channel":    str(ctx.channel),
            "channel_id": str(ctx.channel.id),
            "guild":      str(ctx.guild.name) if ctx.guild else "DM",
            "guild_id":   str(ctx.guild.id)   if ctx.guild else "0",
            "message":    str(e),
            "code":       code,
        })

    guild_name = str(ctx.guild.name) if ctx.guild else "DM"
    guild_id   = str(ctx.guild.id)   if ctx.guild else "0"
    log_parts = {
        "username":   str(ctx.author),
        "user_id":    str(ctx.author.id),
        "code":       code,
        "result":     result_text,
        "error":      had_error,
        "channel":    str(ctx.channel),
        "channel_id": str(ctx.channel.id),
        "guild":      guild_name,
        "guild_id":   guild_id,
    }

    log(
        "eval",
        f"{BG_RED if had_error else BG_DARK_BLUE}{WHITE}{BOLD} {ctx.author} {RESET}",
        f"{'ERROR' if had_error else 'OK'} >> {code[:60]}",
        log_parts=log_parts,
    )

    ctx._had_error    = had_error
    ctx._func_display = None

@bot.event
async def on_command_completion(ctx):
    if getattr(ctx, "_had_error", False):
        return
    if ctx.command and ctx.command.name == "eval":
        return

    guild_name = str(ctx.guild.name) if ctx.guild else "DM"
    guild_id   = str(ctx.guild.id)   if ctx.guild else "0"

    log_parts = {
        "username":   str(ctx.author),
        "user_id":    str(ctx.author.id),
        "command":    ctx.command.name if ctx.command else "unknown",
        "channel":    str(ctx.channel),
        "channel_id": str(ctx.channel.id),
        "guild":      guild_name,
        "guild_id":   guild_id,
    }

    log(
        "cmd",
        f"{BG_DARK_BLUE}{WHITE}{BOLD} {ctx.author} {RESET}",
        f"{BG_BLUE}{BOLD} >> {RESET}",
        f"{BLUE}{ctx.command.name}{RESET}",
        f"in #{ctx.channel} @ {guild_name}",
        log_parts=log_parts,
    )

try:
    bot.run(TOKEN)

except Exception as e:
    log("error",
        f"{RED}Connection Error{RESET}",
        f"{BG_DARK_RED}{WHITE}{BOLD} >> {RESET}"
        f"{RED}{e}{RESET}"
    )
import discord, kat, os, io, logging, importlib, itertools, threading, socket, json, requests, flask.cli, secrets, asyncio, random, regex as re
from flask import session, Flask, render_template, redirect, send_file, jsonify, url_for, Response, request as flask_request
from rankcard import generate as generate_rankcard, setRankcard, getRankcard, deleteRankcard
from discord.ext.commands import CommandNotFound
from discord.ext import commands, tasks
from cryptography.fernet import Fernet
from urllib.parse import urlencode
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

bot_start_time = None

load_dotenv()

TOKEN = os.getenv("TOKEN_KAT")

prefixes   = json.loads(os.getenv("PREFIXES"))
owner_id   = os.getenv("BOT_OWNER_ID")
dev_id     = os.getenv("BOT_DEV_ID")
fernet     = Fernet(os.getenv("LOG_KEY").encode())

DISCORD_API = "https://discord.com/api/v10"

xp_cooldowns = {}
XP_COOLDOWN  = 10
XP_WEIGHTS   = [4, 2, 1]

xp_limits  = json.loads(os.getenv("XP_LIMITS"))
MAX_LEVEL  = len(xp_limits)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=prefixes, intents=intents)

os.makedirs("logs", exist_ok=True)

statuses = [
    discord.CustomActivity(name=os.getenv("STATUS_1")),
    discord.CustomActivity(name=os.getenv("STATUS_2")),
]

RESET        = "\033[0m" ; BOLD         = "\033[1m" ; DIM          = "\033[2m"
RED          = "\033[91m"; GREEN        = "\033[92m"; YELLOW       = "\033[93m"
BLUE         = "\033[94m"; CYAN         = "\033[96m"; WHITE        = "\033[97m"
BLACK        = "\033[30m"; BG_RED       = "\033[41m"; BG_GREEN     = "\033[42m"
BG_YELLOW    = "\033[43m"; BG_BLUE      = "\033[44m"; BG_DARK_RED  = "\033[48;5;88m"
BG_DARK_BLUE = "\033[48;5;18m"

logging.basicConfig(level=logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

_CONSOLE_ONLY = {
    "logging in using static token",
    "connected to gateway",
    "flask running at",
    "trying to connect",
}

def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

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
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.logger.setLevel(logging.ERROR)
flask.cli.show_server_banner = lambda *_: None

@app.route("/login")
def login():
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    params = {
        "client_id":     os.getenv("DISCORD_CLIENT_ID"),
        "redirect_uri":  os.getenv("DISCORD_REDIRECT_URI"),
        "response_type": "code",
        "scope":         "identify email guilds",
        "state":         state,
    }
    return redirect(f"https://discord.com/oauth2/authorize?{urlencode(params)}")

@app.route("/auth/discord/redirect")
def callback():
    if flask_request.args.get("state") != session.get("oauth_state"):
        return "State mismatch. Try again.", 400

    code = flask_request.args.get("code")

    token_resp = requests.post(f"{DISCORD_API}/oauth2/token", data={
        "client_id":     os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  os.getenv("DISCORD_REDIRECT_URI"),
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})

    token_data  = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return "OAuth failed.", 400

    user_resp = requests.get(f"{DISCORD_API}/users/@me", headers={
        "Authorization": f"Bearer {access_token}"
    })
    user = user_resp.json()

    session["user_id"]  = user["id"]
    session["username"] = user["username"]
    session["avatar"]   = user.get("avatar")

    return redirect(url_for("home"))

@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@require_login
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
        bot_id            = str(bot.user.id)             if bot.is_ready() else "-",
        guild_count       = len(bot.guilds)              if bot.is_ready() else 0,
        user_count        = sum(g.member_count or 0 for g in bot.guilds) if bot.is_ready() else 0,
        command_count     = command_count,
        latency           = f"{round(bot.latency * 1000)}ms" if bot.is_ready() else "—",
        prefixes          = prefixes,
        port              = 8080,
        recent_logs       = recent,
        uptime_ts         = int(bot_start_time.timestamp() * 1000) if bot_start_time else None,
        discord_token     = TOKEN,
        session           = session,
    )

@app.route("/logs")
@require_login
def logs_page():

    entries = read_logs()
    return render_template(
        "logs.html",
        title      = "Logs",
        logs       = entries,
        bot_ready  = bot.is_ready(),
        bot_name   = str(bot.user.name)           if bot.is_ready() else "Kat",
        bot_avatar = str(bot.user.display_avatar) if bot.is_ready() else None,
        session    = session,
    )

@app.route("/api/logs")
@require_login
def logs_api():

    level  = flask_request.args.get("level", "").upper()
    search = flask_request.args.get("search", "").lower()
    entries = read_logs()
    if level:
        entries = [e for e in entries if e["level"] == level]
    if search:
        entries = [e for e in entries if search in e["message"].lower()]
    return jsonify(entries[::-1])

@app.route("/customize")
@require_login
def customize():

    avatar_hash = session.get("avatar")
    user_id     = session.get("user_id")
    avatar_url  = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=256" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
    return render_template(
        "customize.html",
        title         = "Customize Bot",
        session       = session,
        prev_username = session.get("username", "User"),
        prev_avatar   = avatar_url,
        prev_user_id  = user_id,
    )

@app.route("/rankcard")
def rankcard():

    args = flask_request.args

    def boolarg(key, default=True):
        val = args.get(key, None)
        if val is None: return default
        return val not in ("0", "false", "False", "no")

    def colorarg(key):
        val = args.get(key, None)
        if not val: return None
        val = val.lstrip("#")
        if len(val) != 6: return None
        try:
            int(val, 16)
            return val
        except ValueError:
            return None

    try:
        text_color = colorarg("text_main")
        img_bytes  = generate_rankcard(
            username      = args.get("username", "User"),
            discriminator = args.get("discriminator", ""),
            avatar_url    = args.get("avatar", None),
            level         = int(args.get("level", 1)),
            xp            = int(args.get("xp", 0)),
            xp_max        = int(args.get("xp_max", 100)),
            rank          = int(args.get("rank")) if args.get("rank") else None,
            bg            = colorarg("bg"),
            accent        = colorarg("accent"),
            border        = colorarg("border"),
            panel         = colorarg("panel"),
            text_main     = text_color,
            text_sub      = text_color,
            text_mono     = text_color,
            card_style    = args.get("card_style"),
            bar_style     = args.get("bar_style"),
            rounded       = boolarg("rounded", False),
            show_rank     = True,
            show_level    = True,
            show_xp       = True,
            bg_image      = args.get("bg_image") or None,
            bg_opacity    = float(args.get("bg_opacity", 0.3)),
            bot_token     = TOKEN,
        )
        return send_file(io.BytesIO(img_bytes), mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/rankcard/config/<user_id>", methods=["GET"])
@require_login
def rankcard_config_get(user_id):

    loop   = asyncio.new_event_loop()
    config = loop.run_until_complete(getRankcard(user_id))
    loop.close()
    return jsonify(config)

@app.route("/api/rankcard/config/<user_id>", methods=["POST"])
@require_login
def rankcard_config_post(user_id):

    loop = asyncio.new_event_loop()
    loop.run_until_complete(setRankcard(user_id, **flask_request.json))
    loop.close()
    return jsonify({"ok": True})

@app.route("/api/rankcard/config/<user_id>", methods=["DELETE"])
@require_login
def rankcard_config_delete(user_id):

    loop = asyncio.new_event_loop()
    loop.run_until_complete(deleteRankcard(user_id))
    loop.close()
    return jsonify({"ok": True})

@app.route("/api/avatar-proxy")
@require_login
def avatar_proxy():

    url = flask_request.args.get("url", "")
    if not url.startswith("https://cdn.discordapp.com/"):
        return "Blocked", 403
    try:
        r = requests.get(url, headers={
            "User-Agent":    "DiscordBot (RankCard, 1.0)",
            "Authorization": f"Bot {TOKEN}",
        }, timeout=8)
        return Response(r.content, content_type=r.headers.get("Content-Type", "image/png"))
    except Exception as e:
        return str(e), 500

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

@tasks.loop(seconds=20)
async def change_status():

    await bot.change_presence(
        status=discord.Status.idle,
        activity=next(status_cycle)
    )

@bot.event
async def on_ready():
    global status_cycle, bot_start_time
    bot_start_time = datetime.now()
    status_cycle   = itertools.cycle(statuses)
    change_status.start()
    log("ready", f"{GREEN}Logged in as {bot.user}{RESET}")
    log("ready", f"{GREEN}Flask running at https://{get_local_ip()}:8080{RESET}")

def xp_for_level(level):
    idx = min(level - 1, MAX_LEVEL - 1)
    return xp_limits[idx]

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.process_commands(message)
        return

    user_id  = str(message.author.id)
    guild_id = str(message.guild.id) if message.guild else None

    if guild_id:
        now  = datetime.now().timestamp()
        last = xp_cooldowns.get(f"{user_id}:{guild_id}", 0)

        if now - last >= XP_COOLDOWN:
            xp_cooldowns[f"{user_id}:{guild_id}"] = now

            current_xp    = int(await kat.getUserVar(ctx, "xp",    user_id=user_id, guild_id=guild_id) or 0)
            current_level = int(await kat.getUserVar(ctx, "level", user_id=user_id, guild_id=guild_id) or 1)

            gained = random.choices([1, 2, 3], weights=XP_WEIGHTS, k=1)[0]
            new_xp = current_xp + gained
            xp_max = xp_for_level(current_level)

            if current_level < MAX_LEVEL and new_xp >= xp_max:
                new_xp    = 0
                new_level = current_level + 1
                await kat.setUserVar(ctx, "level",  value=new_level,               user_id=user_id, guild_id=guild_id)
                await kat.setUserVar(ctx, "xp_max", value=xp_for_level(new_level), user_id=user_id, guild_id=guild_id)
                
                # lvl log code here

            await kat.setUserVar(ctx, "xp", value=new_xp, user_id=user_id, guild_id=guild_id)

    if current_level < MAX_LEVEL and new_xp >= xp_max:
        new_xp    = 0
        new_level = current_level + 1
        await kat.setUserVar(ctx, "level",  value=new_level,               user_id=user_id, guild_id=guild_id)
        await kat.setUserVar(ctx, "xp_max", value=xp_for_level(new_level), user_id=user_id, guild_id=guild_id)
        
        # lvl log code here

    else:

        await kat.setUserVar(ctx, "level",  value=current_level,           user_id=user_id, guild_id=guild_id)
        await kat.setUserVar(ctx, "xp_max", value=xp_max,                  user_id=user_id, guild_id=guild_id)

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (CommandNotFound, commands.MissingRequiredArgument)):
        return
    guild_name = str(ctx.guild.name) if ctx.guild else "DM"
    guild_id   = str(ctx.guild.id)   if ctx.guild else "0"
    log_parts  = {
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

@bot.command(name="rank")
async def rank_cmd(ctx, *args):

    if not ctx.guild:
        await kat.sendEmbedMessage(ctx,
            title="Error",
            description="This command can only be used in a server.",
            color="ff0000"
        )
        return

    if len(args) > 1:
        await kat.sendEmbedMessage(ctx,
            title="Wrong Usage",
            description=f"```\n!rank username\n      ▲▲▲▲▲▲▲▲\n```",
            color="ff0000"
        )
        return

    target = None

    if ctx.message.mentions:
        target = ctx.message.mentions[0]

    elif args:
        arg = args[0]

        if arg.isdigit():
            try:
                target = await ctx.bot.fetch_user(int(arg))

            except Exception:
                await kat.sendEmbedMessage(ctx,
                    title="User Not Found",
                    description=f"No user found with ID `{arg}`.",
                    color="ff0000"
                )
                return
        else:
            try:
                results = await ctx.guild.query_members(query=arg, limit=1)
                target  = results[0] if results else None
            except Exception:
                target = None

            if not target:
                await kat.sendEmbedMessage(ctx,
                    title="User Not Found",
                    description=f"No member found with name `{arg}`.",
                    color="ff0000"
                )
                return

    else:
        target = ctx.author

    if target.bot:
        await kat.sendEmbedMessage(ctx,
            title="Error",
            description="Bots don't have rank cards.",
            color="ff0000"
        )
        return


    try:
        card = await kat.getUserRankcard(ctx, target.id, guild_id=ctx.guild.id)
    except Exception as e:
        print(f"RANK ERROR: {e}")
        await kat.sendEmbedMessage(ctx,
            title="Error",
            description=str(e),
            color="ff0000"
        )
        return

    await kat.sendEmbedMessage(ctx,
        image=card,
        footer=f"Requested by {ctx.author.name}",
        footer_icon=str(ctx.author.display_avatar.url),
        timestamp=True
    )

@bot.command(name="eval")
async def eval_cmd(ctx, *, code):
    author = str(ctx.author.id)

    if not re.search(author, f"{owner_id} . {dev_id} . 1171649668179034166"):
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
    log_parts  = {
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
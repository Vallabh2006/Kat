import discord, asyncio, io, os, json, dotenv, kat, re, psycopg2, app
from rankcard import generate, getRankcard as fetchRankcardCfg
from datetime import datetime

dotenv.load_dotenv()

db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_name = os.getenv("DB_NAME")
db_port = os.getenv("DB_PORT")
db_pass = os.getenv("DB_PASSWORD")

async def top(ctx, bot, log, colors, limit=10):

    if not ctx.guild:
        await kat.sendEmbedMessage(ctx,
            title="Error",
            description="This command can only be used in a server.",
            color="ff0000"
        )
        return

    guild_id = str(ctx.guild.id)

    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_pass, port=db_port)
    cur  = conn.cursor()

    try:
        cur.execute("SELECT value FROM user_var WHERE name = %s", ("level",))
        level_row = cur.fetchone()

        cur.execute("SELECT value FROM user_var WHERE name = %s", ("xp",))
        xp_row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not level_row:
        await kat.sendEmbedMessage(ctx,
            title="Leaderboard",
            description="No data yet.",
            color="5865f2"
        )
        return

    level_data = level_row[0]
    if isinstance(level_data, str):
        level_data = json.loads(level_data)

    xp_data = xp_row[0] if xp_row else {}
    if isinstance(xp_data, str):
        xp_data = json.loads(xp_data)

    scores = {}
    for uid, guild_data in level_data.items():
        if isinstance(guild_data, dict) and guild_id in guild_data:
            lvl = int(guild_data[guild_id] or 1)
            xp  = int((xp_data.get(uid, {}) or {}).get(guild_id, 0))
            scores[uid] = (lvl, xp)

    if not scores:
        await kat.sendEmbedMessage(ctx,
            title="Leaderboard",
            description="No one has earned XP here yet.",
            color="5865f2"
        )
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_scores    = sorted_scores[:min(limit, 10)]

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines  = []

    for i, (uid, (lvl, xp)) in enumerate(top_scores, 1):
        try:
            member = ctx.guild.get_member(int(uid)) or await ctx.guild.fetch_member(int(uid))
            name   = member.nick or member.display_name
        except Exception:
            try:
                user = await bot.fetch_user(int(uid))
                name = user.display_name
            except Exception:
                name = f"User {uid}"

        prefix = medals.get(i, f"`#{i}`")
        lines.append(f"{prefix} **{name}** — Level {lvl} • {xp} XP")

    await kat.sendEmbedMessage(ctx,
        title=f"🏆 {ctx.guild.name} Leaderboard",
        description="\n".join(lines),
        color="5865f2",
        footer=f"Requested by {ctx.author.name}",
        footer_icon=str(ctx.author.display_avatar.url),
        timestamp=True
    )

    c = colors
    log(
        "cmd",
        f"{c['BG_BLUE']}{c['BLUE']}{c['BOLD']} {ctx.author} {c['RESET']}",
        f"{c['BG_DARK_BLUE']}{c['WHITE']}{c['BOLD']} >> {c['RESET']} ",
        f"{c['BLUE']}top @ #{ctx.channel}{c['RESET']}",
        log_parts={
            "username":   str(ctx.author),
            "user_id":    str(ctx.author.id),
            "command":    "top",
            "channel":    str(ctx.channel),
            "channel_id": str(ctx.channel.id),
            "guild":      str(ctx.guild.name),
            "guild_id":   guild_id,
        }
    )

async def uptime(ctx, bot, bot_start_time, log, colors):

    if not bot_start_time:
        await kat.sendEmbedMessage(ctx,
            title="Uptime",
            description="Bot hasn't fully started yet.",
            color="ff0000"
        )
        return

    start_ts = int(bot_start_time.timestamp())
    ping     = round(bot.latency * 1000)

    await kat.sendEmbedMessage(ctx,
        title="⏱️ Uptime",
        description=(
            f"**Online since** <t:{start_ts}:R>\n"
            f"**Last Offline** <t:{start_ts}:f>\n"
            f"**Ping** {ping}ms"
        ),
        color="5865f2",
        timestamp=True
    )

    c = colors
    log(
        "cmd",
        f"{c['BG_BLUE']}{c['BLUE']}{c['BOLD']} {ctx.author} {c['RESET']}",
        f"{c['BG_DARK_BLUE']}{c['WHITE']}{c['BOLD']} >> {c['RESET']} ",
        f"{c['BLUE']}uptime @ #{ctx.channel}{c['RESET']}",
        log_parts={
            "username":   str(ctx.author),
            "user_id":    str(ctx.author.id),
            "command":    "uptime",
            "channel":    str(ctx.channel),
            "channel_id": str(ctx.channel.id),
            "guild":      str(ctx.guild.name) if ctx.guild else "DM",
            "guild_id":   str(ctx.guild.id)   if ctx.guild else "0",
        }
    )


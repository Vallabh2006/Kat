import discord, asyncio, io, aiohttp, os, re, psycopg2, json, dotenv
from rankcard import generate, get_config
from datetime import datetime

db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_name = os.getenv("DB_NAME")
db_port = os.getenv("DB_PORT")
db_pass = os.getenv("DB_PASSWORD")

def parse_color(value):
    if value is None:
        return 0x000000
    
    if isinstance(value, int) or str(value).isdigit():
        num = int(value)
        if 0 <= num <= 16777215:
            return num
        raise ValueError("Color out of range (0-16777215)")

    value = str(value).strip()

    if value.startswith("#"):
        value = value[1:]

    if value.startswith("0x"):
        value = value[2:]

    if len(value) == 3:
        value = "".join(c*2 for c in value)

    if re.fullmatch(r"[0-9a-fA-F]{6}", value):
        return int(value, 16)

    raise ValueError("Invalid hex color")

async def _get_guild(ctx, guild_id=None, channel_id=None):
    guild_id = guild_id or channel_id

    if guild_id:
        return ctx.bot.get_guild(int(guild_id)) or await ctx.bot.fetch_guild(int(guild_id))
    return ctx.guild

async def _get_channel(ctx, channel_id):
    if channel_id:
        return ctx.bot.get_channel(int(channel_id)) or await ctx.bot.fetch_channel(int(channel_id))
    return ctx.channel

async def setServerVar(ctx, name, guild_id=None, value=None):

    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_pass, port=db_port)
    cur = conn.cursor()

    if not guild_id:
        guildid = int((await _get_guild(ctx)).id)
    else:
        guildid = int(guild_id)

    if not value:
        value = ""

    cur.execute(
        "SELECT value FROM server_var WHERE name = %s",
        (name,)
    )

    row = cur.fetchone()

    if row is None:

        data = {str(guildid): value}
        cur.execute(
            "INSERT INTO server_var (name, value) VALUES (%s, %s)",
            (name, json.dumps(data))
        )
    else:
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)

        data[str(guildid)] = value

        cur.execute(
            """
            UPDATE server_var
            SET value = %s
            WHERE name = %s
            """,
            (json.dumps(data), name)
        )

    conn.commit()
    cur.close()
    conn.close()
    return True

async def getServerVar(ctx, name, guild_id=None):

    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_pass, port=db_port)
    cur = conn.cursor()

    if not guild_id:
        guildid = int((await _get_guild(ctx)).id)
    else:
        guildid = int(guild_id)

    cur.execute(
        "SELECT value FROM server_var WHERE name = %s",
        (name,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return None

    data = row[0]
    if isinstance(data, str):
        data = json.loads(data)

    return data.get(str(guildid))

async def sendMessage(ctx, content, channel_id=None):
    channel = await _get_channel(ctx, channel_id)
    return await channel.send(content)

async def reply(ctx, content, message_id, channel_id=None, delay=0):
    channel = await _get_channel(ctx, channel_id)
    msg = await channel.fetch_message(int(message_id))

    if delay > 0:
        await asyncio.sleep(delay)

    return await msg.reply(content)

async def editMessage(ctx, content, message_id, channel_id=None, delay=0):
    channel = await _get_channel(ctx, channel_id)
    msg = await channel.fetch_message(int(message_id))

    if delay > 0:
        await asyncio.sleep(delay)

    return await msg.edit(content=content)

async def deleteIn(ctx, message_id, channel_id=None, time=0):
    channel = await _get_channel(ctx, channel_id)
    msg = await channel.fetch_message(int(message_id))

    if time > 0:
        await asyncio.sleep(time)

    return await msg.delete()

async def dmChannelID(ctx, user_id=None):
    if user_id:
        user = await ctx.bot.fetch_user(user_id)
    else:
        user = ctx.author

    dm = user.dm_channel
    if dm is None:
        dm = await user.create_dm()

    return str(dm.id)

async def dmSendMessage(ctx, content, user_id=None):
    if user_id:
        user = await ctx.bot.fetch_user(user_id)
    else:
        user = ctx.author

    return await user.send(content)

async def publishMessage(ctx, message_id, channel_id=None):
    channel = await _get_channel(ctx, channel_id)
    message = await channel.fetch_message(int(message_id))
    try:
        await message.publish()
        return message
    except Exception as e:
        raise Exception(f"Cannot publish message: {e}")

async def pinMessage(ctx, message_id, channel_id=None):
    channel = await _get_channel(ctx, channel_id)
    message = await channel.fetch_message(int(message_id))
    try:
        await message.pin()
        return message
    except Exception as e:
        raise Exception(f"Cannot pin message: {e}")
    
async def unpinMessage(ctx, message_id, channel_id=None):
    channel = await _get_channel(ctx, channel_id)
    message = await channel.fetch_message(int(message_id))
    try:
        await message.unpin()
        return message
    except Exception as e:
        raise Exception(f"Cannot unpin message: {e}")

async def userAvatar(ctx, user_id=None):
    if user_id:
        user = await ctx.bot.fetch_user(int(user_id))
    else:
        user = ctx.author

    return str(user.display_avatar.url)

async def sendEmbedMessage(
    ctx, channel_id=None, content=None, title=None,
    title_url=None, description=None, color=None,
    author=None, author_icon=None, footer=None,
    footer_icon=None, thumbnail=None, image=None,
    timestamp=False, return_id=False
):
    
    channel = await _get_channel(ctx, channel_id)

    embed_needed = any([
        title, title_url, description, author, footer,
        thumbnail, image, timestamp,
        author_icon, footer_icon, color
    ])
    
    embed = None
    files = []

    if embed_needed:

        embed = discord.Embed(color=discord.Color(parse_color(color))) if color else discord.Embed()

        def handle_media(value):
            if not value:
                return None

            if value.startswith("file:"):
                path = value.replace("file:", "")
                base_dir = os.path.dirname(os.path.abspath(__file__))
                full_path = os.path.join(base_dir, path)

                filename = os.path.basename(full_path)
                files.append(discord.File(full_path, filename=filename))

                return f"attachment://{filename}"

            return value

        if title:
            embed.title = title
        if title_url:
            embed.url = title_url

        if title_url and not title:
            embed.title = title_url

        if description:
            embed.description = description

        if color is not None:
            embed.color = discord.Color(parse_color(color))

        if author or author_icon:
            embed.set_author(
                name=author if author else "\u200b",
                icon_url=handle_media(author_icon)
            )

        if timestamp:
            now_str = datetime.now().strftime("%d %b, %Y")
            footer_text = f"{footer} | {now_str}" if footer else now_str
            embed.set_footer(
                text=footer_text,
                icon_url=handle_media(footer_icon)
            )
        elif footer or footer_icon:
            embed.set_footer(
                text=footer if footer else "\u200b",
                icon_url=handle_media(footer_icon)
            )

        if thumbnail:
            embed.set_thumbnail(url=handle_media(thumbnail))

        file = None
        
        if image:
            if isinstance(image, discord.File):
                embed.set_image(url=f"attachment://{image.filename}")
                file = image
            else:
                embed.set_image(url=handle_media(image))

        if not any([
            embed.title,
            embed.description,
            embed.fields,
            getattr(embed.author, "name", None),
            getattr(embed.footer, "text", None)
        ]):
            embed.description = "\u200b"

    if not content and not embed:
        content = "\u200b"

    if file:
        files.append(file)

    msg = await channel.send(
        content=content,
        embed=embed,
        files=files
    )
    
    if return_id:
        return msg.id

async def addField(ctx, name, value, message_id=None, inline=True, channel_id=None):
    
    channel = await _get_channel(ctx, channel_id)

    if message_id:
        msg = await channel.fetch_message(int(message_id))

        if msg.embeds:
            embed = msg.embeds[0].copy()
        else:
            embed = discord.Embed()

        embed.add_field(name=name, value=value, inline=inline)

        await msg.edit(embeds=[embed])
        return msg.id

    else:
        embed = discord.Embed()
        embed.add_field(name=name, value=value, inline=inline)

        msg = await channel.send(embed=embed)
        return msg.id

async def title(ctx, title=None, title_url=None, message_id=None, channel_id=None):
    channel = await _get_channel(ctx, channel_id)

    if not title and not title_url:
        raise Exception("Title or title_url required")

    if message_id:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0].copy() if msg.embeds else discord.Embed()

        if title is not None:
            embed.title = title

        if title_url is not None:
            embed.url = title_url

        if not embed.title:
            embed.title = "\u200b"

        await msg.edit(embeds=[embed])
        return msg.id

    else:
        embed = discord.Embed()

        if title:
            embed.title = title

        if title_url:
            embed.url = title_url

        if not embed.title:
            embed.title = "\u200b"

        msg = await channel.send(embed=embed)
        return msg.id

async def description(ctx, description, message_id=None, channel_id=None):
    channel = await _get_channel(ctx, channel_id)

    if message_id:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0].copy() if msg.embeds else discord.Embed()
        embed.description = description
        await msg.edit(embeds=[embed])
        return msg.id
    else:
        embed = discord.Embed(description=description)
        msg = await channel.send(embed=embed)
        return msg.id

async def color(ctx, color, message_id=None, channel_id=None):
    channel = await _get_channel(ctx, channel_id)

    color_value = parse_color(color)

    if message_id:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0].copy() if msg.embeds else discord.Embed()
        embed.color = discord.Color(color_value)
        await msg.edit(embeds=[embed])
        return msg.id
    else:
        embed = discord.Embed(color=discord.Color(color_value))
        if not any([embed.title, embed.description, embed.fields]):
            embed.description = "\u200b"
        msg = await channel.send(embed=embed)
        return msg.id

async def author(ctx, author=None, author_icon=None, message_id=None, url=None, channel_id=None):
    if not author and not author_icon:
        raise Exception("Author name or icon required")
    
    channel = await _get_channel(ctx, channel_id)

    files = []

    def handle_media(value):
        if not value:
            return None

        if value.startswith("file:"):
            path = value.replace("file:", "")

            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base_dir, path)

            filename = os.path.basename(full_path)

            files.append(discord.File(full_path, filename=filename))
            return f"attachment://{filename}"

        return value

    if message_id:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0].copy() if msg.embeds else discord.Embed()

        existing_author = embed.author

        author = author if author is not None else existing_author.name
        author_icon = author_icon if author_icon is not None else existing_author.icon_url
        url = url if url is not None else existing_author.url

        if not author:
            author = "\u200b"

        embed.set_author(
            name=author,
            icon_url=handle_media(author_icon),
            url=url
        )

        existing_files = [await att.to_file() for att in msg.attachments]
        files = existing_files + files

        await msg.edit(embed=embed, attachments=files)
        return msg.id

    else:
        embed = discord.Embed()

        if not author:
            author = "\u200b"

        embed.set_author(
            name=author,
            icon_url=handle_media(author_icon),
            url=url
        )

        msg = await channel.send(embed=embed, files=files if files else None)
        return msg.id

async def footer(ctx, footer=None, footer_icon=None, message_id=None, channel_id=None):
    if not footer and not footer_icon:
        raise Exception("Footer text or icon required")

    channel = await _get_channel(ctx, channel_id)

    files = []

    def handle_media(value):
        if not value:
            return None

        if value.startswith("file:"):
            path = value.replace("file:", "")

            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base_dir, path)

            filename = os.path.basename(full_path)

            files.append(discord.File(full_path, filename=filename))
            return f"attachment://{filename}"

        return value

    if message_id:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0].copy() if msg.embeds else discord.Embed()

        existing_footer = embed.footer

        footer = footer if footer is not None else existing_footer.text
        footer_icon = footer_icon if footer_icon is not None else existing_footer.icon_url

        if not footer:
            footer = "\u200b"

        embed.set_footer(
            text=footer,
            icon_url=handle_media(footer_icon)
        )

        existing_files = [await att.to_file() for att in msg.attachments]
        files = existing_files + files

        await msg.edit(embed=embed, attachments=files)
        return msg.id

    else:
        embed = discord.Embed()

        if not footer:
            footer = "\u200b"

        embed.set_footer(
            text=footer,
            icon_url=handle_media(footer_icon)
        )

        msg = await channel.send(embed=embed, files=files if files else None)
        return msg.id

async def thumbnail(ctx, image_url, message_id=None, channel_id=None):
    channel = await _get_channel(ctx, channel_id)

    files = []

    def handle_media(value):
        if not value:
            return None

        if value.startswith("file:"):
            path = value.replace("file:", "")
            base = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base, path)

            filename = os.path.basename(full_path)
            files.append(discord.File(full_path, filename=filename))

            return f"attachment://{filename}"

        return value

    if message_id:
        msg = await channel.fetch_message(int(message_id))
        embed = msg.embeds[0].copy() if msg.embeds else discord.Embed()

        embed.set_thumbnail(url=handle_media(image_url))

        if not any([embed.title, embed.description, embed.fields]):
            embed.description = "\u200b"

        existing = [await att.to_file() for att in msg.attachments]

        files = existing + files

        await msg.edit(embed=embed, attachments=files)
        return msg.id

    else:
        embed = discord.Embed()
        embed.set_thumbnail(url=handle_media(image_url))
        embed.description = "\u200b"

        msg = await channel.send(embed=embed, files=files if files else None)
        return msg.id

async def image(ctx, image_url=None, message_id=None, channel_id=None):
    if not image_url:
        raise ValueError("Image URL or file path required")

    channel = await _get_channel(ctx, channel_id)
    file = None

    if isinstance(image_url, str) and image_url.startswith("file:"):
        path = image_url.replace("file:", "")
        base = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base, path)

        filename = os.path.basename(full_path)
        file = discord.File(full_path, filename=filename)
        image_url = None

    if message_id:
        msg = await channel.fetch_message(int(message_id))

        new_content = msg.content or ""

        if image_url:
            if new_content:
                new_content += "\n"
            new_content += image_url

        if file:

            existing = [await a.to_file() for a in msg.attachments]

            await msg.edit(
                content=new_content,
                attachments=existing + [file]
            )
        else:
            await msg.edit(content=new_content)

        return msg.id

    else:
        if file:
            msg = await channel.send(file=file)
        else:
            msg = await channel.send(image_url)

        return msg.id
    
async def embedImage(ctx, url=None, message_id=None, channel_id=None):
    channel = await _get_channel(ctx, channel_id)

    files = []

    def handle_media(value):
        if not value:
            return None

        if value.startswith("file:"):
            path = value.replace("file:", "")
            base = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base, path)

            filename = os.path.basename(full_path)
            files.append(discord.File(full_path, filename=filename))

            return f"attachment://{filename}"

        return value

    image_url = handle_media(url)

    if message_id:
        msg = await channel.fetch_message(int(message_id))

        embeds = msg.embeds.copy() if msg.embeds else [discord.Embed()]
        embed = embeds[0].copy()

        embed.set_image(url=image_url)

        if not any([embed.title, embed.description, embed.fields]):
            embed.description = "\u200b"

        embeds[0] = embed

        existing_files = [await att.to_file() for att in msg.attachments]
        files = existing_files + files

        await msg.edit(embeds=embeds, attachments=files)
        return msg.id

    else:
        embed = discord.Embed()
        embed.set_image(url=image_url)

        if not embed.description:
            embed.description = "\u200b"

        msg = await channel.send(embed=embed, files=files if files else None)
        return msg.id

async def clear(ctx, count, user_id=None, channel_id=None):

    channel = await _get_channel(ctx, channel_id)

    deleted = 0
    async for message in channel.history(limit=200):
        if deleted >= int(count):
            break

        if user_id and message.author.id != int(user_id):
            continue

        await message.delete()
        deleted += 1

async def modifyUserRole(ctx, user_id, role_id, grant=True, guild_id=None):

    guild = await _get_guild(ctx, guild_id)

    if not guild:
        raise Exception("Guild not found.")

    member = guild.get_member(int(user_id))
    if not member:
        member = await guild.fetch_member(int(user_id))

    if not member:
        raise Exception(f"User {user_id} not found in guild {guild.id}.")

    role = guild.get_role(int(role_id))
    if not role:
        raise Exception(f"Role {role_id} not found in guild {guild.id}.")

    if guild_id:
        guild = ctx.bot.get_guild(int(guild_id))
        if not guild:
            guild = await ctx.bot.fetch_guild(int(guild_id))
    else:
        guild = ctx.guild

    if not guild:
        raise ValueError(f"Guild not found.")

    member = guild.get_member(int(user_id))
    if not member:
        member = await guild.fetch_member(int(user_id))

    if not member:
        raise ValueError(f"User {user_id} not found in guild {guild.id}.")

    role = guild.get_role(int(role_id))
    if not role:
        raise ValueError(f"Role {role_id} not found in guild {guild.id}.")

    if grant:
        await member.add_roles(role, reason=f"Role assigned via command by {ctx.author}")
    elif not grant:
        await member.remove_roles(role, reason=f"Role removed via command by {ctx.author}")
    else:
        raise ValueError(f"Invalid grant '{grant}'. To grant role use grant parameter as True, vice versa")
    
async def getRankcard(ctx, user_id, guild_id=None):
    from rankcard import generate, get_config
    import io, discord

    if guild_id is None:
        guild_id = ctx.guild.id if ctx.guild else None

    try:
        user = await ctx.bot.fetch_user(int(user_id))
        username   = user.name
        avatar_url = str(user.display_avatar.url)
    except Exception:
        username   = str(user_id)
        avatar_url = None

    cfg = get_config(str(user_id))

    level  = 4
    xp     = 23
    xp_max = 250
    rank   = 1

    img_bytes = generate(
        username   = username,
        avatar_url = avatar_url,
        level      = level,
        xp         = xp,
        xp_max     = xp_max,
        rank       = rank,
        **cfg,
    )

    buf = io.BytesIO(img_bytes)
    buf.seek(0)
    return discord.File(buf, filename=f"{username}_rankcard.png")
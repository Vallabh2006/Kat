from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests, io, json, os, psycopg2
from dotenv import load_dotenv

load_dotenv()

db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_name = os.getenv("DB_NAME")
db_port = os.getenv("DB_PORT")
db_pass = os.getenv("DB_PASSWORD")

SANS_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
MONO_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 700, 160

DEFAULTS = {
    "bg":        "111214",
    "border":    "2a2d31",
    "accent":    "f0b429",
    "text_main": "ffffff",
    "text_sub":  "8a8f98",
    "text_mono": "bbbbbb",
    "bar_track": "2d3138",
    "show_rank":  True,
    "show_level": True,
    "show_xp":    True,
    "rounded":    False,
    "bg_image":   None,
    "bg_opacity": 0.3,
}

def h(hex_str):
    s = str(hex_str).lstrip("#")
    if len(s) == 3: s = "".join(c*2 for c in s)
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

def font(path, size):
    try:    return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def xp_fmt(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

def fetch_avatar(url, size, bot_token=None):
    if url and "cdn.discordapp.com" in url:
        headers = {
            "User-Agent": "DiscordBot (RankCard, 1.0)",
            "Authorization": f"Bot {bot_token}" if bot_token else "",
        }
    else:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; RankCard/1.0)"}

    try:
        r = requests.get(url, timeout=8, headers=headers)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGBA")
        iw, ih = img.size
        sq = min(iw, ih)
        img = img.crop(((iw-sq)//2, (ih-sq)//2, (iw+sq)//2, (ih+sq)//2))
        return img.resize((size, size), Image.LANCZOS)
    except Exception:
        return None

def circle_crop(img, size):
    img = img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    out = Image.new("RGBA", (size, size), (0,0,0,0))
    out.paste(img, mask=mask)
    return out

def avatar_placeholder(size, accent_rgb, rounded=False):
    img  = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    if rounded:
        draw.ellipse([0,0,size,size], fill=accent_rgb+(60,))
    else:
        draw.rectangle([0,0,size,size], fill=accent_rgb+(60,))
    cx, cy = size//2, size//2
    hr = size//5
    draw.ellipse([cx-hr, cy//2-hr, cx+hr, cy//2+hr], fill=(255,255,255,120))
    draw.ellipse([cx-size//3, cy+size//14, cx+size//3, cy+size//2], fill=(255,255,255,100))
    return img

async def setRankcard(
    user_id, bg="111214", border="2a2d31", accent="f0b429",
    text_main="ffffff", text_sub="8a8f98", text_mono="bbbbbb",
    bar_track="2d3138", show_rank=True, show_level=True,
    show_xp=True, rounded=False, bg_image=None, bg_opacity=0.3
):

    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_pass, port=db_port)
    cur = conn.cursor()

    try:
        uid = int(user_id)

        cur.execute("SELECT user_id FROM rankcard WHERE user_id = %s", (uid,))
        exists = cur.fetchone()

        fields = {
            "bg": bg, "border": border, "accent": accent, "text_main": text_main,
            "text_sub": text_sub, "text_mono": text_mono, "bar_track": bar_track,
            "show_rank": show_rank, "show_level": show_level, "show_xp": show_xp,
            "rounded": rounded, "bg_image": bg_image, "bg_opacity": bg_opacity
        }

        if not exists:
            fields["user_id"] = uid
            cols = ", ".join(fields.keys())
            vals = ", ".join(["%s"] * len(fields))
            cur.execute(
                f"INSERT INTO rankcard ({cols}) VALUES ({vals})",
                list(fields.values())
            )
        else:
            set_clause = ", ".join(f"{k} = %s" for k in fields)
            cur.execute(
                f"UPDATE rankcard SET {set_clause} WHERE user_id = %s",
                list(fields.values()) + [uid]
            )

        conn.commit()
        return True

    finally:
        cur.close()
        conn.close()

async def getRankcard(user_id):

    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_pass, port=db_port)
    cur = conn.cursor()

    try:
        uid = int(user_id)

        cur.execute("""
            SELECT bg, border, accent, text_main, text_sub, text_mono,
                   bar_track, show_rank, show_level, show_xp, rounded,
                   bg_image, bg_opacity
            FROM rankcard WHERE user_id = %s
        """, (uid,))

        row = cur.fetchone()

        if row is None:
            return {}

        keys = ["bg", "border", "accent", "text_main", "text_sub", "text_mono",
                "bar_track", "show_rank", "show_level", "show_xp", "rounded",
                "bg_image", "bg_opacity"]

        return dict(zip(keys, row))

    finally:
        cur.close()
        conn.close()

def generate(
    username="User",
    discriminator="",
    avatar_url=None,
    level=1,
    xp=0,
    xp_max=100,
    rank=None,
    **kwargs,
):
    cfg = {**DEFAULTS}
    cfg.update({k: v for k, v in kwargs.items() if v is not None})

    BG    = h(cfg["bg"])
    BORDER = h(cfg["border"])
    ACCENT = h(cfg["accent"])
    TXT1  = h(cfg["text_main"])
    TXT2  = h(cfg["text_sub"])
    TRACK = h(cfg["bar_track"])

    BORDER_W = 4
    AV_SIZE  = 120

    card = Image.new("RGBA", (W, H), BORDER)
    draw = ImageDraw.Draw(card)

    draw.rectangle(
        [BORDER_W, BORDER_W, W - BORDER_W, H - BORDER_W],
        fill=BG
    )

    if cfg.get("bg_image"):
        try:
            r = requests.get(cfg["bg_image"], timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            bg = Image.open(io.BytesIO(r.content)).convert("RGBA").resize((W, H), Image.LANCZOS)
            bg.putalpha(int(255 * cfg["bg_opacity"]))
            card.alpha_composite(bg)
        except Exception:
            pass

    AV_X    = W - AV_SIZE - 20
    AV_Y    = (H - AV_SIZE) // 2
    rounded = bool(cfg.get("rounded", False))

    av = fetch_avatar(avatar_url, AV_SIZE, bot_token=cfg.get("bot_token")) if avatar_url else None
    if av is None:
        av = avatar_placeholder(AV_SIZE, ACCENT)

    if rounded:
        av = circle_crop(av, AV_SIZE)
    else:
        av = av.resize((AV_SIZE, AV_SIZE), Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", (AV_SIZE, AV_SIZE), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, AV_SIZE, AV_SIZE], radius=16, fill=255)
        out = Image.new("RGBA", (AV_SIZE, AV_SIZE), (0, 0, 0, 0))
        out.paste(av, mask=mask)
        av = out

    card.paste(av, (AV_X, AV_Y), av)

    LEFT     = 24
    RIGHT    = AV_X - 24
    CONTENT_W = RIGHT - LEFT

    f_name  = ImageFont.truetype("arial.ttf", 35)
    f_stats = ImageFont.truetype("arial.ttf", 20)
    f_xp    = ImageFont.truetype("arial.ttf", 12)

    rank_text = f"#{rank}" if rank is not None else "N/A"

    draw.text((LEFT, 25), f"{rank_text} {username}", font=f_name, fill=TXT1)
    draw.text((LEFT, 71), f"Level {level}", font=f_stats, fill=TXT2)

    pct   = max(0.0, min(1.0, xp / xp_max if xp_max else 0))
    BAR_Y = 100
    BAR_H = 18
    BAR_W = CONTENT_W - 10

    draw.rounded_rectangle([LEFT, BAR_Y, LEFT + BAR_W, BAR_Y + BAR_H], radius=9, fill=TRACK)

    fill_w = int(BAR_W * pct)
    if fill_w > 0:
        draw.rounded_rectangle([LEFT, BAR_Y, LEFT + fill_w, BAR_Y + BAR_H], radius=9, fill=ACCENT)

    draw.text((LEFT, BAR_Y + BAR_H + 8), f"{xp_fmt(xp)} / {xp_fmt(xp_max)} XP", font=f_xp, fill=TXT2)

    buf = io.BytesIO()
    card.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf.read()

async def deleteRankcard(user_id):

    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_pass, port=db_port)
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM rankcard WHERE user_id = %s", (int(user_id),))
        conn.commit()
        return True

    finally:
        cur.close()
        conn.close()
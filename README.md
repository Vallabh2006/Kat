
# Kat

### A modular Discord bot built with **Python**, **discord.py**, and **Flask**, featuring PostgreSQL integration, a custom function library, a web dashboard, and live log monitoring.

----------

## ✨ Features

-    Discord bot powered by `discord.py`
    
-    Web dashboard built with Flask
    
-    Live log viewer for monitoring bot activity
    
-    PostgreSQL database integration
    
-    Modular command and extension system
    
-    Custom `kat.py` utility library for rapid development
    
-    Environment-based configuration
    
-    Modern glass-style web interface
    

----------

## 🚀 Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Vallabh2006/kat.git
cd kat
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file:

```env
TOKEN_KAT=INSERT_DEFAULT_DISCORD_BOT_TOKEN_HERE
TOKEN_<ANOTHER_BOT_NAME>=INSERT_EXTRA_DISCORD_BOT_TOKEN_IF_NEEDED

PREFIXES=["!", "."]
  
BOT_OWNER_ID=INSERT_BOT_OWNER_ID_HERE
BOT_DEV_ID=INSERT_BOT_DEV_ID_HERE
  
LOG_KEY=INSERT_LOG_KEY_HERE
  
STATUS_COUNT=2
STATUS_1=You are being watched, Say Cheese
STATUS_2=Listening to Dawg
  
FLASK_CERT=INSER_FLASK_CERT_LOCATION
FLASK_KEY=INSER_FLASK_KEY_LOCATION
  
DB_HOST=localhost
DB_PORT=INSERT_DATABASE_PORT_HERE
DB_NAME=INSERT_DATABASE_NAME_HERE
DB_USER=INSERT_DATABASE_USERNAME_HERE
DB_PASSWORD=INSERT_DATABASE_PASSWORD_HERE
```

### 4. Run Kat

```bash
python app.py
```

----------

## 🌐 Web Dashboard

When Kat starts, a Flask dashboard is launched alongside the bot.

### Pages

`/`:  Dashboard home page

`/logs`: Live event and bot logs

The dashboard provides a simple interface for monitoring bot activity without opening the console.

----------

## 🔑 Supported Prefixes

Prefixes are loaded from `.env`:

```json
["!", ".", "?", "$"]
```

----------

## 📚 Kat.py Function Reference

### 💬 Messages

-   `sendMessage(ctx, content, channel_id=None)` — Send a message
    
-   `reply(ctx, content, message_id, channel_id=None, delay=None)` — Reply to a message
    
-   `editMessage(ctx, content, message_id, channel_id=None, delay=None)` — Edit a message
    
-   `deleteIn(ctx, message_id, channel_id=None, time=None)` — Delete a message after a delay
    
-   `publishMessage(ctx, message_id, channel_id=None)` — Publish a message
    
-   `pinMessage(ctx, message_id, channel_id=None)` — Pin a message
    
-   `unpinMessage(ctx, message_id, channel_id=None)` — Unpin a message
    
-   `clear(ctx, count, user_id=None, channel_id=None)` — Bulk delete messages
    

### 🎨 Embeds

-   `sendEmbedMessage(ctx, ...)`
    
-   `addField(ctx, name, value, message_id=None, inline=True, channel_id=None)`
    
-   `title(ctx, title, title_url=None, message_id=None, channel_id=None)`
    
-   `description(ctx, description, message_id=None, channel_id=None)`
    
-   `color(ctx, color, message_id=None, channel_id=None)`
    
-   `author(ctx, author, author_icon=None, message_id=None, url=None, channel_id=None)`
    
-   `footer(ctx, footer, footer_icon=None, message_id=None, channel_id=None)`
    
-   `thumbnail(ctx, image_url, message_id=None, channel_id=None)`
    
-   `embedImage(ctx, url, message_id=None, channel_id=None)`
    
-   `image(ctx, image_url, message_id=None, channel_id=None)`
    

#### Supported Color Formats

```python
"#ff0000"
"#f00"
"0xff0000"
16711680
```

#### Local Images

```python
file:Files/sample1.jpg
```

Images may be supplied using either a URL or a local file path prefixed with `file:`.

### 📩 Direct Messages

-   `dmSendMessage(ctx, content, user_id=None)`
    
-   `dmChannelID(ctx, user_id=None)`
    

### 👤 Users & Roles

-   `userAvatar(ctx, user_id=None)`
    
-   `modifyUserRole(ctx, user_id, role_id, grant=True, guild_id=None)`
    

### 🗄️ Database

-   `setServerVar(ctx, name, guild_id=None, value=None)`
    

----------

## 📁 Project Structure

```text
Kat/
│
├── app.py                # Main application
├── kat.py                # Utility function library
│
├── templates/
│   ├── base.html
│   ├── index.html
│   └── logs.html
│
├── static/
│   └── style.css
│
├── Files/                # Local assets
│
├── .env
├── .env.example
├── requirements.txt
│
└── logs/
```

----------

## 📦 Requirements

-   Python 3.10+
    
-   discord.py 2.x
    
-   Flask
    
-   PostgreSQL
    
-   python-dotenv
    

----------

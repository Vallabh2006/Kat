
---

# Kat

### A modular Discord bot built with **Python** and **discord.py**, featuring database integration and a custom function library designed for rapid bot development.

---

##  Setup

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

Create a `.env` file and add the following:
```env
TOKEN_KAT=your_bot_token
TOKEN_<EXTRA_BOT_NAME>=

DB_HOST=your_host
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password
DB_PORT=5432
```

### 4. Run the Bot

```bash
python app.py
```

---

##  Supported Prefixes

```text
!  .  ?  $
```
##  Kat Py Function Reference

###  Messages

-   `sendMessage(ctx, content, channel_id=None)`  :
    Send a message.
    
-   `reply(ctx, content, message_id, channel_id=None, delay=None)`  :
    Reply to a message.
    
-   `editMessage(ctx, content, message_id, channel_id=None, delay=None)`  :
    Edit a message.
    
-   `deleteIn(ctx, message_id, channel_id=None, time=None)`:  
    Delete a message after a delay.
    
-   `publishMessage(ctx, message_id, channel_id=None)`  :
    Publish a message in an Announcement channel.
    
-   `pinMessage(ctx, message_id, channel_id=None)`  :
    Pin a message.
    
-   `unpinMessage(ctx, message_id, channel_id=None)`  :
    Unpin a message.
    
-   `clear(ctx, count, user_id=None, channel_id=None)`  :
    Delete messages, optionally filtered by user.
    

----------

###  Embeds

-   `sendEmbedMessage(ctx, ...)`  :
    Send a customizable embed.
    
-   `addField(ctx, name, value, message_id=None, inline=True, channel_id=None)`  :
    Add a field to an embed.
    
-   `title(ctx, title, title_url=None, message_id=None, channel_id=None)`  :
    Set embed title.
    
-   `description(ctx, description, message_id=None, channel_id=None)`  :
    Set embed description.
    
-   `color(ctx, color, message_id=None, channel_id=None)`  :
    Set embed color.
    
-   `author(ctx, author, author_icon=None, message_id=None, url=None, channel_id=None)`  :
    Set embed author.
    
-   `footer(ctx, footer, footer_icon=None, message_id=None, channel_id=None)` : 
    Set embed footer.
    
-   `thumbnail(ctx, image_url, message_id=None, channel_id=None)`  :
    Set embed thumbnail.
    
-   `embedImage(ctx, url, message_id=None, channel_id=None)`  :
    Set embed image.
    
-   `image(ctx, image_url, message_id=None, channel_id=None)`  :
    Send or attach an image.
    

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

Images may be provided using either a URL or a local file path prefixed with `file:`.

----------

### 📩 Direct Messages

-   `dmSendMessage(ctx, content, user_id=None)`  :
    Send a DM.
    
-   `dmChannelID(ctx, user_id=None)`  :
    Get a user's DM channel ID.
    

----------

### 👤 Users & Roles

-   `userAvatar(ctx, user_id=None)`  :
    Get a user's avatar URL.
    
-   `modifyUserRole(ctx, user_id, role_id, action=1, guild_id=None)`  :
    Add or remove a role. 
    
    Note: To grant role leave the action paramter empty or use 1, to remove a role use 0
    


----------

### 🗄️ Database

-   `setServerVar(ctx, name, guild_id=None, value=None)`  
    Store a server-specific variable.

---  

## 📁 Project Structure

  

```text

Kat/

│

├── app.py # Bot entry point

├── kat.py # Core function library

├── .env # Environment variables

├── .env.example # Environment template

├── requirements.txt # Python dependencies

│

└── Files/ # Local media assets

```

  

---

  

## 📦 Requirements

  

* Python 3.10+

* discord.py 2.x

* PostgreSQL

* python-dotenv

  

---

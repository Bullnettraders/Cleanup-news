import os
import asyncio
import discord
from discord.ext import tasks, commands
import datetime
from dotenv import load_dotenv

# .env laden (für lokale Tests)
load_dotenv()

# Token & Channel-IDs laden
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_IDS = [int(id.strip()) for id in os.getenv("TARGET_CHANNEL_ID").split(",")]

# Discord-Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

# Bot initialisieren
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot ist eingeloggt als {bot.user}")
    cleanup_old_messages.start()

@tasks.loop(hours=24)
async def cleanup_old_messages():
    await bot.wait_until_ready()
    now = datetime.datetime.now(datetime.UTC)
    cutoff = now - datetime.timedelta(days=2)  # NUR älter als 1 Tage

    for channel_id in CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"⚠️ Channel mit ID {channel_id} nicht gefunden.")
            continue

        print(f"🧹 Starte Cleanup für Channel: {channel.name}")
        deleted = 0

        try:
            async for message in channel.history(limit=None, oldest_first=True):
                if message.created_at < cutoff:
                    try:
                        await message.delete()
                        await asyncio.sleep(1)  # Rate Limit beachten
                        deleted += 1
                        if deleted % 10 == 0:
                            print(f"🧽 Bisher gelöscht: {deleted} in {channel.name}")
                    except discord.HTTPException as e:
                        if e.status == 429:
                            retry_after = getattr(e, "retry_after", 2)
                            print(f"⚠️ Rate Limit erreicht. Warte {retry_after} Sekunden.")
                            await asyncio.sleep(retry_after)
                        else:
                            print(f"❌ Fehler beim Löschen: {e}")
                    except discord.Forbidden:
                        print(f"🚫 Keine Berechtigung zum Löschen in {channel.name}.")
        except Exception as e:
            print(f"❌ Fehler beim Zugriff auf Channel {channel.name}: {e}")

        print(f"✅ {deleted} alte Nachrichten gelöscht in {channel.name}")

# Bot starten
bot.run(TOKEN)

import discord
import aiohttp
import subprocess
import tempfile
import os
import time
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN     = os.getenv("BOT_TOKEN")
PASTEFY_TOKEN = os.getenv("PASTEFY_TOKEN")
LUADEC_PATH   = "./luadec"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def upload_to_pastefy(content: str, filename: str) -> str | None:
    url = "https://pastefy.app/api/v2/paste"
    headers = {
        "Authorization": f"Bearer {PASTEFY_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "title": filename,
        "content": content,
        "type": "PASTE",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                paste_id = data.get("paste", {}).get("id")
                return f"https://pastefy.app/{paste_id}/raw" if paste_id else None
    return None


async def fetch_url(url: str) -> bytes | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
    return None


def run_luadec(input_path: str) -> tuple[str, float]:
    start = time.time()
    try:
        result = subprocess.run(
            [LUADEC_PATH, input_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        elapsed = (time.time() - start) * 1000
        output = result.stdout if result.stdout else result.stderr
        return output, elapsed
    except subprocess.TimeoutExpired:
        elapsed = (time.time() - start) * 1000
        return "-- luadec timed out", elapsed
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return f"-- luadec error: {e}", elapsed


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.content.lower().startswith("!el"):
        return

    raw_bytes = None
    filename  = "dump.lua"

    if message.attachments:
        att = message.attachments[0]
        filename  = att.filename
        raw_bytes = await fetch_url(att.url)

    elif message.reference:
        ref = await message.channel.fetch_message(message.reference.message_id)
        if ref.attachments:
            att = ref.attachments[0]
            filename  = att.filename
            raw_bytes = await fetch_url(att.url)
        else:
            words = ref.content.split()
            for word in words:
                if word.startswith("http"):
                    raw_bytes = await fetch_url(word)
                    filename  = word.split("/")[-1] or "dump.lua"
                    if not filename.endswith(".lua"):
                        filename += ".lua"
                    break

    else:
        words = message.content.split()
        for word in words:
            if word.startswith("http"):
                raw_bytes = await fetch_url(word)
                filename  = word.split("/")[-1] or "dump.lua"
                if not filename.endswith(".lua"):
                    filename += ".lua"
                break

    if not raw_bytes:
        await message.reply("❌ No Lua file found. Attach a file, reply to one, or provide a URL.")
        return

    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    try:
        output, elapsed = run_luadec(tmp_path)
    finally:
        os.unlink(tmp_path)

    pastefy_url = await upload_to_pastefy(output, filename)

    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, mode="w", encoding="utf-8") as out:
        out.write(output)
        out_path = out.name

    try:
        file = discord.File(out_path, filename=f"deobf_{filename}")
        msg  = f"**Pastefy:** {pastefy_url}\n`Finished in {elapsed:.2f}ms`"
        await message.reply(msg, file=file)
    finally:
        os.unlink(out_path)


client.run(BOT_TOKEN)

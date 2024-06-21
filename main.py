import pyrogram
from pyrogram import Client, filters
import re
import asyncio
import aiohttp
from pymongo import MongoClient
from pyrogram.errors import FloodWait, RPCError
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB configuration
MONGO_URI = 'mongodb+srv://iamdaxx404:asd@mohio.1uwb6r5.mongodb.net'
client = MongoClient(MONGO_URI)
db = client['mrdaxx_scrapper_db']
cards_collection = db['cards']

def correct_padding(session_string):
    return session_string + "=" * ((4 - len(session_string) % 4) % 4)

app = pyrogram.Client(
    'mrdaxx_scrapper',
    api_id='27649783',
    api_hash='834fd6015b50b781e0f8a41876ca95c8',
    session_string=correct_padding("BAE9p8oAB0gnl5-vQwEqaWQ0-fo4PCz3jAydwwLI5m0v7eAhfjE2zmNXT7Bn20EQwT56yS-AK6qf86_G_MbImwHPJiZpkLUhPUiGJgmIFyh67oMUPbES36pXITRV0_iD2gaIm-gXT1vzkIVp0aGvPLU4yGGEWulWWRpVzqHJ3Ur8GB99_xBHdhWp149eodHVOBCjq9RybgrCRSxrh8rjZ4m8-ugNn9WrBrCFcwDeNhjETGrCNa7TJKKBiC2-2ViGUHYKZJfXdIFtA0osHEWqa3ErSC9u4Pzay4GOVddzXTD0tP7jY5KsDRDv1TJ5kWeAzbuHT8nFgNdWPVh6l3nV2v9NoYsKZAAAAAG2CUg-AA")  # Ensure correct padding
)

BIN_API_URL = 'https://astroboyapi.com/api/bin.php?bin={}'

def filter_cards(text):
    regex = r'\d{15,16}\D*\d{2}\D*\d{2,4}\D*\d{3,4}'
    return re.findall(regex, text)

async def bin_lookup(bin_number):
    bin_info_url = BIN_API_URL.format(bin_number)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        try:
            async with session.get(bin_info_url) as response:
                if response.status == 200:
                    try:
                        return await response.json()
                    except aiohttp.ContentTypeError:
                        logger.error("Invalid content type received")
                        return None
                else:
                    logger.error(f"Failed to fetch BIN info, status code: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error during BIN lookup: {e}")
            return None

async def send_message_with_retry(Client, chat_id, text, retries=5):
    attempt = 0
    while attempt < retries:
        try:
            await Client.send_message(chat_id=chat_id, text=text)
            return
        except FloodWait as e:
            logger.warning(f"FloodWait error: sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
            attempt += 1
        except RPCError as e:
            logger.error(f"RPCError: {e}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            attempt += 1
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            attempt += 1
    logger.error("Failed to send message after multiple retries")

async def process_card(Client, card_info):
    bin_number = card_info[:6]
    bin_info = await bin_lookup(bin_number)
    if bin_info:
        brand = bin_info.get("brand", "N/A")
        card_type = bin_info.get("type", "N/A")
        level = bin_info.get("level", "N/A")
        bank = bin_info.get("bank", "N/A")
        country = bin_info.get("country_name", "N/A")
        country_flag = bin_info.get("country_flag", "")

        formatted_message = (
            "┏━━━━━━━⍟\n"
            "┃𝖡𝖱𝖠𝖨𝖭𝖳𝖱𝖤𝖤 𝖠𝖴𝖳𝖧 𝟓$ ✅\n"
            "┗━━━━━━━━━━━⊛\n\n"
            f"𖠁𝖢𝖠𝖱𝖣 ➔ <code>{card_info}</code>\n\n"
            f"𖠁𝖲𝖳𝖠𝖳𝖴𝖲 ➔ <b>Approved! ✅</b>\n\n"
            f"𖠁𝖡𝖨𝖭 ➔ <b>{brand}, {card_type}, {level}</b>\n\n"
            f"𖠁𝖡𝖠𝖭𝖪 ➔ <b>{bank}</b>\n\n"
            f"𖠁𝖢𝖮𝖴𝖭𝖳𝖱𝖸 ➔ <b>{country}, {country_flag}</b>\n\n"
            "𖠁𝖢𝖱𝖤𝖠𝖳𝖮𝖱 ➔ <b>๏─𝙂𝘽𝙋─๏</b>"
        )

        await send_message_with_retry(Client, '-1002174770449', formatted_message)

        # Save card info to MongoDB to prevent duplicate sending
        cards_collection.insert_one({"card_info": card_info})
        logger.info(f"Card info saved: {card_info}")

async def approved(Client, messages):
    try:
        tasks = []
        for message in messages:
            if re.search(r'(Approved!|Charged|authenticate_successful|𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱|APPROVED|New Cards Found By JennaScrapper|ꕥ Extrap [☭]|み RIMURU SCRAPE by|Approved) ✅', message.text):
                filtered_card_info = filter_cards(message.text)
                if not filtered_card_info:
                    logger.info("No card information found in message")
                    continue

                for card_info in filtered_card_info:
                    if not cards_collection.find_one({"card_info": card_info}):
                        tasks.append(process_card(Client, card_info))
                    else:
                        logger.info(f"Card info already exists: {card_info}")

        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error in approved function: {e}")

message_buffer = []
BATCH_SIZE = 5  # Adjust the batch size as needed
SLEEP_TIME = 3  # Sleep time in seconds between batches

@app.on_message(filters.text)
async def astro(Client, message):
    message_buffer.append(message)
    if len(message_buffer) >= BATCH_SIZE:
        await approved(Client, message_buffer)
        message_buffer.clear()
        logger.info(f"Processed batch of {BATCH_SIZE} messages, sleeping for {SLEEP_TIME} seconds")
        await asyncio.sleep(SLEEP_TIME)

app.run()

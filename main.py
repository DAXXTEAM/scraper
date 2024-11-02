import pyrogram
from pyrogram import Client, filters
import re
import asyncio
import aiohttp
from pymongo import MongoClient

# MongoDB configuration
MONGO_URI = 'mongodb+srv://iamdaxx404:asd@mohio.1uwb6r5.mongodb.net'
client = MongoClient(MONGO_URI)
db = client['mrdaxx_scrapper_db']
cards_collection = db['cards']

app = pyrogram.Client(
    'mrdaxx_scrapper',
    api_id=27649783,  # Use integer without quotes
    api_hash='834fd6015b50b781e0f8a41876ca95c8'
)

BIN_API_URL = 'https://astroboyapi.com/api/bin.php?bin={}'

def filter_cards(text):
    regex = r'\b\d{15,16}\D*\d{2}\D*\d{2,4}\D*\d{3,4}\b'
    return re.findall(regex, text)

async def bin_lookup(bin_number):
    bin_info_url = BIN_API_URL.format(bin_number)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(bin_info_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error: BIN lookup failed with status {response.status}")
        except Exception as e:
            print(f"Error during BIN lookup: {e}")
    return None

async def approved(client_instance, message):
    try:
        if re.search(r'(Approved!|Charged|authenticate_successful|𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱|APPROVED|New Cards Found By DaxxScrapper|ꕥ Extrap [☭]|み RIMURU SCRAPE by|Approved) ✅', message.text):
            filtered_card_info = filter_cards(message.text)
            if not filtered_card_info:
                print("No valid card information found.")
                return

            for card_info in filtered_card_info:
                if cards_collection.find_one({"card_info": card_info}):
                    print("Card already exists in database, skipping.")
                    continue

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
                        "┃**#APPROVED 𝟓$ ✅**\n"
                        "┗━━━━━━━━━━━⊛\n\n"
                        f"**𝖢𝖠𝖱𝖣** ➠ <code>{card_info}</code>\n\n"
                        f"**𝖲𝖳𝖠𝖳𝖴𝖲** ➠ <b>**APPROVED**! ✅</b>\n\n"
                        f"**𝖡𝖨𝖭** ➠ <b>{brand}, {card_type}, {level}</b>\n\n"
                        f"**𝖡𝖠𝖭𝖪** ➠ <b>{bank}</b>\n\n"
                        f"**𝖢𝖮𝖴𝖭𝖳𝖱𝖸** ➠ <b>{country}, {country_flag}</b>\n\n"
                        "**𝖢𝖱𝖤𝖠𝖳𝖮𝖱** ➠ <b>๏─𝙂𝘽𝙋─๏</b>"
                    )

                    await client_instance.send_message(chat_id='@CHARGECCDROP', text=formatted_message)

                    # Save card info to MongoDB to prevent duplicate sending
                    cards_collection.insert_one({"card_info": card_info})
                    print("Card info sent and saved to database.")
    except Exception as e:
        print(f"An error occurred in approved function: {e}")

@app.on_message(filters.text)
async def astro(client_instance, message):
    if message.text:
        await approved(client_instance, message)

app.run()

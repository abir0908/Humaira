import os
import asyncio
import logging
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# =====================================================================
# ১. কনফিগারেশন সেকশন (আপনার অরিজিনাল ডাটা ফিক্সড)
# =====================================================================
BOT_TOKEN = "8733401667:AAFjIRl3BzmdQ2PYgCnXINpB2OIYalWAbVI"

# ২ জন এডমিনের টেলিগ্রাম ইউজার আইডি
ADMIN_IDS = [7755765124, 7683269800] 

# সাপোর্ট ও এডমিন লিংক
SUPPORT_ADMIN_1 = "https://t.me/the_king_na"
SUPPORT_ADMIN_2 = "https://t.me/mr_owner_2"

# থার্ড-পার্টি প্যানেলের আসল API কনফিগারেশন
SMS_PANEL_URL = "http://63.141.255.227/api/v1"
SMS_PANEL_API_KEY = "nxa_73511ddf0d1a3551648c0bf6354387c2cff2349b"
API_HEADERS = {"X-API-Key": SMS_PANEL_API_KEY}

# =====================================================================
# ২. ডাটাবেজ সেকশন (SQLite3)
# =====================================================================
DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backup_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE,
            service TEXT,
            country TEXT,
            status TEXT DEFAULT 'available'
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# =====================================================================
# ৩. API ও ওটিপি পোলিং সেকশন
# =====================================================================
async def fetch_api_number(service: str, country_code: str):
    """নির্দিষ্ট দেশ ও সার্ভিস অনুযায়ী এপিআই থেকে ১টি নাম্বার রিকোয়েস্ট করা"""
    url = f"{SMS_PANEL_URL}/numbers/get"
    payload = {
        "service": service.lower(),
        "country": country_code.lower()
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=API_HEADERS, json=payload, timeout=10) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    if "number" in data and "number_id" in data:
                        return {"phone": data["number"], "id": data["number_id"]}
        return None
    except Exception as e:
        print(f"API Error: {e}")
        return None

async def check_otp_polling(bot: Bot, user_id: int, number_id: str, phone_number: str):
    url = f"{SMS_PANEL_URL}/numbers/{number_id}/sms"
    for _ in range(60): 
        await asyncio.sleep(5)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=API_HEADERS) as response:
                    if response.status == 200:
                        sms_data = await response.json()
                        if sms_data.get("sms") and len(sms_data["sms"]) > 0:
                            otp_code = sms_data["sms"][0].get("otp")
                            if otp_code:
                                await bot.send_message(
                                    user_id, 
                                    f"📩 **নতুন ওটিপি এসেছে!**\n\n"
                                    f"📱 নাম্বার: `{phone_number}`\n"
                                    f"🔑 ওটিপি কোড: `{otp_code}`\n\n"
                                    f"ভেরিফিকেশন সম্পন্ন করুন।"
                                )
                                return
        except Exception as e:
            print(f"OTP Polling Error: {e}")
            break

# =====================================================================
# ৪. বটের হ্যান্ডলার ও ইউজার ইন্টারফেস সেকশন (হুবহু স্ক্রিনশট ডিজাইন)
# =====================================================================
router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()

def get_main_keyboard(user_id: int):
    # স্ক্রিনশট ১ অনুযায়ী নিচের বাটন লেআউট
    buttons = [[KeyboardButton(text="Get Number"), KeyboardButton(text="Traffic")]]
    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton(text="Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    add_user(message.from_user.id, message.from_user.username)
    # স্ক্রিনশট ১ অনুযায়ী স্বাগতম বার্তা
    await message.answer("⚡ ⇨ **M R Owner** ٭", reply_markup=get_main_keyboard(message.from_user.id))

@router.message(F.text == "Traffic")
async def cmd_traffic(message: Message):
    support_text = "⚡ **সহায়তার জন্য নিচে যোগাযোগ করুন:**"
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Admin 1", url=SUPPORT_ADMIN_1)],
        [InlineKeyboardButton(text="👨‍💻 Admin 2", url=SUPPORT_ADMIN_2)]
    ])
    await message.answer(support_text, reply_markup=inline_kb)

@router.message(F.text == "Get Number")
async def cmd_get_number(message: Message):
    # স্ক্রিনশট ১ অনুযায়ী ৩টি সার্ভিস বাটন
    services_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="WhatsApp", callback_query_data="srv_whatsapp"),
            InlineKeyboardButton(text="Facebook", callback_query_data="srv_facebook"),
            InlineKeyboardButton(text="Telegram", callback_query_data="srv_telegram")
        ]
    ])
    await message.answer("⚡ **Select Service**", reply_markup=services_kb)

@router.callback_query(F.data.startswith("srv_"))
async def process_service_selection(callback: CallbackQuery):
    service = callback.data.split("_")[1]
    
    # স্ক্রিনশট ২ অনুযায়ী দেশের তালিকা বাটন লেআউট এবং স্টক কাউন্ট
    country_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇨🇮 IvoryCoast", callback_query_data=f"geo_{service}_ci_IvoryCoast"),
            InlineKeyboardButton(text="🇳🇵 Nepal", callback_query_data=f"geo_{service}_np_Nepal")
        ],
        [
            InlineKeyboardButton(text="🇳🇪 Niger", callback_query_data=f"geo_{service}_ne_Niger"),
            InlineKeyboardButton(text="🇨🇺 Cuba", callback_query_data=f"geo_{service}_cu_Cuba")
        ],
        [
            InlineKeyboardButton(text="🔷 🇨🇲 Cameroon (2)", callback_query_data=f"geo_{service}_cm_Cameroon"),
            InlineKeyboardButton(text="🔷 🇲🇱 Mali (2)", callback_query_data=f"geo_{service}_ml_Mali")
        ],
        [
            InlineKeyboardButton(text="📦 Stock (353)", callback_query_data="ignore")
        ]
    ])
    await callback.message.edit_text("⚡ **Select**", reply_markup=country_kb)

@router.callback_query(F.data.startswith("geo_"))
async def process_country_selection(callback: CallbackQuery, bot: Bot):
    _, service, country_code, country_name = callback.data.split("_")
    await callback.answer(f"{country_name} থেকে নাম্বার খোঁজা হচ্ছে...")
    
    # এপিআই থেকে একটি সিঙ্গেল নাম্বার রিকোয়েস্ট করা
    item = await fetch_api_number(service, country_code)
    
    if not item:
        await callback.message.edit_text("❌ দুঃখিত! এই দেশের স্টক খালি অথবা এপিআই রেসপন্স করছে না।")
        return
        
    phone = item["phone"]
    n_id = item["id"]
    
    # স্ক্রিনশট ৩ অনুযায়ী কাস্টম হেডার ডিজাইন ও কপি বাটন লেআউট
    response_text = f"⏳ **{service.capitalize()}** · 🇳🇵 **{country_name}**\n\n_Copy & request OTP_"
    
    num_buttons = [
        [InlineKeyboardButton(text=f"🗐 {phone}", callback_query_data=f"copy_{phone}")],
        [InlineKeyboardButton(text="📩 OTP Group", url="https://t.me/your_otp_group")]
    ]
    
    num_kb = InlineKeyboardMarkup(inline_keyboard=num_buttons)
    await callback.message.edit_text(response_text, reply_markup=num_kb, parse_mode="Markdown")
    
    # ব্যাকগ্রাউন্ডে ওটিপি চেক লুপ চালু করা
    asyncio.create_task(check_otp_polling(bot, callback.from_user.id, n_id, phone))

@router.callback_query(F.data.startswith("copy_"))
async def handle_copy_click(callback: CallbackQuery):
    phone = callback.data.split("_")[1]
    await callback.answer(f"✅ {phone} কপি করা হয়েছে!", show_alert=False)

@router.callback_query(F.data == "ignore")
async def handle_ignore(callback: CallbackQuery):
    await callback.answer()

# =====================================================================
# ৫. এডমিন প্যানেল হ্যান্ডলার সেকশন
# =====================================================================
@router.message(F.text == "Admin Panel")
async def cmd_admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Broadcast Notice", callback_query_data="adm_broadcast")]
    ])
    await message.answer("⚙️ **Welcome to Admin Panel**", reply_markup=admin_kb)

@router.callback_query(F.data == "adm_broadcast")
async def admin_broadcast_request(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.message.edit_text("📝 **ইউজারদের জন্য আপনার ব্রডকাস্ট নোটিশটি লিখুন:**")

@router.message(AdminStates.waiting_for_broadcast_text, F.text)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS: return
    broadcast_msg = message.text
    all_users = get_all_users()
    
    await message.answer("📢 ব্রডকাস্ট পাঠানো শুরু হয়েছে...")
    success_count = 0
    for u_id in all_users:
        try:
            await bot.send_message(u_id, f"📢 **গুরুত্বপূর্ণ নোটিশ:**\n\n{broadcast_msg}")
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            continue
            
    await message.answer(f"✅ ব্রডকাস্ট সম্পন্ন! মোট {success_count} জন ইউজারের কাছে নোটিশ পৌছেছে।")
    await state.clear()

# =====================================================================
# ৬. মেইন এক্সিকিউশন সেকশন
# =====================================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    print("🤖 বট সফলভাবে চালু হয়েছে এবং লাইভ আছে...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🤖 বট বন্ধ করা হয়েছে।")

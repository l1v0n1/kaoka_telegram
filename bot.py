# -*- coding: utf-8 -*-


import logging
from aiogram import Bot, Dispatcher, executor, types, md
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import time
import os
from config import (
    API_TOKEN,
    admin,
    username,
    unban,
    admchat,
    vipsum,
    number,
    QIWI_SEC_TOKEN,
)
import database as db
import keyboard
import functions
from qiwipyapi import Wallet
from aiogram.utils.deep_linking import get_start_link
from aiogram.utils import markdown
import hashlib
from aiogram.types import InlineQuery
import random
import string
import asyncio
from functools import lru_cache
from aiogram.utils.exceptions import MessageNotModified, ChatNotFound, BotBlocked, TelegramAPIError


# Setup logging with a more specific format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Initialize QIWI wallet for payments
wallet_p2p = Wallet(number, p2p_sec_key=QIWI_SEC_TOKEN)

# Performance optimization: Use a cache dictionary with TTL for liketime and timeout
# to avoid many small database queries
liketime = {}
timeout = {}

# Global caches to avoid repeated file gets and message sends
FILE_CACHE = {}  # Store file paths to avoid repeated getFile requests
EMOJI_CACHE = {}  # Cache emoji results

# File cache TTL in seconds (1 hour)
FILE_CACHE_TTL = 3600

# Define FSM states
class reg(StatesGroup):
    name = State()
    photo = State()
    change_name = State()
    change_photo = State()
    change_city = State()
    mark = State()
    send_text = State()
    report = State()
    text = State()
    btext = State()
    ireport = State()
    deleteform = State()
    checkuser = State()
    msg = State()
    answer = State()
    vipid = State()
    remvip = State()
    buy = State()
    wait = State()
    city = State()

# Helper functions to reduce code duplication and increase performance
async def send_menu_message(chat_id, text):
    """Send a message with the menu keyboard"""
    try:
        await bot.send_message(chat_id, text, reply_markup=keyboard.menu)
    except (ChatNotFound, BotBlocked) as e:
        logger.warning(f"Failed to send message to {chat_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error sending message to {chat_id}: {str(e)}")

async def check_user_block(chat_id):
    """Check if user is blocked and send appropriate message"""
    block = await db.get_document(chat_id)
    return block is not None and block.get("block", 0) == 0

async def get_file_path(photo):
    """Get file path with caching to avoid repeated getFile requests"""
    if photo in FILE_CACHE:
        path, timestamp = FILE_CACHE[photo]
        if time.time() - timestamp < FILE_CACHE_TTL:
            return path
    
    try:
        file = await bot.get_file(photo)
        FILE_CACHE[photo] = (file.file_path, time.time())
        return file.file_path
    except Exception as e:
        logger.error(f"Error getting file path: {str(e)}")
        return None

@lru_cache(maxsize=20)  # Cache emoji results
async def get_emoji(num):
    """Cached version of emojies function to avoid repeated calculations"""
    if num in EMOJI_CACHE:
        return EMOJI_CACHE[num]
    
    result = await functions.emojies(num)
    EMOJI_CACHE[num] = result
    return result

async def safe_send_media(chat_id, media_type, file_id, caption, reply_markup=None, parse_mode=None):
    """Safe wrapper for media sending functions with error handling"""
    try:
        if media_type == "photo":
            return await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        elif media_type == "video":
            return await bot.send_video(chat_id, file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        elif media_type == "voice":
            return await bot.send_voice(chat_id, file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
    except (ChatNotFound, BotBlocked) as e:
        logger.warning(f"Failed to send media to {chat_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error sending media to {chat_id}: {str(e)}")
    
    return None

async def send_profile_media(chat_id, file_id, caption, reply_markup=None, parse_mode=None):
    """Send profile media based on file type"""
    try:
        file_path = await get_file_path(file_id)
        
        if not file_path:
            await bot.send_message(chat_id, "Ошибка при загрузке медиа профиля", reply_markup=reply_markup)
            return
            
        if "video" in file_path:
            await bot.send_video(chat_id, file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        elif "photo" in file_path:
            await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        elif "voice" in file_path:
            await bot.send_voice(chat_id, file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Error sending profile media: {str(e)}")
        await bot.send_message(chat_id, "Ошибка при отправке медиа", reply_markup=reply_markup)

# Error handler for improved stability
@dp.errors_handler()
async def errors_handler(update, exception):
    """
    Handle common bot errors gracefully
    """
    if isinstance(exception, MessageNotModified):
        # Message is not modified, no need to handle
        return True
    
    if isinstance(exception, ChatNotFound):
        logger.warning(f"Chat not found: {update}")
        return True
        
    if isinstance(exception, BotBlocked):
        # User blocked the bot
        logger.warning(f"Bot blocked by user: {update}")
        return True
        
    logger.error(f"Update: {update}\nError: {exception}")
    return True

@dp.message_handler(commands="start", chat_type=["private"])
async def start(message: types.Message):
    try:
        check = await db.check(message.chat.id)
        if check:
            if await check_user_block(message.chat.id):
                await db.update_mark(message.chat.id)
                await send_menu_message(message.chat.id, "Привет, вот меню")
            else:
                await message.answer(
                    f"Вы заблокированы в данном боте.\nРазблокировка: {unban} руб\nПисать: {username}"
                )
        else:
            await message.answer("Привет, как тебя зовут?", reply_markup=keyboard.reglinktg)
            await reg.name.set()
    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


@dp.message_handler(state=reg.name, chat_type=["private"])
async def name(message: types.Message, state: FSMContext):
    string = await functions.simbols_exists(message.text)
    if message.text == "Указать мой тг":
        if message.from_user.username is not None:
            await message.answer(
                'Приятно познакомиться, {}\n\nВведи название города в котором будешь оценивать.\nМожешь использовать кнопку "Не важно", если тебе не хочется указывать город.'.format(
                    message.from_user.mention
                ),
                reply_markup=keyboard.nevajno,
            )
            await state.update_data(name=message.from_user.mention)
            await reg.city.set()
        else:
            await message.answer(
                "У тебя нет @юзернейма, добавь его в профиле телеграм или напиши мне свое имя",
                reply_markup=keyboard.reglinktg,
            )
    else:
        if len(message.text) <= 15:
            if string == False:
                await message.answer(
                    'Приятно познакомиться, {}\n\nВведи название города в котором будешь оценивать.\nМожешь использовать кнопку "Не важно", если тебе не хочется указывать город.'.format(
                        message.text
                    ),
                    reply_markup=keyboard.nevajno,
                )
                await state.update_data(name=message.text)
                await reg.city.set()
            else:
                await message.answer(
                    "Ты используешь запрещенные символы, введи свое имя"
                )
        else:
            await message.answer("Придумай имя покороче, до 15 символов.")


@dp.message_handler(state=reg.city, chat_type=["private"], content_types=["text"])
async def locate(message: types.Message, state: FSMContext):
    string = await functions.city_exists(message.text)
    if string == False:
        text = message.text[:50]
        await state.update_data(city=text)
        await message.answer(
            "Теперь пришли мне свое фото или видео (до 15 секунд) или голосовое сообщение (до 60 секунд)",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        await reg.photo.set()
    else:
        await message.answer(
            "Ты используешь запрещенные символы, введи название города."
        )


@dp.message_handler(
    state=reg.photo, content_types=["photo", "video", "voice"], chat_type=["private"]
)
async def photo_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name")
    city = data.get("city")
    caption = (
        "📛Имя: {}\n💯Вас оценили на: 0.0/10\n📊Вас оценили 0 человек\n🌆Город: {}".format(
            name, city
        )
    )
    try:
        if message.video is not None:
            if int(message.video.duration) <= 15:
                await state.finish()
                video = message.video.file_id
                await db.insert(message.chat.id, name, video, city)
                await message.answer("Вы успешно зарегистрировались\nВот ваш профиль:")
                await bot.send_video(
                    message.chat.id, video, caption=caption, reply_markup=keyboard.menu
                )
            else:
                await message.answer("Видео должно быть до 15 секунд!")
        elif message.voice is not None:
            if int(message.voice.duration) <= 60:
                await state.finish()
                voice = message.voice.file_id
                await db.insert(message.chat.id, name, voice, city)
                await message.answer("Вы успешно зарегистрировались\nВот ваш профиль:")
                await bot.send_voice(
                    message.chat.id, voice, caption=caption, reply_markup=keyboard.menu
                )
            else:
                await message.answer("Голосовое сообщение должно быть до 60 секунд!")
        elif message.photo is not None:
            await state.finish()
            photo = message.photo[0].file_id
            await db.insert(message.chat.id, name, photo, city)
            await message.answer("Вы успешно зарегистрировались\nВот ваш профиль:")
            await bot.send_photo(
                message.chat.id, photo, caption=caption, reply_markup=keyboard.menu
            )
    except Exception as error:
        await bot.send_message(
            admin[0],
            "Юзер {} получил ошибку {} при регистрации".format(message.chat.id, error),
        )
        await state.finish()
        await message.answer(
            "Что-то пошло не так, введите /start\nЕсли ошибка не проходит, писать {}".format(
                username
            )
        )


@dp.message_handler(text="📛Профиль", chat_type=["private"])
async def profile(message: types.Message):
    user_id = message.chat.id
    
    try:
        block = await db.get_document(user_id)
        if not block or block.get("block", 0) != 0:
            await message.answer(
                f"Вы заблокированы в данном боте.\nРазблокировка: {unban} руб\nПисать: {username}"
            )
            return
        
        # Get profile data and prepare caption
        name = block.get("name", "")
        count = block.get("count", 0)
        photo = block.get("photo", "")
        active = block.get("active", 0)
        city = block.get("city", "")
        
        # Update mark in a non-blocking way
        likes = await db.update_mark(user_id)
        
        caption = f"📛Имя: {name}\n💯Вас оценили на: {likes}/10\n📊Вас оценили {count} человек(а)\n🔝Вас могут оценить {active} раз(а)\n🌆Город: {city}"
        
        # Send media with caption
        custom_keyboard = await keyboard.change(user_id)
        await send_profile_media(user_id, photo, caption, custom_keyboard)
            
    except Exception as e:
        logger.error(f"Error in profile handler for user {user_id}: {str(e)}")
        await message.answer("Что-то пошло не так, введите /start")


@dp.message_handler(text="Изменить имя", chat_type=["private"])
async def change_name(message: types.Message):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        await message.answer("Введите новое имя", reply_markup=keyboard.linktg)
        await reg.change_name.set()
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(state=reg.change_name, chat_type=["private"])
async def change_name_state(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        if message.text == "Отмена":
            await message.answer("Отмена!", reply_markup=keyboard.menu)
            await state.finish()
        elif message.text == "Указать мой тг":
            if message.from_user.username is not None:
                await state.finish()
                await db.change_field(
                    message.chat.id, "name", message.from_user.mention
                )
                await message.answer(
                    "Ваше новое имя: {}".format(message.from_user.mention),
                    reply_markup=keyboard.menu,
                )
            else:
                await message.answer(
                    "У тебя нет @юзернейма, добавь его в профиле телеграм или напиши мне свое имя",
                    reply_markup=keyboard.linktg,
                )
        else:
            string = await functions.simbols_exists(message.text)
            if len(message.text) <= 15:
                if string == False:
                    await state.finish()
                    await db.change_field(message.chat.id, "name", message.text)
                    await message.answer(
                        "Ваше новое имя: {}".format(message.text),
                        reply_markup=keyboard.menu,
                    )
                else:
                    await message.answer(
                        "Ты используешь запрещенные символы, введи свое имя"
                    )
            else:
                await message.answer("Придумай имя покороче, до 15 символов.")
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(text="Изменить медиа", chat_type=["private"])
async def change_photo_or_video_or_voice(message: types.Message):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        await message.answer(
            "Отправьте новое фото или видео (до 15 секунд) или голосовое сообщение (до 60 секунд)\nУчтите: При смене фото, видео или голосового сообщения, ваши оценки обнуляются\n\nДля отмены нажмите на соответсвующую кнопку",
            reply_markup=keyboard.cancel,
        )
        await reg.change_photo.set()
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(
    state=reg.change_photo, content_types=["photo", "text", "video", "voice"]
)
async def change_photovideo_state(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        if message.text == "Отмена":
            await message.answer("Отмена!", reply_markup=keyboard.menu)
            await state.finish()
        else:
            if message.text:
                await message.answer("Отправьте фото или видео (до 15 секунд)!")
            else:
                if message.video is not None:
                    if int(message.video.duration) <= 15:
                        await state.finish()
                        file = message.video.file_id
                        await db.change_field(message.chat.id, "mark", 0)
                        await db.change_field(message.chat.id, "photo", file)
                        await db.change_field(message.chat.id, "count", 0)
                        await db.change_field(message.chat.id, "by", [])
                        await db.change_field(message.chat.id, "answer", [])
                        await message.answer(
                            "Медиа в вашем профиле обновлено!",
                            reply_markup=keyboard.menu,
                        )
                    else:
                        await message.answer("Видео должно быть до 15 секунд!")
                elif message.voice is not None:
                    if int(message.voice.duration) <= 60:
                        await state.finish()
                        voice = message.voice.file_id
                        await db.change_field(message.chat.id, "mark", 0)
                        await db.change_field(message.chat.id, "photo", voice)
                        await db.change_field(message.chat.id, "count", 0)
                        await db.change_field(message.chat.id, "by", [])
                        await db.change_field(message.chat.id, "answer", [])
                        await message.answer(
                            "Медиа в вашем профиле обновлено!",
                            reply_markup=keyboard.menu,
                        )
                    else:
                        await message.answer(
                            "Голосовое сообщение должно быть до 60 секунд!"
                        )
                elif message.photo is not None:
                    await state.finish()
                    photo = message.photo[0].file_id
                    await db.change_field(message.chat.id, "mark", 0)
                    await db.change_field(message.chat.id, "photo", photo)
                    await db.change_field(message.chat.id, "count", 0)
                    await db.change_field(message.chat.id, "by", [])
                    await db.change_field(message.chat.id, "answer", [])
                    await message.answer(
                        "Медиа в вашем профиле обновлено!", reply_markup=keyboard.menu
                    )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(text="Изменить город", chat_type=["private"])
async def change_city(message: types.Message):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        await message.answer("Введите название города", reply_markup=keyboard.kbnevajno)
        await reg.change_city.set()
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(state=reg.change_city, chat_type=["private"])
async def change_name_state(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        if message.text == "Отмена":
            await message.answer("Отмена!", reply_markup=keyboard.menu)
            await state.finish()
        else:
            string = await functions.city_exists(message.text)
            if string == False:
                await state.finish()
                text = message.text[:50]
                await db.change_field(message.chat.id, "city", text)
                await message.answer(
                    "Город успешно обновлен!", reply_markup=keyboard.menu
                )
            else:
                await message.answer(
                    "Ты используешь запрещенные символы, введи название города."
                )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(text="Отключить анкету", chat_type=["private"])
async def choiceyesornot(message: types.Message):
    await message.answer(
        "Вы уверены что хотите отключить анкету? Вас больше никто не сможет оценивать.",
        reply_markup=keyboard.yesorno,
    )
    await reg.deleteform.set()


@dp.message_handler(state=reg.deleteform, chat_type=["private"])
async def delete(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        if message.text == "Нет":
            await message.answer("Отмена!", reply_markup=keyboard.menu)
            await state.finish()
        elif message.text == "Да":
            await state.finish()
            await db.change_field(message.chat.id, "active", 0)
            await message.answer(
                "Ваша анкета успешно отключена!\nЧтобы активировать её вновь, введите /start и оцените кого-нибудь.",
                reply_markup=types.ReplyKeyboardRemove(),
            )
        else:
            await message.answer(
                "Используйте клавиатуру!", reply_markup=keyboard.yesorno
            )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(
    text=["Главное меню", "❌Отмена", "Отмена", "Назад"], chat_type=["private"]
)
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        await message.answer("Меню", reply_markup=keyboard.menu)
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(text="🖤VIP", chat_type=["private"])
async def vip(message: types.Message):
    user = await db.get_document(message.chat.id)
    if user["vip"] == 1:
        await message.answer("Вы и так VIP")
    else:
        await message.answer(
            f'VIP-доступ дает вам некоторые возможности, которых нет у обычных пользователей\n- Вы можете ответить сообщением на оценку от пользователя и многое другое\n- Вам показывает больше оценивших, в разделе "Кто меня оценил"\nФункции в VIP-доступе пополняются.\n1 подписка - навсегда.\n\nДля покупки используйте клавиатуру ниже\nЦена VIP: {vipsum}₽',
            reply_markup=keyboard.buy,
        )
        await reg.buy.set()


@dp.message_handler(state=reg.buy, chat_type=["private"])
async def buy_vip(message: types.Message, state: FSMContext):
    if message.text == "Приобрести":
        link, bid = await functions.pay(wallet_p2p)
        if link and bid:
            await state.update_data({"bid": bid})
            await message.answer(
                "Для покупки VIP на 1 месяц - {} руб. После успешной оплаты жми 'Я оплатил'".format(vipsum),
                reply_markup=keyboard.iam,
            )
            await message.answer(link)
            await reg.wait.set()
        else:
            await message.answer("Произошла ошибка с платежной системой. Попробуйте позже.")
            await state.finish()
    else:
        await message.answer("Действие отменено", reply_markup=keyboard.menu)
        await state.finish()


@dp.message_handler(state=reg.wait, chat_type=["private"])
async def wait_success(message: types.Message, state: FSMContext):
    try:
        if message.text == "Я оплатил":
            data = await state.get_data()
            bid = data.get("bid")
            if not bid:
                await message.answer("Ошибка идентификации платежа. Попробуйте заново.", reply_markup=keyboard.menu)
                await state.finish()
                return
                
            # Use the optimized payment status checking function
            status = await functions.check_payment(wallet_p2p, bid)
                
            if status == "PAID" or status == "COMPLETED":
                # Payment successful
                await db.change_field(message.chat.id, "vip", 1)
                await message.answer(
                    "🔥 Поздравляю! Вы приобрели VIP на месяц\n\n⭐️ Теперь вам доступна функция ответа на комментарии!",
                    reply_markup=keyboard.menu,
                )
                # Log successful payment
                logger.info(f"User {message.chat.id} successfully purchased VIP")
                # Notify admins
                for adm in admin:
                    await bot.send_message(
                        adm, f"Пользователь {message.chat.id} купил вип!"
                    )
                await state.finish()
            elif status == "WAITING" or status == "PENDING":
                # Payment still pending
                await message.answer(
                    "⏳ Платеж в обработке. Пожалуйста, подождите или попробуйте еще раз через минуту.",
                    reply_markup=keyboard.iam,
                )
            else:
                # Payment failed or expired
                await message.answer(
                    "❌ Платеж не найден. Пожалуйста, проверьте, была ли произведена оплата.",
                    reply_markup=keyboard.buy,
                )
                await reg.buy.set()
        elif message.text == "Отмена":
            await message.answer("Действие отменено", reply_markup=keyboard.menu)
            await state.finish()
        else:
            await message.answer("Используйте клавиатуру!", reply_markup=keyboard.iam)
    except Exception as e:
        logger.error(f"Payment processing error: {str(e)}")
        await message.answer(
            "Произошла ошибка при проверке платежа. Пожалуйста, свяжитесь с администратором.",
            reply_markup=keyboard.menu
        )
        await state.finish()


@dp.message_handler(text="❤️Оценить", chat_type=["private"])
async def mark(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        try:
            city = block["city"]
            form = await db.get_random_form(message.chat.id, city)
            if form == False:
                linkencoded = await get_start_link(message.chat.id, encode=True)
                await message.answer(
                    "😢Пользователи для оценивания закончились\n\nПригласи друзей и получи больше оценок!\n\nПерешли друзьям или размести в своих соцсетях.\nВот твоя личная ссылка 👇\n{}".format(
                        linkencoded
                    ),
                    reply_markup=keyboard.menu,
                )
            else:
                chat_id = form[0]["chat_id"]
                print("{} оценивает {}".format(message.chat.id, chat_id))
                photo = form[0]["photo"]
                name = form[0]["name"]
                city = form[0]["city"]
                await state.update_data(chat_id=chat_id)
                file = await bot.get_file(photo)
                lnk = markdown.link('Ставь оценку от 1 до 10', "https://t.me/kaoka_channel")
                caption = '📛Имя: {}\n🌆Город: {}\n{}'.format(
                    name, city, lnk
                )
                if "video" in file.file_path:
                    await bot.send_video(
                        message.chat.id,
                        photo,
                        caption=caption,
                        reply_markup=keyboard.mark,
                        parse_mode="Markdown",
                    )
                elif "photo" in file.file_path:
                    await bot.send_photo(
                        message.chat.id,
                        photo,
                        caption=caption,
                        reply_markup=keyboard.mark,
                        parse_mode="Markdown",
                    )
                elif "voice" in file.file_path:
                    await bot.send_voice(
                        message.chat.id,
                        photo,
                        caption=caption,
                        reply_markup=keyboard.mark,
                        parse_mode="Markdown",
                    )
                await reg.mark.set()
        except Exception as error:
            print(error)
            await mark(message, state)
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(state=reg.mark, chat_type=["private"])
async def mark_photo(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        if message.text == "Главное меню":
            await message.answer("Возвращаемся назад", reply_markup=keyboard.menu)
            await state.finish()
        elif message.text == "💌Сообщение":
            await message.answer(
                "Введите сообщение для этого пользователя", reply_markup=keyboard.cancel
            )
            await reg.msg.set()
        elif message.text == "Пропустить":
            await mark(message, state)
        else:
            marks = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
            if message.text in marks:
                try:
                    if (
                        message.chat.id not in liketime
                        or time.time() >= liketime[message.chat.id]
                    ):
                        liketime[message.chat.id] = time.time() + 1
                        data = await state.get_data()
                        chat_id = data.get("chat_id")
                        comment = data.get("comment")
                        await state.finish()
                        fullbase = await db.get_document(chat_id)
                        count = fullbase["count"]
                        active = fullbase["active"]
                        liker = block["active"]
                        await db.change_field(message.chat.id, "active", liker + 1)
                        if active != 0:
                            await db.change_field(chat_id, "active", active - 1)
                        await db.change_field(chat_id, "count", count + 1)
                        await db.update_by(
                            chat_id, message.chat.id, int(message.text), comment
                        )
                        await db.update_mark(chat_id)
                        await mark(message, state)
                    elif (
                        message.chat.id in liketime
                        and time.time() <= liketime[message.chat.id]
                    ):
                        pass
                except Exception as error:
                    print(
                        "Юзер {} получил ошибку {} при оценивании {}\nДокумент: {}".format(
                            message.chat.id, error, chat_id, fullbase
                        )
                    )
                    await mark(message, state)
            elif message.text == "⚠️Жалоба":
                await message.answer(
                    "Укажите причину жалобы", reply_markup=keyboard.reportkb
                )
                await reg.report.set()
            else:
                await message.answer(
                    "Ставь оценку от 1 до 10!", reply_markup=keyboard.mark
                )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(state=reg.report, chat_type=["private"])
async def report_state(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        if message.text in ["🔞Материал для взрослых", "💰Реклама", "👾Другое"]:
            data = await state.get_data()
            chat_id = data.get("chat_id")
            fullbase = await db.get_document(chat_id)
            photo = fullbase["photo"]
            name = fullbase["name"]
            city = fullbase["city"]
            await message.answer("Жалоба успешно отправлена администрации.")
            file = await bot.get_file(photo)
            to = markdown.link(str(chat_id), f"tg://user?id={str(chat_id)}")
            fromm = markdown.link(str(message.chat.id), f"tg://user?id={str(message.chat.id)}")
            if "video" in file.file_path:
                await bot.send_video(
                    admchat,
                    photo,
                    caption="Поступила жалоба на пользователя: {}\nЖалуется: {}\nИмя: {}\nГород: {}\nПричина жалобы: {}".format(
                        to, fromm, name, city, message.text
                    ),
                    reply_markup=await keyboard.admin_ban(chat_id),
                    parse_mode="Markdown",
                )
            elif "photo" in file.file_path:
                await bot.send_photo(
                    admchat,
                    photo,
                    caption="Поступила жалоба на пользователя: {}\nЖалуется: {}\nИмя: {}\nГород: {}\nПричина жалобы: {}".format(
                        to, fromm, name, city, message.text
                    ),
                    reply_markup=await keyboard.admin_ban(chat_id),
                    parse_mode="Markdown",
                )
            elif "voice" in file.file_path:
                await bot.send_voice(
                    admchat,
                    photo,
                    caption="Поступила жалоба на пользователя: {}\nЖалуется: {}\nИмя: {}\nГород: {}\nПричина жалобы: {}".format(
                        to, fromm, name, city, message.text
                    ),
                    reply_markup=await keyboard.admin_ban(chat_id),
                    parse_mode="Markdown",
                )
            await state.finish()
            await mark(message, state)
        elif message.text == "❌Отмена":
            await state.finish()
            await mark(message, state)
        else:
            await message.answer(
                "Используй клавиатуру!", reply_markup=keyboard.reportkb
            )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(state=reg.msg, chat_type=["private"])
async def comment_state(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await state.finish()
        await mark(message, state)
    else:
        if len(message.text) <= 300:
            await state.update_data(comment=message.text)
            await message.answer(
                "Теперь поставьте оценку пользователю", reply_markup=keyboard.mark
            )
            await reg.mark.set()
        else:
            await message.answer("Введите сообщение до 300 символов!")


@dp.message_handler(text="💕Кто меня оценил?", chat_type=["private"])
async def who_liked(message: types.Message, state: FSMContext):
    user_id = message.chat.id
    
    try:
        # Check if user is blocked
        block = await db.get_document(user_id)
        if not block or block.get("block", 0) != 0:
            await message.answer(
                f"Вы заблокированы в данном боте.\nРазблокировка: {unban} руб\nПисать: {username}"
            )
            return
            
        # Check rate limiting
        if user_id in timeout and time.time() <= timeout[user_id]:
            return  # Silent return on rate limit
            
        # Set rate limit
        timeout[user_id] = time.time() + 5
        
        # Update ratings
        await db.update_mark(user_id)
        
        # Get likers
        liked = await db.get_likers(user_id)
        if not liked or not liked[0].get("by"):
            await message.answer("Тебя пока еще никто не оценивал.")
            return
            
        # Determine how many items to show based on VIP status
        xs = list(reversed(liked[0].get("by", [])))
        is_vip = block.get("vip", 0) == 1
        items = xs[:30] if is_vip else xs[:20]
        sender = list(reversed(items))
        
        # Process likers in batches to avoid telegram rate limits
        BATCH_SIZE = 5
        for i in range(0, len(sender), BATCH_SIZE):
            batch = sender[i:i+BATCH_SIZE]
            tasks = []
            
            for m in batch:
                tasks.append(process_liker(m, user_id))
                
            # Process batch concurrently
            await asyncio.gather(*tasks)
            
            # Small delay between batches to avoid rate limits
            if i + BATCH_SIZE < len(sender):
                await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in who_liked handler for user {user_id}: {str(e)}")
        await message.answer("Что-то пошло не так, введите /start")

async def process_liker(liker_data, recipient_id):
    """Process a single liker and send their profile to the recipient"""
    try:
        liker_id = liker_data.get("id")
        if not liker_id:
            return
            
        user = await db.get_profile(liker_id)
        if not user:
            return
            
        name = user.get("name", "")
        photo = user.get("photo", "")
        city = user.get("city", "")
        mark = liker_data.get("mark", 0)
        
        # Process comment if exists
        comment = liker_data.get("comment")
        msg = f"💌Сообщение для вас: {comment}" if comment else ""
        
        # Create caption
        caption = f"📛Имя оценщика: {name}\n💯Оценил(а) вас на {mark}\n🌆Город: {city}\n{msg}"
        
        # Get file type and send appropriate media
        file_path = await get_file_path(photo)
        if not file_path:
            return
            
        reply_markup = await keyboard.report_inline(liker_id, recipient_id)
        
        if "video" in file_path:
            await bot.send_video(recipient_id, photo, caption=caption, reply_markup=reply_markup)
        elif "photo" in file_path:
            await bot.send_photo(recipient_id, photo, caption=caption, reply_markup=reply_markup)
        elif "voice" in file_path:
            await bot.send_voice(recipient_id, photo, caption=caption, reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"Error processing liker {liker_data.get('id')}: {str(e)}")


@dp.message_handler(text="🔝Топ", chat_type=["private"])
async def top(message: types.Message):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        await message.answer(
            "Выберите, какой топ хотите просмотреть", reply_markup=keyboard.topbutton
        )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.callback_query_handler(text="marks")
async def tophandler(call):
    try:
        dbcount = await db.sort_collection_by_mark()
        if not dbcount:  # Check if the result is empty
            await call.message.edit_text("Нет анкет для отображения в топе.", reply_markup=keyboard.topbutton)
            return
            
        # Edit message first to show we're working on it
        await call.message.edit_text(
            "Топ-10 профилей по оценкам.\nВыберите участника:", reply_markup=keyboard.tenbutton
        )
        
        # Prepare all messages in a single batch
        messages = []
        for i in range(min(10, len(dbcount))):
            user = dbcount[i]
            messages.append(
                f"{i+1}) {user.get('name', '')} - {user.get('mark', 0)}/10 ({user.get('count', 0)} оценок)"
            )
        
        # Send messages in a batch to reduce number of API calls
        if messages:
            text = "\n".join(messages)
            await bot.send_message(call.message.chat.id, text)
            
    except MessageNotModified:
        # Ignore this common error
        pass
    except Exception as e:
        logger.error(f"Error in tophandler: {str(e)}")
        try:
            await call.message.edit_text("Произошла ошибка при загрузке топа.", reply_markup=keyboard.topbutton)
        except:
            pass


@dp.callback_query_handler(lambda call: call.data.startswith("marksbutton"))
async def marksbuttons(call):
    try:
        data = call.data.split("_")[1]
        dbcount = await db.sort_collection_by_mark()
        
        if not dbcount or int(data) >= len(dbcount):
            await call.answer("Нет доступных анкет с таким номером")
            return
            
        item = dbcount[int(data)]
        name = item["name"]
        photo = item["photo"]
        count = item["count"]
        likes = await db.update_mark(item["chat_id"])
        file = await bot.get_file(photo)
        
        if "video" in file.file_path:
            media = types.InputMedia(
                type="video",
                media=photo,
                caption="{} Место\n📛Имя: {}\n💯Оценили на: {}/10\n📊Всего оценили {} человек(а)".format(
                    await get_emoji(int(data) + 1), name, likes, count
                ),
            )
        elif "photo" in file.file_path:
            media = types.InputMedia(
                type="photo",
                media=photo,
                caption="{} Место\n📛Имя: {}\n💯Оценили на: {}/10\n📊Всего оценили {} человек(а)".format(
                    await get_emoji(int(data) + 1), name, likes, count
                ),
            )
        elif "voice" in file.file_path:
            media = types.InputMedia(
                type="audio",
                media=photo,
                caption="{} Место\n📛Имя: {}\n💯Оценили на: {}/10\n📊Всего оценили {} человек(а)".format(
                    await get_emoji(int(data) + 1), name, likes, count
                ),
            )
        try:
            await call.message.edit_media(media, keyboard.tenbutton)
        except Exception:
            await call.answer("Вы и так уже на {} кнопке".format(int(data) + 1))
    except Exception as e:
        logger.error(f"Error in marksbuttons: {str(e)}")
        await call.answer("Произошла ошибка при загрузке анкеты")


@dp.callback_query_handler(text="counts")
async def topcount(call):
    try:
        dbcount = await db.sort_collection_by_count()
        if not dbcount:  # Check if the result is empty
            await call.message.edit_text("Нет анкет для отображения в топе.", reply_markup=keyboard.topbutton)
            return
            
        item = dbcount[0]
        await call.message.edit_text(
            "Топ-10 профилей по количеству оценок.\nВыберите участника:", reply_markup=keyboard.countbutton
        )
        for i in range(10):
            try:
                if len(dbcount) > i:
                    user = dbcount[i]
                    await bot.send_message(
                        call.message.chat.id,
                        f"{i+1}) {user['name']} - {user['mark']}/10 ({user['count']} оценок)",
                    )
            except IndexError:
                # Break the loop if there aren't enough users
                break
    except Exception as e:
        logger.error(f"Error in topcount: {str(e)}")
        await call.message.edit_text("Произошла ошибка при загрузке топа.", reply_markup=keyboard.topbutton)


@dp.callback_query_handler(lambda call: call.data.startswith("answer"))
async def answervip(call, state: FSMContext):
    data = call.data.split("_")[1]
    await state.update_data(answerto=data)
    await call.message.edit_caption(
        call.message.caption, reply_markup=await keyboard.answer_report(data)
    )
    await call.message.answer(
        "Отправьте текстовое или голосовое сообщение для этого пользователя",
        reply_markup=keyboard.cancel,
    )
    await reg.answer.set()


@dp.message_handler(
    state=reg.answer, chat_type=["private"], content_types=["text", "voice"]
)
async def answer_state(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Отмена! Возвращаю в главное меню.", reply_markup=keyboard.menu
        )
        await state.finish()
    else:
        data = await state.get_data()
        chat_id = data.get("answerto")
        try:
            if message.voice is not None:
                await message.answer(
                    "Ваш ответ успешно отправлен пользователю.",
                    reply_markup=keyboard.menu,
                )
                fullbase = await db.get_document(message.chat.id)
                photo = fullbase["photo"]
                name = fullbase["name"]
                file = await bot.get_file(photo)
                caption = "📛Пользователь <b>{}</b> ответил на вашу оценку".format(name)
                await bot.send_voice(
                    chat_id,
                    message.voice.file_id,
                    caption=caption,
                    reply_markup=await keyboard.answer_report(message.chat.id),
                    parse_mode="HTML",
                )
                await db.update_answer(int(chat_id), message.chat.id)
                await state.finish()
            elif message.text is not None:
                if len(message.text) <= 300:
                    fullbase = await db.get_document(message.chat.id)
                    photo = fullbase["photo"]
                    name = fullbase["name"]
                    file = await bot.get_file(photo)
                    caption = "📛Пользователь <b>{}</b> ответил на вашу оценку\n💌Сообщение для вас: {}".format(
                        name, message.text
                    )
                    if "video" in file.file_path:
                        await bot.send_video(
                            chat_id,
                            photo,
                            caption=caption,
                            reply_markup=await keyboard.answer_report(message.chat.id),
                            parse_mode="HTML",
                        )
                    elif "photo" in file.file_path:
                        await bot.send_photo(
                            chat_id,
                            photo,
                            caption=caption,
                            reply_markup=await keyboard.answer_report(message.chat.id),
                            parse_mode="HTML",
                        )
                    elif "voice" in file.file_path:
                        await bot.send_voice(
                            chat_id,
                            photo,
                            caption=caption,
                            reply_markup=await keyboard.answer_report(message.chat.id),
                            parse_mode="HTML",
                        )
                    await db.update_answer(int(chat_id), message.chat.id)
                    await message.answer(
                        "Ваш ответ успешно отправлен пользователю.",
                        reply_markup=keyboard.menu,
                    )
                    await state.finish()
                else:
                    await message.answer("Введите сообщение до 300 символов!")
        except Exception as error:
            await message.answer(
                "Не удалось отправить сообщение пользователю",
                reply_markup=keyboard.menu,
            )
            await state.finish()


@dp.message_handler(text="ℹ️Информация", chat_type=["private"])
async def information(message: types.Message):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        await message.answer(
            "🙋Привет! Это бот, в котором ты сможешь оценивать людей, а так же получать оценки от других\n🗯По всем вопросам и предложениям к {}".format(
                username
            ),
            reply_markup=keyboard.links,
        )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.inline_handler()
async def inline_echo(inline_query: InlineQuery):
    if inline_query.query == "":
        chat_id = inline_query.from_user.id
        check = await db.check(chat_id)
        if check:
            fullbase = await db.get_document(chat_id)
            if fullbase["block"] == 0:
                name = fullbase["name"]
                count = fullbase["count"]
                photo = fullbase["photo"]
                likes = await db.update_mark(chat_id)
                active = fullbase["active"]
                city = fullbase["city"]
                caption = "📛Имя: {}\n💯Вас оценили на: {}/10\n📊Вас оценили {} человек(а)\n🔝Вас могут оценить {} раз(а)\n🌆Город: {}".format(
                    name, likes, count, active, city
                )
                file = await bot.get_file(photo)
                randomSource = string.ascii_letters + string.digits
                password = ""
                n = random.randint(4, 20)
                for j in range(n):
                    password += random.choice(randomSource)
                result_id: str = hashlib.md5(password.encode()).hexdigest()
                if "video" in file.file_path:
                    item = types.InlineQueryResultCachedVideo(
                        id=result_id,
                        video_file_id=photo,
                        title=f"Мой профиль",
                        caption=caption,
                        description="Ваш профиль в @kaokabot",
                    )
                    await inline_query.answer(
                        results=[item],
                        is_personal=True,
                        switch_pm_text="Каока Бот - оценка внешности",
                        switch_pm_parameter="kaokabot",
                    )
                elif "photo" in file.file_path:
                    item = types.InlineQueryResultCachedPhoto(
                        id=result_id,
                        photo_file_id=photo,
                        title=f"Мой профиль",
                        caption=caption,
                        description="Ваш профиль в @kaokabot",
                    )
                    await inline_query.answer(
                        results=[item],
                        is_personal=True,
                        switch_pm_text="Каока Бот - оценка внешности",
                        switch_pm_parameter="kaokabot",
                    )
                elif "voice" in file.file_path:
                    item = types.InlineQueryResultCachedVoice(
                        id=result_id,
                        voice_file_id=photo,
                        title=f"Мой профиль",
                        caption=caption,
                    )
                    await inline_query.answer(
                        results=[item],
                        is_personal=True,
                        switch_pm_text="Каока Бот - оценка внешности",
                        switch_pm_parameter="kaokabot",
                    )
            else:
                await inline_query.answer(
                    [],
                    is_personal=True,
                    switch_pm_text="Вы заблокированы в @kaokabot",
                    switch_pm_parameter="banned",
                )
        else:
            await inline_query.answer(
                [],
                is_personal=True,
                switch_pm_text="Вы не зарегистрированы в @kaokabot",
                switch_pm_parameter="notregistered",
            )
    else:
        users = await db.get_users_by_name(inline_query.query.lower())
        items = []
        for i in users:
            fullbase = await db.get_document(i["chat_id"])
            if fullbase["block"] == 0:
                name = fullbase["name"]
                count = fullbase["count"]
                photo = fullbase["photo"]
                likes = await db.update_mark(i["chat_id"])
                active = fullbase["active"]
                city = fullbase["city"]
                caption = "📛Имя: {}\n💯Оценили на: {}/10\n📊Всего оценили {} человек(а)\n🌆Город: {}".format(
                    name, likes, count, city
                )
                file = await bot.get_file(photo)
                randomSource = string.ascii_letters + string.digits
                password = ""
                n = random.randint(4, 20)
                for j in range(n):
                    password += random.choice(randomSource)
                rid: str = hashlib.md5(password.encode()).hexdigest()
                if "video" in file.file_path:
                    item = types.InlineQueryResultCachedVideo(
                        id=rid,
                        video_file_id=photo,
                        title="Профиль",
                        caption=caption,
                        description="{} в @kaokabot".format(name),
                    )
                    items.append(item)
                elif "photo" in file.file_path:
                    item = types.InlineQueryResultCachedPhoto(
                        id=rid,
                        photo_file_id=photo,
                        title="Профиль",
                        caption=caption,
                        description="{} в @kaokabot".format(name),
                    )
                    items.append(item)
                elif "voice" in file.file_path:
                    item = types.InlineQueryResultCachedVoice(
                        id=rid, voice_file_id=photo, title="Профиль", caption=caption
                    )
                    items.append(item)
        if items == []:
            await inline_query.answer(
                results=[],
                is_personal=True,
                switch_pm_text="Я никого не нашел :(",
                switch_pm_parameter="kaokabot",
            )
        else:
            try:
                await inline_query.answer(
                    results=items,
                    is_personal=True,
                    switch_pm_text="Каока Бот - оценка внешности",
                    switch_pm_parameter="kaokabot",
                )
            except:
                pass


@dp.message_handler(commands="admin", chat_type=["private"])
async def admin_panel(message: types.Message):
    if int(message.chat.id) in admin:
        await message.answer("Админ-панель\n/giveactive id value - выдать актив", reply_markup=keyboard.apanel)


@dp.message_handler(commands='giveactive', chat_type=['private'])
async def giveactive(message: types.Message):
    args = message.get_args().split(" ")
    id, value = args[0], args[1]
    await db.change_field(int(id), "active", int(value))
    await message.answer(
        "Пользователю {} успешно установлено {} актива".format(id, value)
    )


@dp.callback_query_handler(lambda call: call.data.startswith("admin"))
async def adminpanel(call, state: FSMContext):
    if "rass" in call.data:
        if int(call.message.chat.id) in admin:
            await call.message.answer(
                "Введите текст для рассылки.\nИспользуйте {имя}\r, чтобы в рассылке упоминалось имя юзера\n\nДля отмены нажмите кнопку ниже 👇",
                reply_markup=keyboard.cancel,
            )
            await reg.send_text.set()
    elif "stats" in call.data:
        if int(call.message.chat.id) in admin:
            count = await db.sender()
            sum = await db.check_counts()
            await call.answer(
                "Всего юзеров: {}\nВсего оценок: {}".format(len(count), sum),
                show_alert=True,
            )
    elif "skip" in call.data:
        await call.answer("Пропущено")
        await call.message.edit_caption(
            "{}\nЮзер пропущен".format(call.message.md_text), parse_mode="MarkdownV2"
        )
    elif "ban" in call.data:
        data = call.data.split("admin_ban_")[1]
        await db.change_field(int(data), "block", 1)
        await call.message.edit_caption(
            "{}\nЮзер забанен".format(call.message.md_text), parse_mode="MarkdownV2"
        )
        await call.answer("Юзер успешно забанен")
    elif "un" in call.data:
        if int(call.message.chat.id) in admin:
            await call.message.answer(
                "Введите id пользователя для разбана\n\nДля отмены нажмите кнопку ниже 👇",
                reply_markup=keyboard.cancel,
            )
            await reg.text.set()
    elif "id" in call.data:
        if int(call.message.chat.id) in admin:
            await call.message.answer(
                "Введите id пользователя для бана\n\nДля отмены нажмите кнопку ниже 👇",
                reply_markup=keyboard.cancel,
            )
            await reg.btext.set()
    elif "report" in call.data:
        if "💌Сообщение для вас:" in call.message.caption:
            comment = call.message.caption.split("💌Сообщение для вас:")[1]
        else:
            comment = ""
        id = call.data.split("admin_report_")[1]
        await state.update_data(reportid=int(id))
        await state.update_data(comment=comment)
        await state.update_data(reporter=call.message.chat.id)
        await call.message.edit_caption(call.message.caption)
        await call.message.answer(
            "Укажите причину жалобы", reply_markup=keyboard.reportkb
        )
        await reg.ireport.set()
    elif "check" in call.data:
        if int(call.message.chat.id) in admin:
            await call.message.answer(
                "Введите telegram id пользователя (циферки)",
                reply_markup=keyboard.cancel,
            )
            await reg.checkuser.set()
    elif call.data == "admin_add_vip":
        if int(call.message.chat.id) in admin:
            await call.message.answer(
                "Введите telegram id пользователя (циферки) для выдачи VIP доступа",
                reply_markup=keyboard.cancel,
            )
            await reg.vipid.set()
    elif call.data == "admin_rem_vip":
        if int(call.message.chat.id) in admin:
            await call.message.answer(
                "Введите telegram id пользователя (циферки) у которого нужно забрать VIP доступ",
                reply_markup=keyboard.cancel,
            )
            await reg.remvip.set()


@dp.message_handler(state=reg.vipid, chat_type=["private"])
async def addvip(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Отмена! Возвращаю в главное меню.", reply_markup=keyboard.menu
        )
        await state.finish()
    else:
        if message.text.isdigit():
            chat = int(message.text)
            check = await db.check(chat)
            if check is None:
                await message.answer("Такого юзера нет")
            else:
                await db.change_field(chat, "vip", 1)
                await message.answer(
                    "Пользователю {} выдан VIP-доступ".format(message.text),
                    reply_markup=keyboard.menu,
                )
                await state.finish()


@dp.message_handler(state=reg.remvip, chat_type=["private"])
async def delvip(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Отмена! Возвращаю в главное меню.", reply_markup=keyboard.menu
        )
        await state.finish()
    else:
        if message.text.isdigit():
            chat = int(message.text)
            check = await db.check(chat)
            if check is None:
                await message.answer("Такого юзера нет")
            else:
                await db.change_field(chat, "vip", 0)
                await message.answer(
                    "У пользователю {} отобран VIP-доступ".format(message.text),
                    reply_markup=keyboard.menu,
                )
                await state.finish()


@dp.message_handler(state=reg.checkuser, chat_type=["private"])
async def checking(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Отмена! Возвращаю в главное меню.", reply_markup=keyboard.menu
        )
        await state.finish()
    else:
        if message.text.isdigit():
            await state.finish()
            user = await db.get_document(int(message.text))
            name = user["name"]
            photo = user["photo"]
            count = user["count"]
            file = await bot.get_file(photo)
            idname = markdown.link(str(name), f"tg://user?id={str(message.text)}")
            if "video" in file.file_path:
                await bot.send_video(
                    message.chat.id,
                    photo,
                    caption="Юзер ID: {}\nИмя: {}\nВсего оценили: {}".format(
                        message.text, idname, count
                    ),
                    reply_markup=keyboard.menu,
                    parse_mode="Markdown",
                )
            elif "photo" in file.file_path:
                await bot.send_photo(
                    message.chat.id,
                    photo,
                    caption="Юзер ID: {}\nИмя: {}\nВсего оценили: {}".format(
                        message.text, idname, count
                    ),
                    reply_markup=keyboard.menu,
                    parse_mode="Markdown",
                )
            elif "voice" in file.file_path:
                await bot.send_voice(
                    message.chat.id,
                    photo,
                    caption="Юзер ID: {}\nИмя: {}\nВсего оценили: {}".format(
                        message.text, idname, count
                    ),
                    reply_markup=keyboard.menu,
                    parse_mode="Markdown",
                )
        else:
            await message.answer("Введите telegram ID!!!")


@dp.message_handler(state=reg.ireport, chat_type=["private"])
async def report_state_inline(message: types.Message, state: FSMContext):
    block = await db.get_document(message.chat.id)
    if block["block"] == 0:
        if message.text in ["🔞Материал для взрослых", "💰Реклама", "👾Другое"]:
            data = await state.get_data()
            chat_id = data.get("reportid")
            comment = data.get("comment")
            reporter = data.get("reporter")
            fullbase = await db.get_document(chat_id)
            photo = fullbase["photo"]
            name = fullbase["name"]
            city = fullbase["city"]
            await message.answer(
                "Жалоба успешно отправлена администрации.", reply_markup=keyboard.menu
            )
            to = markdown.link(str(chat_id), f"tg://user?id={str(chat_id)}")
            fromm = markdown.link(str(reporter), f"tg://user?id={str(reporter)}")
            file = await bot.get_file(photo)
            caption = f'Поступила жалоба на пользователя: {to}\nЖалуется: {fromm}\nИмя: {name}\nКомментарий: {md.quote_html(f"{comment}")}\nГород: {city}\nПричина жалобы: {message.text}'
            if "video" in file.file_path:
                await bot.send_video(
                    admchat,
                    photo,
                    caption=caption,
                    reply_markup=await keyboard.admin_ban(chat_id),
                    parse_mode="Markdown",
                )
            elif "photo" in file.file_path:
                await bot.send_photo(
                    admchat,
                    photo,
                    caption=caption,
                    reply_markup=await keyboard.admin_ban(chat_id),
                    parse_mode="Markdown",
                )
            elif "voice" in file.file_path:
                await bot.send_voice(
                    admchat,
                    photo,
                    caption=caption,
                    reply_markup=await keyboard.admin_ban(chat_id),
                    parse_mode="Markdown",
                )
            await state.finish()
        elif message.text == "❌Отмена":
            await state.finish()
            await message.answer("Отмена!", reply_markup=keyboard.menu)
        else:
            await message.answer(
                "Используй клавиатуру!", reply_markup=keyboard.reportkb
            )
    else:
        await message.answer(
            "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                unban, username
            )
        )


@dp.message_handler(state=reg.send_text, chat_type=["private"])
async def process_name(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Отмена! Возвращаю в главное меню.", reply_markup=keyboard.menu
        )
        await state.finish()
    else:
        info = await db.sender()
        await message.answer("Начинаю рассылку...", reply_markup=keyboard.menu)
        await state.finish()
        x = 0
        for i in range(len(info)):
            try:
                doc = await db.get_document(info[i])
                if r"{имя}" in message.text:
                    text = message.text.replace(r"{имя}", doc["name"])
                else:
                    text = message.text
                await bot.send_message(
                    info[i], str(text), reply_markup=keyboard.senderkb
                )
                x += 1
            except:
                pass
        await message.answer("Рассылка завершена.\nДоставлено сообщений: {}".format(x))


@dp.message_handler(state=reg.text, chat_type=["private"])
async def process_unban(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Отмена! Возвращаю в главное меню.", reply_markup=keyboard.menu
        )
        await state.finish()
    else:
        chat = int(message.text)
        await state.finish()
        await db.change_field(chat, "block", 0)
        await message.answer(
            "Пользователь {} успешно разбанен".format(message.text),
            reply_markup=keyboard.menu,
        )


@dp.message_handler(state=reg.btext, chat_type=["private"])
async def process_unban(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Отмена! Возвращаю в главное меню.", reply_markup=keyboard.menu
        )
        await state.finish()
    else:
        chat = int(message.text)
        await state.finish()
        await db.change_field(chat, "block", 1)
        await message.answer(
            "Пользователь {} успешно забанен".format(message.text),
            reply_markup=keyboard.menu,
        )


@dp.message_handler(chat_type=["private"])
async def all_messages(message: types.Message):
    check = await db.check(message.chat.id)
    if check:
        block = await db.get_document(message.chat.id)
        if block["block"] == 0:
            if message.text in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
                pass
            else:
                await db.update_mark(message.chat.id)
                await message.answer("Привет, вот меню", reply_markup=keyboard.menu)
        else:
            await message.answer(
                "Вы заблокированы в данном боте.\nРазблокировка: {} руб\nПисать: {}".format(
                    unban, username
                )
            )
    else:
        await message.answer("Привет, как тебя зовут?", reply_markup=keyboard.reglinktg)
        await reg.name.set()


@dp.callback_query_handler(lambda call: call.data.startswith("countbutton"))
async def countbuttons(call):
    try:
        data = call.data.split("_")[1]
        dbcount = await db.sort_collection_by_count()
        
        if not dbcount or int(data) >= len(dbcount):
            await call.answer("Нет доступных анкет с таким номером")
            return
            
        item = dbcount[int(data)]
        name = item["name"]
        photo = item["photo"]
        count = item["count"]
        likes = await db.update_mark(item["chat_id"])
        file = await bot.get_file(photo)
        
        if "video" in file.file_path:
            media = types.InputMedia(
                type="video",
                media=photo,
                caption="{} Место\n📛Имя: {}\n💯Оценили на: {}/10\n📊Всего оценили {} человек(а)".format(
                    await get_emoji(int(data) + 1), name, likes, count
                ),
            )
        elif "photo" in file.file_path:
            media = types.InputMedia(
                type="photo",
                media=photo,
                caption="{} Место\n📛Имя: {}\n💯Оценили на: {}/10\n📊Всего оценили {} человек(а)".format(
                    await get_emoji(int(data) + 1), name, likes, count
                ),
            )
        elif "voice" in file.file_path:
            media = types.InputMedia(
                type="audio",
                media=photo,
                caption="{} Место\n📛Имя: {}\n💯Оценили на: {}/10\n📊Всего оценили {} человек(а)".format(
                    await get_emoji(int(data) + 1), name, likes, count
                ),
            )
        try:
            await call.message.edit_media(media, keyboard.countbutton)
        except Exception:
            await call.answer("Вы и так уже на {} кнопке".format(int(data) + 1))
    except Exception as e:
        logger.error(f"Error in countbuttons: {str(e)}")
        await call.answer("Произошла ошибка при загрузке анкеты")


if __name__ == "__main__":
    # Initialize database before starting the bot
    db.setup_db()
    
    # Start the bot with skip_updates=True to avoid answering old messages on restart
    # Also set a reasonable value for updates worker count and pool size
    executor.start_polling(
        dp, 
        skip_updates=True,
        timeout=60,  # Higher timeout for long operations
        relax=0.1,   # Relax period between updates polling
        fast=True,   # Process updates in parallel
    )

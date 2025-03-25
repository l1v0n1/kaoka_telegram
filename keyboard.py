from aiogram import types
import database as db
from config import admin


menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
menu.add(
    types.KeyboardButton('📛Профиль'),
    types.KeyboardButton('❤️Оценить'),
    types.KeyboardButton('💕Кто меня оценил?'),
    types.KeyboardButton('🔝Топ'),
    types.KeyboardButton('ℹ️Информация')
)


async def change(chat_id):
    user = await db.get_document(chat_id)
    change = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    change.add(
        types.KeyboardButton('Изменить имя'),
        types.KeyboardButton('Изменить медиа'),
        types.KeyboardButton('Изменить город'),
        types.KeyboardButton('Отключить анкету'),
        types.KeyboardButton('Назад')
    )
    if user['vip'] != 1:
        change.add(types.KeyboardButton('🖤VIP'))
    return change


linktg = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
linktg.add(types.KeyboardButton('Указать мой тг'), types.KeyboardButton('Отмена'))


reglinktg = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
reglinktg.add(types.KeyboardButton('Указать мой тг')) 


buy = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
buy.add(
    types.KeyboardButton('Приобрести'),
    types.KeyboardButton('Отмена')
)


iam = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
iam.add(
    types.KeyboardButton('Я оплатил'),
    types.KeyboardButton('Отмена')
)


cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel.add(types.KeyboardButton('Отмена'))


mark = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
mark.add(
    types.KeyboardButton('1'),
    types.KeyboardButton('2'),
    types.KeyboardButton('3'),
    types.KeyboardButton('4'),
    types.KeyboardButton('5'),
    types.KeyboardButton('6'),
    types.KeyboardButton('7'),
    types.KeyboardButton('8'),
    types.KeyboardButton('9'),
    types.KeyboardButton('10'))
mark.row()
mark.add(
    types.KeyboardButton('💌Сообщение'))
mark.row()
mark.add(
    types.KeyboardButton('Пропустить'),
    types.KeyboardButton('Главное меню'),
    types.KeyboardButton('⚠️Жалоба')
)


apanel = types.InlineKeyboardMarkup(row_width=3)
apanel.add(
    types.InlineKeyboardButton(text='Рассылка', callback_data='admin_rass'),
    types.InlineKeyboardButton(text='Статистика', callback_data='admin_stats'),
    types.InlineKeyboardButton(text='Разбан', callback_data='admin_un'),
    types.InlineKeyboardButton(text='Бан', callback_data='admin_id'),
    types.InlineKeyboardButton(text='Чек', callback_data='admin_check'),
    types.InlineKeyboardButton(text='+вип', callback_data='admin_add_vip'),
    types.InlineKeyboardButton(text='-вип', callback_data='admin_rem_vip')
    )


links = types.InlineKeyboardMarkup(row_width=2)
links.add(
    types.InlineKeyboardButton(text='Чатик', url='https://t.me/kaoka_chat'),
    types.InlineKeyboardButton(text='Канал', url='https://t.me/kaoka_channel'),
    types.InlineKeyboardButton(text='Поддержать бота', url='https://www.donationalerts.com/r/spasibo_za_donati')
)


reportkb = types.ReplyKeyboardMarkup(resize_keyboard=True)
reportkb.add(
    types.KeyboardButton('🔞Материал для взрослых'),
    types.KeyboardButton('💰Реклама'),
    types.KeyboardButton('👾Другое'),
    types.KeyboardButton('❌Отмена')
)


nevajno = types.ReplyKeyboardMarkup(resize_keyboard=True)
nevajno.add(types.KeyboardButton('Не важно'))


kbnevajno = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
kbnevajno.add(
    types.KeyboardButton('Не важно'),
    types.KeyboardButton('Отмена')
)


async def admin_ban(chat_id):
    adminbanner = types.InlineKeyboardMarkup()
    adminbanner.add(
        types.InlineKeyboardButton(text='Бан', callback_data=f'admin_ban_{chat_id}'),
        types.InlineKeyboardButton(text='Пропустить', callback_data='admin_skip')
    )
    return adminbanner


async def answer_report(chat_id):
    inlinereport = types.InlineKeyboardMarkup()
    inlinereport.add(types.InlineKeyboardButton(text='⚠️Жалоба', callback_data='admin_report_{}'.format(chat_id)))
    return inlinereport


async def report_inline(chat_id, fromwho):
    inlinereport = types.InlineKeyboardMarkup()
    somelist = []
    user = await db.get_document(fromwho)
    answer = await db.find_answer(chat_id)
    for i in answer['answer']:
        somelist.append(i['id'])
    if user['vip'] == 1 and fromwho not in somelist:
        inlinereport.add(types.InlineKeyboardButton(text='💌Ответить', callback_data='answer_{}'.format(chat_id)))
    inlinereport.add(types.InlineKeyboardButton(text='⚠️Жалоба', callback_data='admin_report_{}'.format(chat_id)))

    return inlinereport


senderkb = types.InlineKeyboardMarkup(row_width=1)
senderkb.add(
    types.InlineKeyboardButton(text='🆘По всем вопросам', url=f'tg://user?id={admin[0]}'),
)


yesorno = types.ReplyKeyboardMarkup(resize_keyboard=True)
yesorno.add(
    types.KeyboardButton('Да'),
    types.KeyboardButton('Нет')
)


topbutton = types.InlineKeyboardMarkup(row_width=1)
topbutton.add(
    types.InlineKeyboardButton(text='♦️По оценкам', callback_data='marks'),
    types.InlineKeyboardButton(text='💯По количеству оценок', callback_data='counts')
)


tenbutton = types.InlineKeyboardMarkup(row_width=5)
tenbutton.add(
    types.InlineKeyboardButton(text='1️⃣', callback_data='marksbutton_0'),
    types.InlineKeyboardButton(text='2️⃣', callback_data='marksbutton_1'),
    types.InlineKeyboardButton(text='3️⃣', callback_data='marksbutton_2'),
    types.InlineKeyboardButton(text='4️⃣', callback_data='marksbutton_3'),
    types.InlineKeyboardButton(text='5️⃣', callback_data='marksbutton_4'),
    types.InlineKeyboardButton(text='6️⃣', callback_data='marksbutton_5'),
    types.InlineKeyboardButton(text='7️⃣', callback_data='marksbutton_6'),
    types.InlineKeyboardButton(text='8️⃣', callback_data='marksbutton_7'),
    types.InlineKeyboardButton(text='9️⃣', callback_data='marksbutton_8'),
    types.InlineKeyboardButton(text='🔟', callback_data='marksbutton_9')
)


countbutton = types.InlineKeyboardMarkup(row_width=5)
countbutton.add(
    types.InlineKeyboardButton(text='1️⃣', callback_data='countbutton_0'),
    types.InlineKeyboardButton(text='2️⃣', callback_data='countbutton_1'),
    types.InlineKeyboardButton(text='3️⃣', callback_data='countbutton_2'),
    types.InlineKeyboardButton(text='4️⃣', callback_data='countbutton_3'),
    types.InlineKeyboardButton(text='5️⃣', callback_data='countbutton_4'),
    types.InlineKeyboardButton(text='6️⃣', callback_data='countbutton_5'),
    types.InlineKeyboardButton(text='7️⃣', callback_data='countbutton_6'),
    types.InlineKeyboardButton(text='8️⃣', callback_data='countbutton_7'),
    types.InlineKeyboardButton(text='9️⃣', callback_data='countbutton_8'),
    types.InlineKeyboardButton(text='🔟', callback_data='countbutton_9')
)
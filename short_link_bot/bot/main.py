from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import bot.database as db
from bot.keyboards import main, keyboard_type, get_keyboard_subs
import os



bot = Bot(token = os.getenv("BOT_TOKEN"), parse_mode = ParseMode.HTML)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    await db.reg_user(
        user_id = user.id,
        username = user.username
    )
    await message.answer("Здравствуйте, я бот коротких ссылок", reply_markup = main())



#Cоздание ссылки
class LinkCreate(StatesGroup):
    waiting_for_url = State()

@dp.message(F.text == "Создать ссылку")
async def ask_link(message: Message, state: FSMContext):
    if not await db.is_user_active(message.from_user.id):
        keyboard = get_keyboard_subs(message.from_user.id)
        await message.answer("У вас нет доступа. Продлите подписку", reply_markup = keyboard)
        await state.clear()
        return 
    await message.answer("Отправьте мне сыылку, которую хотите сократить:")
    await state.set_state(LinkCreate.waiting_for_url)


@dp.message(LinkCreate.waiting_for_url)
async def create_link(message: Message, state: FSMContext):

    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("Это не ссылка, отправьте сслыку")
        return
    short_code = await db.save_link(message.from_user.id, url)
    short_url = f"http://localhost:8000/{short_code}"
    await message.answer(f"Готово! Ваша ссылка:\n{short_url}")
    await state.clear()

#Профиль
@dp.message(Command("profile"))
async def profile(message: Message):
    from datetime import datetime, timedelta
    conn = await db.create_db_connection()
    try:
        row = await conn.fetchrow("SELECT is_active, trial_until FROM users WHERE user_id = $1", message.from_user.id)
        if not row:
            await message.answer("Вы не зарегистрированы.")
            return

        trial = row["trial_until"]
        active = row["is_active"]

        msg = "<b>Ваш профиль:</b>\n"
        if active:
            msg += "Подписка активна\n"
        elif trial and trial > datetime.utcnow():
            msg += f"Пробный период до {trial.strftime('%Y-%m-%d %H:%M')}\n"
        else:
            msg += "Подписка неактивна и пробный период истёк.\n"

        await message.answer(msg)
    finally:
        await conn.close()



#Подписка
@dp.callback_query(F.data == "subs")
async def buy_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        await db.activate_subs(user_id, day=30)
        await callback.message.answer("Подписка продлена успешно!")
    except Exception as e:
        await callback.message.answer("Произошла ошибка при активации подписки")
    


#Список ссылок
@dp.message(F.text == "Мои ссылки")
async def list_links(message: Message):
    list = await db.get_links(message.from_user.id)
    if not list:
        await message.answer("У вас пока нет ссылок")
        return
    responce = "Ваши ссылки:\n"
    for original, code in list:
        responce += f"{original} --- http://localhost:8000/{code}\n"
    await message.answer(responce)



#временная статистика
@dp.message(Command('stat'))
async def get_statis(message: Message):
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("error")
        return
    
    short_code = parts[1]
    try:
        total, uni = await db.get_stat(short_code)
        await message.answer(
            f"Статистика по ссылке: {short_code}\n"
            f"Количество переходов: {total}\n"
            f"Уникальные пользователи: {uni}"
        )
    except Exception as e:
        await message.answer("expection error")


#Новая статистика
class StatState(StatesGroup):
    waiting_for_link = State()

@dp.message(F.text == "Статистика")
async def choose_link(message: Message, state: FSMContext):
    links = await db.get_links(message.from_user.id)

    if not links:
        await message.answer("У вас нет ссылок")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard = [
            [InlineKeyboardButton(text=row["original_url"], callback_data = f"stat:{row['short_code']}")]
            for row in links
        ]
    )
    await message.answer("Выберите ссылку:", reply_markup = keyboard)
    await state.set_state(StatState.waiting_for_link)


@dp.callback_query(F.data.startswith("stat:"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    short_code = callback.data.split(":")[1]

    await state.update_data(short_code = short_code)

    await callback.message.answer("Выберите тип статистики:", reply_markup = keyboard_type)

@dp.callback_query(F.data.startswith("type:"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    state_type = callback.data.split(":")[1]

    data = await state.get_data()
    short_code = data.get("short_code")

    if not short_code:
        await callback.message.answer("❌ Ошибка: не выбрана ссылка")
        return

    stats = await db.get_statistics(state_type, short_code)
    if not stats:
        await callback.message.answer("Нет данных ")
        return
    
    text = f"<b>Статистика за период ({state_type}):</b>\n\n"
    for label, count, unique in stats:
        text += f"{label}: кол-во переходов {count} ({unique} уникальных)\n"

    await callback.message.answer(text)


    chart = await generate_chart(stats, title=f"Переходы за {state_type}")
    chart_file = BufferedInputFile(chart.read(), filename="chart.png")
    await callback.message.answer_photo(photo=chart_file)


#Диаграмма  
async def generate_chart(data, title="Статистика"):
    import matplotlib.pyplot as plt
    import numpy as np
    from io import BytesIO

    labels = [label for label, _, _ in data]
    totals = [count for _, count, _ in data]
    uniques = [uniq for _, _, uniq in data]

    x = np.arange(len(labels)) 
    width = 0.35  # ширина столбца

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width/2, totals, width, label='Всего переходов', color='skyblue')
    ax.bar(x + width/2, uniques, width, label='Уникальных', color='limegreen')

    ax.set_xlabel('Дата')
    ax.set_ylabel('Количество')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)

    return buf




#Удаление ссылок
@dp.message(F.text == "Удалить ссылку")
async def delete_link(message: Message):
    links = await db.get_links(message.from_user.id)

    if not links:
        await message.answer("У вас нет ссылок")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard = [
            [InlineKeyboardButton(text=row["original_url"], callback_data = f"delete:{row['short_code']}")]
            for row in links
        ]
    )
    await message.answer("Выберите ссылку, которую хотите удалить:", reply_markup = keyboard)
    

@dp.callback_query(F.data.startswith("delete:"))
async def choose_type(callback: CallbackQuery):
    
    short_code = callback.data.split(":")[1]
    
    try:
        await db.delete_link(short_code, callback.from_user.id)
        await callback.message.answer("Ссылка удалена!")
    except Exception as e:
        await callback.message.answer("Ошибка при удалении")
        















async def on_startup(dp):
    try:
        await db.create_table()
        print("Таблицы базы данных созданы")
    except Exception as e:
        print(f"Не удалось инициализировать базу данных: {e}")
        import sys
        sys.exit(1)

if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot, on_startup = on_startup))
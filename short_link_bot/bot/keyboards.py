from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder



def main():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Создать ссылку")
    builder.button(text="Мои ссылки")
    builder.button(text="Статистика")
    builder.button(text="Удалить ссылку")
    builder.adjust(2)  
    return builder.as_markup()

keyboard_type = InlineKeyboardMarkup(
        inline_keyboard = [
            [InlineKeyboardButton(text="Day", callback_data="type:day")],
            [InlineKeyboardButton(text="Week", callback_data="type:week")],
            [InlineKeyboardButton(text="Month", callback_data="type:month")]
        ]
    )
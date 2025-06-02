from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardButton, InlineKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура меню"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Ваш список игр Steam'))
    builder.row(
        KeyboardButton(text='Добавить url'),
        KeyboardButton(text='Удалить url')
    )
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder='Выберите пункт меню'
    )

def get_finish_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура только с кнопкой завершения"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛑 Завершить")]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder='Нажмите для возврата в меню'
    )

def get_delete_keyboard(games: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура для удаления игр"""
    builder = InlineKeyboardBuilder()
    for idx, game in enumerate(games):
        builder.add(InlineKeyboardButton(
            text=f"❌ {game['name']}",
            callback_data=f"delete_{idx}"
        ))
    builder.adjust(1)
    return builder.as_markup()
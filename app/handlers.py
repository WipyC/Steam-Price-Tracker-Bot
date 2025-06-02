from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import re

from app.keyboards import (
    get_main_keyboard,
    get_finish_keyboard,
    get_delete_keyboard
)
from app.parser import get_steam_game_info

router = Router()
logger = logging.getLogger(__name__)

# Хранение данных в памяти
user_games = {}

class UrlStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_delete = State()  # Новое состояние для удаления

def is_valid_steam_url(url: str) -> bool:
    """Проверяет, является ли URL валидным Steam URL"""
    pattern = r'^https?://store\.steampowered\.com/app/\d+/[^/]*/?$'
    return re.match(pattern, url.strip()) is not None

def normalize_url(url: str) -> str:
    """Приводит URL к стандартному виду"""
    return url.lower().strip().rstrip('/')

@router.message(CommandStart())
async def handle_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "Привет! Я бот для отслеживания цен на игры в Steam",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == 'Ваш список игр Steam')
async def handle_show_games(message: Message):
    """Показывает список игр пользователя"""
    user_id = message.from_user.id
    games = user_games.get(user_id, [])
    
    if not games:
        await message.answer("Ваш список игр пуст")
        return
    
    for game in games:
        result = get_steam_game_info(game['url'])
        if "error" in result:
            await message.answer(f"Ошибка при получении информации: {result['error']}")
            continue
            
        response = f"🎮 <b>{result['name']}</b>\n"
        if result["is_free"]:
            response += "💰 Бесплатно"
        else:
            price = ''.join(c for c in result["price"] if c.isdigit() or c in ',.')
            if "discount" in result:
                original = ''.join(c for c in result["original_price"] if c.isdigit() or c in ',.')
                response += f"🔥 Скидка {result['discount']}\n"
                response += f"💵 {price} руб. (было {original})"
            else:
                response += f"💵 {price} руб."
        
        await message.answer(response, parse_mode='HTML')

@router.message(F.text == 'Добавить url')
async def handle_add_url(message: Message, state: FSMContext):
    """Начинает процесс добавления URL"""
    await state.set_state(UrlStates.waiting_for_url)
    await message.answer(
        "Пришлите мне URL игры из Steam (например: https://store.steampowered.com/app/123456/Game_Name/)\n\n"
        "Можно добавить несколько URL подряд.\n"
        "Для завершения нажмите кнопку ниже или отправьте /cancel",
        reply_markup=get_finish_keyboard()
    )

@router.message(F.text == "🛑 Завершить")
@router.message(Command("cancel"))
async def handle_finish_adding_anywhere(message: Message, state: FSMContext):
    """Обработчик завершения из любого состояния"""
    current_state = await state.get_state()
    
    # Если состояние было сброшено (например, после перезапуска бота)
    if current_state is None:
        await message.answer(
            "Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Если состояние активно - обрабатываем как обычно
    try:
        await state.clear()
        
        try:
            await message.delete()
        except:
            pass
        
        user_id = message.from_user.id
        count = len(user_games.get(user_id, []))
        
        await message.answer(
            f"Добавление завершено. Всего игр: {count}",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при завершении: {e}")
        await message.answer(
            "Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )

# Удаляем старый обработчик и заменяем его ссылкой на новый
@router.message(UrlStates.waiting_for_url, F.text == "🛑 Завершить")
@router.message(UrlStates.waiting_for_url, Command("cancel"))
async def handle_finish_adding(message: Message, state: FSMContext):
    await handle_finish_adding_anywhere(message, state)

@router.message(UrlStates.waiting_for_url)
async def handle_save_url(message: Message, state: FSMContext):
    """Сохраняет URL игры"""
    user_id = message.from_user.id
    url = message.text.strip()
    
    if not is_valid_steam_url(url):
        await message.answer("Это не похоже на Steam URL. Попробуйте ещё раз")
        return
    
    norm_url = normalize_url(url)
    current_games = user_games.get(user_id, [])
    
    # Проверка на дубликаты
    if any(norm_url == normalize_url(game['url']) for game in current_games):
        await message.answer("⚠️ Эта игра уже есть в вашем списке!")
        return
    
    # Получаем информацию об игре для сохранения названия
    game_info = get_steam_game_info(url)
    if "error" in game_info:
        await message.answer(f"Ошибка: {game_info['error']}\nПопробуйте другой URL")
        return
    
    # Сохраняем игру
    if user_id not in user_games:
        user_games[user_id] = []
    
    user_games[user_id].append({
        'url': url,
        'name': game_info['name']
    })
    
    await message.answer(
        f"✅ <b>{game_info['name']}</b> добавлена!\n"
        f"Всего игр: {len(user_games[user_id])}",
        parse_mode='HTML'
    )

@router.message(F.text == 'Удалить url')
async def handle_delete_menu(message: Message, state: FSMContext):
    """Показывает клавиатуру для удаления игр"""
    user_id = message.from_user.id
    games = user_games.get(user_id, [])
    
    if not games:
        await message.answer("Ваш список игр пуст", reply_markup=get_main_keyboard())
        return
    
    await state.set_state(UrlStates.waiting_for_delete)
    try:
        # Отправляем новое сообщение с клавиатурой
        await message.answer(
            "Выберите игру для удаления:",
            reply_markup=get_delete_keyboard(games)
        )
    except Exception as e:
        logger.error(f"Error showing delete keyboard: {e}")
        await message.answer(
            "Ошибка при отображении списка игр",
            reply_markup=get_main_keyboard()
        )

@router.callback_query(UrlStates.waiting_for_delete, F.data.startswith("delete_"))
async def handle_delete_game(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает удаление игры"""
    user_id = callback.from_user.id
    try:
        game_idx = int(callback.data.split("_")[1])
        
        if user_id not in user_games or game_idx >= len(user_games[user_id]):
            await callback.answer("Игра не найдена", show_alert=True)
            return
        
        # Удаляем игру
        deleted_game = user_games[user_id].pop(game_idx)
        
        # Удаляем сообщение с кнопками
        await callback.message.delete()
        await callback.answer()
        
        # Если игры остались - показываем обновленный список
        if user_games.get(user_id):
            await callback.message.answer(
                reply_markup=get_delete_keyboard(user_games[user_id])
            )
        else:
            await state.clear()
            await callback.message.answer(
                "Ваш список игр пуст",
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error deleting game: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

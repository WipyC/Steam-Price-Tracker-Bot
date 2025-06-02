import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def get_steam_game_info(url: str) -> dict:
    """
    Получает информацию об игре из Steam Store
    
    Args:
        url (str): URL страницы игры в Steam Store
        
    Returns:
        dict: Словарь с информацией об игре или ошибкой
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": "birthtime=283993201; lastagecheckage=1-0-1900; mature_content=1",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        # Проверяем валидность URL перед запросом
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"error": "Неверный URL"}
            
        if "steampowered.com" not in parsed.netloc:
            return {"error": "Это не Steam URL"}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Название игры
        game_name = soup.find('div', class_='apphub_AppName')
        if not game_name:
            return {"error": "Название игры не найдено"}
        game_name = game_name.get_text(strip=True)
        
        # Поиск блока с ценой
        price_block = None
        for selector in [
            'div.game_purchase_action',
            'div.game_area_purchase_game_wrapper',
            'div.game_area_purchase_game'
        ]:
            block = soup.select_one(selector)
            if block and ("Купить" in block.get_text() or "Buy" in block.get_text()):
                price_block = block
                break
        
        if not price_block:
            return {"error": "Блок с ценой не найден"}
        
        # Проверка бесплатной игры
        free_check = price_block.find('div', class_='game_purchase_price', string=lambda t: 'Бесплатно' in str(t) or 'Free' in str(t))
        if free_check:
            return {
                "name": game_name,
                "price": "Бесплатно",
                "is_free": True
            }
        
        # Проверка скидки
        discount_price = price_block.find('div', class_='discount_final_price')
        if discount_price:
            return {
                "name": game_name,
                "price": discount_price.get_text(strip=True),
                "original_price": price_block.find('div', class_='discount_original_price').get_text(strip=True),
                "discount": price_block.find('div', class_='discount_pct').get_text(strip=True),
                "is_free": False
            }
        
        # Обычная цена
        regular_price = price_block.find('div', class_='game_purchase_price')
        if regular_price:
            return {
                "name": game_name,
                "price": regular_price.get_text(strip=True),
                "is_free": False
            }
        
        return {"error": "Не удалось определить цену"}
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"error": f"Неожиданная ошибка: {str(e)}"}
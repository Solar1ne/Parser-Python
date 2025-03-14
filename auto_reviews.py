import requests
from bs4 import BeautifulSoup
import random
import time
import json
import sqlite3
import re
import os
from urllib.parse import urljoin, urlparse

# База данных
def setup_database():
    """Create the database and table if they don't exist."""
    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            product_name TEXT,
            comment TEXT,
            rating INTEGER,
            created_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("База данных готова к использованию.")

# Функция для получения случайного User-Agent
def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)

# Функция для запроса API отзывов
def fetch_reviews_api(product_id, page=1, limit=10):
    print(f"Запрос API для получения отзывов продукта {product_id}, страница {page}")
    
    # Создаем сессию
    session = requests.Session()
    
    # Начинаем с посещения главной страницы для получения куки
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }
        
        # Посещаем главную страницу для получения куков
        main_page = session.get('https://lenta.com/', headers=headers, timeout=10)
        print(f"Статус запроса главной страницы: {main_page.status_code}")
        
        # Случайная задержка для имитации человеческого поведения
        time.sleep(random.uniform(2, 4))
        
        # Теперь посещаем страницу продукта для получения дополнительных куков
        product_page_url = f'https://lenta.com/product/{product_id}/'
        product_page = session.get(product_page_url, headers=headers, timeout=10)
        print(f"Статус запроса страницы продукта: {product_page.status_code}")
        
        # Обновляем заголовки для запроса API, добавляя Referer
        api_headers = headers.copy()
        api_headers.update({
            'Referer': product_page_url,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # Попробуем найти API URL в HTML страницы
        soup = BeautifulSoup(product_page.text, 'html.parser')
        
        # Сохраним страницу для анализа
        with open('product_page.html', 'w', encoding='utf-8') as f:
            f.write(product_page.text)
        
        # Попробуем разные варианты API URL
        base_url = 'https://lenta.com'
        api_endpoints = [
            f'/api/v1/products/{product_id}/reviews?page={page}&limit={limit}',
            f'/api/v2/products/{product_id}/reviews?page={page}&limit={limit}',
            f'/api/products/{product_id}/reviews?page={page}&limit={limit}'
        ]
        
        # Ищем ссылки на API в HTML
        script_tags = soup.find_all('script')
        api_urls_from_html = []
        
        for script in script_tags:
            script_content = script.string or ''
            if 'reviews' in script_content.lower() and 'api' in script_content.lower():
                # Ищем URL API в скрипте
                api_url_match = re.search(r'["\'](\S*api\S*reviews\S*)["\']', script_content)
                if api_url_match:
                    api_urls_from_html.append(api_url_match.group(1))
        
        if api_urls_from_html:
            print(f"Найдены потенциальные API URL в HTML: {api_urls_from_html}")
            api_endpoints.extend(api_urls_from_html)
        
        # Пробуем каждый API endpoint
        for endpoint in api_endpoints:
            api_url = urljoin(base_url, endpoint)
            print(f"Пробуем API URL: {api_url}")
            
            try:
                # Добавляем случайную задержку
                time.sleep(random.uniform(1, 3))
                
                api_response = session.get(api_url, headers=api_headers, timeout=10)
                print(f"Статус API запроса: {api_response.status_code}")
                
                if api_response.status_code == 200:
                    try:
                        data = api_response.json()
                        with open(f'api_response_page_{page}.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print(f"Сохранен ответ API в api_response_page_{page}.json")
                        return data
                    except json.JSONDecodeError:
                        print("Ответ API не является JSON")
                        with open(f'api_response_page_{page}.html', 'w', encoding='utf-8') as f:
                            f.write(api_response.text)
            except requests.RequestException as e:
                print(f"Ошибка при запросе к API {api_url}: {e}")
        
        # Если API не работает, попробуем извлечь отзывы напрямую из HTML
        print("Пробуем извлечь отзывы из HTML страницы продукта...")
        
        # Поиск отзывов на странице
        reviews_data = extract_reviews_from_html(product_page.text, product_id)
        if reviews_data:
            return {'reviews': reviews_data, 'from_html': True}
        
        return None
        
    except requests.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None

# Функция для извлечения отзывов из HTML
def extract_reviews_from_html(html_content, product_id):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ищем название продукта
        product_name = "Неизвестный продукт"
        title_tag = soup.find('h1')
        if title_tag:
            product_name = title_tag.text.strip()
            print(f"Название продукта: {product_name}")
        
        # Ищем блок с отзывами
        reviews_block = None
        
        # Пробуем разные селекторы для блока отзывов
        selectors = [
            'lu-feedback-review',
            'div.lu-review',
            'div.product-tab--review-margin',
            'div[class*="review"]'
        ]
        
        for selector in selectors:
            reviews_elements = soup.select(selector)
            if reviews_elements:
                reviews_block = reviews_elements
                print(f"Найден блок отзывов по селектору: {selector}, количество: {len(reviews_elements)}")
                break
        
        if not reviews_block:
            print("Блок отзывов не найден в HTML")
            return []
        
        # Извлекаем данные из каждого отзыва
        reviews = []
        
        for review_elem in reviews_block:
            # Ищем текст отзыва
            review_text_elem = review_elem.select_one('p.lu-review_text') or review_elem.select_one('p[class*="text"]') or review_elem.select_one('p')
            if not review_text_elem:
                continue
                
            review_text = review_text_elem.text.strip()
            
            # Ищем рейтинг (по количеству звезд)
            rating = 5  # По умолчанию
            rating_elements = review_elem.select('div[class*="rating-active"]') or review_elem.select('div[class*="star"]')
            if rating_elements:
                rating = len(rating_elements)
            
            # Ищем дату
            date = "Неизвестная дата"
            date_elem = review_elem.select_one('div.lu-review_date') or review_elem.select_one('div[class*="date"]') or review_elem.select_one('span[class*="date"]')
            if date_elem:
                date = date_elem.text.strip()
            
            review_data = {
                "platform": "Lenta.com",
                "product_name": product_name,
                "comment": review_text,
                "rating": rating,
                "created_at": date
            }
            
            reviews.append(review_data)
            print(f"Извлечен отзыв: {review_text[:30]}... (Дата: {date}, Рейтинг: {rating})")
        
        return reviews
        
    except Exception as e:
        print(f"Ошибка при извлечении отзывов из HTML: {e}")
        return []

# Функция для сохранения отзывов в базу данных
def save_reviews_to_db(reviews):
    if not reviews:
        print("Нет отзывов для сохранения")
        return 0
    
    try:
        conn = sqlite3.connect("reviews.db")
        cursor = conn.cursor()
        
        # Преобразуем список отзывов в формат для вставки
        reviews_data = []
        for r in reviews:
            reviews_data.append((
                r["platform"], 
                r["product_name"], 
                r["comment"], 
                r["rating"], 
                r["created_at"]
            ))
        
        # Вставляем отзывы в базу данных
        cursor.executemany(
            "INSERT INTO reviews (platform, product_name, comment, rating, created_at) VALUES (?, ?, ?, ?, ?)",
            reviews_data
        )
        
        conn.commit()
        saved_count = cursor.rowcount
        conn.close()
        
        print(f"Сохранено {saved_count} отзывов в базу данных")
        return saved_count
    
    except Exception as e:
        print(f"Ошибка при сохранении отзывов в базу данных: {e}")
        return 0

# Основная функция для сбора отзывов
def collect_reviews(product_url, max_pages=3):
    # Извлекаем ID продукта из URL
    product_id = None
    url_parts = product_url.strip('/').split('/')
    product_id = url_parts[-1]
    
    # Проверяем формат ID (возможно нужно извлечь числовой ID)
    if '-' in product_id:
        # Если ID имеет формат "tvorog-ekoniva-9-bez-zmzh-rossiya-300g-664609", извлекаем числовой ID "664609"
        numeric_id_match = re.search(r'(\d+)$', product_id)
        if numeric_id_match:
            numeric_id = numeric_id_match.group(1)
            print(f"Извлечен числовой ID: {numeric_id} из {product_id}")
            product_id_for_api = numeric_id
        else:
            product_id_for_api = product_id
    else:
        product_id_for_api = product_id
    
    print(f"ID продукта для API: {product_id_for_api}")
    print(f"ID продукта (оригинальный): {product_id}")
    
    # Собираем отзывы через API
    all_reviews = []
    
    for page in range(1, max_pages + 1):
        response_data = fetch_reviews_api(product_id, page=page)
        
        if not response_data:
            print(f"Не удалось получить данные для страницы {page}")
            break
        
        # Обрабатываем ответ
        if 'from_html' in response_data and response_data['from_html']:
            # Если отзывы были извлечены из HTML
            page_reviews = response_data['reviews']
        else:
            # Если отзывы были получены через API, нужно правильно извлечь их из JSON
            # Структура может зависеть от API
            if 'reviews' in response_data:
                page_reviews = response_data['reviews']
            elif 'data' in response_data and 'reviews' in response_data['data']:
                page_reviews = response_data['data']['reviews']
            elif 'results' in response_data:
                page_reviews = response_data['results']
            else:
                # Сохраняем ответ для анализа
                with open(f'unknown_api_structure_page_{page}.json', 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, ensure_ascii=False, indent=2)
                print(f"Неизвестная структура ответа API, сохранена в unknown_api_structure_page_{page}.json")
                page_reviews = []
        
        if not page_reviews:
            print(f"Нет отзывов на странице {page}")
            break
        
        # Проверяем, что у нас есть правильные поля в отзывах
        formatted_reviews = []
        for review in page_reviews:
            # Если отзывы уже в нашем формате (извлечены из HTML)
            if 'platform' in review and 'product_name' in review and 'comment' in review:
                formatted_reviews.append(review)
            else:
                # Если отзывы пришли в формате API, преобразуем их
                formatted_review = {
                    "platform": "Lenta.com",
                    "product_name": product_id,  # Заглушка, будет заменена позже
                    "comment": review.get('text', review.get('content', review.get('comment', ''))),
                    "rating": review.get('rating', review.get('stars', 5)),
                    "created_at": review.get('date', review.get('created_at', 'Неизвестная дата'))
                }
                formatted_reviews.append(formatted_review)
        
        all_reviews.extend(formatted_reviews)
        print(f"Получено {len(formatted_reviews)} отзывов на странице {page}")
        
        # Случайная задержка между запросами страниц
        if page < max_pages:
            sleep_time = random.uniform(2, 5)
            print(f"Пауза {sleep_time:.2f} секунд перед запросом следующей страницы...")
            time.sleep(sleep_time)
    
    return all_reviews

# Функция для просмотра сохраненных отзывов
def view_reviews():
    try:
        conn = sqlite3.connect("reviews.db")
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица reviews
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
        table_exists = cursor.fetchone()
        if not table_exists:
            print("Таблица 'reviews' не существует в базе данных.")
            return
        
        # Выполняем запрос на получение всех записей
        cursor.execute("SELECT * FROM reviews")
        rows = cursor.fetchall()
        
        if not rows:
            print("База данных пуста. Нет сохраненных отзывов.")
            return
        
        # Получаем имена столбцов
        column_names = [description[0] for description in cursor.description]
        
        # Выводим заголовки столбцов
        print("\n" + "-" * 100)
        header = f"{column_names[0]:<3} | {column_names[1]:<10} | {column_names[2]:<20} | {column_names[3]:<30} | {column_names[4]:<6} | {column_names[5]:<15}"
        print(header)
        print("-" * 100)
        
        # Выводим данные
        for row in rows:
            # Обрезаем слишком длинные поля для лучшего отображения
            product_name = str(row[2])[:20] if len(str(row[2])) > 20 else row[2]
            comment = str(row[3])[:30] if len(str(row[3])) > 30 else row[3]
            
            row_text = f"{row[0]:<3} | {row[1]:<10} | {product_name:<20} | {comment:<30} | {row[4]:<6} | {row[5]:<15}"
            print(row_text)
        
        print("-" * 100)
        print(f"Всего отзывов: {len(rows)}")
        
    except Exception as e:
        print(f"Ошибка при просмотре базы данных: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# Основная функция
def main():
    # Настраиваем базу данных
    setup_database()
    
    while True:
        print("\n=== МЕНЮ ===")
        print("1. Собрать отзывы автоматически")
        print("2. Просмотреть все отзывы")
        print("3. Выход")
        
        choice = input("\nВыберите действие (1-3): ")
        
        if choice == "1":
            product_url = input("Введите URL страницы товара (Enter для примера): ")
            if not product_url:
                product_url = "https://lenta.com/product/tvorog-ekoniva-9-bez-zmzh-rossiya-300g-664609/"
            
            max_pages = 3
            try:
                pages_input = input("Сколько страниц отзывов собрать (Enter для 3): ")
                if pages_input:
                    max_pages = int(pages_input)
            except ValueError:
                print("Используется значение по умолчанию: 3 страницы")
            
            print(f"\nНачинаем сбор отзывов с {product_url}")
            reviews = collect_reviews(product_url, max_pages=max_pages)
            
            if reviews:
                print(f"Собрано {len(reviews)} отзывов")
                save_reviews_to_db(reviews)
            else:
                print("Отзывы не собраны.")
                
        elif choice == "2":
            view_reviews()
        elif choice == "3":
            print("Программа завершена.")
            break
        else:
            print("Неверный ввод. Пожалуйста, выберите 1, 2 или 3.")

if __name__ == "__main__":
    main() 
import requests
from bs4 import BeautifulSoup
import random
import time
import json
import sqlite3
import re
import os
from urllib.parse import urljoin, urlparse
from lxml import etree

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

# Функция для парсинга отзывов с Perekrestok.ru
def fetch_perekrestok_reviews(product_url, page=1):
    print(f"Запрос страницы отзывов: {product_url}, страница {page}")
    
    # Создаем сессию
    session = requests.Session()
    
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Сначала посещаем главную страницу для получения куков
        main_page = session.get('https://www.perekrestok.ru/', headers=headers, timeout=10)
        print(f"Статус запроса главной страницы: {main_page.status_code}")
        
        # Случайная задержка
        time.sleep(random.uniform(2, 4))
        
        # Затем запрашиваем страницу продукта
        if page > 1:
            # Если нужна не первая страница отзывов, добавляем параметр page
            product_page_url = f"{product_url}?page={page}" if '?' not in product_url else f"{product_url}&page={page}"
        else:
            product_page_url = product_url
            
        print(f"Запрашиваем URL: {product_page_url}")
        product_page = session.get(product_page_url, headers=headers, timeout=10)
        print(f"Статус запроса страницы отзывов: {product_page.status_code}")
        
        # Сохраняем страницу для анализа
        with open(f'perekrestok_page_{page}.html', 'w', encoding='utf-8') as f:
            f.write(product_page.text)
        print(f"Сохранен HTML страницы в perekrestok_page_{page}.html")
        
        # Проверяем на наличие признаков блокировки
        if product_page.status_code >= 400 or "captcha" in product_page.text.lower() or "recaptcha" in product_page.text.lower():
            print("Возможно, сайт заблокировал запрос. Проверьте сохраненный HTML файл.")
            return []
        
        # Извлекаем отзывы
        reviews = extract_perekrestok_reviews(product_page.text, product_url)
        
        # Проверяем, есть ли следующая страница
        soup = BeautifulSoup(product_page.text, 'html.parser')
        has_next_page = check_next_page(soup, page)
        
        return {
            'reviews': reviews,
            'has_next_page': has_next_page
        }
        
    except requests.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return {'reviews': [], 'has_next_page': False}

# Функция для извлечения отзывов из HTML страницы Perekrestok
def extract_perekrestok_reviews(html_content, product_url):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ищем название продукта
        product_name = "Неизвестный продукт"
        title_tag = soup.find('h1')
        if title_tag:
            product_name = title_tag.text.strip()
            print(f"Название продукта: {product_name}")
        
        # Используем явно указанный XPath для поиска отзывов
        # Для работы с XPath в BeautifulSoup будем использовать lxml
        
        # Преобразуем HTML в формат lxml
        parser = etree.HTMLParser()
        tree = etree.fromstring(html_content, parser)
        
        # Используем точный XPath, предоставленный пользователем
        review_text_elements = tree.xpath('/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div[1]/div[2]/div[2]/p')
        
        print(f"Найдено элементов по указанному XPath: {len(review_text_elements)}")
        
        if not review_text_elements:
            print("По указанному XPath элементы не найдены, пробуем альтернативные методы...")
            
            # Пробуем близкие XPath
            alternative_xpaths = [
                '/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div/div[2]/div[2]/p',
                '/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div//p',
                '//div[contains(@class, "review")]/p',
                '//p[contains(@class, "text")]',
                '//div[contains(@class, "review")]//p'
            ]
            
            for xpath in alternative_xpaths:
                alternative_elements = tree.xpath(xpath)
                if alternative_elements:
                    review_text_elements = alternative_elements
                    print(f"Найдены элементы по альтернативному XPath {xpath}: {len(alternative_elements)}")
                    break
            
            # Если не нашли по XPath, возвращаемся к поиску через CSS селекторы
            if not review_text_elements:
                print("Пробуем поиск через CSS селекторы...")
                
                # Ищем индивидуальные отзывы
                review_elements = []
                review_selectors = [
                    '.reviewCard',
                    '.review-card',
                    '.review-item',
                    'div[data-qa="review-item"]',
                    '.sc-16b00b87-1',
                    'div.review'
                ]
                
                for selector in review_selectors:
                    elements = soup.select(selector)
                    if elements:
                        review_elements = elements
                        print(f"Найдены отзывы по селектору: {selector}, количество: {len(elements)}")
                        break
                
                if not review_elements:
                    print("Не найдены отзывы ни по XPath, ни по CSS селекторам")
                    return []
                
                # Извлекаем отзывы из найденных элементов
                reviews = []
                for review_elem in review_elements:
                    try:
                        # Ищем текст отзыва
                        review_text = None
                        text_selectors = [
                            'p.reviewText', 
                            '.review-text',
                            '.review-content',
                            'div[data-qa="review-text"]',
                            'p', # Если не найдено по специфичным селекторам, ищем любой параграф
                            'div.text'
                        ]
                        
                        for selector in text_selectors:
                            text_elem = review_elem.select_one(selector)
                            if text_elem and text_elem.text.strip():
                                review_text = text_elem.text.strip()
                                break
                        
                        # Если не нашли текст по селекторам, берем весь текст элемента
                        if not review_text:
                            review_text = review_elem.text.strip()
                            # Очищаем от служебной информации
                            review_text = re.sub(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}', '', review_text)
                            review_text = review_text.strip()
                        
                        if not review_text or len(review_text) < 5:
                            continue
                        
                        # Заполняем данные отзыва
                        review_data = {
                            "platform": "Perekrestok.ru",
                            "product_name": product_name,
                            "comment": review_text,
                            "rating": 5,  # По умолчанию
                            "created_at": "Неизвестная дата"
                        }
                        
                        # Пытаемся найти рейтинг и дату
                        # (код для поиска рейтинга и даты аналогичен оригинальному)
                        
                        reviews.append(review_data)
                        print(f"Извлечен отзыв: {review_text[:50]}...")
                    except Exception as e:
                        print(f"Ошибка при обработке отзыва: {e}")
                
                return reviews
        
        # Если нашли элементы по XPath, извлекаем из них отзывы
        reviews = []
        for element in review_text_elements:
            try:
                review_text = element.text.strip()
                if not review_text or len(review_text) < 5:
                    continue
                
                # Ищем родительский элемент отзыва для извлечения даты и рейтинга
                parent_element = None
                current = element
                for _ in range(3):  # Поднимаемся на 3 уровня вверх
                    if current.getparent() is not None:
                        current = current.getparent()
                        if 'review' in str(etree.tostring(current)).lower():
                            parent_element = current
                            break
                
                # Извлекаем рейтинг и дату (если найден родительский элемент)
                rating = 5  # По умолчанию
                date = "Неизвестная дата"
                
                if parent_element is not None:
                    # Преобразуем элемент lxml в строку и создаем новый soup для извлечения данных
                    parent_html = etree.tostring(parent_element).decode('utf-8')
                    parent_soup = BeautifulSoup(parent_html, 'html.parser')
                    
                    # Ищем рейтинг
                    rating_selectors = [
                        '.rating',
                        '.stars',
                        '.score',
                        'div[data-qa="review-rating"]',
                        'span.rating-value'
                    ]
                    
                    for selector in rating_selectors:
                        rating_elem = parent_soup.select_one(selector)
                        if rating_elem:
                            try:
                                rating_text = rating_elem.text.strip()
                                if rating_text and rating_text[0].isdigit():
                                    rating = int(float(rating_text.replace(',', '.')))
                                    break
                            except ValueError:
                                pass
                    
                    # Ищем дату
                    date_selectors = [
                        '.date',
                        '.review-date',
                        '.timestamp',
                        'div[data-qa="review-date"]',
                        'span.date'
                    ]
                    
                    for selector in date_selectors:
                        date_elem = parent_soup.select_one(selector)
                        if date_elem and date_elem.text.strip():
                            date = date_elem.text.strip()
                            break
                
                # Формируем данные отзыва
                review_data = {
                    "platform": "Perekrestok.ru",
                    "product_name": product_name,
                    "comment": review_text,
                    "rating": rating,
                    "created_at": date
                }
                
                reviews.append(review_data)
                print(f"Извлечен отзыв по XPath: {review_text[:50]}... (Дата: {date}, Рейтинг: {rating})")
                
            except Exception as e:
                print(f"Ошибка при обработке отзыва из XPath: {e}")
        
        return reviews
        
    except Exception as e:
        print(f"Ошибка при извлечении отзывов из HTML: {e}")
        return []

# Функция для проверки наличия следующей страницы
def check_next_page(soup, current_page):
    # Ищем элементы пагинации
    pagination_selectors = [
        'ul.pagination',
        '.paging',
        '.pages',
        'div[data-qa="pagination"]'
    ]
    
    for selector in pagination_selectors:
        pagination = soup.select_one(selector)
        if pagination:
            # Проверяем, есть ли кнопка следующей страницы
            next_button = pagination.select_one('li.next:not(.disabled), .next-page:not(.disabled), [data-qa="next-page"]')
            if next_button:
                return True
            
            # Проверяем, есть ли страница с номером больше текущей
            page_links = pagination.select('a')
            for link in page_links:
                try:
                    page_num = int(link.text.strip())
                    if page_num > current_page:
                        return True
                except ValueError:
                    continue
    
    # Проверяем по тексту
    next_text = soup.find(string=lambda text: 'следующая' in text.lower() or 'далее' in text.lower() or 'вперед' in text.lower())
    if next_text:
        return True
        
    return False

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

# Основная функция для сбора отзывов с Perekrestok
def collect_perekrestok_reviews(product_url, max_pages=3):
    # Проверяем, что URL указывает на страницу отзывов
    if not '/reviews' in product_url:
        product_url = product_url + '/reviews'
    
    print(f"Начинаем сбор отзывов с {product_url}")
    all_reviews = []
    
    for page in range(1, max_pages + 1):
        result = fetch_perekrestok_reviews(product_url, page)
        
        # Проверяем тип результата - должен быть словарь с ключами 'reviews' и 'has_next_page'
        if isinstance(result, dict) and 'reviews' in result:
            reviews = result['reviews']
            has_next_page = result.get('has_next_page', False)
        else:
            # Если результат не словарь, а список (для обратной совместимости)
            reviews = result
            has_next_page = False
            print("Внимание: результат в устаревшем формате")
        
        if not reviews:
            print(f"Отзывы на странице {page} не найдены")
            break
        
        all_reviews.extend(reviews)
        print(f"Собрано {len(reviews)} отзывов на странице {page}. Всего: {len(all_reviews)}")
        
        if not has_next_page:
            print("Следующая страница не найдена. Сбор отзывов завершен.")
            break
        
        # Пауза между запросами
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
        header = f"{column_names[0]:<3} | {column_names[1]:<15} | {column_names[2]:<20} | {column_names[3]:<30} | {column_names[4]:<6} | {column_names[5]:<15}"
        print(header)
        print("-" * 100)
        
        # Выводим данные
        for row in rows:
            # Обрезаем слишком длинные поля для лучшего отображения
            product_name = str(row[2])[:20] if len(str(row[2])) > 20 else row[2]
            comment = str(row[3])[:30] if len(str(row[3])) > 30 else row[3]
            
            row_text = f"{row[0]:<3} | {row[1]:<15} | {product_name:<20} | {comment:<30} | {row[4]:<6} | {row[5]:<15}"
            print(row_text)
        
        print("-" * 100)
        print(f"Всего отзывов: {len(rows)}")
        
    except Exception as e:
        print(f"Ошибка при просмотре базы данных: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# Функция для ввода отзывов вручную
def manual_input_reviews():
    try:
        reviews = []
        
        print("\n=== РУЧНОЙ ВВОД ОТЗЫВОВ ===")
        product_name = input("Введите название продукта: ")
        
        while True:
            print("\nВвод нового отзыва (для завершения оставьте текст отзыва пустым)")
            comment = input("Текст отзыва: ")
            if not comment:
                break
            
            rating = 0
            while rating < 1 or rating > 5:
                try:
                    rating = int(input("Рейтинг (от 1 до 5): "))
                    if rating < 1 or rating > 5:
                        print("Рейтинг должен быть от 1 до 5")
                except ValueError:
                    print("Введите число от 1 до 5")
            
            date = input("Дата (например, 25 марта 2024): ")
            if not date:
                date = "Неизвестная дата"
            
            review = {
                "platform": "Perekrestok.ru",
                "product_name": product_name,
                "comment": comment,
                "rating": rating,
                "created_at": date
            }
            
            reviews.append(review)
            print(f"Отзыв добавлен. Всего: {len(reviews)}")
        
        return reviews
    except Exception as e:
        print(f"Ошибка при вводе отзывов: {e}")
        return []

# Основная функция
def main():
    # Настраиваем базу данных
    setup_database()
    
    while True:
        print("\n=== МЕНЮ ===")
        print("1. Собрать отзывы с Perekrestok.ru автоматически")
        print("2. Ввести отзывы вручную")
        print("3. Просмотреть все отзывы")
        print("4. Выход")
        
        choice = input("\nВыберите действие (1-4): ")
        
        if choice == "1":
            product_url = input("Введите URL страницы товара (Enter для примера): ")
            if not product_url:
                product_url = "https://www.perekrestok.ru/cat/120/p/kefir-ekoniva-3-2-1kg-3922310"
            
            max_pages = 3
            try:
                pages_input = input("Сколько страниц отзывов собрать (Enter для 3): ")
                if pages_input:
                    max_pages = int(pages_input)
            except ValueError:
                print("Используется значение по умолчанию: 3 страницы")
            
            reviews = collect_perekrestok_reviews(product_url, max_pages=max_pages)
            
            if reviews:
                print(f"Собрано {len(reviews)} отзывов")
                save_reviews_to_db(reviews)
            else:
                print("Отзывы не собраны.")
                
        elif choice == "2":
            reviews = manual_input_reviews()
            if reviews:
                save_reviews_to_db(reviews)
                
        elif choice == "3":
            view_reviews()
            
        elif choice == "4":
            print("Программа завершена.")
            break
            
        else:
            print("Неверный ввод. Пожалуйста, выберите 1, 2, 3 или 4.")

if __name__ == "__main__":
    main() 
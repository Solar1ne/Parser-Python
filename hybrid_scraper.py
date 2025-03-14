import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import sqlite3
import random
import time
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

# Глобальные настройки
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
]

# Настройка базы данных
def setup_database():
    """Создает базу данных и таблицу, если они не существуют."""
    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            product_name TEXT,
            comment TEXT,
            rating INTEGER,
            created_at TEXT,
            collected_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    logging.info("База данных готова к использованию.")

# Функция для получения отзывов с помощью прямых HTTP-запросов
def get_reviews_with_requests(url, max_pages=3):
    """Пытается получить отзывы с помощью HTTP-запросов с продвинутыми заголовками."""
    all_reviews = []
    product_name = "Неизвестный продукт"
    
    # Расширенные HTTP заголовки для имитации браузера
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.perekrestok.ru/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    # Сначала посещаем главную страницу для получения cookies
    try:
        logging.info("Посещение главной страницы для получения cookies...")
        session = requests.Session()
        main_response = session.get('https://www.perekrestok.ru/', headers=headers, timeout=10)
        
        if main_response.status_code != 200:
            logging.warning(f"Не удалось получить доступ к главной странице. Код статуса: {main_response.status_code}")
            return [], product_name
        
        # Добавляем небольшую паузу
        time.sleep(random.uniform(2, 4))
        
        # Теперь пробуем получить страницу с отзывами
        logging.info(f"Запрос страницы отзывов: {url}")
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logging.warning(f"Не удалось получить страницу отзывов. Код статуса: {response.status_code}")
            return [], product_name
        
        # Сохраняем страницу для анализа
        with open('perekrestok_page_requests.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logging.info("Сохранена страница в perekrestok_page_requests.html")
        
        # Парсим страницу
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Пытаемся получить название продукта
        try:
            product_title = soup.find('h1')
            if product_title:
                product_name = product_title.text.strip()
                logging.info(f"Название продукта: {product_name}")
        except Exception as e:
            logging.warning(f"Не удалось получить название продукта: {e}")
        
        # Проверяем на наличие блокировки
        if "captcha" in response.text.lower() or "робот" in response.text.lower() or "403" in response.text:
            logging.warning("Обнаружена защита от ботов в ответе HTTP-запроса")
            return [], product_name
        
        # Ищем отзывы
        reviews = []
        
        # Ищем отзывы с использованием различных селекторов
        review_elements = soup.select('div.review p, p.review-text, .reviewText, .comment-text')
        
        if not review_elements:
            logging.warning("Не удалось найти отзывы с помощью стандартных селекторов")
            return [], product_name
        
        for review_elem in review_elements:
            try:
                review_text = review_elem.text.strip()
                if not review_text:
                    continue
                
                # Ищем рейтинг и дату в родительских элементах
                rating = 5  # По умолчанию
                date = "Неизвестная дата"
                
                # Поднимаемся по дереву DOM для поиска рейтинга и даты
                parent = review_elem.parent
                for _ in range(3):  # Проверяем до 3 уровней вверх
                    if not parent:
                        break
                    
                    # Ищем рейтинг
                    rating_elem = parent.select_one('.rating, .stars, [class*="rating"], [class*="star"]')
                    if rating_elem:
                        try:
                            rating_text = rating_elem.text.strip()
                            if rating_text and rating_text[0].isdigit():
                                rating = int(float(rating_text.replace(',', '.')))
                        except:
                            # Считаем количество активных звезд
                            active_stars = parent.select('.active, [class*="active"]')
                            if active_stars:
                                rating = len(active_stars)
                                if rating > 5:
                                    rating = 5
                    
                    # Ищем дату
                    date_elem = parent.select_one('.date, [class*="date"]')
                    if date_elem:
                        date = date_elem.text.strip()
                    else:
                        # Ищем по формату даты в тексте
                        parent_text = parent.text
                        date_match = re.search(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}', parent_text)
                        if date_match:
                            date = date_match.group(0)
                    
                    parent = parent.parent
                
                # Создаем запись отзыва
                review_data = {
                    "platform": "Perekrestok.ru",
                    "product_name": product_name,
                    "comment": review_text,
                    "rating": rating,
                    "created_at": date,
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                reviews.append(review_data)
                logging.info(f"Собран отзыв: {review_text[:50]}...")
                
            except Exception as e:
                logging.warning(f"Ошибка при обработке отзыва: {e}")
        
        all_reviews.extend(reviews)
        logging.info(f"Собрано {len(reviews)} отзывов с помощью HTTP-запросов")
        
        # Если мы собрали хотя бы один отзыв, пытаемся найти следующие страницы
        if reviews and max_pages > 1:
            # Ищем ссылки на следующие страницы (реализация зависит от структуры сайта)
            # Этот код нужно будет доработать в зависимости от того, как организована пагинация
            pass
        
        return all_reviews, product_name
        
    except Exception as e:
        logging.error(f"Ошибка при выполнении HTTP-запросов: {e}")
        return [], product_name

# Функция для получения отзывов с помощью Selenium
def get_reviews_with_selenium(url, max_pages=1):
    """Пытается получить отзывы с помощью Selenium с минимальной конфигурацией."""
    all_reviews = []
    product_name = "Неизвестный продукт"
    driver = None
    
    try:
        logging.info("Инициализация Selenium...")
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
        
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1366, 768)
        
        # Маскируем WebDriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Посещаем главную страницу
        logging.info("Посещение главной страницы...")
        driver.get("https://www.perekrestok.ru/")
        time.sleep(random.uniform(3, 5))
        
        # Переходим на страницу с отзывами
        logging.info(f"Переход на страницу отзывов: {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        # Делаем скриншот
        screenshot_path = "perekrestok_selenium_screenshot.png"
        driver.save_screenshot(screenshot_path)
        logging.info(f"Сохранен скриншот в {screenshot_path}")
        
        # Сохраняем HTML для анализа
        with open("perekrestok_page_selenium.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logging.info("Сохранен HTML страницы в perekrestok_page_selenium.html")
        
        # Проверяем на блокировку
        if any(term in driver.page_source.lower() for term in ["captcha", "робот", "403", "forbidden"]):
            logging.warning("Обнаружена защита от ботов при использовании Selenium")
            return [], product_name
        
        # Получаем название продукта
        try:
            product_element = driver.find_element(By.TAG_NAME, "h1")
            product_name = product_element.text.strip()
            logging.info(f"Название продукта: {product_name}")
        except Exception as e:
            logging.warning(f"Не удалось получить название продукта: {e}")
        
        # Ищем отзывы с использованием разных селекторов
        selectors = [
            # XPaths
            "/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div[1]/div[2]/div[2]/p",
            "/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div/div[2]/div[2]/p",
            "//div[contains(@class, 'review')]/p",
            "//p[contains(@class, 'text')]",
            "//div[contains(@class, 'review')]//p",
            # CSS селекторы
            ".reviewText",
            "p.review-text",
            "div.review p",
            ".reviewsContent p"
        ]
        
        reviews = []
        for selector in selectors:
            try:
                if selector.startswith("//") or selector.startswith("/html"):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    logging.info(f"Найдено {len(elements)} отзывов по селектору: {selector}")
                    
                    for element in elements:
                        try:
                            review_text = element.text.strip()
                            if not review_text:
                                continue
                            
                            # Получаем родительский элемент для поиска рейтинга и даты
                            try:
                                parent_element = element.find_element(By.XPATH, "./..")
                                parent_html = parent_element.get_attribute("outerHTML")
                            except:
                                parent_element = element
                                parent_html = ""
                            
                            # Ищем рейтинг
                            rating = 5  # По умолчанию
                            try:
                                rating_elements = parent_element.find_elements(By.XPATH, ".//div[contains(@class, 'rating') or contains(@class, 'star')]")
                                if rating_elements:
                                    rating_text = rating_elements[0].text.strip()
                                    if rating_text and rating_text[0].isdigit():
                                        rating = int(float(rating_text.replace(',', '.')))
                            except:
                                pass
                            
                            # Ищем дату
                            date = "Неизвестная дата"
                            try:
                                date_elements = parent_element.find_elements(By.XPATH, ".//div[contains(@class, 'date')]")
                                if date_elements:
                                    date = date_elements[0].text.strip()
                            except:
                                # Ищем дату по формату
                                if parent_html:
                                    date_match = re.search(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}', parent_html)
                                    if date_match:
                                        date = date_match.group(0)
                            
                            # Создаем запись отзыва
                            review_data = {
                                "platform": "Perekrestok.ru",
                                "product_name": product_name,
                                "comment": review_text,
                                "rating": rating,
                                "created_at": date,
                                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            reviews.append(review_data)
                            logging.info(f"Собран отзыв: {review_text[:50]}...")
                            
                        except Exception as e:
                            logging.warning(f"Ошибка при обработке отзыва: {e}")
                    
                    # Если нашли отзывы по этому селектору, прекращаем поиск
                    if reviews:
                        break
            except Exception as e:
                logging.warning(f"Ошибка при использовании селектора {selector}: {e}")
        
        all_reviews.extend(reviews)
        logging.info(f"Собрано {len(reviews)} отзывов с помощью Selenium")
        
        return all_reviews, product_name
        
    except Exception as e:
        logging.error(f"Ошибка при использовании Selenium: {e}")
        return [], product_name
    
    finally:
        if driver:
            close_browser = input("Закрыть браузер? (y/n): ").lower() == 'y'
            if close_browser:
                driver.quit()
                logging.info("Браузер закрыт")
            else:
                logging.info("Браузер оставлен открытым")

# Функция для разбора HTML-файла
def parse_html_file(file_path, product_name="Неизвестный продукт"):
    """Парсит сохраненный HTML-файл для извлечения отзывов."""
    if not os.path.exists(file_path):
        logging.error(f"Файл {file_path} не существует")
        return [], product_name
    
    try:
        logging.info(f"Парсинг HTML-файла: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Пытаемся получить название продукта
        try:
            title_element = soup.find('h1')
            if title_element:
                extracted_product_name = title_element.text.strip()
                if extracted_product_name and "forbidden" not in extracted_product_name.lower():
                    product_name = extracted_product_name
                    logging.info(f"Название продукта из HTML: {product_name}")
        except Exception as e:
            logging.warning(f"Не удалось извлечь название продукта из HTML: {e}")
        
        # Ищем отзывы с помощью различных селекторов
        selectors = [
            'div.review p', 'p.review-text', '.reviewText', '.comment-text',
            '.review-content p', '.comments-item__text', '[class*="review"] p'
        ]
        
        reviews = []
        for selector in selectors:
            review_elements = soup.select(selector)
            if review_elements:
                logging.info(f"Найдено {len(review_elements)} отзывов по селектору: {selector}")
                
                for review_elem in review_elements:
                    try:
                        review_text = review_elem.text.strip()
                        if not review_text:
                            continue
                        
                        # Ищем рейтинг и дату в родительских элементах
                        rating = 5  # По умолчанию
                        date = "Неизвестная дата"
                        
                        # Поднимаемся по дереву DOM для поиска рейтинга и даты
                        parent = review_elem.parent
                        for _ in range(3):  # Проверяем до 3 уровней вверх
                            if not parent:
                                break
                            
                            # Ищем рейтинг
                            rating_elem = parent.select_one('.rating, .stars, [class*="rating"], [class*="star"]')
                            if rating_elem:
                                try:
                                    rating_text = rating_elem.text.strip()
                                    if rating_text and rating_text[0].isdigit():
                                        rating = int(float(rating_text.replace(',', '.')))
                                except:
                                    # Считаем количество активных звезд
                                    active_stars = parent.select('.active, [class*="active"]')
                                    if active_stars:
                                        rating = len(active_stars)
                                        if rating > 5:
                                            rating = 5
                            
                            # Ищем дату
                            date_elem = parent.select_one('.date, [class*="date"]')
                            if date_elem:
                                date = date_elem.text.strip()
                            else:
                                # Ищем по формату даты в тексте
                                parent_text = parent.text
                                date_match = re.search(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}', parent_text)
                                if date_match:
                                    date = date_match.group(0)
                            
                            parent = parent.parent
                        
                        # Создаем запись отзыва
                        review_data = {
                            "platform": "Perekrestok.ru",
                            "product_name": product_name,
                            "comment": review_text,
                            "rating": rating,
                            "created_at": date,
                            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        reviews.append(review_data)
                        logging.info(f"Собран отзыв из HTML: {review_text[:50]}...")
                        
                    except Exception as e:
                        logging.warning(f"Ошибка при обработке отзыва из HTML: {e}")
                
                # Если нашли отзывы по этому селектору, прекращаем поиск
                if reviews:
                    break
        
        logging.info(f"Извлечено {len(reviews)} отзывов из HTML-файла")
        return reviews, product_name
        
    except Exception as e:
        logging.error(f"Ошибка при парсинге HTML-файла: {e}")
        return [], product_name

# Функция для ручного ввода отзывов
def manual_input_reviews():
    """Позволяет вручную ввести отзывы."""
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
                "created_at": date,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            reviews.append(review)
            print(f"Отзыв добавлен. Всего: {len(reviews)}")
        
        return reviews
    except Exception as e:
        logging.error(f"Ошибка при ручном вводе отзывов: {e}")
        return []

# Функция для сохранения отзывов в базу данных
def save_reviews_to_db(reviews):
    """Сохраняет отзывы в базу данных."""
    if not reviews:
        logging.warning("Нет отзывов для сохранения")
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
                r["created_at"],
                r.get("collected_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ))
        
        # Вставляем отзывы в базу данных
        cursor.executemany(
            "INSERT INTO reviews (platform, product_name, comment, rating, created_at, collected_at) VALUES (?, ?, ?, ?, ?, ?)",
            reviews_data
        )
        
        conn.commit()
        saved_count = cursor.rowcount
        conn.close()
        
        logging.info(f"Сохранено {saved_count} отзывов в базу данных")
        return saved_count
    
    except Exception as e:
        logging.error(f"Ошибка при сохранении отзывов в базу данных: {e}")
        return 0

# Функция для просмотра сохраненных отзывов
def view_reviews():
    """Просматривает сохраненные отзывы."""
    try:
        conn = sqlite3.connect("reviews.db")
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица reviews
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
        table_exists = cursor.fetchone()
        if not table_exists:
            logging.warning("Таблица 'reviews' не существует в базе данных.")
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
        print("\n" + "-" * 110)
        header = f"{column_names[0]:<4} | {column_names[1]:<15} | {column_names[2]:<20} | {column_names[3]:<40} | {column_names[4]:<6} | {column_names[5]:<15}"
        print(header)
        print("-" * 110)
        
        # Выводим данные
        for row in rows:
            # Обрезаем слишком длинные поля для лучшего отображения
            product_name = str(row[2])[:20] if len(str(row[2])) > 20 else row[2]
            comment = str(row[3])[:40] if len(str(row[3])) > 40 else row[3]
            
            row_text = f"{row[0]:<4} | {row[1]:<15} | {product_name:<20} | {comment:<40} | {row[4]:<6} | {row[5]:<15}"
            print(row_text)
        
        print("-" * 110)
        print(f"Всего отзывов: {len(rows)}")
        
    except Exception as e:
        logging.error(f"Ошибка при просмотре базы данных: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# Основная функция
def main():
    # Настраиваем базу данных
    setup_database()
    
    while True:
        print("\n=== МЕНЮ ===")
        print("1. Собрать отзывы автоматически (гибридный метод)")
        print("2. Ввести отзывы вручную")
        print("3. Разобрать HTML-файл с отзывами")
        print("4. Просмотреть все отзывы")
        print("5. Выход")
        
        choice = input("\nВыберите действие (1-5): ")
        
        if choice == "1":
            product_url = input("Введите URL страницы товара (Enter для примера): ")
            if not product_url:
                product_url = "https://www.perekrestok.ru/cat/120/p/kefir-ekoniva-3-2-1kg-3922310/reviews"
            
            print("\nВыбор метода сбора:")
            print("1. HTTP запросы")
            print("2. Selenium")
            print("3. Оба метода последовательно")
            
            method_choice = input("Выберите метод (1-3): ")
            
            all_reviews = []
            product_name = "Неизвестный продукт"
            
            if method_choice == "1" or method_choice == "3":
                # HTTP запросы
                print("\nИспользуем метод HTTP-запросов...")
                http_reviews, product_name_http = get_reviews_with_requests(product_url)
                
                if http_reviews:
                    all_reviews.extend(http_reviews)
                    product_name = product_name_http
                    print(f"Собрано {len(http_reviews)} отзывов с помощью HTTP-запросов")
                else:
                    print("Не удалось собрать отзывы с помощью HTTP-запросов")
            
            if method_choice == "2" or (method_choice == "3" and not all_reviews):
                # Selenium
                print("\nИспользуем метод Selenium...")
                selenium_reviews, product_name_selenium = get_reviews_with_selenium(product_url)
                
                if selenium_reviews:
                    all_reviews.extend(selenium_reviews)
                    if product_name == "Неизвестный продукт":
                        product_name = product_name_selenium
                    print(f"Собрано {len(selenium_reviews)} отзывов с помощью Selenium")
                else:
                    print("Не удалось собрать отзывы с помощью Selenium")
            
            # Сохраняем собранные отзывы
            if all_reviews:
                save_reviews_to_db(all_reviews)
            else:
                print("Отзывы не собраны автоматически.")
                print("Вы можете попробовать собрать отзывы вручную или разобрать HTML-файл.")
                
        elif choice == "2":
            reviews = manual_input_reviews()
            if reviews:
                save_reviews_to_db(reviews)
                
        elif choice == "3":
            file_path = input("Введите путь к HTML-файлу с отзывами: ")
            product_name = input("Введите название продукта (Enter для автоопределения): ")
            
            if not product_name:
                product_name = "Неизвестный продукт"
            
            reviews, detected_name = parse_html_file(file_path, product_name)
            
            if reviews:
                if detected_name != "Неизвестный продукт" and product_name == "Неизвестный продукт":
                    product_name = detected_name
                
                print(f"Извлечено {len(reviews)} отзывов из HTML-файла")
                save_reviews_to_db(reviews)
            else:
                print("Не удалось извлечь отзывы из HTML-файла")
                
        elif choice == "4":
            view_reviews()
            
        elif choice == "5":
            print("Программа завершена.")
            break
            
        else:
            print("Неверный ввод. Пожалуйста, выберите число от 1 до 5.")

if __name__ == "__main__":
    main() 
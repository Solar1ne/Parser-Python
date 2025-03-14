from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import json
import sqlite3
import re
import os

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

# Настройка Selenium для обхода защиты от ботов
def setup_selenium():
    options = Options()
    # Важно: НЕ используем headless режим, чтобы не вызывать подозрений
    
    # Stealth настройки для имитации реального браузера
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Дополнительные настройки
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    
    # Случайный user-agent
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
    ]
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    # Инициализация драйвера
    driver = webdriver.Chrome(options=options)
    
    # Установка размера окна как у обычного пользователя
    driver.set_window_size(1366, 768)
    
    # Маскировка Selenium WebDriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

# Функция имитации человеческого поведения
def human_like_behavior(driver):
    # Случайные паузы между действиями
    time.sleep(random.uniform(1, 3))
    
    # Случайные движения мыши (имитация через JavaScript)
    for _ in range(random.randint(3, 7)):
        x = random.randint(100, 700)
        y = random.randint(100, 500)
        driver.execute_script(f"window.scrollTo({x}, {y})")
        time.sleep(random.uniform(0.3, 0.7))
    
    # Прокрутка страницы как человек (с разной скоростью и паузами)
    total_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(5):
        scroll_height = total_height * (i + 1) / 5
        driver.execute_script(f"window.scrollTo(0, {scroll_height});")
        time.sleep(random.uniform(0.7, 1.5))
    
    # Возврат наверх (как это делают люди)
    for i in range(3):
        driver.execute_script(f"window.scrollTo(0, {total_height - (i+1)*total_height/3});")
        time.sleep(random.uniform(0.5, 1))
    
    # Финальная пауза
    time.sleep(random.uniform(1, 2))

# Функция для ожидания пользовательского ввода (для ручного решения CAPTCHA)
def wait_for_user_action(message="Выполните необходимые действия (например, решите CAPTCHA) и нажмите Enter для продолжения"):
    input(message)

# Функция для получения отзывов с Perekrestok
def get_perekrestok_reviews(url, max_pages=3):
    driver = setup_selenium()
    all_reviews = []
    
    try:
        # Сначала посещаем главную страницу для установки cookies
        print("Посещаем главную страницу...")
        driver.get("https://www.perekrestok.ru/")
        human_like_behavior(driver)
        
        # Затем переходим на страницу с отзывами
        print(f"Переходим на страницу отзывов: {url}")
        driver.get(url)
        
        # Ожидаем загрузки страницы
        time.sleep(random.uniform(3, 5))
        
        # Сохраняем скриншот для проверки
        driver.save_screenshot("perekrestok_reviews_page.png")
        print("Сохранен скриншот страницы в perekrestok_reviews_page.png")
        
        # Проверяем наличие CAPTCHA или блокировки
        page_text = driver.page_source.lower()
        if "captcha" in page_text or "робот" in page_text or "403" in page_text:
            print("Обнаружена CAPTCHA или блокировка. Пожалуйста, решите её вручную...")
            # Даем пользователю возможность решить CAPTCHA
            wait_for_user_action()
        
        # Получаем название продукта
        try:
            product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
            print(f"Название продукта: {product_name}")
        except NoSuchElementException:
            product_name = "Кефир Эконива 3.2%"
            print(f"Не удалось найти название продукта, используется значение по умолчанию: {product_name}")
        
        # Имитируем поведение человека перед сбором отзывов
        human_like_behavior(driver)
        
        # Обрабатываем заданное количество страниц с отзывами
        for page in range(1, max_pages + 1):
            print(f"Обработка страницы отзывов {page}...")
            
            # Попытка найти отзывы по указанному XPath
            try:
                # Используем точный XPath, предоставленный пользователем
                review_elements = driver.find_elements(By.XPATH, '/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div[1]/div[2]/div[2]/p')
                
                if not review_elements:
                    # Пробуем альтернативные XPath
                    alternative_xpaths = [
                        '/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div/div[2]/div[2]/p',
                        '//div[contains(@class, "review")]/p',
                        '//p[contains(@class, "text")]',
                        '//div[contains(@class, "review")]//p'
                    ]
                    
                    for xpath in alternative_xpaths:
                        review_elements = driver.find_elements(By.XPATH, xpath)
                        if review_elements:
                            print(f"Найдены отзывы по XPath: {xpath}, количество: {len(review_elements)}")
                            break
                else:
                    print(f"Найдены отзывы по указанному XPath, количество: {len(review_elements)}")
                
                # Если не удалось найти отзывы по XPath, пробуем CSS селекторы
                if not review_elements:
                    css_selectors = [
                        '.reviewText',
                        'p.review-text',
                        'div.review p',
                        '.reviewsContent p'
                    ]
                    
                    for selector in css_selectors:
                        review_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if review_elements:
                            print(f"Найдены отзывы по селектору: {selector}, количество: {len(review_elements)}")
                            break
                
                # Если всё еще не нашли отзывы, позволяем пользователю указать элементы вручную
                if not review_elements:
                    print("Не удалось найти отзывы автоматически.")
                    print("Осмотрите страницу и решите, содержит ли она отзывы.")
                    wait_for_user_action("Нажмите Enter, чтобы продолжить, или введите 'q' для выхода: ")
                    user_input = input()
                    if user_input.lower() == 'q':
                        break
                
                # Обрабатываем найденные отзывы
                page_reviews = []
                
                for i, element in enumerate(review_elements):
                    try:
                        # Получаем текст отзыва
                        review_text = element.text.strip()
                        if not review_text:
                            continue
                        
                        print(f"Отзыв {i+1}: {review_text[:50]}...")
                        
                        # Пытаемся найти рейтинг и дату, поднимаясь вверх по DOM
                        rating = 5  # По умолчанию
                        date = "Неизвестная дата"
                        
                        # Находим родительский элемент отзыва
                        parent_element = element.find_element(By.XPATH, './ancestor::div[contains(@class, "review") or contains(@class, "comment")]')
                        
                        # Ищем рейтинг
                        try:
                            # Проверяем на наличие звезд или числа
                            rating_element = parent_element.find_element(By.XPATH, './/div[contains(@class, "rating") or contains(@class, "stars")]')
                            
                            # Если нашли тег с рейтингом, пробуем извлечь число
                            rating_text = rating_element.text.strip()
                            if rating_text and rating_text[0].isdigit():
                                rating = int(float(rating_text.replace(',', '.')))
                            else:
                                # Если не нашли числа, считаем звезды/иконки
                                stars = parent_element.find_elements(By.XPATH, './/div[contains(@class, "active")] | .//img[contains(@src, "star")] | .//svg[contains(@class, "star")]')
                                if stars:
                                    rating = len(stars)
                        except NoSuchElementException:
                            pass
                        
                        # Ищем дату
                        try:
                            date_element = parent_element.find_element(By.XPATH, './/div[contains(@class, "date")] | .//span[contains(@class, "date")]')
                            date = date_element.text.strip()
                        except NoSuchElementException:
                            # Если не нашли по классу, ищем по формату даты в тексте
                            parent_text = parent_element.text
                            date_match = re.search(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}', parent_text)
                            if date_match:
                                date = date_match.group(0)
                        
                        # Создаем запись отзыва
                        review_data = {
                            "platform": "Perekrestok.ru",
                            "product_name": product_name,
                            "comment": review_text,
                            "rating": rating,
                            "created_at": date
                        }
                        
                        page_reviews.append(review_data)
                        
                    except Exception as e:
                        print(f"Ошибка при обработке отзыва {i+1}: {e}")
                
                print(f"Извлечено {len(page_reviews)} отзывов на странице {page}")
                all_reviews.extend(page_reviews)
                
                # Проверяем наличие следующей страницы
                if page < max_pages:
                    has_next_page = False
                    
                    # Пробуем найти кнопку "Следующая страница"
                    next_page_selectors = [
                        '//button[contains(text(), "Следующая")]',
                        '//a[contains(text(), "Следующая")]',
                        '//button[contains(@class, "next")]',
                        '//a[contains(@class, "next")]'
                    ]
                    
                    for selector in next_page_selectors:
                        try:
                            next_button = driver.find_element(By.XPATH, selector)
                            if next_button.is_displayed() and next_button.is_enabled():
                                # Имитируем человеческую паузу перед кликом
                                time.sleep(random.uniform(1, 2))
                                next_button.click()
                                print("Переход на следующую страницу...")
                                has_next_page = True
                                time.sleep(random.uniform(3, 5))  # Ждем загрузки следующей страницы
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not has_next_page:
                        print("Кнопка следующей страницы не найдена или недоступна")
                        break
                
            except Exception as e:
                print(f"Ошибка при обработке страницы {page}: {e}")
                break
        
        print(f"Всего собрано {len(all_reviews)} отзывов")
        return all_reviews
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return []
        
    finally:
        # Спрашиваем пользователя перед закрытием браузера
        close_browser = input("Закрыть браузер? (y/n): ").lower() == 'y'
        if close_browser:
            driver.quit()
            print("Браузер закрыт")
        else:
            print("Браузер оставлен открытым")

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
        print("1. Собрать отзывы автоматически (с Selenium)")
        print("2. Ввести отзывы вручную")
        print("3. Просмотреть все отзывы")
        print("4. Выход")
        
        choice = input("\nВыберите действие (1-4): ")
        
        if choice == "1":
            product_url = input("Введите URL страницы товара (Enter для примера): ")
            if not product_url:
                product_url = "https://www.perekrestok.ru/cat/120/p/kefir-ekoniva-3-2-1kg-3922310/reviews"
            
            max_pages = 3
            try:
                pages_input = input("Сколько страниц отзывов собрать (Enter для 3): ")
                if pages_input:
                    max_pages = int(pages_input)
            except ValueError:
                print("Используется значение по умолчанию: 3 страницы")
            
            reviews = get_perekrestok_reviews(product_url, max_pages=max_pages)
            
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
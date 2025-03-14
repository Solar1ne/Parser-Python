from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import random
import json
import sqlite3
import re
import os
import pickle
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
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0'
]

# Функции для работы с базой данных
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

def save_cookies(driver, path):
    """Сохраняет cookies браузера в файл."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, 'wb') as file:
        pickle.dump(driver.get_cookies(), file)
    logging.info(f"Cookies сохранены в {path}")

def load_cookies(driver, path):
    """Загружает cookies из файла в браузер."""
    if not os.path.exists(path):
        logging.warning(f"Файл cookies {path} не существует")
        return False
    
    with open(path, 'rb') as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            # Иногда возникает ошибка с неверными данными cookie
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logging.warning(f"Не удалось добавить cookie: {e}")
    
    logging.info(f"Cookies загружены из {path}")
    return True

def setup_selenium():
    """Настраивает браузер Selenium с улучшенными настройками против обнаружения."""
    options = Options()
    
    # Расширенные настройки для маскировки автоматизации
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Дополнительные настройки приватности и безопасности
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    
    # Случайный user-agent
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"--user-agent={user_agent}")
    logging.info(f"Используется User-Agent: {user_agent}")
    
    # Разрешение экрана как у обычного десктопа
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    
    # Размер окна браузера
    driver.set_window_size(1366, 768)
    
    # Расширенная маскировка WebDriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() { return [1, 2, 3, 4, 5]; }})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: function() { return ['ru-RU', 'ru', 'en-US', 'en']; }})")
    
    # Установка часового пояса для Москвы
    driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {'timezoneId': 'Europe/Moscow'})
    
    # Устанавливаем языковые настройки
    driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': {'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'}})
    
    return driver

def human_like_interaction(driver):
    """Имитирует поведение человека при просмотре страницы."""
    logging.info("Имитация человеческого поведения...")
    
    # Начальная пауза после загрузки страницы
    time.sleep(random.uniform(2, 4))
    
    # Случайное число движений мыши
    for _ in range(random.randint(3, 8)):
        x = random.randint(100, 1200)
        y = random.randint(100, 600)
        driver.execute_script(f"window.scrollTo({x}, {y})")
        time.sleep(random.uniform(0.3, 1.2))
    
    # Естественная прокрутка страницы
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    
    # Прокрутка вниз постепенно
    current_position = 0
    while current_position < total_height:
        # Двигаемся вниз с переменной скоростью
        scroll_step = random.randint(100, 300)
        current_position += scroll_step
        
        # Иногда делаем небольшую паузу во время прокрутки
        if random.random() < 0.2:
            time.sleep(random.uniform(0.5, 1.5))
            
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(random.uniform(0.8, 2.0))
    
    # Случайные задержки взгляда на определенных частях страницы
    for _ in range(random.randint(2, 4)):
        pause_position = random.randint(viewport_height, total_height - viewport_height)
        driver.execute_script(f"window.scrollTo(0, {pause_position});")
        time.sleep(random.uniform(1.5, 3.5))
    
    # Возврат в случайную позицию
    random_position = random.randint(0, int(total_height * 0.7))
    driver.execute_script(f"window.scrollTo(0, {random_position});")
    time.sleep(random.uniform(1, 2))
    
    # Симуляция клика по случайному элементу (не всегда)
    if random.random() < 0.3:
        try:
            # Пытаемся найти случайные некритичные элементы для клика
            clickable_elements = driver.find_elements(By.CSS_SELECTOR, "a:not([href*='login']):not([href*='register']), button:not([type='submit'])")
            if clickable_elements:
                random_element = random.choice(clickable_elements)
                # Проверяем, безопасен ли клик (не ведет на другую страницу)
                href = random_element.get_attribute("href")
                if href is None or "perekrestok.ru" in href:
                    logging.info("Имитация случайного клика...")
                    time.sleep(random.uniform(0.5, 1.5))
                    driver.execute_script("arguments[0].click();", random_element)
                    time.sleep(random.uniform(1, 3))
                    # Возврат назад, если нужно
                    if driver.current_url != "https://www.perekrestok.ru/":
                        driver.back()
        except Exception as e:
            logging.warning(f"Ошибка при имитации случайного клика: {e}")
    
    # Финальная пауза
    time.sleep(random.uniform(1, 3))
    logging.info("Имитация человеческого поведения завершена")

def prepare_session(driver):
    """Подготавливает сессию с установкой cookies и посещением разных страниц."""
    cookies_path = "cookies/perekrestok_cookies.pkl"
    
    # Сначала посещаем главную страницу
    logging.info("Переход на главную страницу...")
    driver.get("https://www.perekrestok.ru/")
    time.sleep(random.uniform(3, 5))
    
    # Пытаемся загрузить сохраненные cookies
    cookies_loaded = load_cookies(driver, cookies_path)
    
    # Если cookies загружены, обновляем страницу
    if cookies_loaded:
        driver.refresh()
        time.sleep(random.uniform(2, 4))
    
    # Имитация человеческого поведения
    human_like_interaction(driver)
    
    # Посещаем несколько случайных разделов
    categories = [
        "https://www.perekrestok.ru/cat/271/moloko-syr-ajca",
        "https://www.perekrestok.ru/cat/153/hleb-vypecka",
        "https://www.perekrestok.ru/cat/111/sladosti-konfety-shokolad"
    ]
    
    # Посещаем 1-2 случайные категории
    for _ in range(random.randint(1, 2)):
        category_url = random.choice(categories)
        logging.info(f"Переход в категорию: {category_url}")
        driver.get(category_url)
        time.sleep(random.uniform(3, 6))
        human_like_interaction(driver)
    
    # Сохраняем cookies после всех действий
    save_cookies(driver, cookies_path)
    
    logging.info("Сессия подготовлена")

def get_perekrestok_reviews(url, max_pages=3, max_retries=3):
    """Получает отзывы с Perekrestok.ru с улучшенными методами обхода защиты."""
    driver = setup_selenium()
    all_reviews = []
    
    try:
        # Подготовка сессии
        prepare_session(driver)
        
        # Переход на страницу товара
        logging.info(f"Переход на страницу отзывов: {url}")
        
        # Перед переходом на страницу товара, меняем реферер и пользовательское поведение
        driver.execute_script(f'window.location.href = "{url}";')
        time.sleep(random.uniform(4, 6))
        
        # Сохраняем скриншот для анализа
        screenshot_path = f"screenshots/perekrestok_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        os.makedirs("screenshots", exist_ok=True)
        driver.save_screenshot(screenshot_path)
        logging.info(f"Сохранен скриншот страницы в {screenshot_path}")
        
        # Проверяем на наличие блокировки или CAPTCHA
        page_source = driver.page_source.lower()
        if "captcha" in page_source or "робот" in page_source or "forbidden" in page_source or "403" in page_source:
            logging.warning("Обнаружена защита от ботов. Пробуем обойти...")
            
            # Попытки повторных входов с разными параметрами
            for retry in range(max_retries):
                logging.info(f"Попытка {retry + 1} из {max_retries}...")
                
                # Пробуем зайти через другую категорию
                driver.get("https://www.perekrestok.ru/")
                time.sleep(random.uniform(2, 4))
                
                # Имитируем поиск товара
                try:
                    search_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Поиск'], input[type='search']"))
                    )
                    
                    # Вводим текст медленно, как человек
                    product_name = "Кефир Эконива"
                    for char in product_name:
                        search_box.send_keys(char)
                        time.sleep(random.uniform(0.1, 0.3))
                    
                    time.sleep(random.uniform(0.5, 1))
                    search_box.send_keys(Keys.ENTER)
                    time.sleep(random.uniform(3, 5))
                    
                    # Ищем ссылки на товары
                    product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/cat/']")
                    if product_links:
                        for link in product_links:
                            if "Кефир" in link.text:
                                product_url = link.get_attribute("href")
                                logging.info(f"Найден товар: {product_url}")
                                # Кликаем на товар
                                driver.execute_script("arguments[0].click();", link)
                                time.sleep(random.uniform(3, 5))
                                
                                # Ищем кнопку/ссылку на отзывы
                                try:
                                    reviews_links = driver.find_elements(By.XPATH, 
                                                                        "//a[contains(text(), 'отзыв') or contains(., 'Отзыв')] | " +
                                                                        "//button[contains(text(), 'отзыв') or contains(., 'Отзыв')] | " +
                                                                        "//div[contains(text(), 'отзыв') or contains(., 'Отзыв')]")
                                    
                                    if reviews_links:
                                        for rev_link in reviews_links:
                                            if rev_link.is_displayed():
                                                logging.info(f"Найдена ссылка на отзывы: {rev_link.text}")
                                                driver.execute_script("arguments[0].click();", rev_link)
                                                time.sleep(random.uniform(3, 5))
                                                break
                                except Exception as e:
                                    logging.warning(f"Ошибка при поиске ссылки на отзывы: {e}")
                                
                                break
                except Exception as e:
                    logging.warning(f"Ошибка при поиске товара: {e}")
                
                # Проверяем, успешно ли обошли защиту
                if "captcha" not in driver.page_source.lower() and "forbidden" not in driver.page_source.lower():
                    logging.info("Успешно обошли защиту!")
                    break
                
                # Если все попытки исчерпаны
                if retry == max_retries - 1:
                    logging.error("Не удалось обойти защиту. Сохраняем HTML для анализа.")
                    with open("blocked_page.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    return []
        
        # Попытка определить название продукта
        try:
            product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
            logging.info(f"Название продукта: {product_name}")
        except NoSuchElementException:
            product_name = "Кефир Эконива 3.2%"
            logging.warning(f"Не удалось найти название продукта, используется значение по умолчанию: {product_name}")
        
        # Дополнительная имитация человеческого поведения
        human_like_interaction(driver)
        
        # Обрабатываем заданное количество страниц с отзывами
        for page in range(1, max_pages + 1):
            logging.info(f"Обработка страницы отзывов {page}...")
            
            try:
                # Массив всех возможных XPath и CSS селекторов
                selectors = [
                    # XPaths
                    ('/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div[1]/div[2]/div[2]/p', By.XPATH),
                    ('/html/body/div[1]/div/main/div/div[2]/div/div[1]/div[2]/section/div[3]/div/div/div[2]/div[2]/p', By.XPATH),
                    ('//div[contains(@class, "review")]/p', By.XPATH),
                    ('//p[contains(@class, "text")]', By.XPATH),
                    ('//div[contains(@class, "review")]//p', By.XPATH),
                    ('//div[contains(@class, "feedback") or contains(@class, "отзыв")]//p', By.XPATH),
                    # CSS селекторы
                    ('.reviewText', By.CSS_SELECTOR),
                    ('p.review-text', By.CSS_SELECTOR),
                    ('div.review p', By.CSS_SELECTOR),
                    ('.reviewsContent p', By.CSS_SELECTOR),
                    ('.review-content p', By.CSS_SELECTOR),
                    ('.comments-item__text', By.CSS_SELECTOR)
                ]
                
                review_elements = []
                used_selector = None
                
                # Пробуем все селекторы
                for selector, selector_type in selectors:
                    try:
                        elements = driver.find_elements(selector_type, selector)
                        if elements:
                            review_elements = elements
                            used_selector = selector
                            logging.info(f"Найдены отзывы по селектору: {selector}, количество: {len(elements)}")
                            break
                    except Exception as e:
                        logging.warning(f"Ошибка при использовании селектора {selector}: {e}")
                
                # Если нет отзывов, пробуем найти любой текст
                if not review_elements:
                    logging.warning("Не удалось найти отзывы по стандартным селекторам")
                    
                    # Записываем HTML страницы для дальнейшего анализа
                    with open(f"review_page_{page}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    
                    logging.info(f"HTML страницы сохранен в review_page_{page}.html")
                    continue
                
                # Обрабатываем найденные отзывы
                page_reviews = []
                
                for i, element in enumerate(review_elements):
                    try:
                        # Получаем текст отзыва
                        review_text = element.text.strip()
                        if not review_text:
                            continue
                        
                        logging.info(f"Отзыв {i+1}: {review_text[:50]}...")
                        
                        # Ищем рейтинг и дату
                        rating = 5  # По умолчанию
                        date = "Неизвестная дата"
                        
                        # Находим родительский элемент
                        try:
                            # Поднимаемся вверх по DOM дереву до контейнера отзыва
                            parent_element = element
                            for _ in range(5):  # Поднимаемся максимум на 5 уровней вверх
                                parent_element = parent_element.find_element(By.XPATH, "./..")
                                parent_html = parent_element.get_attribute('outerHTML')
                                # Если в родительском элементе есть признаки контейнера отзыва
                                if any(marker in parent_html.lower() for marker in ['review', 'отзыв', 'comment', 'rating', 'star']):
                                    break
                        except:
                            parent_element = element
                        
                        # Ищем рейтинг в родительском элементе
                        try:
                            # Ищем элементы рейтинга
                            rating_selectors = [
                                './/span[contains(@class, "rating") or contains(@class, "star")]',
                                './/div[contains(@class, "rating") or contains(@class, "star")]',
                                './/img[contains(@src, "star")]',
                                './/svg[contains(@class, "star")]'
                            ]
                            
                            for rating_selector in rating_selectors:
                                rating_elements = parent_element.find_elements(By.XPATH, rating_selector)
                                if rating_elements:
                                    # Если есть числовой рейтинг
                                    rating_text = rating_elements[0].text.strip()
                                    if rating_text and rating_text[0].isdigit():
                                        try:
                                            rating = int(float(rating_text.replace(',', '.')))
                                            break
                                        except ValueError:
                                            pass
                                    
                                    # Если нет числового рейтинга, считаем количество активных звезд
                                    active_stars = parent_element.find_elements(By.XPATH, 
                                                                             './/div[contains(@class, "active")] | ' +
                                                                             './/svg[contains(@class, "active")] | ' +
                                                                             './/img[contains(@src, "active")]')
                                    if active_stars:
                                        rating = len(active_stars)
                                        if 1 <= rating <= 5:
                                            break
                        except Exception as e:
                            logging.warning(f"Ошибка при получении рейтинга: {e}")
                        
                        # Ищем дату в родительском элементе
                        try:
                            date_selectors = [
                                './/span[contains(@class, "date")]',
                                './/div[contains(@class, "date")]',
                                './/span[contains(text(), ".20")]',
                                './/div[contains(text(), ".20")]'
                            ]
                            
                            for date_selector in date_selectors:
                                date_elements = parent_element.find_elements(By.XPATH, date_selector)
                                if date_elements:
                                    date = date_elements[0].text.strip()
                                    if date:
                                        break
                            
                            # Если не нашли по селекторам, ищем по регулярному выражению в тексте
                            if date == "Неизвестная дата":
                                parent_text = parent_element.text
                                date_patterns = [
                                    r'\d{1,2}[./]\d{1,2}[./]20\d{2}',
                                    r'\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+20\d{2}'
                                ]
                                
                                for pattern in date_patterns:
                                    date_match = re.search(pattern, parent_text)
                                    if date_match:
                                        date = date_match.group(0)
                                        break
                        except Exception as e:
                            logging.warning(f"Ошибка при получении даты: {e}")
                        
                        # Создаем запись отзыва
                        review_data = {
                            "platform": "Perekrestok.ru",
                            "product_name": product_name,
                            "comment": review_text,
                            "rating": rating,
                            "created_at": date,
                            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        page_reviews.append(review_data)
                        
                    except Exception as e:
                        logging.warning(f"Ошибка при обработке отзыва {i+1}: {e}")
                
                logging.info(f"Извлечено {len(page_reviews)} отзывов на странице {page}")
                all_reviews.extend(page_reviews)
                
                # Проверяем наличие следующей страницы
                if page < max_pages:
                    next_page_found = False
                    
                    # Варианты селекторов для кнопки "Следующая"
                    next_page_selectors = [
                        ('//button[contains(text(), "Следующая") or contains(text(), "След")]', By.XPATH),
                        ('//a[contains(text(), "Следующая") or contains(text(), "След")]', By.XPATH),
                        ('//button[contains(@class, "next")]', By.XPATH),
                        ('//a[contains(@class, "next")]', By.XPATH),
                        ('//li[contains(@class, "next")]/a', By.XPATH),
                        ('.pagination-next', By.CSS_SELECTOR),
                        ('.pagination__arrow--next', By.CSS_SELECTOR)
                    ]
                    
                    for selector, selector_type in next_page_selectors:
                        try:
                            next_buttons = driver.find_elements(selector_type, selector)
                            for next_button in next_buttons:
                                if next_button.is_displayed() and next_button.is_enabled():
                                    # Прокручиваем до кнопки
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                                    time.sleep(random.uniform(0.5, 1.5))
                                    
                                    # Кликаем как человек
                                    logging.info(f"Найдена кнопка следующей страницы: {next_button.text}")
                                    driver.execute_script("arguments[0].click();", next_button)
                                    logging.info("Переход на следующую страницу...")
                                    
                                    # Ждем загрузки страницы
                                    time.sleep(random.uniform(3, 5))
                                    
                                    # Добавляем дополнительное человеческое взаимодействие
                                    human_like_interaction(driver)
                                    
                                    next_page_found = True
                                    break
                            
                            if next_page_found:
                                break
                        except Exception as e:
                            logging.warning(f"Ошибка при поиске кнопки следующей страницы с селектором {selector}: {e}")
                    
                    if not next_page_found:
                        logging.warning("Кнопка следующей страницы не найдена или недоступна")
                        break
                
            except Exception as e:
                logging.error(f"Ошибка при обработке страницы {page}: {e}")
                break
        
        # Сохраняем cookies сессии перед завершением
        save_cookies(driver, "cookies/perekrestok_cookies.pkl")
        
        logging.info(f"Всего собрано {len(all_reviews)} отзывов")
        return all_reviews
        
    except Exception as e:
        logging.error(f"Произошла общая ошибка: {e}")
        return []
        
    finally:
        # Даем пользователю возможность просмотреть браузер перед закрытием
        close_browser = input("Закрыть браузер? (y/n): ").lower() == 'y'
        if close_browser:
            driver.quit()
            logging.info("Браузер закрыт")
        else:
            logging.info("Браузер оставлен открытым")

def save_reviews_to_db(reviews):
    """Сохраняет отзывы в базу данных."""
    if not reviews:
        logging.warning("Нет отзывов для сохранения")
        return 0
    
    try:
        conn = sqlite3.connect("reviews.db")
        cursor = conn.cursor()
        
        # Подготавливаем данные для вставки
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
            logging.info("База данных пуста. Нет сохраненных отзывов.")
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
        logging.error(f"Ошибка при просмотре базы данных: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def main():
    """Основная функция программы."""
    # Настраиваем базу данных
    setup_database()
    
    while True:
        print("\n=== МЕНЮ ===")
        print("1. Собрать отзывы автоматически (с улучшенной защитой от обнаружения)")
        print("2. Просмотреть все отзывы")
        print("3. Выход")
        
        choice = input("\nВыберите действие (1-3): ")
        
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
                logging.warning("Используется значение по умолчанию: 3 страницы")
            
            reviews = get_perekrestok_reviews(product_url, max_pages=max_pages)
            
            if reviews:
                logging.info(f"Собрано {len(reviews)} отзывов")
                save_reviews_to_db(reviews)
            else:
                logging.warning("Отзывы не собраны.")
                
        elif choice == "2":
            view_reviews()
            
        elif choice == "3":
            logging.info("Программа завершена.")
            break
            
        else:
            print("Неверный ввод. Пожалуйста, выберите 1, 2 или 3.")

if __name__ == "__main__":
    main() 
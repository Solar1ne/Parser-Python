from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlite3
import time
import os
import random
import tkinter as tk
from tkinter import simpledialog, messagebox

# Настройка Selenium с возможностью ручного вмешательства
def setup_driver(headless=False):
    print("Настройка браузера с возможностью ручного вмешательства...")
    
    options = webdriver.ChromeOptions()
    
    # Не используем headless режим для возможности ручного вмешательства
    if headless:
        options.add_argument("--headless")
    
    # Настройки для маскировки автоматизации
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Дополнительные настройки
    options.add_argument('--disable-extensions')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    
    # Используем реалистичный user-agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    options.add_argument(f'user-agent={user_agent}')
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Устанавливаем реалистичный размер окна
        driver.set_window_size(1366, 768)
        print("Браузер успешно настроен")
        return driver
    except Exception as e:
        print(f"Ошибка при настройке браузера: {e}")
        raise Exception("Не удалось настроить браузер")

# Функция для ожидания ручного вмешательства (если нужно)
def wait_for_manual_action(message="Пожалуйста, выполните необходимые действия и нажмите OK для продолжения"):
    root = tk.Tk()
    root.withdraw()  # Скрываем основное окно
    messagebox.showinfo("Требуется ручное действие", message)
    root.destroy()

# Функция для имитации поведения человека
def human_like_interaction(driver):
    print("Имитация поведения человека...")
    # Случайная пауза
    time.sleep(random.uniform(2, 4))
    
    # Имитация прокрутки как человек
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(1, 6):  # Меньше итераций для более естественной прокрутки
        # Прокрутка с разной скоростью и на разную глубину
        scroll_amount = random.uniform(0.1, 0.3) * scroll_height  # Случайная часть страницы
        driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
        time.sleep(random.uniform(1, 3))  # Более долгая пауза между прокрутками
    
    # Еще одна прокрутка вниз
    driver.execute_script(f"window.scrollTo(0, {scroll_height * 0.7});")
    time.sleep(random.uniform(2, 4))
    
    # Возвращаемся вверх с остановками
    driver.execute_script(f"window.scrollTo(0, {scroll_height * 0.3});")
    time.sleep(random.uniform(1, 2))
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(random.uniform(1, 3))

# Функция для проверки наличия CAPTCHA или блокировки
def check_for_captcha_or_block(driver):
    # Проверка на наличие признаков блокировки или CAPTCHA
    if "403" in driver.title or "Forbidden" in driver.title or "запрещен" in driver.page_source:
        print("Обнаружена страница с блокировкой или CAPTCHA")
        
        # Запрашиваем ручное вмешательство
        wait_for_manual_action("Пожалуйста, решите CAPTCHA или выполните другие действия, затем нажмите OK")
        
        # Проверяем после ручного вмешательства
        if "403" in driver.title or "Forbidden" in driver.title or "запрещен" in driver.page_source:
            return False  # Блокировка осталась
        return True  # Пользователь успешно решил проблему
    
    return True  # Нет блокировки

# Функция для парсинга отзывов с Lenta.com с ручным вмешательством
def get_reviews(product_url, pages=3, use_manual_mode=True):
    driver = setup_driver(headless=False)  # Всегда используем видимый браузер для возможности ручного вмешательства
    
    try:
        # Открываем главную страницу
        print(f"Открываем главную страницу Lenta.com...")
        driver.get("https://lenta.com/")
        time.sleep(random.uniform(3, 5))
        
        # Проверка на блокировку/CAPTCHA
        if not check_for_captcha_or_block(driver):
            print("Не удалось обойти блокировку даже после ручного вмешательства")
            return []
        
        # Переходим на страницу товара
        print(f"Переходим на страницу товара {product_url}...")
        driver.get(product_url)
        time.sleep(random.uniform(5, 7))
        
        # Проверка на блокировку/CAPTCHA
        if not check_for_captcha_or_block(driver):
            print("Не удалось обойти блокировку при доступе к странице товара")
            return []
        
        # Имитация поведения человека
        human_like_interaction(driver)
        
        # Подтверждение, что мы на правильной странице
        if use_manual_mode:
            wait_for_manual_action("Пожалуйста, убедитесь что страница товара загрузилась корректно. Нажмите OK для продолжения.")
        
        # Сохраняем скриншот
        driver.save_screenshot("page_loaded.png")
        print("Сохранен скриншот страницы в page_loaded.png")
        
        # Список для хранения отзывов
        reviews = []
        
        # Получаем название продукта
        product_name = "Неизвестный продукт"
        try:
            product_elements = driver.find_elements(By.CSS_SELECTOR, "h1")
            if product_elements:
                product_name = product_elements[0].text.strip()
                print(f"Найдено название продукта: {product_name}")
        except Exception as e:
            print(f"Ошибка при получении названия продукта: {e}")
        
        # Ручное вмешательство для клика по кнопке отзывов
        if use_manual_mode:
            wait_for_manual_action("Пожалуйста, нажмите на кнопку 'Читать отзывы' или аналогичную на странице, затем нажмите OK")
        else:
            # Пробуем автоматически найти и нажать на кнопку отзывов
            button_clicked = False
            button_selectors = [
                "//button[contains(text(), 'Читать отзывы')]",
                "//button[contains(text(), 'Показать все отзывы')]",
                "button.p-button-third",
                ".product-tab_votes-controls button"
            ]
            
            for selector in button_selectors:
                try:
                    locator_type = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                    button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((locator_type, selector)))
                    button.click()
                    button_clicked = True
                    print(f"Нажата кнопка отзывов с селектором: {selector}")
                    time.sleep(3)
                    break
                except Exception:
                    continue
            
            if not button_clicked:
                print("Не удалось автоматически нажать кнопку отзывов")
                if use_manual_mode:
                    wait_for_manual_action("Не удалось найти кнопку отзывов. Пожалуйста, нажмите на неё вручную, затем нажмите OK")
        
        # Даем время для загрузки отзывов
        time.sleep(3)
        
        # Основной цикл по страницам с отзывами
        page_counter = 0
        while page_counter < pages:
            # Плавная прокрутка вниз
            previous_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(4):  # Несколько шагов прокрутки
                driver.execute_script(f"window.scrollBy(0, {random.randint(300, 700)});")
                time.sleep(random.uniform(1, 2))
            
            # Ждем загрузки контента
            time.sleep(3)
            
            # Запрашиваем у пользователя подтверждение, что отзывы загружены
            if use_manual_mode and page_counter == 0:
                wait_for_manual_action("Убедитесь, что отзывы загружены. Если нет, прокрутите страницу или выполните другие действия. Затем нажмите OK.")
            
            # Получаем отзывы
            review_elements = []
            
            # Пытаемся найти элементы отзывов разными способами
            selectors = [
                "//lu-feedback-review",
                "//div[contains(@class, 'review')]",
                ".lu-review",
                "lu-feedback-review"
            ]
            
            for selector in selectors:
                try:
                    locator_type = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                    elements = driver.find_elements(locator_type, selector)
                    if elements:
                        review_elements = elements
                        print(f"Найдены отзывы с селектором {selector}: {len(elements)} шт.")
                        break
                except Exception as e:
                    print(f"Ошибка при поиске отзывов с селектором {selector}: {e}")
            
            # Если не нашли отзывы автоматически, запрашиваем ручной XPath
            if not review_elements and use_manual_mode:
                root = tk.Tk()
                root.withdraw()
                custom_selector = simpledialog.askstring(
                    "Ввод селектора", 
                    "Не удалось найти отзывы автоматически. Введите CSS-селектор или XPath для отзывов:"
                )
                root.destroy()
                
                if custom_selector:
                    try:
                        locator_type = By.XPATH if custom_selector.startswith("//") else By.CSS_SELECTOR
                        review_elements = driver.find_elements(locator_type, custom_selector)
                        print(f"Найдены отзывы с пользовательским селектором: {len(review_elements)} шт.")
                    except Exception as e:
                        print(f"Ошибка при использовании пользовательского селектора: {e}")
            
            if not review_elements:
                print("Отзывы не найдены на этой странице.")
                break
            
            # Обрабатываем найденные отзывы
            for review in review_elements:
                try:
                    # Извлекаем текст отзыва
                    comment = None
                    comment_selectors = [".//p[contains(@class, 'text')]", ".//p", "p", ".lu-review_text"]
                    
                    for selector in comment_selectors:
                        try:
                            locator_type = By.XPATH if selector.startswith(".//") else By.CSS_SELECTOR
                            comment_element = review.find_element(locator_type, selector)
                            comment = comment_element.text.strip()
                            if comment:
                                break
                        except:
                            continue
                    
                    if not comment:
                        continue
                    
                    # Извлекаем рейтинг
                    rating = 5  # По умолчанию
                    rating_selectors = [".//div[contains(@class, 'rating')]", ".//div[contains(@class, 'star')]"]
                    
                    for selector in rating_selectors:
                        try:
                            rating_elements = review.find_elements(By.XPATH, selector)
                            if rating_elements:
                                rating = len(rating_elements)
                                break
                        except:
                            continue
                    
                    # Извлекаем дату
                    date = "Неизвестная дата"
                    date_selectors = [".//div[contains(@class, 'date')]", ".//span[contains(@class, 'date')]"]
                    
                    for selector in date_selectors:
                        try:
                            date_element = review.find_element(By.XPATH, selector)
                            date = date_element.text.strip()
                            if date:
                                break
                        except:
                            continue
                    
                    # Добавляем отзыв, если он не дублируется
                    review_data = {
                        "platform": "Lenta.com",
                        "product_name": product_name,
                        "comment": comment,
                        "rating": rating,
                        "created_at": date
                    }
                    
                    is_duplicate = False
                    for existing_review in reviews:
                        if existing_review["comment"] == comment:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        reviews.append(review_data)
                        print(f"Добавлен отзыв: {comment[:50]}... (Дата: {date}, Рейтинг: {rating})")
                    
                except Exception as e:
                    print(f"Ошибка при обработке отзыва: {e}")
            
            # Проверяем, нужно ли загружать больше отзывов
            if use_manual_mode:
                root = tk.Tk()
                root.withdraw()
                load_more = messagebox.askyesno(
                    "Загрузить еще?",
                    f"Загружено {len(reviews)} отзывов. Загрузить еще? Если на странице есть кнопка 'Загрузить еще', нажмите на неё перед тем, как нажать 'Да'."
                )
                root.destroy()
                
                if not load_more:
                    break
            else:
                # Пробуем автоматически нажать кнопку "Загрузить еще"
                load_more_clicked = False
                load_more_selectors = [
                    "//button[contains(text(), 'Загрузить еще')]",
                    "//button[contains(text(), 'Показать еще')]",
                    "button[class*='more']"
                ]
                
                for selector in load_more_selectors:
                    try:
                        locator_type = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                        load_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((locator_type, selector)))
                        load_button.click()
                        load_more_clicked = True
                        print("Нажата кнопка 'Загрузить еще'")
                        time.sleep(3)
                        break
                    except:
                        continue
                
                if not load_more_clicked:
                    print("Не найдена кнопка 'Загрузить еще' или все отзывы уже загружены")
                    break
            
            page_counter += 1
        
        print(f"Всего собрано уникальных отзывов: {len(reviews)}")
        return reviews
    
    except Exception as e:
        print(f"Произошла ошибка при получении отзывов: {e}")
        return []
    
    finally:
        # Спрашиваем пользователя, закрывать ли браузер
        if use_manual_mode:
            root = tk.Tk()
            root.withdraw()
            close_browser = messagebox.askyesno("Закрыть браузер?", "Закрыть браузер?")
            root.destroy()
            
            if close_browser:
                driver.quit()
                print("Браузер закрыт.")
            else:
                print("Браузер оставлен открытым для ручного просмотра.")
        else:
            driver.quit()

# Функция для сохранения в SQLite
def save_to_db(reviews):
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
    
    reviews_data = [(r["platform"], r["product_name"], r["comment"], r["rating"], r["created_at"]) for r in reviews]
    cursor.executemany("INSERT INTO reviews (platform, product_name, comment, rating, created_at) VALUES (?, ?, ?, ?, ?)", reviews_data)
    
    conn.commit()
    conn.close()
    print(f"Сохранено {len(reviews)} отзывов в базу данных reviews.db")

# Функция для ручного ввода отзывов
def manual_input_reviews():
    reviews = []
    
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
            except:
                print("Введите число от 1 до 5")
        
        date = input("Дата (например, 25 марта 2024): ")
        
        review = {
            "platform": "Lenta.com",
            "product_name": product_name,
            "comment": comment,
            "rating": rating,
            "created_at": date
        }
        
        reviews.append(review)
        print(f"Отзыв добавлен. Всего: {len(reviews)}")
    
    return reviews

# Основная функция
def main():
    try:
        import tkinter
    except ImportError:
        print("Установка tkinter...")
        os.system("pip install python-tk")
    
    # Запрашиваем у пользователя режим работы
    print("\n=== Парсер отзывов Lenta.com ===")
    print("1. Автоматический режим с ручным вмешательством")
    print("2. Полностью ручной ввод отзывов")
    
    choice = 0
    while choice not in [1, 2]:
        try:
            choice = int(input("Выберите режим работы (1 или 2): "))
        except:
            print("Введите 1 или 2")
    
    reviews = []
    
    if choice == 1:
        product_url = input("Введите URL страницы товара (Enter для использования примера): ")
        if not product_url:
            product_url = "https://lenta.com/product/tvorog-ekoniva-9-bez-zmzh-rossiya-300g-664609/"
        
        pages = 3
        try:
            pages_input = input("Сколько страниц отзывов парсить (Enter для 3): ")
            if pages_input:
                pages = int(pages_input)
        except:
            print("Используется значение по умолчанию: 3 страницы")
        
        print(f"\nНачинаем парсинг отзывов с {product_url}")
        print("В процессе будут появляться диалоговые окна для ручного вмешательства.")
        print("Следуйте инструкциям в этих окнах.\n")
        
        reviews = get_reviews(product_url, pages=pages, use_manual_mode=True)
    
    elif choice == 2:
        print("\nРежим ручного ввода отзывов.")
        reviews = manual_input_reviews()
    
    if reviews:
        save_to_db(reviews)
        print(f"Сбор отзывов завершен. Собрано и сохранено {len(reviews)} отзывов.")
    else:
        print("Отзывы не собраны.")

if __name__ == "__main__":
    main()

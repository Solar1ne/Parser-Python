import sqlite3
import sys
import os

def setup_database():
    """Create the database and table if they don't exist."""
    try:
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
    except Exception as e:
        print(f"Ошибка при настройке базы данных: {e}")
        sys.exit(1)

def manual_input_reviews():
    """Manually input reviews and save them to the database."""
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
                "platform": "Lenta.com",
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

def save_to_db(reviews):
    """Save reviews to the database."""
    if not reviews:
        print("Нет отзывов для сохранения.")
        return
    
    try:
        conn = sqlite3.connect("reviews.db")
        cursor = conn.cursor()
        
        # Подготавливаем данные для вставки
        reviews_data = [(r["platform"], r["product_name"], r["comment"], r["rating"], r["created_at"]) for r in reviews]
        
        # Вставляем данные
        cursor.executemany(
            "INSERT INTO reviews (platform, product_name, comment, rating, created_at) VALUES (?, ?, ?, ?, ?)", 
            reviews_data
        )
        
        conn.commit()
        conn.close()
        
        print(f"Сохранено {len(reviews)} отзывов в базу данных.")
    except Exception as e:
        print(f"Ошибка при сохранении в базу данных: {e}")

def view_reviews():
    """View all reviews in the database."""
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

def main():
    # Настраиваем базу данных
    setup_database()
    
    while True:
        print("\n=== МЕНЮ ===")
        print("1. Ввести новые отзывы")
        print("2. Просмотреть все отзывы")
        print("3. Выход")
        
        choice = input("\nВыберите действие (1-3): ")
        
        if choice == "1":
            reviews = manual_input_reviews()
            if reviews:
                save_to_db(reviews)
        elif choice == "2":
            view_reviews()
        elif choice == "3":
            print("Программа завершена.")
            break
        else:
            print("Неверный ввод. Пожалуйста, выберите 1, 2 или 3.")

if __name__ == "__main__":
    main() 
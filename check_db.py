import sqlite3
import os

def view_reviews():
    print(f"Текущая директория: {os.getcwd()}")
    print(f"Проверка существования файла БД: {'reviews.db' in os.listdir()}")
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect("reviews.db")
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица reviews
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
        table_exists = cursor.fetchone()
        if not table_exists:
            print("Таблица 'reviews' не существует в базе данных.")
            print("Доступные таблицы:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                print(f" - {table[0]}")
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
        print(f"{column_names[0]:<3} | {column_names[1]:<10} | {column_names[2]:<30} | {column_names[3]:<40} | {column_names[4]:<6} | {column_names[5]:<15}")
        print("-" * 100)
        
        # Выводим данные
        for row in rows:
            # Обрезаем слишком длинные поля для лучшего отображения
            product_name = row[2][:30] if len(str(row[2])) > 30 else row[2]
            comment = row[3][:40] if len(str(row[3])) > 40 else row[3]
            
            print(f"{row[0]:<3} | {row[1]:<10} | {product_name:<30} | {comment:<40} | {row[4]:<6} | {row[5]:<15}")
        
        print("-" * 100)
        print(f"Всего отзывов: {len(rows)}")
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    view_reviews() 
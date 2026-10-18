"""
main.py — сбор отзывов о приложении из Google Play, раскладка по звёздам,
отчёт и AI-анализ проблем и преимуществ.

Запуск:
    python main.py                                   # спросит число отзывов
    python main.py --package com.logistic.sdek -n 500
"""

import argparse
from pathlib import Path

from google_play_scraper import app, reviews, Sort
import pandas as pd
import os
from datetime import datetime
from generate import create_analyze_file
import asyncio

def get_app_details(package_name, lang='ru', country='ru'):
    """Получить информацию о приложении"""
    try:
        print(f"🔍 Получаем информацию о приложении {package_name}...")
        return app(package_name, lang=lang, country=country)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def get_all_reviews(package_name, lang='ru', country='ru', max_reviews=300):
    """Получить отзывы"""
    try:
        print("📝 Собираем отзывы...")
        all_reviews = []
        continuation_token = None
        
        while len(all_reviews) < max_reviews:
            reviews_batch, continuation_token = reviews(
                package_name,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=100,
                continuation_token=continuation_token
            )
            
            if not reviews_batch:
                break
                
            all_reviews.extend(reviews_batch)
            print(f"✅ Получено {len(all_reviews)} отзывов...")
            
            if continuation_token is None:
                break
        
        return all_reviews[:max_reviews]
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def sort_reviews_by_rating(reviews_list):
    """Сортировать отзывы по рейтингу от 1 до 5 звезд"""
    sorted_reviews = {1: [], 2: [], 3: [], 4: [], 5: []}
    
    for review in reviews_list:
        rating = review['score']
        if 1 <= rating <= 5:
            sorted_reviews[rating].append(review)
    
    return sorted_reviews

def save_reviews_to_csv(sorted_reviews, folder_name):
    """Сохранить отзывы в CSV файлы по рейтингам"""
    print("💾 Сохраняем отзывы в CSV...")
    
    for rating in range(1, 6):
        reviews_list = sorted_reviews[rating]
        if reviews_list:
            # Создаем простой DataFrame
            data = []
            for review in reviews_list:
                data.append({
                    'userName': review['userName'],
                    'rating': review['score'],
                    'date': str(review['at']),  # Просто преобразуем в строку
                    'review': review['content'],
                    'developer_reply': review.get('replyContent', ''),
                    'likes': review.get('thumbsUpCount', 0)
                })
            
            df = pd.DataFrame(data)
            filename = f"{folder_name}/reviews_{rating}_stars.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✅ {rating} звезд: {len(reviews_list)} отзывов")

def save_all_reviews_csv(sorted_reviews, folder_name):
    """Сохранить все отзывы в один CSV"""
    print("💾 Сохраняем все отзывы в один файл...")
    
    all_data = []
    for rating in range(1, 6):
        for review in sorted_reviews[rating]:
            all_data.append({
                'userName': review['userName'],
                'rating': review['score'],
                'stars': rating,
                'date': str(review['at']),
                'review': review['content'],
                'developer_reply': review.get('replyContent', ''),
                'likes': review.get('thumbsUpCount', 0)
            })
    
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(f"{folder_name}/all_reviews.csv", index=False, encoding='utf-8-sig')
        print(f"✅ Всего отзывов: {len(all_data)}")

def create_simple_report(sorted_reviews, app_title, package_name, folder_name):
    """Создать простой отчет"""
    total_reviews = sum(len(reviews) for reviews in sorted_reviews.values())
    
    report = f"""ОТЧЕТ ПО ОТЗЫВАМ
Приложение: {app_title}
Пакет: {package_name}
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Всего отзывов: {total_reviews}

Распределение по звездам:
"""
    for rating in range(1, 6):
        count = len(sorted_reviews[rating])
        percent = (count / total_reviews * 100) if total_reviews > 0 else 0
        report += f"{rating} звезд: {count} ({percent:.1f}%)\n"
    
    # Сохраняем отчет
    with open(f"{folder_name}/report.txt", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)

def show_examples(sorted_reviews):
    """Показать примеры отзывов"""
    print("\n📋 ПРИМЕРЫ ОТЗЫВОВ:")
    print("=" * 50)
    
    for rating in range(1, 6):
        reviews_list = sorted_reviews[rating]
        if reviews_list:
            print(f"\n⭐ {rating} звезд ({len(reviews_list)} отзывов):")
            for i, review in enumerate(reviews_list[:2], 1):
                print(f"{i}. {review['content'][:80]}...")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Сбор и анализ отзывов из Google Play")
    parser.add_argument("--package", default="com.logistic.sdek", help="id приложения в Google Play")
    parser.add_argument("-n", "--max-reviews", type=int, help="сколько отзывов собрать")
    parser.add_argument("--lang", default="ru")
    parser.add_argument("--country", default="ru")
    args = parser.parse_args()

    PACKAGE_NAME = args.package
    LANGUAGE = args.lang
    COUNTRY = args.country
    MAX_REVIEWS = args.max_reviews or int(input('Введите сколько нужно обработать комментариев: '))
    
    print("🚀 ЗАПУСК СБОРА ОТЗЫВОВ")
    print("=" * 40)
    
    # Получаем информацию о приложении
    app_details = get_app_details(PACKAGE_NAME, LANGUAGE, COUNTRY)
    if not app_details:
        return
    
    print(f"✅ Приложение: {app_details['title']}")
    print(f"⭐ Рейтинг: {app_details['score']}")
    print(f"📥 Установки: {app_details['installs']}")
    
    # Получаем отзывы
    all_reviews = get_all_reviews(PACKAGE_NAME, LANGUAGE, COUNTRY, MAX_REVIEWS)
    if not all_reviews:
        print("❌ Не удалось получить отзывы")
        return
    
    print(f"✅ Всего собрано отзывов: {len(all_reviews)}")
    
    # Сортируем по рейтингу
    sorted_reviews = sort_reviews_by_rating(all_reviews)
    
    # Показываем примеры
    show_examples(sorted_reviews)
    
    # Создаем папку для результатов
    folder_name = f"reviews_{PACKAGE_NAME}"
    os.makedirs(folder_name, exist_ok=True)
    
    # Сохраняем данные
    save_reviews_to_csv(sorted_reviews, folder_name)
    save_all_reviews_csv(sorted_reviews, folder_name)
    create_simple_report(sorted_reviews, app_details['title'], PACKAGE_NAME, folder_name)
    
    print("\n🤖 Запускаем AI анализ...")
    asyncio.run(create_analyze_file(Path(folder_name), app_details['title']))
    
    print(f"\n🎉 ГОТОВО!")
    print(f"📁 Файлы сохранены в папку: {folder_name}")
    print("\nСозданные файлы:")
    print("- reviews_1_stars.csv - отзывы с 1 звездой")
    print("- reviews_2_stars.csv - отзывы с 2 звездами") 
    print("- reviews_3_stars.csv - отзывы с 3 звездами")
    print("- reviews_4_stars.csv - отзывы с 4 звездами")
    print("- reviews_5_stars.csv - отзывы с 5 звездами")
    print("- all_reviews.csv - все отзывы в одном файле")
    print("- report.txt - сводный отчет")
    print("- reviews_analyze.txt - AI-анализ проблем и преимуществ")

if __name__ == "__main__":
    main()
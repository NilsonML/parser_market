"""
generate.py — анализ отзывов через LLM (OpenRouter): главные проблемы и преимущества
по выборке 1★ и 5★ отзывов. Если все модели недоступны — честная сводка по цифрам.
"""

from pathlib import Path

import pandas as pd
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import asyncio
import random

load_dotenv()
AI_TOKEN = os.getenv('AI_TOKEN')

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=AI_TOKEN,
)

# Модели в порядке приоритета
models_to_try = [
    "minimax/minimax-m2:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-14b-instruct:free",
    "microsoft/wizardlm-2-7b:free"
]

async def ai_generate_from_csv(folder: Path, app_title: str):
    try:
        # Path вместо строки с "\\": обратный слэш работает только на Windows
        df1 = pd.read_csv(folder / "reviews_1_stars.csv")
        df2 = pd.read_csv(folder / "reviews_5_stars.csv")
        
        # Берем меньше данных для экономии токенов
        df1_sample = df1.head(10)
        df2_sample = df2.head(10)
        
        # Конвертируем в текстовый формат
        csv1_text = df1_sample.to_string(index=False)
        csv2_text = df2_sample.to_string(index=False)
        
        # Создаем промпт с данными из CSV
        prompt = f"""
Проанализируй эти отзывы на приложение {app_title}:

ОТЗЫВЫ С 1 ЗВЕЗДОЙ (проблемы):
{csv1_text}

ОТЗЫВЫ С 5 ЗВЕЗДАМИ (преимущества):
{csv2_text}

Выдели основные проблемы и преимущества. Будь кратким.
"""
        
        # Пробуем разные модели с увеличенными задержками
        max_retries = 3
        
        for model in models_to_try:
            for attempt in range(max_retries):
                try:
                    print(f"🔄 Попытка {attempt + 1} с моделью: {model}")
                    
                    completion = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system", 
                                "content": "Ты аналитик. Отвечай кратко на русском. Анализируй проблемы и преимущества."
                            },
                            {
                                "role": "user", 
                                "content": prompt
                            }
                        ],
                        max_tokens=800,  # Сильно ограничиваем токены
                        temperature=0.3
                    )
                    
                    print(f"✅ Успешно использована модель: {model}")
                    return completion.choices[0].message.content
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ Ошибка с моделью {model}: {error_msg}")
                    
                    if "rate-limited" in error_msg or "429" in error_msg:
                        if attempt < max_retries - 1:
                            # Увеличиваем задержку при повторной попытке
                            extended_wait = random.randint(90, 180)
                            print(f"🚫 Лимит! Ждем {extended_wait} секунд...")
                            await asyncio.sleep(extended_wait)
                            continue
                        else:
                            print(f"🚫 Модель {model} недоступна, пробуем следующую...")
                            continue
                    else:
                        # Ошибка не из-за лимита (модель удалена, неверный запрос) —
                        # повтор с той же моделью не поможет, сразу берём следующую
                        break
        
        # Если все модели не сработали
        return create_fallback_analysis(df1, df2, app_title)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return f"Ошибка анализа: {e}"

def create_fallback_analysis(df1, df2, app_title):
    """Сводка без ИИ: только то, что следует из данных.

    Раньше здесь были "выводы" ("технические проблемы — основная причина
    негатива"), написанные заранее и не зависящие от данных. Такой текст
    выглядит как анализ, но им не является — убрано.
    """
    print("⚠️ Все AI модели недоступны, сохраняем сводку по цифрам...")
    total_negative = len(df1)
    total_positive = len(df2)
    total = total_negative + total_positive
    share = total_positive / total * 100 if total else 0.0
    return f"""
СВОДКА ПО ОТЗЫВАМ: {app_title}
(AI-анализ недоступен — только статистика)

- Отзывов с 1 звездой: {total_negative}
- Отзывов с 5 звёздами: {total_positive}
- Доля 5★ среди крайних оценок: {share:.1f}%

Для содержательного анализа запустите скрипт позже, когда модели будут доступны.
"""

async def create_analyze_file(folder: Path, app_title: str):
    try:
        text = await ai_generate_from_csv(folder, app_title)
        
        # Сохраняем рядом с отзывами, а не в корень проекта
        output_path = folder / "reviews_analyze.txt"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✅ Анализ сохранен в: {output_path}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании файла: {e}")
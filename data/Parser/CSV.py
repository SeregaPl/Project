import pandas as pd
import re

# 1. Загружаем данные
df = pd.read_csv('Avito_Cars_Complete2.csv', sep=';')


def process_title(row):
    title = str(row['title'])

    # Значения по умолчанию для года и пробега
    year = "N/A"
    probeg = "N/A"

    # Ищем год (4 цифры подряд)
    year_match = re.search(r'(\d{4})', title)
    if year_match:
        year = year_match.group(1)

    # Ищем пробег (цифры перед "км")
    probeg_match = re.search(r'(\d[\d\s]*)\s*км', title)
    if probeg_match:
        clean_probeg = probeg_match.group(1).replace(" ", "").strip()
        if clean_probeg:
            probeg = clean_probeg

    # Очищаем title: оставляем только название (до первой запятой)
    new_title = title.split(',')[0].strip()

    return pd.Series([new_title, year, probeg])


# 2. Обрабатываем название, год и пробег
df[['title', 'year', 'probeg']] = df.apply(process_title, axis=1)

# 3. Заполняем пустоты в seller_name
# fillna заменяет отсутствующие значения (NaN), а replace('') — пустые строки
df['seller_name'] = df['seller_name'].fillna('N/A').replace('', 'N/A')

# 4. Переупорядочиваем столбцы (year и probeg сразу после title)
cols = list(df.columns)
starting_cols = ['brand', 'title', 'year', 'probeg']
remaining_cols = [c for c in cols if c not in starting_cols]
df = df[starting_cols + remaining_cols]

# 5. Сохраняем результат
df.to_csv('Avito_Cars_Data_Full_Clean2.csv', sep=';', index=False, encoding='utf-8-sig')

print("Готово! Проверьте файл 'Avito_Cars_Data_Full_Clean2.csv'.")
print("Теперь N/A стоит в 'year', 'probeg' и 'seller_name', если данные отсутствовали.")
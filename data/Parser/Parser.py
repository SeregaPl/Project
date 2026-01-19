import csv
import time
import re
import os
import random
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    if not text:
        return 'N/A'
    text = text.replace('\xa0', ' ')
    return ' '.join(text.split())


def extract_models_from_html(html_code: str) -> List[Dict]:
    """Извлекает список моделей из вашего HTML блока."""
    soup = BeautifulSoup(html_code, 'lxml')
    model_links = soup.find_all('a', attrs={'data-marker': 'popular-rubricator/link'})

    brands_config = []
    for link in model_links:
        name = link.get_text(strip=True)
        href = link.get('href')
        if name and href:
            brands_config.append({"name": name, "url": f"https://www.avito.ru{href}"})
    return brands_config


def get_max_pages(driver) -> int:
    """Автоматически определяет количество страниц на текущей странице модели."""
    try:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagination = soup.find('ul', attrs={'data-marker': 'pagination-button'})
        if not pagination:
            return 1

        pages = pagination.find_all('span', class_=re.compile(r'styles-module-text'))
        page_numbers = []
        for p in pages:
            text = p.get_text(strip=True)
            if text.isdigit():
                page_numbers.append(int(text))

        return max(page_numbers) if page_numbers else 1
    except:
        return 1


def save_to_csv(data: List[Dict[str, str]], filename: str):
    fieldnames = ['brand', 'title', 'price', 'seller_name', 'rating', 'reviews_count', 'link']
    existing_links = set()

    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    if 'link' in row: existing_links.add(row['link'])
        except:
            pass

    new_data = [item for item in data if item['link'] not in existing_links]
    if not new_data: return

    file_exists = os.path.exists(filename)
    with open(filename, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        if not file_exists or os.path.getsize(filename) == 0:
            writer.writeheader()
        writer.writerows(new_data)
    print(f"Добавлено {len(new_data)} новых строк.")


def parse_avito_auto(models_config: List[Dict], output_file: str):
    options = Options()
    options.page_load_strategy = 'eager'
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)

    try:
        for model in models_config:
            print(f"\n>>> ПАРСИНГ МОДЕЛИ: {model['name']}")

            # Первый заход для определения количества страниц
            driver.get(model['url'])
            time.sleep(random.uniform(3, 5))
            max_pages = get_max_pages(driver)
            print(f"Обнаружено страниц: {max_pages}")

            for page in range(1, max_pages + 1):
                separator = '&' if '?' in model['url'] else '?'
                url = f"{model['url']}{separator}p={page}"

                print(f"[{model['name']}] Страница {page}/{max_pages}...")
                driver.get(url)

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-marker="item"]')))
                except:
                    print("Контент не найден или капча.")
                    continue

                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, 'lxml')
                listings = soup.find_all('div', attrs={'data-marker': 'item'})

                current_page_items = []
                for listing in listings:
                    try:
                        title_tag = listing.find('a', attrs={'data-marker': 'item-title'})
                        title = clean_text(title_tag.get_text()) if title_tag else 'N/A'
                        link = 'https://www.avito.ru' + title_tag['href'] if title_tag else 'N/A'

                        price_tag = listing.find('meta', attrs={'itemprop': 'price'})
                        price = f"{price_tag['content']}" if price_tag else '0'

                        # ВАША РАБОЧАЯ ЛОГИКА ИЗВЛЕЧЕНИЯ ПРОДАВЦА
                        seller_name, rating, reviews_count = "N/A", "0.0", "нет отзывов"
                        seller_main_div = listing.find('div', class_=re.compile(r'style-root-.*'))

                        if seller_main_div:
                            # Имя продавца
                            seller_p = seller_main_div.find('p', attrs={'data-marker': False})
                            if seller_p:
                                seller_name = clean_text(seller_p.get_text())

                            # Рейтинг
                            rating_tag = seller_main_div.find('span', attrs={'data-marker': 'seller-info/score'})
                            if rating_tag:
                                rating = clean_text(rating_tag.get_text())

                            # Отзывы
                            reviews_tag = seller_main_div.find('p', attrs={'data-marker': 'seller-info/summary'})
                            if reviews_tag:
                                reviews_count = clean_text(reviews_tag.get_text())

                        current_page_items.append({
                            'brand': model['name'],
                            'title': title,
                            'price': price,
                            'seller_name': seller_name,
                            'rating': rating,
                            'reviews_count': reviews_count,
                            'link': link,
                        })
                    except Exception:
                        continue

                if current_page_items:
                    save_to_csv(current_page_items, output_file)

                time.sleep(random.uniform(3, 6))

    finally:
        driver.quit()


if __name__ == "__main__":
    # 1. Поместите сюда HTML-код моделей
    MODELS_HTML = """
    <div class="popular-rubricator-links-UAkHE" data-marker="popular-rubricator/links"><div class="popular-rubricator-row-Q5kSL" data-marker="popular-rubricator/links/row"><a href="/all/avtomobili/luxgen/7_suv-ASgBAgICAkTgtg3emCjitg2InSg?cd=1" class="popular-rubricator-link-b5pkS" title="7 SUV" data-category-id="9" data-marker="popular-rubricator/link">7 SUV</a><span class="popular-rubricator-count-uPVWQ" data-marker="popular-rubricator/count">12</span></div></div>
    """

    # 2. Авто-создание списка ссылок
    BRANDS_LIST = extract_models_from_html(MODELS_HTML)

    # 3. Запуск
    FINAL_FILE = 'Avito_Cars_Complete.csv'
    parse_avito_auto(BRANDS_LIST, FINAL_FILE)
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time

st.set_page_config(page_title="Аналитика авторынка", layout="wide")
st.title("Аналитика авторынка")

FILE_PATH = "/app/car_analytics.csv"


@st.cache_data(ttl=600)
def load_data():
    if not os.path.exists(FILE_PATH):
        st.warning("Файл данных не найден...")
        return None
    try:
        df = pd.read_csv(
            FILE_PATH,
            sep=',',
            on_bad_lines='skip',
            engine='c',
            low_memory=False,
            quotechar='"'
        )
        # Чистим названия колонок
        df.columns = [c.strip() for c in df.columns]

        # Преобразование типов
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['year_prod'] = pd.to_numeric(df['year_prod'], errors='coerce')
        df['probeg'] = pd.to_numeric(df['probeg'], errors='coerce')

        # Удаляем только строки без цены
        df = df.dropna(subset=['price'])

        return df
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return None


df = load_data()

if df is not None:
    # --- 1. МЕТРИКИ ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Всего объявлений", f"{len(df):,}".replace(',', ' '))
    m2.metric("Моделей в базе", len(df['brand'].unique()))
    m3.metric("Последнее обновление", time.strftime("%H:%M:%S"))

    st.divider()

    # --- 2. ЛИНЕЙНЫЙ ГРАФИК (БЕЗ 2026) ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Динамика объявлений по годам")
        # Группируем данные
        line_data = df.groupby(['year_prod', 'predicted_liquidity']).size().reset_index(name='количество')

        # Фильтр: от 1990 до 2025 года включительно
        mask = (line_data['year_prod'] >= 1990) & (line_data['year_prod'] <= 2025)

        fig_line = px.line(
            line_data[mask],
            x='year_prod',
            y='количество',
            color='predicted_liquidity',
            markers=True,
            labels={
                'year_prod': 'Год производства',
                'количество': 'Количество объявлений',
                'predicted_liquidity': 'Ликвидность'
            }
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with col2:
        st.subheader("Доли ликвидности")
        liq_counts = df['predicted_liquidity'].value_counts().reset_index()
        liq_counts.columns = ['Ликвидность', 'количество']
        fig_pie = px.pie(liq_counts, values='количество', names='Ликвидность', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # --- 3. ГИСТОГРАММА И ТЕПЛОВАЯ КАРТА ---
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Распределение по пробегу")
        fig_hist = px.histogram(
            df[df['probeg'] < 500000],
            x="probeg",
            nbins=50,
            color_discrete_sequence=['#636EFA'],
            labels={'probeg': 'Пробег', 'count': 'Количество'}
        )
        fig_hist.update_layout(xaxis_title="Пробег (км)", yaxis_title="Количество авто")
        st.plotly_chart(fig_hist, use_container_width=True)

    with col4:
        st.subheader("Плотность цен")
        heat_sample = df.sample(n=min(len(df), 100000))
        fig_heat = px.density_heatmap(
            heat_sample[heat_sample['year_prod'] > 2000],
            x="year_prod", y="probeg", z="price",
            histfunc="avg", nbinsx=25, nbinsy=25,
            color_continuous_scale="Viridis",
            labels={
                'year_prod': 'Год производства',
                'probeg': 'Пробег',
                'price': 'Средняя цена'
            }
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # --- 4. КАРТА ЦЕН (SCATTER) ---
    st.subheader("Карта цен: Частники vs Дилеры")
    color_map = {
        "Person": "red", "Seller": "red", "Private": "red", "Individual": "red",
        "Dealer": "green", "Market": "green", "Company": "green", "Business": "green"
    }

    df_sample = df.sample(n=min(len(df), 50000), random_state=42)
    fig_scatter = px.scatter(
        df_sample,
        x='year_prod',
        y='price',
        color='seller_type',
        color_discrete_map=color_map,
        opacity=0.4,
        hover_data={'brand': True, 'title': True, 'probeg': True, 'price': True},
        labels={
            'year_prod': 'Год производства',
            'price': 'Цена (₽)',
            'seller_type': 'Тип продавца',
            'brand': 'Марка',
            'probeg': 'Пробег'
        },
        range_y=[0, df['price'].quantile(0.99)]
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

else:
    st.info("Загрузка данных...")
import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Конфигурация страницы
st.set_page_config(
    page_title="Debbie Mice Colony Dashboard",
    page_icon="🐭",
    layout="wide"
)

# 2. Кэширование загрузки и предобработки данных
@st.cache_data
def load_data():
    df = pd.read_excel('Debbie_mice_colony.xlsx', sheet_name='Main', engine='openpyxl')
    
    # Приведение даты рождения к типу datetime (ошибки/знаки '?' преобразуются в NaT)
    df['Birth_date_clean'] = pd.to_datetime(df['Birth_date'], errors='coerce')
    
    # Нормализация наименований окраса (приведение к нижнему регистру)
    if 'Color' in df.columns:
        df['Color_clean'] = df['Color'].astype(str).str.strip().str.lower()
        df['Color_clean'] = df['Color_clean'].replace({'nan': 'unspecified', '?': 'unspecified'})
    else:
        df['Color_clean'] = 'unspecified'
        
    # Преобразование Cre в человекочитаемый формат
    df['Cre_status'] = df['Cre'].map({1.0: 'Cre+', 0.0: 'Cre-'}).fillna('Unknown')
    
    # Форматирование Ear_Tag для корректного поиска
    df['Ear_Tag_str'] = df['Ear_Tag'].astype(str).str.replace('.0', '', regex=False)
    
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Ошибка загрузки файла 'Debbie_mice_colony.xlsx': {e}")
    st.stop()

# 3. Боковая панель: Фильтры
st.sidebar.title("🔍 Colony Filters")

# --- Фильтр 1: Генотип ---
all_genotypes = sorted([str(g) for g in df_raw['Genotype'].dropna().unique()])
selected_genotypes = st.sidebar.multiselect(
    "Genotype", 
    options=all_genotypes, 
    default=all_genotypes
)

# --- Фильтр 2: Пол ---
all_sexes = sorted([str(s) for s in df_raw['Sex'].dropna().unique()])
selected_sexes = st.sidebar.multiselect(
    "Sex", 
    options=all_sexes, 
    default=all_sexes
)

# --- Фильтр 3: Статус Cre ---
all_cre = sorted(df_raw['Cre_status'].unique())
selected_cre = st.sidebar.multiselect(
    "Cre Status", 
    options=all_cre, 
    default=all_cre
)

# --- Фильтр 4: Диапазон дат рождения ---
valid_dates = df_raw['Birth_date_clean'].dropna()
min_date = valid_dates.min().date()
max_date = valid_dates.max().date()

date_range = st.sidebar.date_input(
    "Birth Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# --- Фильтр 5: Поиск по клетке (Cage ID) ---
all_cages = sorted([str(c) for c in df_raw['Cage_ID'].dropna().unique()])
selected_cages = st.sidebar.multiselect(
    "Cage ID (Optional)", 
    options=all_cages, 
    default=[]
)

# --- Фильтр 6: Текстовый поиск по Ear Tag / Родителям ---
search_tag = st.sidebar.text_input("Search Ear Tag / Parent ID", "").strip()

# 4. Применение фильтрации
filtered_df = df_raw.copy()

# Фильтрация по Genotype
if selected_genotypes:
    filtered_df = filtered_df[filtered_df['Genotype'].astype(str).isin(selected_genotypes)]

# Фильтрация по Sex
if selected_sexes:
    filtered_df = filtered_df[filtered_df['Sex'].astype(str).isin(selected_sexes)]

# Фильтрация по Cre
if selected_cre:
    filtered_df = filtered_df[filtered_df['Cre_status'].isin(selected_cre)]

# Фильтрация по Дате рождения
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
    filtered_df = filtered_df[
        (filtered_df['Birth_date_clean'].dt.date >= start_d) & 
        (filtered_df['Birth_date_clean'].dt.date <= end_d)
    ]

# Фильтрация по Cage_ID
if selected_cages:
    filtered_df = filtered_df[filtered_df['Cage_ID'].astype(str).isin(selected_cages)]

# Фильтрация по поисковому запросу
if search_tag:
    tag_match = filtered_df['Ear_Tag_str'].str.contains(search_tag, case=False, na=False)
    father_match = filtered_df['Father'].astype(str).str.contains(search_tag, case=False, na=False)
    mother_match = filtered_df['Mother'].astype(str).str.contains(search_tag, case=False, na=False)
    filtered_df = filtered_df[tag_match | father_match | mother_match]

# 5. Главная панель: Дашборд
st.title("🐭 Debbie Mice Colony Analysis")
st.markdown("Интерактивный дашборд для анализа структуры колонии, генотипов и демографии.")

# Метрики (Key Metrics)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Mice (Filtered)", len(filtered_df))
col2.metric("Unique Cages", filtered_df['Cage_ID'].nunique())
col3.metric("Females (f)", len(filtered_df[filtered_df['Sex'] == 'f']))
col4.metric("Males (m)", len(filtered_df[filtered_df['Sex'] == 'm']))

st.divider()

# 6. Научные графики (Чистый белый фон)
tab1, tab2, tab3 = st.tabs(["📊 Genotypes & Demographics", "📈 Birth Dynamics", "📋 Raw Data"])

# Общий стиль для графиков с белым фоном
white_layout = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    xaxis=dict(showgrid=True, gridcolor='#E5E5E5', linecolor='black'),
    yaxis=dict(showgrid=True, gridcolor='#E5E5E5', linecolor='black'),
    font=dict(color='black')
)

with tab1:
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("Genotype Distribution by Sex")
        geno_sex = filtered_df.groupby(['Genotype', 'Sex']).size().reset_index(name='Count')
        fig_geno = px.bar(
            geno_sex, 
            x='Genotype', 
            y='Count', 
            color='Sex',
            barmode='group',
            color_discrete_map={'f': '#4C72B0', 'm': '#55A868'},
            title="Mice Count by Genotype and Sex"
        )
        fig_geno.update_layout(**white_layout)
        st.plotly_chart(fig_geno, use_container_width=True)

    with col_g2:
        st.subheader("Cre Status Ratio")
        cre_counts = filtered_df['Cre_status'].value_counts().reset_index()
        cre_counts.columns = ['Cre Status', 'Count']
        fig_cre = px.pie(
            cre_counts, 
            names='Cre Status', 
            values='Count',
            color_discrete_sequence=['#C44E52', '#8172B2', '#CCB974'],
            title="Cre+ vs Cre- Proportion"
        )
        fig_cre.update_layout(paper_bgcolor='white', font=dict(color='black'))
        st.plotly_chart(fig_cre, use_container_width=True)

with tab2:
    st.subheader("Births Over Time")
    birth_df = filtered_df.dropna(subset=['Birth_date_clean']).copy()
    if not birth_df.empty:
        birth_df['YearMonth'] = birth_df['Birth_date_clean'].dt.to_period('M').astype(str)
        timeline = birth_df.groupby(['YearMonth', 'Genotype']).size().reset_index(name='Count')
        
        fig_time = px.line(
            timeline, 
            x='YearMonth', 
            y='Count', 
            color='Genotype',
            markers=True,
            title="Monthly Birth Count by Genotype"
        )
        fig_time.update_layout(**white_layout)
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No valid birth dates available for the selected filters.")

with tab3:
    st.subheader("Filtered Colony Records")
    
    # Столбцы для отображения
    display_cols = ['Ear_Tag', 'Genotype', 'Cre_status', 'Flox_1', 'Flox_2', 'Sex', 'Color', 'Birth_date', 'Cage_ID', 'Breeding_cage', 'Father', 'Mother']
    existing_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(filtered_df[existing_cols], use_container_width=True)
    
    # Кнопка скачивания CSV
    csv_data = filtered_df[existing_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name="filtered_mice_colony.csv",
        mime="text/csv"
    )
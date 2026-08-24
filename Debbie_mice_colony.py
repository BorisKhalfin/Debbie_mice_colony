import streamlit as st
import pandas as pd
import plotly.express as px
import time
from PIL import Image

# ---------------------------------------------------------
# Splash Screen on start for 5 seconds
# ---------------------------------------------------------
if 'splash_shown' not in st.session_state:
    st.session_state.splash_shown = False

if not st.session_state.splash_shown:
    splash = st.empty()
    with splash.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                logo = Image.open("DTree.png")
                st.image(logo, use_container_width=True)
            except FileNotFoundError:
                st.info("Loading Laboratory Dashboard...")
            
            st.markdown("<h3 style='text-align: center;'>Loading Laboratory Dashboard...</h3>", unsafe_allow_html=True)
    
    time.sleep(5)
    st.session_state.splash_shown = True
    splash.empty()
    st.rerun()

# Sidebar logo and link to the website
try:
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <a href="https://toiber.wixsite.com/toiber-lab" target="_blank" title="Visit Toiber Lab Website">
                <img src="https://raw.githubusercontent.com/streamlit/streamlit/main/docs/static/logo.png" id="lab_logo_img" style="display:none;"/>
            </a>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.sidebar.image("DTree.png", width=120)
    st.sidebar.link_button("🌐 Toiber Lab Website", "https://toiber.wixsite.com/toiber-lab")
except Exception:
    pass


# 1. Config
st.set_page_config(
    page_title="Debbie Mice Colony Dashboard",
    page_icon="🐭",
    layout="wide"
)

# 2. Cache & Data Loading
URL_ALL_MICE = "https://docs.google.com/spreadsheets/d/1Eco6HKJJjpK4Q7RJ407bm-rS1TCjGWKdiA33f5jMUC0/export?format=csv&gid=1525111892"
URL_LIVE_MICE = "https://docs.google.com/spreadsheets/d/1Eco6HKJJjpK4Q7RJ407bm-rS1TCjGWKdiA33f5jMUC0/export?format=csv&gid=2128634233"

@st.cache_data(ttl=600)
def load_data(sheet_url: str):
    df = pd.read_csv(sheet_url)

    # Standardization for column names between sheets
    rename_dict = {}
    if 'Age, M' in df.columns:
        rename_dict['Age, M'] = 'Age_M'
    if 'cre' in df.columns:
        rename_dict['cre'] = 'Cre'
    if 'ID' in df.columns and 'Ear_Tag' not in df.columns:
        rename_dict['ID'] = 'Ear_Tag'
    if 'Cage' in df.columns and 'Cage_ID' not in df.columns:
        rename_dict['Cage'] = 'Cage_ID'
    
    if rename_dict:
        df = df.rename(columns=rename_dict)

    # Datetime
    if 'Birth_date' in df.columns:
        df['Birth_date_clean'] = pd.to_datetime(df['Birth_date'], errors='coerce')
    else:
        df['Birth_date_clean'] = pd.NaT

    # Color
    if 'Color' in df.columns:
        df['Color_clean'] = df['Color'].astype(str).str.strip().str.lower()
        df['Color_clean'] = df['Color_clean'].replace({'nan': 'unspecified', '?': 'unspecified'})
    else:
        df['Color_clean'] = 'unspecified'

    # Age_M numeric processing
    if 'Age_M' in df.columns:
        df['Age_M_num'] = pd.to_numeric(df['Age_M'], errors='coerce')
    else:
        df['Age_M_num'] = None

    # Cre status
    if 'Cre' in df.columns:
        cre_col = df['Cre'].astype(str).str.strip().str.upper()
        df['Cre_status'] = cre_col.map({
            '1.0': 'Cre+', '1': 'Cre+', 'TRUE': 'Cre+',
            '0.0': 'Cre-', '0': 'Cre-', 'FALSE': 'Cre-'
        }).fillna('Unknown')
    else:
        df['Cre_status'] = 'Unknown'

    # Ear_Tag string
    if 'Ear_Tag' in df.columns:
        df['Ear_Tag_str'] = df['Ear_Tag'].astype(str).str.replace('.0', '', regex=False)
    else:
        df['Ear_Tag_str'] = ''

    return df


# 3. Data Source Selection
st.sidebar.title("📊 Data Source")

selected_source = st.sidebar.radio(
    "Select Sheet:",
    options=["Main Colony Sheet", "Live Mice Sheet 🐭"],
    index=0
)

current_url = URL_LIVE_MICE if selected_source == "Live Mice Sheet 🐭" else URL_ALL_MICE

try:
    df_raw = load_data(current_url)
except Exception as e:
    st.error(f"Error loading data from Google Spreadsheet: {e}")
    st.stop()


# 4. Filters Section
st.sidebar.title("🔍 Colony Filters")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

include_all_mice = st.sidebar.checkbox("Include ALL Mice (Ignore Filters)", value=False)

st.sidebar.divider()

# --- FILTER 1: Age_M Range ---
if 'Age_M_num' in df_raw.columns and not df_raw['Age_M_num'].dropna().empty:
    min_age = int(df_raw['Age_M_num'].min())
    max_age = int(df_raw['Age_M_num'].max())
    age_range = st.sidebar.slider(
        "Age_M (Months)",
        min_value=min_age,
        max_value=max_age,
        value=(min_age, max_age),
        disabled=include_all_mice
    )
else:
    age_range = None

# --- FILTER 2: Cre Status ---
all_cre = sorted(df_raw['Cre_status'].unique())
selected_cre = st.sidebar.multiselect(
    "Cre Status", 
    options=all_cre, 
    default=all_cre,
    disabled=include_all_mice
)

# --- FILTER 3: Genotype ---
all_genotypes = sorted([str(g) for g in df_raw['Genotype'].dropna().unique()]) if 'Genotype' in df_raw.columns else []
selected_genotypes = st.sidebar.multiselect(
    "Genotype", 
    options=all_genotypes, 
    default=all_genotypes,
    disabled=include_all_mice
)

# --- FILTER 4: Sex ---
all_sexes = sorted([str(s) for s in df_raw['Sex'].dropna().unique()]) if 'Sex' in df_raw.columns else []
selected_sexes = st.sidebar.multiselect(
    "Sex", 
    options=all_sexes, 
    default=all_sexes,
    disabled=include_all_mice
)

# --- FILTER 5: Color ---
all_colors = sorted([str(c) for c in df_raw['Color'].dropna().unique()]) if 'Color' in df_raw.columns else []
selected_colors = st.sidebar.multiselect(
    "Color", 
    options=all_colors, 
    default=all_colors,
    disabled=include_all_mice
)


# 5. Apply Filters
if include_all_mice:
    filtered_df = df_raw.copy()
else:
    filtered_df = df_raw.copy()

    # Filter Age_M
    if age_range and 'Age_M_num' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['Age_M_num'] >= age_range[0]) & 
            (filtered_df['Age_M_num'] <= age_range[1]) | 
            (filtered_df['Age_M_num'].isna())
        ]

    # Filter Cre
    if selected_cre:
        filtered_df = filtered_df[filtered_df['Cre_status'].isin(selected_cre)]

    # Filter Genotype
    if selected_genotypes and 'Genotype' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Genotype'].astype(str).isin(selected_genotypes)]

    # Filter Sex
    if selected_sexes and 'Sex' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Sex'].astype(str).isin(selected_sexes)]

    # Filter Color
    if selected_colors and 'Color' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Color'].astype(str).isin(selected_colors)]


# 6. Dashboard Section
title_prefix = "Live Mice" if selected_source == "Live Mice Sheet 🐭" else "Debbie Mice Colony"
st.title(f"🐭 {title_prefix} Analysis")
st.markdown(f"Interactive dashboard for analyzing colony structure and demographics (**{selected_source}**).")

# Key Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Mice (Filtered)", len(filtered_df))
col2.metric("Unique Cages", filtered_df['Cage_ID'].nunique() if 'Cage_ID' in filtered_df.columns else 0)
col3.metric("Females (f)", len(filtered_df[filtered_df['Sex'] == 'f']) if 'Sex' in filtered_df.columns else 0)
col4.metric("Males (m)", len(filtered_df[filtered_df['Sex'] == 'm']) if 'Sex' in filtered_df.columns else 0)

st.divider()

# Graphs & Tabs
tab1, tab2, tab3 = st.tabs(["📊 Genotypes & Demographics", "📈 Birth Dynamics", "📋 Raw Data"])

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
        st.subheader("Mice Distribution by Genotype and Sex")
        if not filtered_df.empty and 'Genotype' in filtered_df.columns and 'Sex' in filtered_df.columns:
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
        else:
            st.info("No data available to display Genotype distribution.")

        st.markdown("**Genotype Summary**")
        if not filtered_df.empty and 'Genotype' in filtered_df.columns:
            geno_summary = filtered_df['Genotype'].value_counts(dropna=False).reset_index()
            geno_summary.columns = ['Genotype', 'Count']
            
            total_mice = len(filtered_df)
            geno_summary['Percentage'] = (geno_summary['Count'] / total_mice * 100).map("{:.1f}%".format)
            
            st.dataframe(geno_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No data available for the selected filters.")

    with col_g2:
        st.subheader("Cre Status Ratio")
        if not filtered_df.empty:
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
    if not birth_df.empty and 'Genotype' in birth_df.columns:
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
    
    display_cols = ['Ear_Tag', 'Age_M', 'Genotype', 'Cre_status', 'Sex', 'Color', 'Birth_date', 'Cage_ID', 'Destiny']
    existing_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(filtered_df[existing_cols], use_container_width=True)
    
    csv_data = filtered_df[existing_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name="filtered_mice_colony.csv",
        mime="text/csv"
    )

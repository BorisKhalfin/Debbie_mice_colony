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
    # Spalsh screen container activated
    splash = st.empty()
    with splash.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                logo = Image.open("DTree.png")
                st.image(logo, use_column_width=True)
            except FileNotFoundError:
                st.info("Loading Laboratory Dashboard...")
            
            st.markdown("<h3 style='text-align: center;'>Loading Laboratory Dashboard...</h3>", unsafe_allow_html=True)
    
    # Delay 5 seconds
    time.sleep(5)
    
    # Reporting that the screen was shown to avoid loop
    st.session_state.splash_shown = True
    splash.empty()
    st.rerun()

# 1. Config
st.set_page_config(
    page_title="Debbie Mice Colony Dashboard",
    page_icon="🐭",
    layout="wide"
)

# 2. Cache & Data Loading from Google Sheets
@st.cache_data(ttl=600)  # Check for updates every 10 minutes
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1Eco6HKJJjpK4Q7RJ407bm-rS1TCjGWKdiA33f5jMUC0/export?format=csv&gid=1525111892"
    df = pd.read_csv(sheet_url)

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

    # Cre status
    if 'Cre' in df.columns:
        cre_numeric = pd.to_numeric(df['Cre'], errors='coerce')
        df['Cre_status'] = cre_numeric.map({1.0: 'Cre+', 0.0: 'Cre-'}).fillna('Unknown')
    else:
        df['Cre_status'] = 'Unknown'

    # Ear_Tag
    if 'Ear_Tag' in df.columns:
        df['Ear_Tag_str'] = df['Ear_Tag'].astype(str).str.replace('.0', '', regex=False)
    else:
        df['Ear_Tag_str'] = ''

    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Error loading data from Google Spreadsheet: {e}")
    st.stop()


# 3. Filters
st.sidebar.title("🔍 Colony Filters")

# Refresh data from Google Sheets
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

# Include ALL Mice and Ignore all Filters
include_all_mice = st.sidebar.checkbox("Include ALL Mice (Ignore Filters)", value=False)

# Unknown DOB display or ignore 
include_unknown_dob = st.sidebar.checkbox("Include Unknown Birth Dates", value=True)

st.sidebar.divider()

# Include ALL Mice and cancell all filters
all_genotypes = sorted([str(g) for g in df_raw['Genotype'].dropna().unique()]) if 'Genotype' in df_raw.columns else []
selected_genotypes = st.sidebar.multiselect(
    "Genotype", 
    options=all_genotypes, 
    default=all_genotypes,
    disabled=include_all_mice
)

all_sexes = sorted([str(s) for s in df_raw['Sex'].dropna().unique()]) if 'Sex' in df_raw.columns else []
selected_sexes = st.sidebar.multiselect(
    "Sex", 
    options=all_sexes, 
    default=all_sexes,
    disabled=include_all_mice
)

all_cre = sorted(df_raw['Cre_status'].unique())
selected_cre = st.sidebar.multiselect(
    "Cre Status", 
    options=all_cre, 
    default=all_cre,
    disabled=include_all_mice
)

# DOB filter
valid_dates = df_raw['Birth_date_clean'].dropna()
if not valid_dates.empty:
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    date_range = st.sidebar.date_input(
        "Birth Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        disabled=include_all_mice
    )
else:
    date_range = None

all_cages = sorted([str(c) for c in df_raw['Cage_ID'].dropna().unique()]) if 'Cage_ID' in df_raw.columns else []
selected_cages = st.sidebar.multiselect(
    "Cage ID (Optional)", 
    options=all_cages, 
    default=[],
    disabled=include_all_mice
)

search_tag = st.sidebar.text_input("Search Ear Tag / Parent ID", "", disabled=include_all_mice).strip()

# 4. Filters applied
if include_all_mice:
    # All tails together even if some data missing
    filtered_df = df_raw.copy()
else:
    filtered_df = df_raw.copy()

    if selected_genotypes and 'Genotype' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Genotype'].astype(str).isin(selected_genotypes)]

    if selected_sexes and 'Sex' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Sex'].astype(str).isin(selected_sexes)]

    if selected_cre:
        filtered_df = filtered_df[filtered_df['Cre_status'].isin(selected_cre)]

    # All DOB, include unknown ones
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        date_mask = (
            (filtered_df['Birth_date_clean'].dt.date >= start_d) & 
            (filtered_df['Birth_date_clean'].dt.date <= end_d)
        )
        if include_unknown_dob:
            date_mask = date_mask | filtered_df['Birth_date_clean'].isna()
        
        filtered_df = filtered_df[date_mask]

    if selected_cages and 'Cage_ID' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Cage_ID'].astype(str).isin(selected_cages)]

    if search_tag:
        tag_match = filtered_df['Ear_Tag_str'].str.contains(search_tag, case=False, na=False) if 'Ear_Tag_str' in filtered_df.columns else pd.Series(False, index=filtered_df.index)
        father_match = filtered_df['Father'].astype(str).str.contains(search_tag, case=False, na=False) if 'Father' in filtered_df.columns else pd.Series(False, index=filtered_df.index)
        mother_match = filtered_df['Mother'].astype(str).str.contains(search_tag, case=False, na=False) if 'Mother' in filtered_df.columns else pd.Series(False, index=filtered_df.index)
        filtered_df = filtered_df[tag_match | father_match | mother_match]

# 5. Dashboard
st.title("🐭 Debbie Mice Colony Analysis")
st.markdown("Interactive dashboard for analyzing colony structure, genotypes, and demographics.")

# Key Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Mice (Filtered)", len(filtered_df))
col2.metric("Unique Cages", filtered_df['Cage_ID'].nunique() if 'Cage_ID' in filtered_df.columns else 0)
col3.metric("Females (f)", len(filtered_df[filtered_df['Sex'] == 'f']) if 'Sex' in filtered_df.columns else 0)
col4.metric("Males (m)", len(filtered_df[filtered_df['Sex'] == 'm']) if 'Sex' in filtered_df.columns else 0)

st.divider()

# Graphs
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

        # Table
        st.markdown("**Genotype Summary**")
        if not filtered_df.empty and 'Genotype' in filtered_df.columns:
            geno_summary = filtered_df['Genotype'].value_counts(dropna=False).reset_index()
            geno_summary.columns = ['Genotype', 'Count']
            
            total_mice = len(filtered_df)
            geno_summary['Percentage'] = (geno_summary['Count'] / total_mice * 100).map("{:.1f}%".format)
            
            st.dataframe(
                geno_summary,
                use_container_width=True,
                hide_index=True
            )
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
    
    display_cols = ['Ear_Tag', 'Genotype', 'Cre_status', 'Flox_1', 'Flox_2', 'Sex', 'Color', 'Birth_date', 'Cage_ID', 'Breeding_cage', 'Father', 'Mother']
    existing_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(filtered_df[existing_cols], use_container_width=True)
    
    csv_data = filtered_df[existing_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name="filtered_mice_colony.csv",
        mime="text/csv"
    )

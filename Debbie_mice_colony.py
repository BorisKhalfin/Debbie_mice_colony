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

# 2. Cache & Data Loading from Google Sheets
URL_ALL_MICE = "https://docs.google.com/spreadsheets/d/1Eco6HKJJjpK4Q7RJ407bm-rS1TCjGWKdiA33f5jMUC0/export?format=csv&gid=1525111892"
URL_LIVE_MICE = "https://docs.google.com/spreadsheets/d/1Eco6HKJJjpK4Q7RJ407bm-rS1TCjGWKdiA33f5jMUC0/export?format=csv&gid=2128634233"
URL_EXP_MICE = "https://docs.google.com/spreadsheets/d/1Eco6HKJJjpK4Q7RJ407bm-rS1TCjGWKdiA33f5jMUC0/export?format=csv&gid=659844600"

@st.cache_data(ttl=600)  # Check for updates every 10 minutes
def load_data(sheet_url: str):
    df = pd.read_csv(sheet_url)

    # Clean dates
    if 'Birth_date' in df.columns:
        df['Birth_date_clean'] = pd.to_datetime(df['Birth_date'], errors='coerce')
    else:
        df['Birth_date_clean'] = pd.NaT

    if 'Destiny date' in df.columns:
        df['Destiny_date_clean'] = pd.to_datetime(df['Destiny date'], errors='coerce')
    else:
        df['Destiny_date_clean'] = pd.NaT

    # Clean Color
    if 'Color' in df.columns:
        df['Color_clean'] = df['Color'].astype(str).str.strip().str.lower()
        df['Color_clean'] = df['Color_clean'].replace({'nan': 'unspecified', '?': 'unspecified'})
    else:
        df['Color_clean'] = 'unspecified'

    # Cre status
    if 'Cre' in df.columns:
        cre_col = df['Cre'].astype(str).str.strip().str.upper()
        df['Cre_status'] = cre_col.map({'1.0': 'Cre+', '1': 'Cre+', 'TRUE': 'Cre+', '0.0': 'Cre-', '0': 'Cre-', 'FALSE': 'Cre-'}).fillna('Unknown')
    elif 'cre' in df.columns:
        cre_col = df['cre'].astype(str).str.strip().str.upper()
        df['Cre_status'] = cre_col.map({'1.0': 'Cre+', '1': 'Cre+', 'TRUE': 'Cre+', '0.0': 'Cre-', '0': 'Cre-', 'FALSE': 'Cre-'}).fillna('Unknown')
    else:
        df['Cre_status'] = 'Unknown'

    # Ear_Tag / ID
    if 'Ear_Tag' in df.columns:
        df['Ear_Tag_str'] = df['Ear_Tag'].astype(str).str.replace('.0', '', regex=False)
    elif 'ID' in df.columns:
        df['Ear_Tag_str'] = df['ID'].astype(str).str.replace('.0', '', regex=False)
        df['Ear_Tag'] = df['ID']
    else:
        df['Ear_Tag_str'] = ''

    # Cage mapping fallback
    if 'Cage' in df.columns and 'Cage_ID' not in df.columns:
        df['Cage_ID'] = df['Cage']

    # Age_M numeric
    if 'Age_M' in df.columns:
        df['Age_M_num'] = pd.to_numeric(df['Age_M'], errors='coerce')

    return df


# 3. Sidebar - Source Selection
st.sidebar.title("📊 Data for Panda")

selected_source = st.sidebar.radio(
    "Select mice to see and analyze:",
    options=["All mice ever", "At our service 🐭", "Experiments 2026-2027"],
    index=0
)

if selected_source == "At our service 🐭":
    current_url = URL_LIVE_MICE
elif selected_source == "Experiments 2026-2027":
    current_url = URL_EXP_MICE
else:
    current_url = URL_ALL_MICE

try:
    df_raw = load_data(current_url)
except Exception as e:
    st.error(f"Error loading data from Google Spreadsheet: {e}")
    st.stop()


# ---------------------------------------------------------
# 4. Sidebar Filters (Fixed default to include ALL 1555 mice)
# ---------------------------------------------------------
st.sidebar.title("🔍 Colony Filters")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

# Include ALL Mice override
include_all_mice = st.sidebar.checkbox("Include ALL Mice (Ignore Filters)", value=False)
include_unknown_dob = st.sidebar.checkbox("Include Unknown Birth Dates", value=True)

st.sidebar.divider()

# Genotype Filter
all_genotypes = sorted([str(g) for g in df_raw['Genotype'].dropna().unique()]) if 'Genotype' in df_raw.columns else []
selected_genotypes = st.sidebar.multiselect(
    "Genotype", 
    options=all_genotypes, 
    default=all_genotypes,
    disabled=include_all_mice
)

# Sex Filter
all_sexes = sorted([str(s) for s in df_raw['Sex'].dropna().unique()]) if 'Sex' in df_raw.columns else []
selected_sexes = st.sidebar.multiselect(
    "Sex", 
    options=all_sexes, 
    default=all_sexes,
    disabled=include_all_mice
)

# Cre Filter
all_cre = sorted(df_raw['Cre_status'].unique())
selected_cre = st.sidebar.multiselect(
    "Cre Status", 
    options=all_cre, 
    default=all_cre,
    disabled=include_all_mice
)

# Color Filter (if present)
if 'Color' in df_raw.columns:
    all_colors = sorted([str(c) for c in df_raw['Color'].dropna().unique()])
    selected_colors = st.sidebar.multiselect(
        "Color", 
        options=all_colors, 
        default=all_colors,
        disabled=include_all_mice
    )
else:
    all_colors, selected_colors = [], []

# Destiny Filter (if present)
if 'Destiny' in df_raw.columns:
    all_destinies = sorted([str(d) for d in df_raw['Destiny'].dropna().unique()])
    selected_destinies = st.sidebar.multiselect(
        "Destiny", 
        options=all_destinies, 
        default=all_destinies,
        disabled=include_all_mice
    )
else:
    all_destinies, selected_destinies = [], []

# DOB Filter
valid_dates = df_raw['Birth_date_clean'].dropna()
if not valid_dates.empty and selected_source != "Experiments 2026-2027":
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

# Cage Filter
cage_col = 'Cage_ID' if 'Cage_ID' in df_raw.columns else ('Cage' if 'Cage' in df_raw.columns else None)
all_cages = sorted([str(c) for c in df_raw[cage_col].dropna().unique()]) if cage_col else []
selected_cages = st.sidebar.multiselect(
    "Cage ID (Optional)", 
    options=all_cages, 
    default=[],
    disabled=include_all_mice
)

search_tag = st.sidebar.text_input("Search Ear Tag / Parent ID", "", disabled=include_all_mice).strip()

# ---------------------------------------------------------
# 5. Apply Filters (Preserves NaNs & full dataset by default)
# ---------------------------------------------------------
filtered_df = df_raw.copy()

if not include_all_mice:
    # Filter Genotype ONLY if user deselected something
    if 'Genotype' in filtered_df.columns and len(selected_genotypes) < len(all_genotypes):
        filtered_df = filtered_df[
            filtered_df['Genotype'].astype(str).isin(selected_genotypes) | filtered_df['Genotype'].isna()
        ]

    # Filter Sex ONLY if user deselected something
    if 'Sex' in filtered_df.columns and len(selected_sexes) < len(all_sexes):
        filtered_df = filtered_df[
            filtered_df['Sex'].astype(str).isin(selected_sexes) | filtered_df['Sex'].isna()
        ]

    # Filter Cre ONLY if user deselected something
    if len(selected_cre) < len(all_cre):
        filtered_df = filtered_df[filtered_df['Cre_status'].isin(selected_cre)]

    # Filter Color ONLY if user deselected something
    if 'Color' in filtered_df.columns and len(selected_colors) < len(all_colors):
        filtered_df = filtered_df[
            filtered_df['Color'].astype(str).isin(selected_colors) | filtered_df['Color'].isna()
        ]

    # Filter Destiny ONLY if user deselected something
    if 'Destiny' in filtered_df.columns and len(selected_destinies) < len(all_destinies):
        filtered_df = filtered_df[
            filtered_df['Destiny'].astype(str).isin(selected_destinies) | filtered_df['Destiny'].isna()
        ]

    # Date Range Filter
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        date_mask = (
            (filtered_df['Birth_date_clean'].dt.date >= start_d) & 
            (filtered_df['Birth_date_clean'].dt.date <= end_d)
        )
        if include_unknown_dob:
            date_mask = date_mask | filtered_df['Birth_date_clean'].isna()
        filtered_df = filtered_df[date_mask]

    # Cage Filter
    if selected_cages and cage_col:
        filtered_df = filtered_df[filtered_df[cage_col].astype(str).isin(selected_cages)]

    # Search Tag
    if search_tag:
        tag_match = filtered_df['Ear_Tag_str'].str.contains(search_tag, case=False, na=False) if 'Ear_Tag_str' in filtered_df.columns else pd.Series(False, index=filtered_df.index)
        father_match = filtered_df['Father'].astype(str).str.contains(search_tag, case=False, na=False) if 'Father' in filtered_df.columns else pd.Series(False, index=filtered_df.index)
        mother_match = filtered_df['Mother'].astype(str).str.contains(search_tag, case=False, na=False) if 'Mother' in filtered_df.columns else pd.Series(False, index=filtered_df.index)
        parents_match = filtered_df['Parents'].astype(str).str.contains(search_tag, case=False, na=False) if 'Parents' in filtered_df.columns else pd.Series(False, index=filtered_df.index)
        filtered_df = filtered_df[tag_match | father_match | mother_match | parents_match]

# 6. Dashboard Render
title_prefix = selected_source
st.title(f"🐭 {title_prefix} Analysis")
st.markdown(f"Interactive dashboard for analyzing colony structure, genotypes, and demographics (**{selected_source}**).")

# Key Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Mice (Filtered)", len(filtered_df))
col2.metric("Females (f)", len(filtered_df[filtered_df['Sex'] == 'f']) if 'Sex' in filtered_df.columns else 0)
col3.metric("Males (m)", len(filtered_df[filtered_df['Sex'] == 'm']) if 'Sex' in filtered_df.columns else 0)

if 'Age_M_num' in filtered_df.columns and not filtered_df['Age_M_num'].dropna().empty:
    avg_age = filtered_df['Age_M_num'].mean()
    col4.metric("Avg Age (Months)", f"{avg_age:.1f}")
elif cage_count_col := ('Cage_ID' if 'Cage_ID' in filtered_df.columns else ('Cage' if 'Cage' in filtered_df.columns else None)):
    col4.metric("Unique Cages", filtered_df[cage_count_col].nunique())
else:
    col4.metric("Cre+", len(filtered_df[filtered_df['Cre_status'] == 'Cre+']))

st.divider()

# Layout setup for Plotly graphs
white_layout = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    xaxis=dict(showgrid=True, gridcolor='#E5E5E5', linecolor='black'),
    yaxis=dict(showgrid=True, gridcolor='#E5E5E5', linecolor='black'),
    font=dict(color='black')
)

# Tabs switching based on selected source
if selected_source == "Experiments 2026-2027":
    tab1, tab2, tab3 = st.tabs(["📊 Experiments 2026-2027", "📈 Experiment Dynamics", "📋 Raw Data"])
else:
    tab1, tab2, tab3 = st.tabs(["📊 Genotypes & Demographics", "📈 Birth Dynamics", "📋 Raw Data"])

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

        # Breakdown by Destiny if Experimental Sheet
        if selected_source == "Experiments 2026-2027" and 'Destiny' in filtered_df.columns:
            st.subheader("Distribution by Destiny")
            destiny_counts = filtered_df['Destiny'].value_counts().reset_index()
            destiny_counts.columns = ['Destiny', 'Count']
            fig_dest = px.bar(
                destiny_counts,
                x='Destiny',
                y='Count',
                color='Destiny',
                title="Mice Allocation across Experimental Destinies"
            )
            fig_dest.update_layout(**white_layout)
            st.plotly_chart(fig_dest, use_container_width=True)
        else:
            st.markdown("**Genotype Summary**")
            if not filtered_df.empty and 'Genotype' in filtered_df.columns:
                geno_summary = filtered_df['Genotype'].value_counts(dropna=False).reset_index()
                geno_summary.columns = ['Genotype', 'Count']
                
                total_mice = len(filtered_df)
                geno_summary['Percentage'] = (geno_summary['Count'] / total_mice * 100).map("{:.1f}%".format)
                
                st.dataframe(geno_summary, use_container_width=True, hide_index=True)

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

        if selected_source == "Experiments 2026-2027" and 'Age_M_num' in filtered_df.columns:
            st.subheader("Age Distribution (Months)")
            fig_age = px.histogram(
                filtered_df,
                x='Age_M_num',
                nbins=15,
                color='Sex',
                title="Lifespan duration"
            )
            fig_age.update_layout(**white_layout)
            st.plotly_chart(fig_age, use_container_width=True)

with tab2:
    if selected_source == "Experiments 2026-2027":
        st.subheader("Experiment Dynamics (by Destiny Date)")
        exp_df = filtered_df.dropna(subset=['Destiny_date_clean']).copy()
        if not exp_df.empty:
            exp_df['YearMonth'] = exp_df['Destiny_date_clean'].dt.to_period('M').astype(str)
            
            if 'Destiny' in exp_df.columns:
                timeline = exp_df.groupby(['YearMonth', 'Destiny']).size().reset_index(name='Count')
                fig_time = px.line(
                    timeline, 
                    x='YearMonth', 
                    y='Count', 
                    color='Destiny',
                    markers=True,
                    title="Monthly Mice Allocation by Experiment (Destiny)"
                )
            else:
                timeline = exp_df.groupby('YearMonth').size().reset_index(name='Count')
                fig_time = px.line(
                    timeline, 
                    x='YearMonth', 
                    y='Count', 
                    markers=True,
                    title="Monthly Mice Count in Experiments"
                )
            fig_time.update_layout(**white_layout)
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("No valid 'Destiny date' entries found to plot dynamics.")
    else:
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
    
    if selected_source == "Experiments 2026-2027":
        display_cols = ['Ear_Tag', 'Age_M', 'Cre', 'Cre_status', 'Genotype', 'Sex', 'Color', 'Destiny', 'Destiny date']
    else:
        display_cols = ['Ear_Tag', 'ID', 'Genotype', 'Cre_status', 'Flox_1', 'Flox_2', 'Floxlox allel 1', 'Floxlox allel 2', 'Sex', 'Color', 'Birth_date', 'Cage_ID', 'Cage', 'Breeding_cage', 'Father', 'Mother', 'Parents', 'Destiny']
    
    existing_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(filtered_df[existing_cols], use_container_width=True)
    
    csv_data = filtered_df[existing_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name=f"filtered_mice_{selected_source.lower().replace(' ', '_')}.csv",
        mime="text/csv"
    )

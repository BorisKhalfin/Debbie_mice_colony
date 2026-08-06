import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Config
st.set_page_config(
    page_title="Debbie Mice Colony Dashboard",
    page_icon="🐭",
    layout="wide"
)

# 2. Cache
@st.cache_data(ttl=600)  # ttl=600 Refresh every 10 min
def load_data():
    sheets = {
       
        "Fertility": "1525111892",
        
    }

    base_url = "https://docs.google.com/spreadsheets/d/1Eco6HKJJjpK4Q7RJ407bm-rS1TCjGWKdiA33f5jMUC0/export?format=csv&gid="

    dataframes = {}
    for name, gid in sheets.items():
        url = base_url + gid
        dataframes[name] = pd.read_csv(url)
    
    # Datetime
    df['Birth_date_clean'] = pd.to_datetime(df['Birth_date'], errors='coerce')
    
    # Color
    if 'Color' in df.columns:
        df['Color_clean'] = df['Color'].astype(str).str.strip().str.lower()
        df['Color_clean'] = df['Color_clean'].replace({'nan': 'unspecified', '?': 'unspecified'})
    else:
        df['Color_clean'] = 'unspecified'
        
    # Cre from boolean to +/-
    df['Cre_status'] = df['Cre'].map({1.0: 'Cre+', 0.0: 'Cre-'}).fillna('Unknown')
    
    # Ear_Tag
    df['Ear_Tag_str'] = df['Ear_Tag'].astype(str).str.replace('.0', '', regex=False)
    
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"File unavailable 'Debbie_mice_colony.xlsx': {e}")
    st.stop()

# 3. Filters
st.sidebar.title("🔍 Colony Filters")

# Genotype filter
all_genotypes = sorted([str(g) for g in df_raw['Genotype'].dropna().unique()])
selected_genotypes = st.sidebar.multiselect(
    "Genotype", 
    options=all_genotypes, 
    default=all_genotypes
)

# Sex filter
all_sexes = sorted([str(s) for s in df_raw['Sex'].dropna().unique()])
selected_sexes = st.sidebar.multiselect(
    "Sex", 
    options=all_sexes, 
    default=all_sexes
)

# Cre filter
all_cre = sorted(df_raw['Cre_status'].unique())
selected_cre = st.sidebar.multiselect(
    "Cre Status", 
    options=all_cre, 
    default=all_cre
)

# DOB filter
valid_dates = df_raw['Birth_date_clean'].dropna()
min_date = valid_dates.min().date()
max_date = valid_dates.max().date()

date_range = st.sidebar.date_input(
    "Birth Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Cage filter
all_cages = sorted([str(c) for c in df_raw['Cage_ID'].dropna().unique()])
selected_cages = st.sidebar.multiselect(
    "Cage ID (Optional)", 
    options=all_cages, 
    default=[]
)

# Parental filter
search_tag = st.sidebar.text_input("Search Ear Tag / Parent ID", "").strip()

# 4. Filters applied
filtered_df = df_raw.copy()

if selected_genotypes:
    filtered_df = filtered_df[filtered_df['Genotype'].astype(str).isin(selected_genotypes)]

if selected_sexes:
    filtered_df = filtered_df[filtered_df['Sex'].astype(str).isin(selected_sexes)]

if selected_cre:
    filtered_df = filtered_df[filtered_df['Cre_status'].isin(selected_cre)]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
    filtered_df = filtered_df[
        (filtered_df['Birth_date_clean'].dt.date >= start_d) & 
        (filtered_df['Birth_date_clean'].dt.date <= end_d)
    ]

if selected_cages:
    filtered_df = filtered_df[filtered_df['Cage_ID'].astype(str).isin(selected_cages)]

if search_tag:
    tag_match = filtered_df['Ear_Tag_str'].str.contains(search_tag, case=False, na=False)
    father_match = filtered_df['Father'].astype(str).str.contains(search_tag, case=False, na=False)
    mother_match = filtered_df['Mother'].astype(str).str.contains(search_tag, case=False, na=False)
    filtered_df = filtered_df[tag_match | father_match | mother_match]

# 5. Dashboard
st.title("🐭 Debbie Mice Colony Analysis")
st.markdown("Interactive dashboard for analyzing colony structure, genotypes, and demographics.")

# Key Metrics)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Mice (Filtered)", len(filtered_df))
col2.metric("Unique Cages", filtered_df['Cage_ID'].nunique())
col3.metric("Females (f)", len(filtered_df[filtered_df['Sex'] == 'f']))
col4.metric("Males (m)", len(filtered_df[filtered_df['Sex'] == 'm']))

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

        # Table
        st.markdown("**Genotype Summary**")
        if not filtered_df.empty:
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
    
    # Columns
    display_cols = ['Ear_Tag', 'Genotype', 'Cre_status', 'Flox_1', 'Flox_2', 'Sex', 'Color', 'Birth_date', 'Cage_ID', 'Breeding_cage', 'Father', 'Mother']
    existing_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(filtered_df[existing_cols], use_container_width=True)
    
    # CSV Download
    csv_data = filtered_df[existing_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name="filtered_mice_colony.csv",
        mime="text/csv"
    )

import streamlit as st
import pandas as pd

# Configure the mobile-friendly page layout
st.set_page_config(page_title="Team Outlet Dashboard", layout="wide")

# Fetch credentials from Streamlit Secrets
EXCEL_URL = st.secrets["sharepoint"]["file_url"]
SHEET_NAME = st.secrets["sharepoint"]["sheet_name"]

# Cache the data for 10 minutes so the app loads instantly for the team
@st.cache_data(ttl=600) 
def load_data():
    # Read the data from the SharePoint Excel file
    df = pd.read_excel(EXCEL_URL, sheet_name=SHEET_NAME)
    
    # Remove any accidental spaces at the beginning or end of column names
    df.columns = df.columns.str.strip()
    
    # Convert Account Number to string to prevent commas in the display
    if 'Account Number' in df.columns:
        df['Account Number'] = df['Account Number'].astype(str).str.replace(r'\.0$', '', regex=True)
        
    return df

st.title("📊 WB Trade Claim Details")

try:
    df = load_data()
    
    st.subheader("Filter Rows")
    
    # --- ROW FILTERS ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Month Filter
        if 'Month' in df.columns:
            months = df['Month'].dropna().unique().tolist()
            selected_month = st.selectbox("Select Month:", ["All"] + months)
            if selected_month != "All":
                df = df[df['Month'] == selected_month]

        # ASM Filter
        if 'Asm' in df.columns:
            asms = df['Asm'].dropna().unique().tolist()
            selected_asm = st.selectbox("Select ASM:", ["All"] + asms)
            if selected_asm != "All":
                df = df[df['Asm'] == selected_asm]
            
    with col2:
        # Payment Status Filter
        if 'Payment Status' in df.columns:
            statuses = df['Payment Status'].dropna().unique().tolist()
            selected_status = st.selectbox("Select Payment Status:", ["All"] + statuses)
            if selected_status != "All":
                df = df[df['Payment Status'] == selected_status]

        # TSE REV Filter
        if 'TSE REV' in df.columns:
            tses = df['TSE REV'].dropna().unique().tolist()
            selected_tse = st.selectbox("Select TSE REV:", ["All"] + tses)
            if selected_tse != "All":
                df = df[df['TSE REV'] == selected_tse]
                
        # Payment To Filter
        if 'Payment To' in df.columns:
            payment_tos = df['Payment To'].dropna().unique().tolist()
            selected_payment_to = st.selectbox("Select Payment To:", ["All"] + payment_tos)
            if selected_payment_to != "All":
                df = df[df['Payment To'] == selected_payment_to]

    with col3:
        # Free text search for Outlet Name
        if 'Outlet Name' in df.columns:
            search_outlet = st.text_input("🔍 Search by Outlet Name:", "")
            if search_outlet:
                df = df[df['Outlet Name'].str.contains(search_outlet, case=False, na=False)]
                
            # Dropdown selection for Outlet Name
            outlets = df['Outlet Name'].dropna().unique().tolist()
            selected_outlet = st.selectbox("Or Select Specific Outlet:", ["All"] + outlets)
            if selected_outlet != "All":
                df = df[df['Outlet Name'] == selected_outlet]
    
    st.divider()
    st.subheader("Outlet Payment & Bank Status")
    
    base_cols = [
        'Month', 'Outlet Name', 'Lic ID', 'Payment To', 'Claim Amount', 
        'Payment Status', 'Payment Date', 'UTR NO', 'Bank Name', 'Account Number', 
        'IFSC Code'
    ]
    
    available_cols = [col for col in base_cols if col in df.columns]
    
    selected_cols = st.multiselect(
        "⚙️ Choose Columns to Display:",
        options=available_cols,
        default=available_cols
    )
    
    if selected_cols:
        st.dataframe(df[selected_cols], use_container_width=True, hide_index=True)
    else:
        st.warning("Please select at least one column to display.")
    
except Exception as e:
    st.error("Error loading data from SharePoint. Please check your network connection or SharePoint file permissions.")
    st.write(f"Technical details: {e}")

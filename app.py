import io
import pandas as pd
import requests
import streamlit as st

# Configure the mobile-friendly page layout
st.set_page_config(page_title="Team Outlet Dashboard", layout="wide")

# Fetch credentials from Streamlit Secrets
EXCEL_URL = st.secrets["sharepoint"]["file_url"]
DEFAULT_SHEET = st.secrets["sharepoint"]["sheet_name"]


# Cache the data for 10 minutes, with a manual clear via Refresh
@st.cache_data(ttl=600)
def load_workbook_data(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  response = requests.get(url, headers=headers)
  if response.status_code != 200:
    raise Exception(
        f"Failed to download file. Status code: {response.status_code}"
    )

  excel_bytes = io.BytesIO(response.content)
  all_sheets = pd.read_excel(excel_bytes, sheet_name=None)
  return all_sheets


st.title("📊 WB Trade Claim & KYC Details")

try:
  # Load all sheets from workbook
  sheets_dict = load_workbook_data(EXCEL_URL)
  available_sheet_names = list(sheets_dict.keys())

  # --- SIDEBAR CONTROLS ---
  st.sidebar.header("🛠️ Dashboard Controls")

  # Manual Refresh Button
  if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

  st.sidebar.divider()
  st.sidebar.subheader("📁 Select Sheet Tab:")

  # Initialize session state for active sheet if not present
  if "selected_sheet" not in st.session_state:
    st.session_state.selected_sheet = (
        DEFAULT_SHEET
        if DEFAULT_SHEET in available_sheet_names
        else available_sheet_names[0]
    )

  # Render all sheets as buttons in the sidebar
  for sheet in available_sheet_names:
    btn_label = f"📍 {sheet}" if st.session_state.selected_sheet == sheet else sheet
    if st.sidebar.button(btn_label, key=f"sheet_btn_{sheet}"):
      st.session_state.selected_sheet = sheet
      st.rerun()

  # Get the dataframe for the selected sheet
  selected_sheet = st.session_state.selected_sheet
  df = sheets_dict[selected_sheet].copy()

  # Remove any accidental spaces at the beginning or end of column names
  df.columns = df.columns.str.strip()

  # --- EXCLUDE SPECIFIC COLUMNS ---
  columns_to_remove = [
      "Licence Copy Submitted",
      "Current Year Licence Copy Submitted (2025-26)",
  ]
  for col in columns_to_remove:
    if col in df.columns:
      df = df.drop(columns=[col])

  # Convert Account Number to string to prevent formatting errors in display
  if "Account Number" in df.columns:
    df["Account Number"] = (
        df["Account Number"].astype(str).str.replace(r"\.0$", "", regex=True)
    )

  st.subheader(f"Active Sheet: {selected_sheet}")
  st.subheader("Filter Rows")

  # --- ROW FILTERS (ASM Name, TSE Name, License No) ---
  col1, col2, col3 = st.columns(3)

  with col1:
    # ASM Name Filter
    asm_col = next(
        (
            c
            for c in df.columns
            if c.lower() in ["asm name", "asm", "area sales manager"]
        ),
        None,
    )
    if asm_col:
      asms = df[asm_col].dropna().unique().tolist()
      selected_asm = st.selectbox(f"Select {asm_col}:", ["All"] + asms)
      if selected_asm != "All":
        df = df[df[asm_col] == selected_asm]

  with col2:
    # TSE Name Filter
    tse_col = next(
        (
            c
            for c in df.columns
            if c.lower()
            in ["tse name", "tse rev", "tse", "territory sales executive"]
        ),
        None,
    )
    if tse_col:
      tses = df[tse_col].dropna().unique().tolist()
      selected_tse = st.selectbox(f"Select {tse_col}:", ["All"] + tses)
      if selected_tse != "All":
        df = df[df[tse_col] == selected_tse]

  with col3:
    # License No Filter
    lic_col = next(
        (
            c
            for c in df.columns
            if c.lower()
            in ["license no", "licence no", "lic id", "licid", "license id"]
        ),
        None,
    )
    if lic_col:
      lic_ids = df[lic_col].dropna().unique().tolist()
      lic_ids = [str(x) for x in lic_ids]
      selected_lic = st.selectbox("Select License No:", ["All"] + lic_ids)
      if selected_lic != "All":
        df = df[df[lic_col].astype(str) == selected_lic]

  # --- OUTLET REFERENCE SEARCH & DROPDOWN SELECTION ---
  outlet_col = next(
      (
          c
          for c in df.columns
          if c.lower()
          in ["outlet reference", "outlet name", "outlet", "customer name"]
      ),
      None,
  )
  if outlet_col:
    st.markdown("---")
    search_col1, search_col2 = st.columns(2)

    with search_col1:
      # Get unique list of outlets for suggestion/autocompletion reference
      outlet_list = df[outlet_col].dropna().astype(str).unique().tolist()
      search_outlet = st.selectbox(
          "🔍 Search Outlet Reference (Select or type to filter):",
          ["All"] + outlet_list,
      )
      if search_outlet != "All":
        df = df[df[outlet_col].astype(str) == search_outlet]

    with search_col2:
      outlets = df[outlet_col].dropna().unique().tolist()
      selected_outlet = st.selectbox(
          "Or Select Specific Outlet Reference:", ["All"] + outlets
      )
      if selected_outlet != "All":
        df = df[df[outlet_col] == selected_outlet]

  st.divider()

  # --- ROW COUNT / SEARCH REFERENCE ---
  total_rows = len(df)
  st.info(
      f"📌 **Search Reference:** Showing **{total_rows}** matching records out"
      f" of the sheet data."
  )

  st.subheader("Sheet Data & Records")

  # --- COLUMN VISIBILITY (SHOW ALL REMAINING COLUMNS BY DEFAULT) ---
  all_columns = df.columns.tolist()

  selected_cols = st.multiselect(
      "⚙️ Choose Columns to Display (All columns selected by default):",
      options=all_columns,
      default=all_columns,
  )

  if selected_cols:
    st.dataframe(df[selected_cols], use_container_width=True, hide_index=True)
  else:
    st.warning("Please select at least one column to display.")

except Exception as e:
  st.error(
      "Error loading data from SharePoint. Please check your network connection"
      " or SharePoint file permissions."
  )
  st.write(f"Technical details: {e}")

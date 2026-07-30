import io
from datetime import datetime, time
import pandas as pd
import requests
import streamlit as st

# Configure the mobile-friendly page layout
st.set_page_config(page_title="Team Outlet Dashboard", layout="wide")

# Fetch credentials from Streamlit Secrets
EXCEL_URL = st.secrets["sharepoint"]["file_url"]
DEFAULT_SHEET = st.secrets["sharepoint"]["sheet_name"]


# Cache the data. We include a dynamic time key based on whether 9:00 PM today has passed
# so that the cache automatically expires/refreshes post 9 PM daily.
@st.cache_data(ttl=3600)
def load_workbook_data(url, refresh_key):
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


# Helper function to convert dataframe into an in-memory Excel (.xlsx) file download
def convert_df_to_excel(df):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="Filtered_Data")
  processed_data = output.getvalue()
  return processed_data


st.title("📊 WB Trade Claim & KYC Details")

try:
  # --- AUTO-REFRESH LOGIC FOR 9:00 PM DAILY ---
  now = datetime.now()
  if now.time() >= time(21, 0):
    current_refresh_key = f"{now.date()}_post_21"
  else:
    current_refresh_key = f"{now.date()}_pre_21"

  # Load all sheets from workbook using the dynamic daily key
  sheets_dict = load_workbook_data(EXCEL_URL, current_refresh_key)
  available_sheet_names = list(sheets_dict.keys())

  # --- SIDEBAR CONTROLS ---
  st.sidebar.header("🛠️ Dashboard Controls")

  # Manual Refresh Button
  if st.sidebar.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.rerun()

  st.sidebar.divider()

  # --- EXTERNAL LINK TAB ---
  st.sidebar.markdown(
      "🔗 **[Go to Sale](https://wbsale.streamlit.app/)**", unsafe_allow_html=True
  )

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

  # --- DYNAMIC ROW FILTERS BASED ON SHEET TYPE ---
  sheet_lower = selected_sheet.lower()
  is_first_three = (
      selected_sheet in available_sheet_names[:3]
      if len(available_sheet_names) >= 3
      else True
  )
  is_payment_sheet = (
      "trade payment details" in sheet_lower
      or "marketing payment details" in sheet_lower
  )

  if is_payment_sheet:
    # 6 columns for Payment Details sheets
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
      month_col = next(
          (c for c in df.columns if c.lower() in ["month", "months", "period"]),
          None,
      )
      if month_col:
        months = df[month_col].dropna().unique().tolist()
        selected_month = st.selectbox(f"Select {month_col}:", ["All"] + months)
        if selected_month != "All":
          df = df[df[month_col] == selected_month]

    with col2:
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

    with col3:
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

    with col4:
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

    with col5:
      pay_to_col = next(
          (
              c
              for c in df.columns
              if c.lower() in ["payment to", "pay to", "payment_to"]
          ),
          None,
      )
      if pay_to_col:
        pay_tos = df[pay_to_col].dropna().unique().tolist()
        selected_pay_to = st.selectbox(
            f"Select {pay_to_col}:", ["All"] + pay_tos
        )
        if selected_pay_to != "All":
          df = df[df[pay_to_col] == selected_pay_to]

    with col6:
      pay_status_col = next(
          (
              c
              for c in df.columns
              if c.lower() in ["payment status", "status", "payment_status"]
          ),
          None,
      )
      if pay_status_col:
        pay_statuses = df[pay_status_col].dropna().unique().tolist()
        selected_status = st.selectbox(
            f"Select {pay_status_col}:", ["All"] + pay_statuses
        )
        if selected_status != "All":
          df = df[df[pay_status_col] == selected_status]

  elif is_first_three:
    # 4 columns for first 3 tabs (Month + ASM Name + TSE Name + License No)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
      month_col = next(
          (c for c in df.columns if c.lower() in ["month", "months", "period"]),
          None,
      )
      if month_col:
        months = df[month_col].dropna().unique().tolist()
        selected_month = st.selectbox(f"Select {month_col}:", ["All"] + months)
        if selected_month != "All":
          df = df[df[month_col] == selected_month]

    with col2:
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

    with col3:
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

    with col4:
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

  else:
    # Standard 3 columns for other sheets
    col1, col2, col3 = st.columns(3)

    with col1:
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

  # --- COLUMN DISPLAY CONTROL ---
  all_columns = df.columns.tolist()
  show_all_cols = st.checkbox(
      "✅ Display All Columns Automatically", value=True
  )

  if show_all_cols:
    selected_cols = all_columns
  else:
    selected_cols = st.multiselect(
        "⚙️ Choose Specific Columns to Display:",
        options=all_columns,
        default=all_columns,
    )

  if selected_cols:
    filtered_df = df[selected_cols]
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # --- EXCEL (.xlsx) DOWNLOAD BUTTON ---
    excel_data = convert_df_to_excel(filtered_df)
    st.download_button(
        label="📥 Download Filtered Data as Excel (.xlsx)",
        data=excel_data,
        file_name=f"{selected_sheet}_Filtered_Data.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
  else:
    st.warning("Please select at least one column to display.")

except Exception as e:
  st.error(
      "Error loading data from SharePoint. Please check your network connection"
      " or SharePoint file permissions."
  )
  st.write(f"Technical details: {e}")

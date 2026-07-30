import io
import pandas as pd
import requests
import streamlit as st

# Configure the mobile-friendly page layout
st.set_page_config(page_title="Team Outlet Dashboard", layout="wide")

# Fetch credentials from Streamlit Secrets
EXCEL_URL = st.secrets["sharepoint"]["file_url"]
DEFAULT_SHEET = st.secrets["sharepoint"]["sheet_name"]


# Cache the data for 10 minutes, but it can be manually cleared via the Refresh button
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
  # Read all sheets into a dictionary of DataFrames
  all_sheets = pd.read_excel(excel_bytes, sheet_name=None)
  return all_sheets


st.title("📊 WB Trade Claim Details")

try:
  # Load all sheets from workbook
  sheets_dict = load_workbook_data(EXCEL_URL)
  available_sheet_names = list(sheets_dict.keys())

  # --- SIDEBAR CONTROLS ---
  st.sidebar.header("🛠️ Dashboard Controls")

  # Manual Refresh Button
  if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()  # Clears the 10-minute cache
    st.rerun()  # Triggers an immediate app reload

  st.sidebar.divider()

  # Select Sheet Tab from Sidebar
  default_idx = (
      available_sheet_names.index(DEFAULT_SHEET)
      if DEFAULT_SHEET in available_sheet_names
      else 0
  )
  selected_sheet = st.sidebar.selectbox(
      "📁 Select Sheet Tab:", available_sheet_names, index=default_idx
  )

  # Get the dataframe for the selected sheet
  df = sheets_dict[selected_sheet].copy()

  # Remove any accidental spaces at the beginning or end of column names
  df.columns = df.columns.str.strip()

  # Convert Account Number to string to prevent formatting/comma errors in display
  if "Account Number" in df.columns:
    df["Account Number"] = (
        df["Account Number"].astype(str).str.replace(r"\.0$", "", regex=True)
    )

  st.subheader(f"Active Sheet: {selected_sheet}")
  st.subheader("Filter Rows")

  # --- ROW FILTERS ---
  col1, col2, col3 = st.columns(3)

  with col1:
    # Month Filter
    if "Month" in df.columns:
      months = df["Month"].dropna().unique().tolist()
      selected_month = st.selectbox("Select Month:", ["All"] + months)
      if selected_month != "All":
        df = df[df["Month"] == selected_month]

    # ASM Filter
    if "Asm" in df.columns:
      asms = df["Asm"].dropna().unique().tolist()
      selected_asm = st.selectbox("Select ASM:", ["All"] + asms)
      if selected_asm != "All":
        df = df[df["Asm"] == selected_asm]

  with col2:
    # Payment Status Filter
    if "Payment Status" in df.columns:
      statuses = df["Payment Status"].dropna().unique().tolist()
      selected_status = st.selectbox("Select Payment Status:", ["All"] + statuses)
      if selected_status != "All":
        df = df[df["Payment Status"] == selected_status]

    # TSE REV Filter
    if "TSE REV" in df.columns:
      tses = df["TSE REV"].dropna().unique().tolist()
      selected_tse = st.selectbox("Select TSE REV:", ["All"] + tses)
      if selected_tse != "All":
        df = df[df["TSE REV"] == selected_tse]

    # Payment To Filter
    if "Payment To" in df.columns:
      payment_tos = df["Payment To"].dropna().unique().tolist()
      selected_payment_to = st.selectbox("Select Payment To:", ["All"] + payment_tos)
      if selected_payment_to != "All":
        df = df[df["Payment To"] == selected_payment_to]

  with col3:
    # Free text search for Outlet Name
    if "Outlet Name" in df.columns:
      search_outlet = st.text_input("🔍 Search by Outlet Name:", "")
      if search_outlet:
        df = df[df["Outlet Name"].str.contains(search_outlet, case=False, na=False)]

      # Dropdown selection for Outlet Name
      outlets = df["Outlet Name"].dropna().unique().tolist()
      selected_outlet = st.selectbox("Or Select Specific Outlet:", ["All"] + outlets)
      if selected_outlet != "All":
        df = df[df["Outlet Name"] == selected_outlet]

  st.divider()
  st.subheader("Outlet Payment & Bank Status")

  base_cols = [
      "Month",
      "Outlet Name",
      "Lic ID",
      "Payment To",
      "Claim Amount",
      "Payment Status",
      "Payment Date",
      "UTR NO",
      "Bank Name",
      "Account Number",
      "IFSC Code",
  ]

  available_cols = [col for col in base_cols if col in df.columns]
  # Fallback to all columns if base_cols don't match the chosen sheet layout
  if not available_cols:
    available_cols = df.columns.tolist()

  selected_cols = st.multiselect(
      "⚙️ Choose Columns to Display:",
      options=df.columns.tolist(),
      default=available_cols,
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

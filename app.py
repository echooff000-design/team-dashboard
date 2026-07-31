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


# Cache the data with a dynamic time key based on whether 9:00 PM today has passed
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

  # --- AUTHENTICATION CHECK USING "Users" SHEET ---
  if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

  if not st.session_state.logged_in:
    # Modern Dark Theme Login Page matching user's design reference (without logo)
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #0e1117;
            }
            .login-card {
                background-color: #161b22;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
                max-width: 450px;
                margin: 40px auto;
                border: 1px solid #30363d;
            }
            .login-title {
                color: #ffffff;
                font-size: 28px;
                font-weight: 700;
                text-align: center;
                margin-bottom: 8px;
            }
            .login-subtitle {
                color: #8b949e;
                font-size: 14px;
                text-align: center;
                margin-bottom: 30px;
            }
            .stTextInput label {
                color: #c9d1d9 !important;
                font-weight: 500;
            }
            .stTextInput input {
                background-color: #0d1117 !important;
                color: #ffffff !important;
                border: 1px solid #30363d !important;
                border-radius: 8px !important;
                padding: 10px 14px !important;
            }
            .stTextInput input:focus {
                border-color: #58a6ff !important;
                box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15) !important;
            }
            .stButton button {
                background-color: #21262d !important;
                color: #ffffff !important;
                border: 1px solid #30363d !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                padding: 10px 20px !important;
                transition: background-color 0.2s ease;
            }
            .stButton button:hover {
                background-color: #30363d !important;
                border-color: #8b949e !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
      st.markdown(
          """
            <div class="login-card">
                <div class="login-title">Welcome Back</div>
                <div class="login-subtitle">Sign in to access WB Sale Data Dashboard</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

      with st.form("login_form"):
        userid_input = st.text_input("User ID", placeholder="Enter your User ID")
        password_input = st.text_input(
            "Password", type="password", placeholder="Enter your password"
        )
        st.markdown("<br>", unsafe_allow_html=True)
        submit_button = st.form_submit_button("Sign In", use_container_width=True)

        if submit_button:
          users_sheet_key = next(
              (s for s in available_sheet_names if s.strip().lower() == "users"),
              None,
          )

          if users_sheet_key:
            users_df = sheets_dict[users_sheet_key].copy()
            users_df.columns = users_df.columns.str.strip()

            id_col = next(
                (c for c in users_df.columns if c.lower() == "user_id"), None
            )
            p_col = next(
                (
                    c
                    for c in users_df.columns
                    if c.lower() in ["password", "pass", "pwd"]
                ),
                None,
            )
            name_col = next(
                (c for c in users_df.columns if c.lower() == "name"), None
            )

            if id_col and p_col:
              matched_user = users_df[
                  (users_df[id_col].astype(str).str.strip() == userid_input.strip())
                  & (
                      users_df[p_col].astype(str).str.strip()
                      == password_input.strip()
                  )
              ]

              if not matched_user.empty:
                st.session_state.logged_in = True
                if name_col and not pd.isna(matched_user.iloc[0][name_col]):
                  st.session_state.username = str(matched_user.iloc[0][name_col])
                else:
                  st.session_state.username = userid_input
                st.success("Login successful! Redirecting...")
                st.rerun()
              else:
                st.error("Invalid User ID or Password.")
            else:
              st.error(
                  "Could not locate 'User_ID' or 'Password' columns in the"
                  " 'Users' sheet."
              )
          else:
            st.error(
                "The 'Users' sheet was not found in your uploaded workbook."
            )

    st.stop()

  # --- MAIN DASHBOARD (LOADS AFTER SUCCESSFUL LOGIN) ---
  st.title("📊 WB Trade Claim & KYC Details")

  # --- SIDEBAR CONTROLS ---
  st.sidebar.header("🛠️ Dashboard Controls")
  st.sidebar.write(f"👤 Logged in as: **{st.session_state.get('username')}**")

  if st.sidebar.button("🔒 Logout"):
    st.session_state.logged_in = False
    st.rerun()

  st.sidebar.divider()

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

  # Filter out the 'Users' sheet from sidebar tabs
  data_sheet_names = [
      s for s in available_sheet_names if s.strip().lower() != "users"
  ]

  # Initialize session state for active sheet if not present
  if "selected_sheet" not in st.session_state:
    st.session_state.selected_sheet = (
        DEFAULT_SHEET
        if DEFAULT_SHEET in data_sheet_names
        else data_sheet_names[0]
    )

  # Render all sheets as buttons in the sidebar
  for sheet in data_sheet_names:
    btn_label = f"📍 {sheet}" if st.session_state.selected_sheet == sheet else sheet
    if st.sidebar.button(btn_label, key=f"sheet_btn_{sheet}"):
      st.session_state.selected_sheet = sheet
      st.rerun()

  # Get the dataframe for the selected sheet
  selected_sheet = st.session_state.selected_sheet
  df = sheets_dict[selected_sheet].copy()

  # Remove any accidental spaces at the beginning or end of column names
  df.columns = df.columns.str.strip()

  # --- KEEP A CLEAN UNMODIFIED COPY FOR FILTERS BEFORE DROPPING TABLE COLUMNS ---
  df_filters = df.copy()

  # --- CUSTOM TRANSFORMATIONS & COLUMN MODIFICATIONS PER SHEET TYPE ---
  sheet_lower = selected_sheet.lower()
  is_payment_sheet = (
      "trade payment details" in sheet_lower
      or "marketing payment details" in sheet_lower
  )
  is_gift_sheet = "gift claim details" in sheet_lower

  if is_payment_sheet:
    claim_col = next(
        (c for c in df.columns if c.lower() in ["claim amount", "claim_amount"]),
        None,
    )
    net_col = next(
        (c for c in df.columns if c.lower() in ["net amount", "net_amount"]),
        None,
    )

    if claim_col and net_col:
      df[claim_col] = df[net_col]

    # Remove ASM, TSE Rev, ID, Net Amount, Payment Status from table display
    cols_to_drop_payment = [
        "ID",
        "ASM",
        "TSE Rev",
        "Net Amount",
        "Payment Status",
        "New ASM Remarks",
        "Licence Copy Submitted",
        "Current Year Licence Copy Submitted (2025-26)",
    ]
    for col in cols_to_drop_payment:
      match_col = next(
          (c for c in df.columns if c.lower() == col.lower()), None
      )
      if match_col:
        df = df.drop(columns=[match_col])

  elif is_gift_sheet:
    cols_to_drop_gift = ["ASM", "TSE", "ASM Name", "TSE Name"]
    for col in cols_to_drop_gift:
      match_col = next(
          (c for c in df.columns if c.lower() == col.lower()), None
      )
      if match_col:
        df = df.drop(columns=[match_col])

    columns_to_remove = [
        "Licence Copy Submitted",
        "Current Year Licence Copy Submitted (2025-26)",
    ]
    for col in columns_to_remove:
      if col in df.columns:
        df = df.drop(columns=[col])
  else:
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
  is_first_three = (
      selected_sheet in data_sheet_names[:3]
      if len(data_sheet_names) >= 3
      else True
  )

  if is_payment_sheet:
    # 6 filters for Payment Details sheets (Month, ASM Name, TSE Name, License No, Payment To, Payment Status)
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
      month_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["month", "months", "period"]
          ),
          None,
      )
      if month_col:
        months = df_filters[month_col].dropna().unique().tolist()
        selected_month = st.selectbox(f"Select {month_col}:", ["All"] + months)
        if selected_month != "All":
          mask = df_filters[month_col] == selected_month
          df = df[mask]
          df_filters = df_filters[mask]

    with col2:
      asm_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["asm name", "asm", "area sales manager"]
          ),
          None,
      )
      if asm_col:
        asms = df_filters[asm_col].dropna().unique().tolist()
        selected_asm = st.selectbox(f"Select {asm_col}:", ["All"] + asms)
        if selected_asm != "All":
          mask = df_filters[asm_col] == selected_asm
          df = df[mask]
          df_filters = df_filters[mask]

    with col3:
      tse_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower()
              in ["tse name", "tse rev", "tse", "territory sales executive"]
          ),
          None,
      )
      if tse_col:
        tses = df_filters[tse_col].dropna().unique().tolist()
        selected_tse = st.selectbox(f"Select {tse_col}:", ["All"] + tses)
        if selected_tse != "All":
          mask = df_filters[tse_col] == selected_tse
          df = df[mask]
          df_filters = df_filters[mask]

    with col4:
      lic_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower()
              in ["license no", "licence no", "lic id", "licid", "license id"]
          ),
          None,
      )
      if lic_col:
        lic_ids = df_filters[lic_col].dropna().unique().tolist()
        lic_ids = [str(x) for x in lic_ids]
        selected_lic = st.selectbox("Select License No:", ["All"] + lic_ids)
        if selected_lic != "All":
          mask = df_filters[lic_col].astype(str) == selected_lic
          df = df[mask]
          df_filters = df_filters[mask]

    with col5:
      pay_to_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["payment to", "pay to", "payment_to"]
          ),
          None,
      )
      if pay_to_col:
        pay_tos = df_filters[pay_to_col].dropna().unique().tolist()
        selected_pay_to = st.selectbox(
            f"Select {pay_to_col}:", ["All"] + pay_tos
        )
        if selected_pay_to != "All":
          mask = df_filters[pay_to_col] == selected_pay_to
          df = df[mask]
          df_filters = df_filters[mask]

    with col6:
      pay_status_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["payment status", "status", "payment_status"]
          ),
          None,
      )
      if pay_status_col:
        pay_statuses = df_filters[pay_status_col].dropna().unique().tolist()
        selected_status = st.selectbox(
            f"Select {pay_status_col}:", ["All"] + pay_statuses
        )
        if selected_status != "All":
          mask = df_filters[pay_status_col] == selected_status
          df = df[mask]
          df_filters = df_filters[mask]

  elif is_gift_sheet:
    col1, col2 = st.columns(2)

    with col1:
      month_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["month", "months", "period"]
          ),
          None,
      )
      if month_col:
        months = df_filters[month_col].dropna().unique().tolist()
        selected_month = st.selectbox(f"Select {month_col}:", ["All"] + months)
        if selected_month != "All":
          mask = df_filters[month_col] == selected_month
          df = df[mask]
          df_filters = df_filters[mask]

    with col2:
      lic_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower()
              in ["license no", "licence no", "lic id", "licid", "license id"]
          ),
          None,
      )
      if lic_col:
        lic_ids = df_filters[lic_col].dropna().unique().tolist()
        lic_ids = [str(x) for x in lic_ids]
        selected_lic = st.selectbox("Select License No:", ["All"] + lic_ids)
        if selected_lic != "All":
          mask = df_filters[lic_col].astype(str) == selected_lic
          df = df[mask]
          df_filters = df_filters[mask]

  elif is_first_three:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
      month_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["month", "months", "period"]
          ),
          None,
      )
      if month_col:
        months = df_filters[month_col].dropna().unique().tolist()
        selected_month = st.selectbox(f"Select {month_col}:", ["All"] + months)
        if selected_month != "All":
          mask = df_filters[month_col] == selected_month
          df = df[mask]
          df_filters = df_filters[mask]

    with col2:
      asm_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["asm name", "asm", "area sales manager"]
          ),
          None,
      )
      if asm_col:
        asms = df_filters[asm_col].dropna().unique().tolist()
        selected_asm = st.selectbox(f"Select {asm_col}:", ["All"] + asms)
        if selected_asm != "All":
          mask = df_filters[asm_col] == selected_asm
          df = df[mask]
          df_filters = df_filters[mask]

    with col3:
      tse_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower()
              in ["tse name", "tse rev", "tse", "territory sales executive"]
          ),
          None,
      )
      if tse_col:
        tses = df_filters[tse_col].dropna().unique().tolist()
        selected_tse = st.selectbox(f"Select {tse_col}:", ["All"] + tses)
        if selected_tse != "All":
          mask = df_filters[tse_col] == selected_tse
          df = df[mask]
          df_filters = df_filters[mask]

    with col4:
      lic_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower()
              in ["license no", "licence no", "lic id", "licid", "license id"]
          ),
          None,
      )
      if lic_col:
        lic_ids = df_filters[lic_col].dropna().unique().tolist()
        lic_ids = [str(x) for x in lic_ids]
        selected_lic = st.selectbox("Select License No:", ["All"] + lic_ids)
        if selected_lic != "All":
          mask = df_filters[lic_col].astype(str) == selected_lic
          df = df[mask]
          df_filters = df_filters[mask]

  else:
    col1, col2, col3 = st.columns(3)

    with col1:
      asm_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower() in ["asm name", "asm", "area sales manager"]
          ),
          None,
      )
      if asm_col:
        asms = df_filters[asm_col].dropna().unique().tolist()
        selected_asm = st.selectbox(f"Select {asm_col}:", ["All"] + asms)
        if selected_asm != "All":
          mask = df_filters[asm_col] == selected_asm
          df = df[mask]
          df_filters = df_filters[mask]

    with col2:
      tse_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower()
              in ["tse name", "tse rev", "tse", "territory sales executive"]
          ),
          None,
      )
      if tse_col:
        tses = df_filters[tse_col].dropna().unique().tolist()
        selected_tse = st.selectbox(f"Select {tse_col}:", ["All"] + tses)
        if selected_tse != "All":
          mask = df_filters[tse_col] == selected_tse
          df = df[mask]
          df_filters = df_filters[mask]

    with col3:
      lic_col = next(
          (
              c
              for c in df_filters.columns
              if c.lower()
              in ["license no", "licence no", "lic id", "licid", "license id"]
          ),
          None,
      )
      if lic_col:
        lic_ids = df_filters[lic_col].dropna().unique().tolist()
        lic_ids = [str(x) for x in lic_ids]
        selected_lic = st.selectbox("Select License No:", ["All"] + lic_ids)
        if selected_lic != "All":
          mask = df_filters[lic_col].astype(str) == selected_lic
          df = df[mask]
          df_filters = df_filters[mask]

  # --- OUTLET REFERENCE SEARCH & DROPDOWN SELECTION ---
  outlet_col = next(
      (
          c
          for c in df_filters.columns
          if c.lower()
          in ["outlet reference", "outlet name", "outlet", "customer name"]
      ),
      None,
  )
  if outlet_col:
    st.markdown("---")
    search_col1, search_col2 = st.columns(2)

    with search_col1:
      outlet_list = df_filters[outlet_col].dropna().astype(str).unique().tolist()
      search_outlet = st.selectbox(
          "🔍 Search Outlet Reference (Select or type to filter):",
          ["All"] + outlet_list,
      )
      if search_outlet != "All":
        mask = df_filters[outlet_col].astype(str) == search_outlet
        df = df[mask]
        df_filters = df_filters[mask]

    with search_col2:
      outlets = df_filters[outlet_col].dropna().unique().tolist()
      selected_outlet = st.selectbox(
          "Or Select Specific Outlet Reference:", ["All"] + outlets
      )
      if selected_outlet != "All":
        mask = df_filters[outlet_col] == selected_outlet
        df = df[mask]
        df_filters = df_filters[mask]

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
    selected_cols = st.native_multiselect(
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

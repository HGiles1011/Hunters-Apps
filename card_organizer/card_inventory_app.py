import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, timedelta
import pandas as pd
import plotly.express as px

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

@st.cache_resource
def get_worksheet():
    try:
        sheet = client.open_by_key("15zMGzqJ1IYsh7i8q8WVaMrHsq0L7ddv9BYsmDHgUHSM")
        return sheet.worksheet("Inventory")
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheet: {e}")
        st.stop()
        return None

inventory_ws = get_worksheet()

@st.cache_data(ttl=60)
def get_inventory_data():
    if inventory_ws is None:
        return [], []
    try:
        records = inventory_ws.get_all_records()
        header = inventory_ws.row_values(1)
        return records, header
    except Exception as e:
        st.error(f"❌ Error loading inventory from Google Sheet: {e}")
        return [], []

def clear_inventory_cache():
    st.cache_data.clear()

if 'refresh_data_needed' not in st.session_state:
    st.session_state.refresh_data_needed = False
if 'current_tab_index' not in st.session_state:
    st.session_state.current_tab_index = 0

if st.session_state.refresh_data_needed:
    clear_inventory_cache()
    st.session_state.refresh_data_needed = False
records, header = get_inventory_data()

st.set_page_config(page_title="Card Inventory Manager", layout="wide")
st.title("📇 Trading Card Inventory App")

tab_options = ["➕ Add New Card", "✏️ Update Card Information", "📊 Profit Tracker"]
selected_tab = st.radio("Select View", tab_options, index=st.session_state.current_tab_index, horizontal=True)

def safe_float_conversion(money_str):
    if isinstance(money_str, (int, float)):
        return float(money_str)
    if isinstance(money_str, str):
        cleaned_str = money_str.replace('$', '').replace(',', '')
        try:
            return float(cleaned_str)
        except ValueError:
            return 0.0
    return 0.0

# --- Tab 1 ---
if selected_tab == "➕ Add New Card":
    st.header("➕ Add New Card Entry")

    # --- Calculate next available Lot Number ---
    current_lot_numbers = []
    for record in records:
        try:
            lot_num = int(record.get('Lot Number', 0))
            current_lot_numbers.append(lot_num)
        except (ValueError, TypeError):
            continue
    
    next_lot_number = 1
    if current_lot_numbers:
        next_lot_number = max(current_lot_numbers) + 1
    # --- End Calculate next available Lot Number ---


    with st.form(key='add_card_form'):
        col1, col2, col3 = st.columns(3)

        set_name_options = ["Topps Chrome", "Topps Chrome Update", "Topps Chrome Cosmic", "Bowman Chrome", "Bowman Paper", "Topps Series 1", "Topps Heritage", "Topps Heritage Mini", "Topps Opening Day", "Topps Inception", "Bowman Inception", "Topps Big League", "Topps Dynasty", "Topps Gypsy Queen", "Topps Archive Signature Edition", "Topps Tier One", "Topps Finest", "Topps Series 2", "Topps Stadium Club", "Topps Museum Collection", "Topps Japan Edition", "Topps Allen & Ginter", "Topps Gold Label", "Topps Black Chrome", "Topps Pristine", "Topps Chrome Platinum Anniversary", "Topps Update Series", "Topps Heritage High Number", "Topps Five Star", "Bowman's Best", "Topps Triple Threads", "Bowman Sapphire Edition", "Topps Chrome Pro Debut", "Topps Pro Debut", "Topps Finest Flashbacks"]
        numbered_parallel_options = ["Base", "/499", "/299", "/250", "/199", "/150", "/99", "/75", "/71", "/50", "/25", "/10", "/5", "1/1", "Image Variation", "Case Hit", "Insert", "Purple"]
        year_options = list(range(date.today().year, 1949, -1))

        with col1:
            st.markdown("#### Card Details")
            player_name = st.text_input("Player Name")
            card_type = st.selectbox("Set Name", set_name_options)
            numbered_parallel = st.selectbox("Numbered/Parallel", numbered_parallel_options)
            cb_auto, cb_patch, cb_graded, cb_listed = st.columns(4)
            with cb_auto:
                auto = st.checkbox("Auto")
            with cb_patch:
                patch = st.checkbox("Patch")
            with cb_graded:
                graded = st.checkbox("Graded") 
            with cb_listed:
                listed = st.checkbox("Listed")

        with col2:
            st.markdown("#### Purchase & Origin")
            year = st.selectbox("Year", year_options)
            bought_from = st.text_input("Website (Bought From)")
            seller_name = st.text_input("Seller Name")

        with col3:
            st.markdown("#### Financials & ID")
            purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, format="%.2f")
            purchase_date = st.date_input("Date Purchased", value=date.today())
            lot_number = st.number_input("Lot Number", min_value=0, value=next_lot_number)

        st.write("---")
        submitted = st.form_submit_button("Submit Card Entry")

        if submitted:
            if not player_name.strip():
                st.error("❗ Player Name cannot be empty.")
            else:
                row = [player_name, card_type, numbered_parallel, "Yes" if auto else "No", 
                       "Yes" if patch else "No", year, "Yes" if graded else "No", bought_from, 
                       seller_name, f"${purchase_price:.2f}", 
                       str(purchase_date), "Yes" if listed else "No", int(lot_number)]
                try:
                    if inventory_ws:
                        inventory_ws.append_row(row)
                        st.success("✅ Card entry added to Google Sheet!")
                        st.session_state.refresh_data_needed = True
                        st.session_state.current_tab_index = 0
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to write to Google Sheet: {e}")

# --- Tab 2 ---
elif selected_tab == "✏️ Update Card Information":
    st.header("✏️ Update Card Information")

    card_options = ["--- Select a Card to Update ---"]
    card_gsheet_row_map = {}
    card_current_data_map = {}

    if not records:
        st.info("No cards found in inventory to update.")
    else:
        for i, record in enumerate(records):
            gsheet_row_number = i + 2
            display_name = f"{record.get('Player Name', 'N/A')} - {record.get('Year', 'N/A')} - {record.get('Set Name', 'N/A')} - {record.get('Numbered', 'N/A')} - {record.get('Purchase Price', 'N/A')} (Row {gsheet_row_number})"
            card_options.append(display_name)
            card_gsheet_row_map[display_name] = gsheet_row_number
            card_current_data_map[display_name] = record

    selected_card_display = st.selectbox("Select Card to Update", card_options, key='update_card_select')

    if selected_card_display != "--- Select a Card to Update ---":
        selected_gsheet_row_index = card_gsheet_row_map.get(selected_card_display)
        current_record = card_current_data_map.get(selected_card_display, {})

        # --- Update Listing Status Section (Now standalone and at top) ---
        st.markdown("#### Update Listing Status")
        with st.form(key='update_listed_form'):
            current_listed_status = current_record.get('Listed', 'No') == 'Yes'
            new_listed_status = st.checkbox("Is Listed?", value=current_listed_status)
            update_listed_submitted = st.form_submit_button("Update Listed Status")

            if update_listed_submitted and inventory_ws:
                try:
                    listed_col = header.index('Listed') + 1
                    new_listed_value = "Yes" if new_listed_status else "No"
                    
                    inventory_ws.update_cell(selected_gsheet_row_index, listed_col, new_listed_value)
                    st.success(f"✅ Card listing status updated to: **{new_listed_value}**!")
                    st.session_state.refresh_data_needed = True
                    st.session_state.current_tab_index = 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating listed status: {e}")
        # --- End Update Listing Status Section ---

        st.markdown("---") # Separator between status and sale info

        st.markdown("#### Update Sale Information")
        with st.form(key='update_sale_form'):
            sold_date = st.date_input("Sold Date", value=date.today())
            sold_price = st.number_input("Sold Price ($)", min_value=0.0, format="%.2f")
            sale_takeaway = st.number_input("Takeaway from Sale ($)", min_value=0.0, format="%.2f")
            update_submitted = st.form_submit_button("Update Sale Info")

            if update_submitted and inventory_ws:
                try:
                    sold_date_col = header.index('Sold Date') + 1
                    sold_price_col = header.index('Sold Price') + 1
                    takeaway_col = header.index('Takeaway') + 1
                    cells_to_update = [
                        gspread.Cell(selected_gsheet_row_index, sold_date_col, str(sold_date)),
                        gspread.Cell(selected_gsheet_row_index, sold_price_col, f"${sold_price:.2f}"),
                        gspread.Cell(selected_gsheet_row_index, takeaway_col, f"${sale_takeaway:.2f}")
                    ]
                    inventory_ws.update_cells(cells_to_update)
                    st.success("✅ Sale info updated!")
                    st.session_state.refresh_data_needed = True
                    st.session_state.current_tab_index = 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating sale info: {e}")

# --- Tab 3 ---
elif selected_tab == "📊 Profit Tracker":
    st.header("📊 Profit Tracker")
    if st.button("Refresh Profit Data"):
        st.session_state.refresh_data_needed = True
        st.session_state.current_tab_index = 2
        st.rerun()

    if not records:
        st.info("No records to calculate profit from.")
    else:
        try:
            df = pd.DataFrame(records)
            df['Purchase Price_num'] = df['Purchase Price'].apply(safe_float_conversion)
            df['Sold Price_num'] = df['Sold Price'].apply(safe_float_conversion)
            df['Takeaway_num'] = df['Takeaway'].apply(safe_float_conversion)
            df['Purchase Date_dt'] = pd.to_datetime(df['Date Purchased'], errors='coerce')
            df['Sold Date_dt'] = pd.to_datetime(df['Sold Date'], errors='coerce')

            df['Profit_Per_Item'] = df.apply(
                lambda row: row['Takeaway_num'] - row['Purchase Price_num']
                if pd.notna(row['Sold Date_dt']) else 0,
                axis=1
            )

            total_spent = sum(df['Purchase Price_num'])
            total_sold = sum(df['Sold Price_num'])
            total_profit = df['Profit_Per_Item'].sum()

            st.metric("Total Spent", f"${total_spent:.2f}")
            st.metric("Total Sold", f"${total_sold:.2f}")
            st.metric("Total Profit", f"${total_profit:.2f}")

            # ✅ CSV Download Button
            st.download_button(
                label="⬇️ Download Inventory as CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='card_inventory.csv',
                mime='text/csv'
            )

            st.markdown("---") # Separator for metrics and charts

            # --- Inventory Status (Pie Chart) - Moved to top ---
            st.subheader("📦 Inventory Status")
            status_data = pd.DataFrame({
                'Status': ['In Inventory', 'Sold'],
                'Count': [df['Sold Date_dt'].isna().sum(), df['Sold Date_dt'].notna().sum()]
            })
            fig_inventory = px.pie(status_data, values='Count', names='Status',
                                   title='Inventory vs. Sold', hole=0.3, template='plotly_white',
                                   hover_data={'Count': False, 'Status': False})
            fig_inventory.update_traces(hovertemplate='Status: %{label}<br>Count: %{value}<extra></extra>')
            fig_inventory.update_traces(textinfo='percent+label', textposition='outside',
                                         texttemplate='%{label}<br>%{percent}')
            fig_inventory.update_layout(uniformtext_minsize=10, uniformtext_mode='hide')
            st.plotly_chart(fig_inventory, use_container_width=True)
            # --- End Inventory Status ---

            st.markdown("---") # Separator between charts

            # --- Daily Spending Chart ---
            st.subheader("📈 Daily Spending")
            spending_data = df.dropna(subset=['Purchase Date_dt']).copy()
            spending_data['Purchase Day'] = spending_data['Purchase Date_dt'].dt.date
            daily_spending = spending_data.groupby('Purchase Day')['Purchase Price_num'].sum().reset_index()

            if not daily_spending.empty:
                fig_spending = px.bar(daily_spending, x='Purchase Day', y='Purchase Price_num',
                                      title='Total Spending Per Day', template='plotly_white',
                                      hover_data={'Purchase Day': False, 'Purchase Price_num': False}) 
                fig_spending.update_traces(hovertemplate='Total Spent: $%{y:.2f}<extra></extra>')
                fig_spending.update_layout(hovermode="x unified") 

                # Automatic 2-month zoom for Daily Spending
                if not daily_spending['Purchase Day'].empty:
                    max_date = daily_spending['Purchase Day'].max()
                    min_date_2_months_ago = max_date - timedelta(days=60) # Approximately 2 months
                    fig_spending.update_xaxes(range=[min_date_2_months_ago, max_date])

                st.plotly_chart(fig_spending, use_container_width=True)
            else:
                st.info("No purchase data for daily chart.")
            # --- End Daily Spending Chart ---

            st.markdown("---") # Separator between charts

            # --- Monthly Spending Chart ---
            st.subheader("📈 Monthly Spending")
            spending_data_monthly = df.dropna(subset=['Purchase Date_dt']).copy()
            # Sort by date before creating 'Purchase Month' to ensure correct period order
            spending_data_monthly = spending_data_monthly.sort_values(by='Purchase Date_dt')
            # Format month as "Mon YYYY" for better display
            spending_data_monthly['Purchase Month'] = spending_data_monthly['Purchase Date_dt'].dt.strftime('%b %Y')
            monthly_spending = spending_data_monthly.groupby('Purchase Month')['Purchase Price_num'].sum().reset_index()

            if not monthly_spending.empty:
                # To ensure chronological order on x-axis, re-index based on original month period
                monthly_spending['Sort Key'] = pd.to_datetime(monthly_spending['Purchase Month'], format='%b %Y')
                monthly_spending = monthly_spending.sort_values(by='Sort Key').drop(columns='Sort Key')

                fig_monthly_spending = px.bar(monthly_spending, x='Purchase Month', y='Purchase Price_num',
                                              title='Total Spending Per Month', template='plotly_white',
                                              hover_data={'Purchase Month': False, 'Purchase Price_num': False})
                # Custom hover template to show only total spent
                fig_monthly_spending.update_traces(hovertemplate='Total Spent: $%{y:.2f}<extra></extra>')
                fig_monthly_spending.update_layout(hovermode="x unified")

                # Automatic 2-year zoom for Monthly Spending
                if not monthly_spending['Purchase Month'].empty:
                    # Convert month strings back to datetime objects for range calculation
                    monthly_dates = pd.to_datetime(monthly_spending['Purchase Month'], format='%b %Y')
                    max_month_date = monthly_dates.max()
                    # Calculate 2 years ago from the latest month (approximately 730 days)
                    min_month_date_2_years_ago = max_month_date - timedelta(days=2*365)
                    fig_monthly_spending.update_xaxes(range=[min_month_date_2_years_ago, max_month_date])

                st.plotly_chart(fig_monthly_spending, use_container_width=True)
            else:
                st.info("No purchase data for monthly chart.")
            # --- End Monthly Spending Chart ---

            st.markdown("---") # Separator between charts

            # --- Cumulative Profit Trend Chart ---
            st.subheader("💰 Cumulative Profit Trend")
            profit_trend_data = df.dropna(subset=['Sold Date_dt']).copy()
            # Sort by Sold Date for correct cumulative sum calculation
            profit_trend_data = profit_trend_data.sort_values(by='Sold Date_dt')
            
            # Group by day and sum daily profits, then calculate cumulative sum
            daily_profit_sum = profit_trend_data.groupby('Sold Date_dt')['Profit_Per_Item'].sum().reset_index()
            daily_profit_sum['Cumulative Profit'] = daily_profit_sum['Profit_Per_Item'].cumsum()

            if not daily_profit_sum.empty:
                fig_profit = px.line(daily_profit_sum, x='Sold Date_dt', y='Cumulative Profit',
                                     title='Cumulative Profit Trend Over Time', template='plotly_white', markers=True,
                                     hover_data={'Sold Date_dt': False, 'Cumulative Profit': False})
                fig_profit.update_traces(hovertemplate='Cumulative Profit: $%{y:.2f}<extra></extra>')
                fig_profit.update_layout(hovermode="x unified")
                st.plotly_chart(fig_profit, use_container_width=True)
            else:
                st.info("No profit data for cumulative chart.")
            # --- End Cumulative Profit Trend Chart ---

        except Exception as e:
            st.error(f"❌ Error generating charts: {e}")
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
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

tab_options = ["➕ Add New Card", "✏️ Update Sale Info", "📊 Profit Tracker"]
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
    with st.form(key='add_card_form'):
        col1, col2, col3 = st.columns(3)

        set_name_options = ["Topps Chrome", "Topps Chrome Update", "Topps Series 1", "Topps Heritage", "Topps Heritage Mini", "Topps Opening Day", "Topps Inception", "Bowman Inception", "Topps Big League", "Topps Dynasty", "Topps Gypsy Queen", "Bowman", "Topps Archive Signature Edition", "Topps Tier One", "Topps Finest", "Topps Series 2", "Topps Stadium Club", "Topps Museum Collection", "Topps Japan Edition", "Topps Allen & Ginter", "Bowman Chrome", "Topps Gold Label", "Topps Black Chrome", "Topps Pristine", "Topps Chrome Platinum Anniversary", "Topps Update Series", "Topps Heritage High Number", "Topps Five Star", "Bowman Draft", "Bowman's Best", "Topps Triple Threads", "Bowman Sapphire Edition", "Topps Pro Debut", "Topps Finest Flashbacks"]
        numbered_parallel_options = ["None", "/499", "/299", "/250", "/199", "/150", "/99", "/75", "/50", "/25", "/10", "/5", "1/1", "Image Variation", "Case Hit", "Insert"]
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
            purchase_price = st.number_input("Bought Price ($)", min_value=0.0, format="%.2f")
            purchase_date = st.date_input("Date Purchased", value=date.today())
            lot_number = st.number_input("Lot Number", min_value=0)

        st.write("---")
        submitted = st.form_submit_button("Submit Card Entry")

        if submitted:
            if not player_name.strip():
                st.error("❗ Player Name cannot be empty.")
            else:
                row = [player_name, card_type, numbered_parallel, "Yes" if auto else "No", "Yes" if patch else "No", year, "Yes" if graded else "No", bought_from, seller_name, f"${purchase_price:.2f}", str(purchase_date), "Yes" if listed else "No", int(lot_number)]
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
elif selected_tab == "✏️ Update Sale Info":
    st.header("✏️ Update Sale Info")

    card_options = ["--- Select a Card to Update ---"]
    card_gsheet_row_map = {}

    if not records:
        st.info("No cards found in inventory to update.")
    else:
        for i, record in enumerate(records):
            gsheet_row_number = i + 2
            display_name = f"{record.get('Player Name', 'N/A')} - {record.get('Year', 'N/A')} - {record.get('Set Name', 'N/A')} - {record.get('Numbered', 'N/A')} - {record.get('Purchase Price', 'N/A')} (Row {gsheet_row_number})"
            card_options.append(display_name)
            card_gsheet_row_map[display_name] = gsheet_row_number

    selected_card_display = st.selectbox("Select Card to Update", card_options, key='update_card_select')
    if selected_card_display != "--- Select a Card to Update ---":
        selected_gsheet_row_index = card_gsheet_row_map.get(selected_card_display)
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

            st.markdown("---")
            st.subheader("📈 Monthly Spending")
            spending_data = df.dropna(subset=['Purchase Date_dt']).copy()
            spending_data['Purchase Month'] = spending_data['Purchase Date_dt'].dt.to_period('M').astype(str)
            monthly_spending = spending_data.groupby('Purchase Month')['Purchase Price_num'].sum().reset_index()
            if not monthly_spending.empty:
                fig_spending = px.bar(monthly_spending, x='Purchase Month', y='Purchase Price_num',
                                      title='Total Spending Per Month', template='plotly_white')
                st.plotly_chart(fig_spending, use_container_width=True)
            else:
                st.info("No purchase data for chart.")

            st.subheader("📦 Inventory Status")
            status_data = pd.DataFrame({
                'Status': ['In Inventory', 'Sold'],
                'Count': [df['Sold Date_dt'].isna().sum(), df['Sold Date_dt'].notna().sum()]
            })
            fig_inventory = px.pie(status_data, values='Count', names='Status',
                                   title='Inventory vs. Sold', hole=0.3, template='plotly_white')
            st.plotly_chart(fig_inventory, use_container_width=True)

            st.subheader("💰 Profit Trend")
            profit_trend_data = df.dropna(subset=['Sold Date_dt']).copy()
            profit_trend_data['Sale Month'] = profit_trend_data['Sold Date_dt'].dt.to_period('M').astype(str)
            monthly_profit = profit_trend_data.groupby('Sale Month')['Profit_Per_Item'].sum().reset_index()
            if not monthly_profit.empty:
                fig_profit = px.line(monthly_profit, x='Sale Month', y='Profit_Per_Item',
                                     title='Monthly Profit Trend', template='plotly_white', markers=True)
                st.plotly_chart(fig_profit, use_container_width=True)
            else:
                st.info("No profit data for chart.")

        except Exception as e:
            st.error(f"❌ Error generating charts: {e}")


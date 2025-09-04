import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, timedelta
import pandas as pd
import plotly.express as px

# --- Google Sheets Setup ---
# The provided service account key file must be in the same directory as the script.
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"❌ Error setting up Google Sheets credentials: {e}")
    st.info("Please make sure you have a valid 'credentials.json' file in the same directory as this script.")
    st.stop()

@st.cache_resource
def get_worksheet():
    """Connects to the Google Sheet and returns the Inventory worksheet."""
    try:
        # Replace the key with your actual Google Sheet key
        sheet = client.open_by_key("15zMGzqJ1IYsh7i8q8WVaMrHsq0L7ddv9BYsmDHgUHSM")
        return sheet.worksheet("Inventory")
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheet: {e}")
        st.info("Please verify the Google Sheet key and that the service account has access.")
        st.stop()
        return None

inventory_ws = get_worksheet()

@st.cache_data(ttl=60)
def get_inventory_data():
    """Fetches all records and headers from the inventory worksheet."""
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
    """Clears the Streamlit cache for inventory data."""
    st.cache_data.clear()

# Initialize session state for refreshing data and tracking the current tab
if 'refresh_data_needed' not in st.session_state:
    st.session_state.refresh_data_needed = False
if 'current_tab_index' not in st.session_state:
    st.session_state.current_tab_index = 0

# Check if a data refresh is needed and clear the cache if so
if st.session_state.refresh_data_needed:
    clear_inventory_cache()
    st.session_state.refresh_data_needed = False
records, header = get_inventory_data()

st.set_page_config(page_title="Card Inventory Manager", layout="wide")
st.title("📇 Trading Card Inventory App")

tab_options = ["➕ Add New Card", "✏️ Update Card Information", "📊 Profit Tracker", "📋 Cards Inventory"]
selected_tab = st.radio("Select View", tab_options, index=st.session_state.current_tab_index, horizontal=True)

def safe_float_conversion(money_str):
    """Safely converts a string with a dollar sign to a float."""
    if isinstance(money_str, (int, float)):
        return float(money_str)
    if isinstance(money_str, str):
        cleaned_str = money_str.replace('$', '').replace(',', '')
        try:
            return float(cleaned_str)
        except ValueError:
            return 0.0
    return 0.0

# --- Football Card Definitions ---
football_sets = ["Prizm", "Optic", "Select", "Mosaic", "Contenders", "Spectra", "Unparalleled", "Black", "Flawless", "National Treasures"]
football_parallels = [
    "Base", "Silver", "Green", "Green Scope", "Green Wave", "Green Ice", "Orange", "Orange /249", "Orange Scope", 
    "Orange Wave", "Orange Lazer", "Orange Ice", "Black & White Checker", "Red & Black Checker", "Red Pandora", 
    "Red Stars", "Red Camo", "Red", "Black Pandora", "Dragon Scale", "/99", "Gold /10", "Gold Vinyl /5", 
    "Green Shimmer /5", "Camo /25", "Hyper /25", "Red /299", "Blue /199","Purple /99", "Orange /75", "White /35", 
    "White /25", "Red & Yellow /44", "White Knight /3", "Black Finite 1/1", "Black Stars 1/1", "Gold Shimmer /10", 
    "Choice Nebula 1/1", "Downtown", "Manga (SSP)", "Color Blast (SSP)"
]

# --- Baseball Card Definitions ---
baseball_sets = ["Topps Chrome", "Topps Chrome Update", "Topps Chrome Cosmic", "Topps Chrome Logofractor", "Bowman Chrome", "Bowman Paper", "Topps Series 1", "Topps Heritage", "Topps Diamond Icons", "Topps Heritage Mini", "Topps Opening Day", "Topps Inception", "Bowman Inception", "Topps Big League", "Topps Dynasty", "Topps Gypsy Queen", "Topps Archive Signature Edition", "Topps Tier One", "Topps Finest", "Topps Series 2", "Topps Stadium Club", "Topps Museum Collection", "Topps Japan Edition", "Topps Allen & Ginter", "Topps Gold Label", "Topps Black Chrome", "Topps Pristine", "Topps Chrome Platinum Anniversary", "Topps Update Series", "Topps Heritage High Number", "Topps Five Star", "Bowman's Best", "Topps Triple Threads", "Bowman Sapphire Edition", "Topps Chrome Pro Debut", "Topps Pro Debut", "Topps Finest Flashbacks"]
baseball_parallels = ["Base", "/499", "/299", "/250", "/199", "/150", "/99", "/75", "/71", "/50", "/25", "/10", "/5", "1/1", "Image Variation", "Case Hit", "Insert", "Purple", "Raywave", "Refractor", "XFractor"]


# --- Tab 1: Add New Card ---
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

    # --- Sport Type Selection is placed OUTSIDE the form for reactivity ---
    st.markdown("#### Select Card Sport")
    sport_type = st.radio("Sport Type", ["Baseball", "Football"], index=0, horizontal=True, key='sport_type_selection')

    if sport_type == "Baseball":
        current_set_name_options = baseball_sets
        current_numbered_parallel_options = baseball_parallels
    else: # Football
        current_set_name_options = football_sets
        current_numbered_parallel_options = football_parallels
    # --- End Sport Type Selection ---

    with st.form(key='add_card_form'):
        col1, col2, col3 = st.columns(3)

        year_options = list(range(date.today().year, 1949, -1))

        with col1:
            st.markdown("#### Card Details")
            player_name = st.text_input("Player Name")
            # These selectboxes will use the options based on the sport_type selected above
            card_set_name = st.selectbox("Set Name", current_set_name_options)
            numbered_parallel = st.selectbox("Numbered/Parallel", current_numbered_parallel_options)
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
                # --- REMOVED sport_type from the list of values to append ---
                row = [player_name, card_set_name, numbered_parallel, "Yes" if auto else "No", 
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

# --- Tab 2: Update Card Information ---
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
            # --- REMOVED sport type from the display name for new records ---
            display_name = f"{record.get('Player Name', 'N/A')} - {record.get('Year', 'N/A')} - {record.get('Set Name', 'N/A')} - {record.get('Numbered', 'N/A')} - {record.get('Purchase Price', 'N/A')} (Row {gsheet_row_number})"
            card_options.append(display_name)
            card_gsheet_row_map[display_name] = gsheet_row_number
            card_current_data_map[display_name] = record

    selected_card_display = st.selectbox("Select Card to Update", card_options, key='update_card_select')

    if selected_card_display != "--- Select a Card to Update ---":
        selected_gsheet_row_index = card_gsheet_row_map.get(selected_card_display)
        current_record = card_current_data_map.get(selected_card_display, {})

        # --- New Form for Status Updates ---
        st.markdown("#### Update Status")
        with st.form(key='update_status_form'):
            col_listed, col_graded, _ = st.columns([1, 1, 6]) 
            with col_listed:
                current_listed_status = current_record.get('Listed', 'No') == 'Yes'
                new_listed_status = st.checkbox("Is Listed?", value=current_listed_status, key='listed_checkbox')
            with col_graded:
                current_graded_status = current_record.get('Graded', 'No') == 'Yes'
                new_graded_status = st.checkbox("Is Graded?", value=current_graded_status, key='graded_checkbox')
            
            status_update_submitted = st.form_submit_button("Update Card Status")

            if status_update_submitted and inventory_ws:
                try:
                    cells_to_update = []
                    
                    listed_col = header.index('Listed') + 1
                    new_listed_value = "Yes" if new_listed_status else "No"
                    cells_to_update.append(gspread.Cell(selected_gsheet_row_index, listed_col, new_listed_value))

                    graded_col = header.index('Graded') + 1
                    new_graded_value = "Yes" if new_graded_status else "No"
                    cells_to_update.append(gspread.Cell(selected_gsheet_row_index, graded_col, new_graded_value))
                    
                    inventory_ws.update_cells(cells_to_update)
                    st.success("✅ Card status updated!")
                    st.session_state.refresh_data_needed = True
                    st.session_state.current_tab_index = 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating card status: {e}")

        # --- Original Form for Sale Information ---
        st.markdown("#### Update Sale Information")
        with st.form(key='update_sale_info_form'):
            sold_date_val = pd.to_datetime(current_record.get('Sold Date')).date() if 'Sold Date' in current_record and current_record.get('Sold Date') else date.today()
            sold_price_val = safe_float_conversion(current_record.get('Sold Price', 0.0))
            sale_takeaway_val = safe_float_conversion(current_record.get('Takeaway', 0.0))

            sold_date = st.date_input("Sold Date", value=sold_date_val)
            sold_price = st.number_input("Sold Price ($)", min_value=0.0, format="%.2f", value=sold_price_val)
            sale_takeaway = st.number_input("Takeaway from Sale ($)", min_value=0.0, format="%.2f", value=sale_takeaway_val)
            
            sale_update_submitted = st.form_submit_button("Update Sale Information")

            if sale_update_submitted and inventory_ws:
                try:
                    cells_to_update = []
                    
                    sold_date_col = header.index('Sold Date') + 1
                    sold_price_col = header.index('Sold Price') + 1
                    takeaway_col = header.index('Takeaway') + 1
                    cells_to_update.append(gspread.Cell(selected_gsheet_row_index, sold_date_col, str(sold_date)))
                    cells_to_update.append(gspread.Cell(selected_gsheet_row_index, sold_price_col, f"${sold_price:.2f}"))
                    cells_to_update.append(gspread.Cell(selected_gsheet_row_index, takeaway_col, f"${sale_takeaway:.2f}"))
                    
                    inventory_ws.update_cells(cells_to_update)
                    st.success("✅ Sale information updated!")
                    st.session_state.refresh_data_needed = True
                    st.session_state.current_tab_index = 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating sale info: {e}")

# --- Tab 3: Profit Tracker ---
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

            st.download_button(
                label="⬇️ Download Inventory as CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='card_inventory.csv',
                mime='text/csv'
            )

            st.markdown("---")

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
            
            st.markdown("---")

            st.subheader("📈 Daily Spending")
            spending_data = df.dropna(subset=['Purchase Date_dt']).copy()
            spending_data['Purchase Day'] = spending_data['Purchase Date_dt'].dt.date
            daily_spending = spending_data.groupby('Purchase Day')['Purchase Price_num'].sum().reset_index()

            if not daily_spending.empty:
                fig_spending = px.bar(daily_spending, x='Purchase Day', y='Purchase Price_num',
                                       title='Total Spending Per Day', template='plotly_white',
                                       hover_data={'Purchase Day': False, 'Purchase Price_num': False}) 
                fig_spending.update_traces(hovertemplate='Date: %{x}<br>Total Spent: $%{y:.2f}<extra></extra>')
                fig_spending.update_layout(hovermode="x unified") 

                if not daily_spending['Purchase Day'].empty:
                    max_date = daily_spending['Purchase Day'].max()
                    min_date_2_months_ago = max_date - timedelta(days=60)
                    fig_spending.update_xaxes(range=[min_date_2_months_ago, max_date])

                st.plotly_chart(fig_spending, use_container_width=True)
            else:
                st.info("No purchase data for daily chart.")

            st.markdown("---")

            st.subheader("📈 Monthly Spending")
            spending_data_monthly = df.dropna(subset=['Purchase Date_dt']).copy()
            spending_data_monthly = spending_data_monthly.sort_values(by='Purchase Date_dt')
            spending_data_monthly['Purchase Month'] = spending_data_monthly['Purchase Date_dt'].dt.strftime('%b %Y')
            monthly_spending = spending_data_monthly.groupby('Purchase Month')['Purchase Price_num'].sum().reset_index()

            if not monthly_spending.empty:
                monthly_spending['Sort Key'] = pd.to_datetime(monthly_spending['Purchase Month'], format='%b %Y')
                monthly_spending = monthly_spending.sort_values(by='Sort Key').drop(columns='Sort Key')

                fig_monthly_spending = px.bar(monthly_spending, x='Purchase Month', y='Purchase Price_num',
                                               title='Total Spending Per Month', template='plotly_white',
                                               hover_data={'Purchase Month': False})
                fig_monthly_spending.update_traces(hovertemplate='Month: %{x}<br>Total Spent: $%{y:.2f}<extra></extra>')
                fig_monthly_spending.update_layout(hovermode="x unified")

                if not monthly_spending['Purchase Month'].empty:
                    monthly_dates = pd.to_datetime(monthly_spending['Purchase Month'], format='%b %Y')
                    max_month_date = monthly_dates.max()
                    min_month_date_2_years_ago = max_month_date - timedelta(days=2*365)
                    fig_monthly_spending.update_xaxes(range=[min_month_date_2_years_ago, max_month_date])

                st.plotly_chart(fig_monthly_spending, use_container_width=True)
            else:
                st.info("No purchase data for monthly chart.")

            st.markdown("---")

            st.subheader("💰 Cumulative Profit Trend")
            profit_trend_data = df.dropna(subset=['Sold Date_dt']).copy()
            profit_trend_data = profit_trend_data.sort_values(by='Sold Date_dt')
            
            daily_profit_sum = profit_trend_data.groupby('Sold Date_dt')['Profit_Per_Item'].sum().reset_index()
            daily_profit_sum['Cumulative Profit'] = daily_profit_sum['Profit_Per_Item'].cumsum()

            if not daily_profit_sum.empty:
                fig_profit = px.line(daily_profit_sum, x='Sold Date_dt', y='Cumulative Profit',
                                       title='Cumulative Profit Trend Over Time', template='plotly_white', markers=True,
                                       hover_data={'Sold Date_dt': False}) 
                fig_profit.update_traces(hovertemplate='Date: %{x|%b %d, %Y}<br>Cumulative Profit: $%{y:.2f}<extra></extra>')
                fig_profit.update_layout(hovermode="x unified", hoverlabel_namelength=-1)
                st.plotly_chart(fig_profit, use_container_width=True)
            else:
                st.info("No profit data for cumulative chart.")

        except Exception as e:
            st.error(f"❌ Error generating charts: {e}")

# --- Tab 4: Cards Inventory ---
elif selected_tab == "📋 Cards Inventory":
    st.header("📋 All Cards in Inventory")
    if not records:
        st.info("No cards found in inventory.")
    else:
        df_all_cards = pd.DataFrame(records)
        st.dataframe(df_all_cards, use_container_width=True, height=600)

        st.download_button(
            label="⬇️ Download All Cards as CSV",
            data=df_all_cards.to_csv(index=False).encode('utf-8'),
            file_name='all_cards_inventory.csv',
            mime='text/csv'
        )

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- Google Sheets Setup (Keep as is) ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open the Google Sheet once and store it
# This avoids re-opening the sheet object on every script rerun, though gspread might internally cache
@st.cache_resource
def get_worksheet():
    """Authorizes and opens the Google Sheet worksheet, cached globally."""
    try:
        sheet = client.open_by_key("15zMGzqJ1IYsh7i8q8WVaMrHsq0L7ddv9BYsmDHgUHSM")
        return sheet.worksheet("Inventory")
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheet: {e}")
        st.stop() # Stop the app if connection fails
        return None

inventory_ws = get_worksheet() # Get the worksheet object once

# --- Cache the data reading ---
@st.cache_data(ttl=60) # Cache for 60 seconds. Adjust TTL based on how frequently data changes.
def get_inventory_data():
    """Fetches all records and header from the Google Sheet, with caching."""
    if inventory_ws is None:
        return [], [] # Handle case where worksheet connection failed

    try:
        # Fetching all records is efficient as it's one API call for all data
        records = inventory_ws.get_all_records()
        header = inventory_ws.row_values(1) # This is a separate API call. Consider if header changes often.
        return records, header
    except Exception as e:
        st.error(f"❌ Error loading inventory from Google Sheet: {e}")
        return [], []

def clear_inventory_cache():
    """Clears the cache for inventory data."""
    st.cache_data.clear()

# --- Streamlit UI ---
st.set_page_config(page_title="Card Inventory Manager", layout="wide")
st.title("📇 Trading Card Inventory App")

tabs = st.tabs(["➕ Add New Card", "✏️ Update Sale Info", "📊 Profit Tracker"])

# Helper function for safe float conversion (retained as discussed)
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

# TAB 1: Add New Card
with tabs[0]:
    st.header("➕ Add New Card Entry")

    with st.form(key='add_card_form'):
        col1, col2, col3 = st.columns(3)

        set_name_options = [
            "Topps Chrome", "Topps Chrome Update", "Topps Series 1",
            "Topps Heritage", "Topps Heritage Mini","Topps Opening Day",
            "Topps Inception", "Bowman Inception", "Topps Big League",
            "Topps Dynasty", "Topps Gypsy Queen", "Bowman",
            "Topps Archive Signature Edition", "Topps Tier One",
            "Topps Finest", "Topps Series 2", "Topps Stadium Club",
            "Topps Museum Collection", "Topps Japan Edition",
            "Topps Allen & Ginter", "Bowman Chrome", "Topps Gold Label",
            "Topps Black Chrome", "Topps Pristine", "Topps Chrome Platinum Anniversary",
            "Topps Update Series", "Topps Heritage High Number",
            "Topps Five Star", "Bowman Draft", "Bowman's Best",
            "Topps Triple Threads", "Bowman Sapphire Edition",
            "Topps Pro Debut", "Topps Finest Flashbacks"
        ]
        numbered_parallel_options = [
            "None",
            "/499", "/299", "/250", "/199", "/150", "/99", "/75", "/50", "/25", "/10", "/5", "1/1",
            "Image Variation", "Case Hit", "Insert"
        ]
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
                st.error("❗ Player Name cannot be empty. Please enter a name to submit the card.")
            else:
                row = [
                    player_name,
                    card_type,
                    numbered_parallel,
                    "Yes" if auto else "No",
                    "Yes" if patch else "No",
                    year,
                    "Yes" if graded else "No",
                    bought_from,
                    seller_name,
                    f"${purchase_price:.2f}",
                    str(purchase_date),
                    "Yes" if listed else "No",
                    int(lot_number)
                ]
                try:
                    # Append row is a single API call
                    if inventory_ws: # Ensure worksheet is available
                        inventory_ws.append_row(row)
                        st.success("✅ Card entry added to Google Sheet!")
                        clear_inventory_cache() # Clear cache so next read fetches fresh data
                        st.rerun() # Rerun to refresh the data displayed in other tabs
                except Exception as e:
                    st.error(f"❌ Failed to write to Google Sheet: {e}")

# TAB 2: Update Sale Info
with tabs[1]:
    st.header("✏️ Update Sale Info")

    # This call is cached, so it's efficient if within TTL
    records, header = get_inventory_data()

    card_options = ["--- Select a Card to Update ---"]
    card_gsheet_row_map = {}

    if not records:
        st.info("No cards found in inventory to update. Add cards using the '➕ Add New Card' tab first.")
    else:
        for i, record in enumerate(records):
            gsheet_row_number = i + 2 # Google Sheets rows are 1-indexed, and header is row 1

            player = record.get('Player Name', 'N/A')
            year = record.get('Year', 'N/A')
            card_type_val = record.get('Set Name', 'N/A')
            numbered = record.get('Numbered/Parallel', 'None')
            auto_val = record.get('Auto', 'No')
            patch_val = record.get('Patch', 'No')
            graded_val = record.get('Graded', 'No')
            lot_num = record.get('Lot Number', 'N/A')

            display_name_parts = [player, str(year), card_type_val]
            if numbered and numbered != 'None':
                display_name_parts.append(f"({numbered})")
            if auto_val == 'Yes':
                display_name_parts.append("(Auto)")
            if patch_val == 'Yes':
                display_name_parts.append("(Patch)")
            if graded_val == 'Yes':
                display_name_parts.append("(Graded)")
            if lot_num and lot_num != 'N/A':
                display_name_parts.append(f"[Lot: {lot_num}]")

            display_name = " - ".join(str(part).strip() for part in display_name_parts if str(part).strip() != '')
            unique_display_name = f"{display_name} (Row {gsheet_row_number})"
            card_options.append(unique_display_name)
            card_gsheet_row_map[unique_display_name] = gsheet_row_number

    selected_card_display = st.selectbox("Select Card to Update", card_options, key='update_card_select')

    initial_sold_date = date.today()
    initial_sold_price = 0.0
    initial_sale_takeaway = 0.0
    selected_gsheet_row_index = None
    selected_record_from_cache = None # Store the full record from cache

    if selected_card_display != "--- Select a Card to Update ---":
        selected_gsheet_row_index = card_gsheet_row_map.get(selected_card_display)
        if selected_gsheet_row_index:
            # OPTIMIZATION: Retrieve the record directly from the cached 'records' list
            # instead of doing a new inventory_ws.row_values() call.
            # This assumes 'records' is comprehensive and up-to-date (which it is, due to cache clear on update).
            try:
                # records is 0-indexed for list, but Google Sheet rows are 1-indexed
                # records[i] corresponds to gsheet_row_number = i + 2
                # So, selected_gsheet_row_index - 2 gives the list index
                selected_record_from_cache = records[selected_gsheet_row_index - 2]

                if 'Sold Date' in selected_record_from_cache and selected_record_from_cache['Sold Date']:
                    try:
                        initial_sold_date = date.fromisoformat(selected_record_from_cache['Sold Date'])
                    except ValueError:
                        pass
                if 'Sold Price' in selected_record_from_cache and selected_record_from_cache['Sold Price']:
                    try:
                        # Use safe_float_conversion here too for robustness
                        initial_sold_price = safe_float_conversion(selected_record_from_cache['Sold Price'])
                    except ValueError:
                        pass
                if 'Takeaway' in selected_record_from_cache and selected_record_from_cache['Takeaway']:
                    try:
                        # Use safe_float_conversion here too for robustness
                        initial_sale_takeaway = safe_float_conversion(selected_record_from_cache['Takeaway'])
                    except ValueError:
                        pass
            except IndexError:
                st.warning("Selected card record not found in cache. This might indicate a data sync issue.")
                selected_gsheet_row_index = None # Reset to prevent update
            except Exception as e:
                st.error(f"Error pre-filling data from cache: {e}")
                selected_gsheet_row_index = None
        else:
            st.warning("Could not find row information for the selected card.")
    elif selected_card_display == "--- Select a Card to Update ---" and len(card_options) > 1:
        st.info("Please select a card from the dropdown to view/update its sale info.")

    if selected_gsheet_row_index:
        sold_date = st.date_input("Sold Date", value=initial_sold_date)
        sold_price = st.number_input("Sold Price ($)", min_value=0.0, format="%.2f", value=initial_sold_price)
        sale_takeaway = st.number_input("Takeaway from Sale ($)", min_value=0.0, format="%.2f", value=initial_sale_takeaway)

        if st.button("Update Sale Info", key='update_sale_button'):
            if inventory_ws is None: # Safety check
                st.error("❌ Google Sheet connection not established. Please refresh the app.")
            else:
                try:
                    # Find column indices dynamically using the header from cached data
                    sold_date_col = header.index('Sold Date') + 1
                    sold_price_col = header.index('Sold Price') + 1
                    takeaway_col = header.index('Takeaway') + 1

                    # Prepare the values to update
                    values_to_update = [
                        (selected_gsheet_row_index, sold_date_col, str(sold_date)),
                        (selected_gsheet_row_index, sold_price_col, f"${sold_price:.2f}"),
                        (selected_gsheet_row_index, takeaway_col, f"${sale_takeaway:.2f}")
                    ]

                    # Convert to gspread.Cell objects for update_cells
                    cells_to_update = []
                    for row, col, value in values_to_update:
                        cells_to_update.append(gspread.Cell(row, col, value))

                    # Perform the batch update (ONE API CALL)
                    inventory_ws.update_cells(cells_to_update)

                    clean_display_name = selected_card_display.split(' (Row ')[0]
                    st.success(f"✅ Sale info updated for {clean_display_name}!")
                    clear_inventory_cache() # Clear cache after updating to reflect changes
                    st.rerun() # Rerun to refresh UI and updated data
                except ValueError as ve:
                    st.error(f"❌ Error: Required column not found in Google Sheet. Please ensure 'Sold Date', 'Sold Price', and 'Takeaway' columns exist. Details: {ve}")
                except Exception as e:
                    st.error(f"❌ Error updating sale info: {e}")

# TAB 3: Profit Tracker
with tabs[2]:
    st.header("📊 Profit Tracker")
    # This call is cached, so it's efficient if within TTL
    records, _ = get_inventory_data()

    if not records:
        st.info("No records to calculate profit from.")
    else:
        try:
            total_spent = sum(safe_float_conversion(r.get("Purchase Price", "$0")) for r in records if r.get("Purchase Price") is not None)
            total_sold = sum(safe_float_conversion(r.get("Sold Price", "$0")) for r in records if r.get("Sold Price") is not None)

            total_profit = 0.0
            for r in records:
                if r.get('Sold Date') and r.get('Takeaway') is not None and r.get('Purchase Price') is not None:
                    # Use the safe conversion for all values
                    takeaway_val = safe_float_conversion(r['Takeaway'])
                    purchase_price_val = safe_float_conversion(r['Purchase Price'])
                    total_profit += (takeaway_val - purchase_price_val)

            st.metric("Total Spent", f"${total_spent:.2f}")
            st.metric("Total Sold", f"${total_sold:.2f}")
            st.metric("Total Profit", f"${total_profit:.2f}")
        except Exception as e:
            st.error(f"❌ Failed to calculate totals: {e}")
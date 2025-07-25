import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# Google Sheets Setup (Keep as is)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open the Google Sheet (Keep as is)
sheet = client.open_by_key("15zMGzqJ1IYsh7i8q8WVaMrHsq0L7ddv9BYsmDHgUHSM")
inventory_ws = sheet.worksheet("Inventory")

# Streamlit UI (Keep as is)
st.set_page_config(page_title="Card Inventory Manager", layout="wide")
st.title("📇 Trading Card Inventory App")

tabs = st.tabs(["➕ Add New Card", "✏️ Update Sale Info", "📊 Profit Tracker"])

# TAB 1: Add New Card
with tabs[0]:
    st.header("➕ Add New Card Entry")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### Card Details")
        player_name = st.text_input("Player Name")

        card_type = st.selectbox(
            "Set Name",
            [
                "Topps Series 1", "Topps Heritage", "Topps Heritage Mini",
                "Topps Opening Day", "Topps Inception", "Bowman Inception",
                "Topps Big League", "Topps Dynasty", "Topps Gypsy Queen",
                "Bowman", "Topps Archive Signature Edition", "Topps Tier One",
                "Topps Finest", "Topps Series 2", "Topps Stadium Club",
                "Topps Museum Collection", "Topps Chrome", "Topps Chrome Update",
                "Topps Japan Edition", "Topps Allen & Ginter", "Bowman Chrome",
                "Topps Gold Label", "Topps Black Chrome", "Topps Pristine",
                "Topps Chrome Platinum Anniversary", "Topps Update Series",
                "Topps Heritage High Number", "Topps Five Star", "Bowman Draft",
                "Bowman's Best", "Topps Triple Threads", "Bowman Sapphire Edition",
                "Topps Pro Debut", "Topps Finest Flashbacks"
            ]
        )

        numbered_parallel = st.selectbox(
            "Numbered/Parallel",
            [
                "None", "1/1", "Image Variation", "Case Hit",
                "/499", "/299", "/250", "/199", "/150", "/99", "/75", "/50", "/25", "/10", "/5",
                "Insert"
            ]
        )

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
        year = st.selectbox("Year", list(range(date.today().year, 1949, -1)))
        bought_from = st.text_input("Website (Bought From)")
        seller_name = st.text_input("Seller Name")

    with col3:
        st.markdown("#### Financials & ID")
        purchase_price = st.number_input("Bought Price ($)", min_value=0.0, format="%.2f")
        purchase_date = st.date_input("Date Purchased", value=date.today())
        lot_number = st.number_input("Lot Number", min_value=0)

    st.write("---")
    if st.button("Submit Card Entry"):
        if not player_name.strip():
            st.error("❗ Player Name cannot be empty. Please enter a name to submit the card.")
            st.stop()

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
            inventory_ws.append_row(row)
            st.success("✅ Card entry added to Google Sheet!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to write to Google Sheet: {e}")

# TAB 2: Update Sale Info
with tabs[1]:
    st.header("✏️ Update Sale Info")

    try:
        records = inventory_ws.get_all_records()
        header = inventory_ws.row_values(1)
    except Exception as e:
        st.error(f"❌ Could not load inventory from Google Sheet: {e}")
        records = []
        header = []

    card_options = ["--- Select a Card to Update ---"]
    card_gsheet_row_map = {}

    if not records:
        st.info("No cards found in inventory to update. Add cards using the '➕ Add New Card' tab first.")
    else:
        for i, record in enumerate(records):
            gsheet_row_number = i + 2

            player = record.get('Player Name', 'N/A')
            year = record.get('Year', 'N/A')
            card_type_val = record.get('Set Name', 'N/A') # Using 'Set Name' as discussed
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

    selected_card_display = st.selectbox("Select Card to Update", card_options)

    initial_sold_date = date.today()
    initial_sold_price = 0.0
    initial_sale_takeaway = 0.0
    selected_gsheet_row_index = None

    if selected_card_display != "--- Select a Card to Update ---":
        selected_gsheet_row_index = card_gsheet_row_map.get(selected_card_display)
        if selected_gsheet_row_index:
            try:
                row_values = inventory_ws.row_values(selected_gsheet_row_index)
                selected_record = dict(zip(header, row_values))

                if 'Sold Date' in selected_record and selected_record['Sold Date']:
                    try:
                        initial_sold_date = date.fromisoformat(selected_record['Sold Date'])
                    except ValueError:
                        pass
                if 'Sold Price' in selected_record and selected_record['Sold Price']:
                    try:
                        initial_sold_price = float(selected_record['Sold Price'].replace('$', ''))
                    except ValueError:
                        pass
                if 'Takeaway' in selected_record and selected_record['Takeaway']:
                    try:
                        initial_sale_takeaway = float(selected_record['Takeaway'].replace('$', ''))
                    except ValueError:
                        pass
            except Exception as e:
                st.error(f"Error fetching existing card data for pre-fill: {e}")
                selected_gsheet_row_index = None
        else:
            st.warning("Could not find row information for the selected card.")

    if selected_gsheet_row_index:
        sold_date = st.date_input("Sold Date", value=initial_sold_date)
        sold_price = st.number_input("Sold Price ($)", min_value=0.0, format="%.2f", value=initial_sold_price)
        sale_takeaway = st.number_input("Takeaway from Sale ($)", min_value=0.0, format="%.2f", value=initial_sale_takeaway)

        if st.button("Update Sale Info"):
            try:
                inventory_ws.update_cell(selected_gsheet_row_index, 14, str(sold_date))
                inventory_ws.update_cell(selected_gsheet_row_index, 15, f"${sold_price:.2f}")
                inventory_ws.update_cell(selected_gsheet_row_index, 16, f"${sale_takeaway:.2f}")

                clean_display_name = selected_card_display.split(' (Row ')[0]
                st.success(f"✅ Sale info updated for {clean_display_name}!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error updating sale info: {e}")
    elif selected_card_display != "--- Select a Card to Update ---":
         st.info("Please select a card from the dropdown to view/update its sale info.")

# TAB 3: Profit Tracker
with tabs[2]:
    st.header("📊 Profit Tracker")
    try:
        records = inventory_ws.get_all_records()
        total_spent = sum(float(r.get("Purchase Price", "$0").replace('$','')) for r in records if r.get("Purchase Price"))
        total_sold = sum(float(r.get("Sold Price", "$0").replace('$','')) for r in records if r.get("Sold Price"))

        # --- MODIFIED: Total Profit calculation ---
        total_profit = 0.0
        for r in records:
            # Only calculate profit for cards that have a 'Sold Date' (meaning they were sold)
            if r.get('Sold Date') and r.get('Takeaway') and r.get('Purchase Price'):
                try:
                    takeaway_val = float(r['Takeaway'].replace('$', ''))
                    purchase_price_val = float(r['Purchase Price'].replace('$', ''))
                    total_profit += (takeaway_val - purchase_price_val)
                except ValueError:
                    # Skip if conversion to float fails for any value
                    pass
        # --- END MODIFIED ---

        st.metric("Total Spent", f"${total_spent:.2f}")
        st.metric("Total Sold", f"${total_sold:.2f}")
        st.metric("Total Profit", f"${total_profit:.2f}")
    except Exception as e:
        st.error(f"❌ Failed to calculate totals: {e}")
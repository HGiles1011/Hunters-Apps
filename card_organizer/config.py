# my_card_app/config.py

# --- Configuration ---
# IMPORTANT: Make sure this path is correct for your system.
# If you move the script or the Excel file, you will need to update this path.
EXCEL_FILE_PATH = r"C:\Users\huntd\Dropbox\Hunter\Cards Excel Sheet.xlsx"

# Define the fields for the "Entry" tab
ENTRY_FIELDS = [
    "Player", "Card Type", "Numbered or Parallel", "Year", "Graded", "Price of Grading",
    "Bought From", "Seller Name", "Listed", "Bought Price", "Lot Number"
]

# Define the fields for the "Sale Update" tab
SALE_UPDATE_FIELDS = [
    "Sold Price", "Takeaway From Sale", "Profit", "COGS"
]

# Combined list of all fields for consistent Excel header and column indexing
ALL_FIELDS = ENTRY_FIELDS + SALE_UPDATE_FIELDS

# Years for dropdown
CURRENT_YEAR = 2025
YEARS_RANGE = [str(year) for year in range(CURRENT_YEAR, CURRENT_YEAR - 31, -1)] # Last 30 years + current

# Treeview columns for the Update Sale Data tab
TREEVIEW_COLUMNS = ("Player", "Card Type", "Year", "Bought Price")
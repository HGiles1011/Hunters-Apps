# card_organizer/update_sale_tab.py

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

# Import shared modules
from . import config
from . import excel_manager
from . import ui_elements # Import the new module

class UpdateSaleTab:
    def __init__(self, parent_notebook_frame):
        self.frame = ttk.Frame(parent_notebook_frame)
        self.selected_entry_index = -1
        self.selected_entry_data = None
        self.sale_entries = {}

        self._create_widgets()
        self.refresh_treeview()

    def _create_widgets(self):
        """Creates the UI elements for the Update Sale Data tab."""
        # Frame for the Treeview (list of entries)
        tree_frame = ttk.LabelFrame(self.frame, text="Select Entry to Update")
        tree_frame.pack(padx=10, pady=10, fill="both", expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(tree_frame, columns=config.TREEVIEW_COLUMNS, show="headings",
                                yscrollcommand=tree_scroll.set, selectmode="browse")

        for col in config.TREEVIEW_COLUMNS:
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col, width=100)

        self.tree.pack(fill="both", expand=True)
        tree_scroll.config(command=self.tree.yview)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Frame for the sale update input fields
        sale_input_frame = ttk.LabelFrame(self.frame, text="Sale Details")
        sale_input_frame.pack(padx=10, pady=10, fill="x")

        # Use a sub-frame for the actual input fields to manage grid rows easily
        # This allows ui_elements.create_labeled_input to use grid_size() correctly
        sale_input_fields_grid_frame = tk.Frame(sale_input_frame)
        sale_input_fields_grid_frame.pack(fill="both", expand=True)

        for field in config.SALE_UPDATE_FIELDS:
            widget_info = None
            if field == "Takeaway From Sale":
                widget_info = ui_elements.create_labeled_input(
                    sale_input_fields_grid_frame, field, 'scrolledtext'
                )
            else:
                widget_info = ui_elements.create_labeled_input(
                    sale_input_fields_grid_frame, field, 'entry'
                )
            self.sale_entries[field] = widget_info

        submit_sale_update_btn = tk.Button(sale_input_frame, text="Update Sale Data", command=self._submit_sale_update)
        submit_sale_update_btn.pack(pady=10) # Using pack for the button

    def refresh_treeview(self):
        """
        Refreshes the data displayed in the Treeview.
        Skips the header row (handled by excel_manager.get_all_excel_data) and the first actual data row (Excel row 2).
        """
        for item in self.tree.get_children():
            self.tree.delete(item)
        data = excel_manager.get_all_excel_data()

        for i, row in enumerate(data):
            if i == 0:
                continue
            self.tree.insert("", "end", iid=str(i), values=row)

    def _on_tree_select(self, event):
        """Event handler for when a row is selected in the Treeview."""
        selected_item = self.tree.focus()
        if not selected_item:
            self.selected_entry_index = -1
            self.selected_entry_data = None
            self._clear_sale_entries()
            return

        self.selected_entry_index = int(selected_item)
        
        all_data = excel_manager.get_all_excel_data()
        if 0 <= self.selected_entry_index < len(all_data):
            self.selected_entry_data = all_data[self.selected_entry_index]
            self._populate_sale_entries(self.selected_entry_data)
        else:
            messagebox.showwarning("Error", "Invalid selection index. Please re-select.")
            self.selected_entry_index = -1
            self.selected_entry_data = None
            self._clear_sale_entries()

    def _populate_sale_entries(self, data):
        """Populates the sale update entry fields with data from the selected row."""
        self._clear_sale_entries()
        for field_name in config.SALE_UPDATE_FIELDS:
            try:
                original_col_idx = config.ALL_FIELDS.index(field_name)
                value_to_display = data[original_col_idx] if original_col_idx < len(data) else ""

                widget_info = self.sale_entries[field_name]
                widget = widget_info['widget']

                if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                    widget.insert("1.0", str(value_to_display))
                else:
                    widget.insert(0, str(value_to_display))
            except (IndexError, KeyError) as e:
                print(f"Warning: Could not populate {field_name}. Error: {e}. Data might be incomplete or field not found.")

    def _clear_sale_entries(self):
        """Clears only the sale update entry fields."""
        for field in self.sale_entries:
            widget_info = self.sale_entries[field]
            widget = widget_info['widget']
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)

    def _submit_sale_update(self):
        """
        Handles updating sale data for a selected entry.
        Attempts to update using openpyxl first, then falls back to win32com.client.
        """
        if self.selected_entry_index == -1:
            messagebox.showwarning("No Selection", "Please select an entry from the list to update.")
            return
        if self.selected_entry_data is None:
            messagebox.showwarning("Error", "No data loaded for selected entry. Please re-select.")
            self.selected_entry_index = -1
            return

        updated_full_data = list(self.selected_entry_data)

        for field in config.SALE_UPDATE_FIELDS:
            widget_info = self.sale_entries[field]
            widget = widget_info['widget']

            value = ""
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                value = widget.get("1.0", tk.END).strip()
            else:
                value = widget.get().strip()

            if field in ["Sold Price", "Profit", "COGS"]:
                try:
                    value = float(value) if value else 0.0
                except ValueError:
                    messagebox.showwarning("Input error", f"Please enter a valid number for {field}.")
                    return

            col_idx = config.ALL_FIELDS.index(field)
            updated_full_data[col_idx] = value

        # --- Attempt to update using openpyxl first (works when Excel is closed) ---
        if excel_manager.update_excel_row_openpyxl(self.selected_entry_index, updated_full_data):
            messagebox.showinfo("Success", "Entry updated in Excel file on disk!")
            self._clear_sale_entries()
            self.refresh_treeview()
            self.selected_entry_index = -1
            self.selected_entry_data = None
            return

        # --- If openpyxl fails, try with win32com.client (works when Excel is open) ---
        if excel_manager.update_excel_row_com(self.selected_entry_index, updated_full_data):
            messagebox.showinfo("Success", "Entry updated in open Excel workbook!")
            self._clear_sale_entries()
            self.refresh_treeview()
            self.selected_entry_index = -1
            self.selected_entry_data = None
            return

        # --- If both methods fail ---
        messagebox.showerror("Error", "Could not update Excel file.\n"
                                    "Please ensure the file is not open exclusively by another program, "
                                    "or that the file path is correct and accessible.")
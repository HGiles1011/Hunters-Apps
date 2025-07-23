# card_organizer/new_entry_tab.py

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

# Import shared modules
from . import config
from . import excel_manager
from . import ui_elements # Import the new module

class NewEntryTab:
    def __init__(self, parent_notebook_frame, refresh_treeview_callback):
        self.frame = ttk.Frame(parent_notebook_frame)
        self.refresh_treeview_callback = refresh_treeview_callback
        self.entry_widgets = {} # Stores widgets for the Entry tab

        self._create_widgets()

    def _create_widgets(self):
        """Creates the UI elements for the New Entry tab."""
        canvas = tk.Canvas(self.frame)
        scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Use a sub-frame for the actual input fields to manage grid rows easily
        # This allows ui_elements.create_labeled_input to use grid_size() correctly
        input_fields_frame = tk.Frame(scrollable_frame)
        input_fields_frame.pack(fill="both", expand=True)


        for field in config.ENTRY_FIELDS:
            widget_info = None
            if field == "Numbered or Parallel":
                var = tk.StringVar(input_fields_frame)
                widget_info = ui_elements.create_labeled_input(
                    input_fields_frame, field, 'combobox', options=["Yes", "No"], textvariable=var
                )
            elif field == "Year":
                var = tk.StringVar(input_fields_frame)
                widget_info = ui_elements.create_labeled_input(
                    input_fields_frame, field, 'combobox', options=config.YEARS_RANGE, textvariable=var
                )
            elif field == "Graded" or field == "Listed":
                var = tk.IntVar(input_fields_frame)
                widget_info = ui_elements.create_labeled_input(
                    input_fields_frame, field, 'checkbutton', textvariable=var
                )
            else:
                widget_info = ui_elements.create_labeled_input(
                    input_fields_frame, field, 'entry'
                )
            
            self.entry_widgets[field] = widget_info

        submit_new_btn = tk.Button(scrollable_frame, text="Submit New Entry", command=self._submit_new_entry)
        # Place the button below all input fields
        submit_new_btn.pack(pady=20) # Using pack for the button as it's outside the grid of input_fields_frame

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _clear_entry_fields(self):
        """Clears all input fields on the new entry tab."""
        for field in self.entry_widgets:
            widget_info = self.entry_widgets[field]
            widget = widget_info['widget']
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                widget.delete("1.0", tk.END)
            elif isinstance(widget, ttk.Combobox):
                widget.set('')
            elif isinstance(widget, tk.Checkbutton):
                widget_info['var'].set(0)
            else:
                widget.delete(0, tk.END)

    def _submit_new_entry(self):
        """
        Handles submission of data from the 'Entry' tab.
        Attempts to save using openpyxl first, then falls back to win32com.client.
        """
        full_entry_data = [""] * len(config.ALL_FIELDS) # Initialize with empty strings for all fields

        for field in config.ENTRY_FIELDS:
            widget_info = self.entry_widgets[field]
            widget = widget_info['widget']

            value = ""
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                value = widget.get("1.0", tk.END).strip()
            elif isinstance(widget, ttk.Combobox):
                value = widget.get().strip()
            elif isinstance(widget, tk.Checkbutton):
                state = widget_info['var'].get()
                value = "Yes" if state == 1 else "No"
            else:
                value = widget.get().strip()

            # Data type conversion/validation for numeric fields
            if field in ["Price of Grading", "Bought Price"]:
                try:
                    value = float(value) if value else 0.0
                except ValueError:
                    messagebox.showwarning("Input error", f"Please enter a valid number for {field}.")
                    return
            elif field == "Year":
                if value:
                    try:
                        value = int(value)
                    except ValueError:
                        messagebox.showwarning("Input error", f"Please enter a valid year for {field}.")
                        return
                else:
                    value = ""

            col_idx = config.ALL_FIELDS.index(field)
            full_entry_data[col_idx] = value

        # Simple validation example: Player and Card Type are required
        if not full_entry_data[config.ALL_FIELDS.index("Player")] or not full_entry_data[config.ALL_FIELDS.index("Card Type")]:
            messagebox.showwarning("Input error", "Player and Card Type are required.")
            return

        # --- Attempt to save using openpyxl first (works when Excel is closed) ---
        if excel_manager.append_to_file(full_entry_data):
            messagebox.showinfo("Success", "New entry saved to Excel file on disk!")
            self._clear_entry_fields()
            self.refresh_treeview_callback() # Callback to refresh the other tab's treeview
            return

        # --- If openpyxl fails, try with win32com.client (works when Excel is open) ---
        if excel_manager.append_to_open_excel_com(full_entry_data):
            messagebox.showinfo("Success", "New entry appended to open Excel workbook!")
            self._clear_entry_fields()
            self.refresh_treeview_callback()
            return

        # --- If both methods fail ---
        messagebox.showerror("Error", "Could not save new entry to Excel file.\n"
                                    "Please ensure the file is not open exclusively by another program, "
                                    "or that the file path is correct and accessible.")
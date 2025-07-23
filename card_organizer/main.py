# card_organizer/main.py

import tkinter as tk
from tkinter import ttk

# Import your tab classes
from .new_entry_tab import NewEntryTab
from .update_sale_tab import UpdateSaleTab

class CardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Card Hobby Entry App")

        self._create_notebook()

    def _create_notebook(self):
        """Creates the main tabbed interface (ttk.Notebook)."""
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, expand=True, fill="both")

        # Instantiate UpdateSaleTab first, as its refresh_treeview method is needed by NewEntryTab
        self.update_sale_tab_instance = UpdateSaleTab(notebook)
        self.new_entry_tab_instance = NewEntryTab(notebook, self.update_sale_tab_instance.refresh_treeview)

        # Add the tabs to the notebook
        notebook.add(self.new_entry_tab_instance.frame, text="New Entry")
        notebook.add(self.update_sale_tab_instance.frame, text="Update Sale Data")

if __name__ == "__main__":
    root = tk.Tk()
    app = CardApp(root)
    root.mainloop()
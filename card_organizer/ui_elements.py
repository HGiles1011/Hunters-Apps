# card_organizer/ui_elements.py

import tkinter as tk
from tkinter import scrolledtext, ttk

def create_labeled_input(parent_frame, field_name, input_type, options=None, textvariable=None):
    """
    Creates a label and an associated input widget (Entry, Combobox, Checkbutton, ScrolledText).
    Returns a dictionary containing the widget and its associated variable (if any).

    Args:
        parent_frame (tk.Frame or ttk.Frame): The frame to place the widgets in.
        field_name (str): The text for the label.
        input_type (str): 'entry', 'combobox', 'checkbutton', 'scrolledtext'.
        options (list, optional): Values for combobox.
        textvariable (tk.StringVar/IntVar, optional): Variable to link to the widget.
    """
    label = tk.Label(parent_frame, text=field_name + ":")
    # Align label to the right, no horizontal padding for flush look
    label.grid(row=parent_frame.grid_size()[1], column=0, sticky="e", pady=5) # Use grid_size for next row

    widget = None
    var = textvariable

    if input_type == 'entry':
        widget = tk.Entry(parent_frame, width=50)
    elif input_type == 'combobox':
        if var is None:
            var = tk.StringVar(parent_frame)
        widget = ttk.Combobox(parent_frame, textvariable=var, values=options, state="readonly")
    elif input_type == 'checkbutton':
        if var is None:
            var = tk.IntVar(parent_frame)
        widget = tk.Checkbutton(parent_frame, variable=var, text="") # Empty text as label is separate
    elif input_type == 'scrolledtext':
        widget = scrolledtext.ScrolledText(parent_frame, width=40, height=4, wrap=tk.WORD)
    else:
        raise ValueError(f"Unknown input_type: {input_type}")

    # Place widget flush next to the label, aligned to the left
    widget.grid(row=parent_frame.grid_size()[1] -1, column=1, sticky="w", pady=5) # Place on the same row as label

    return {'widget': widget, 'var': var} if var else {'widget': widget}
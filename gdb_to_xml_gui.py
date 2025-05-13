import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import threading
import os
# Make sure transform_opposite.py is in the same directory or accessible via PYTHONPATH
try:
    import transform_opposite 
except ImportError:
    # This is a fallback if the script is in a different directory and not in PYTHONPATH
    # For a more robust solution, consider packaging or setting PYTHONPATH
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        import transform_opposite
    except ImportError as e:
        # If it still fails, we can't proceed.
        # A simple GUI might not be the place for complex path manipulation.
        # For now, we'll let the error propagate if the import fails after trying to add the script's dir.
        print(f"Critical Error: Could not import 'transform_opposite.py'. Ensure it's in the same directory or PYTHONPATH. {e}")
        # Optionally, show an error in the GUI if it were already initialized, but here it's too early.
        # For simplicity, this example will likely fail to run if this import fails.
        raise

class GDBToXMLConverterApp:
    def __init__(self, master):
        self.master = master
        master.title("GDB to LandXML Converter")
        master.geometry("700x550")

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam') # or 'alt', 'default', 'classic'

        # Frame for input
        input_frame = ttk.LabelFrame(master, text="Input/Output Folders", padding=(10, 5))
        input_frame.pack(padx=10, pady=10, fill="x")

        # Input GDB Directory
        ttk.Label(input_frame, text="Input GDBs Folder:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.input_gdb_dir_var = tk.StringVar()
        self.input_gdb_entry = ttk.Entry(input_frame, textvariable=self.input_gdb_dir_var, width=60)
        self.input_gdb_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_input_btn = ttk.Button(input_frame, text="Browse...", command=self.browse_input_gdb_dir)
        self.browse_input_btn.grid(row=0, column=2, padx=5, pady=5)

        # Output XML Directory
        ttk.Label(input_frame, text="Output XMLs Folder:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.output_xml_dir_var = tk.StringVar()
        self.output_xml_entry = ttk.Entry(input_frame, textvariable=self.output_xml_dir_var, width=60)
        self.output_xml_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.browse_output_btn = ttk.Button(input_frame, text="Browse...", command=self.browse_output_xml_dir)
        self.browse_output_btn.grid(row=1, column=2, padx=5, pady=5)
        
        input_frame.columnconfigure(1, weight=1) # Make entry expand

        # Set default paths (optional, based on script location)
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.input_gdb_dir_var.set(os.path.join(script_dir, "input_gdbs"))
            self.output_xml_dir_var.set(os.path.join(script_dir, "output_xmls"))
        except Exception:
            pass # In case __file__ is not defined (e.g. interactive)

        # Convert Button
        self.convert_button = ttk.Button(master, text="Start Conversion", command=self.start_conversion_thread)
        self.convert_button.pack(pady=10)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(master, variable=self.progress_var, maximum=100, length=680)
        self.progress_bar.pack(pady=5, padx=10, fill="x")


        # Status/Log Area
        status_frame = ttk.LabelFrame(master, text="Log", padding=(10, 5))
        status_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
        self.status_text.pack(fill="both", expand=True)
        
        # Center the window
        master.eval('tk::PlaceWindow . center')


    def browse_input_gdb_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_gdb_dir_var.set(directory)

    def browse_output_xml_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_xml_dir_var.set(directory)

    def log_status(self, message):
        self.master.after(0, self._log_status_thread_safe, message)

    def _log_status_thread_safe(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        # Crude progress update - can be made more sophisticated
        if "Processing GDB" in message:
             self.progress_var.set(self.progress_var.get() + 5) # Increment a bit
        if "Finished processing." in message or "Conversion process complete." in message:
            self.progress_var.set(100)


    def conversion_task(self):
        input_gdb_dir = self.input_gdb_dir_var.get()
        output_xml_dir = self.output_xml_dir_var.get()

        if not input_gdb_dir or not output_xml_dir:
            self.log_status("Error: Input and Output directories must be specified.")
            self.convert_button.config(state=tk.NORMAL)
            self.progress_var.set(0)
            return

        self.log_status("Starting conversion...")
        self.progress_var.set(0)
        try:
            # Call the refactored function from transform_opposite.py
            transform_opposite.run_conversion(input_gdb_dir, output_xml_dir, status_callback=self.log_status)
        except Exception as e:
            self.log_status(f"An error occurred during conversion: {e}")
            import traceback
            self.log_status(traceback.format_exc())
        finally:
            self.convert_button.config(state=tk.NORMAL)
            # self.log_status("Conversion process complete.") # Already logged by run_conversion
            # self.progress_bar.stop() # If it was in indeterminate mode
            if self.progress_var.get() < 100 and "error" not in self.status_text.get("1.0", tk.END).lower() : # if not already 100 and no error
                 self.progress_var.set(100) # Mark as complete if no specific error set it lower

    def start_conversion_thread(self):
        self.convert_button.config(state=tk.DISABLED)
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete('1.0', tk.END) # Clear previous logs
        self.status_text.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # Run the conversion in a separate thread to keep the GUI responsive
        self.conversion_thread = threading.Thread(target=self.conversion_task, daemon=True)
        self.conversion_thread.start()

if __name__ == '__main__':
    root = tk.Tk()
    app = GDBToXMLConverterApp(root)
    root.mainloop()

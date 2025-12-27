import os
import re
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ebooklib import epub
from ai_cleaner import clean_text_with_ai
from cleaner import clean_structure
from merger import merge_paragraphs
# Configuration for custom tkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class TextToEpubApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Text to EPUB Converter")
        self.geometry("600x650") # Increased height for new options

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1) # Log area expands (index shifted)

        # Input File Selection
        self.input_file_path = ctk.StringVar()
        self.btn_browse_input = ctk.CTkButton(self, text="Select Input Text File", command=self.browse_input)
        self.btn_browse_input.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.lbl_input_path = ctk.CTkLabel(self, textvariable=self.input_file_path, text_color="gray")
        self.lbl_input_path.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Metadata Inputs
        self.frame_meta = ctk.CTkFrame(self)
        self.frame_meta.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.frame_meta.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_meta, text="Title:").grid(row=0, column=0, padx=10, pady=10)
        self.entry_title = ctk.CTkEntry(self.frame_meta, placeholder_text="Book Title")
        self.entry_title.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.frame_meta, text="Author:").grid(row=1, column=0, padx=10, pady=10)
        self.entry_author = ctk.CTkEntry(self.frame_meta, placeholder_text="Author Name")
        self.entry_author.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # AI Configuration
        self.frame_ai = ctk.CTkFrame(self)
        self.frame_ai.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.frame_ai.grid_columnconfigure(1, weight=1)
        
        self.use_ai_var = ctk.BooleanVar(value=False)
        self.chk_use_ai = ctk.CTkCheckBox(self.frame_ai, text="Use AI for Cleaning (Experimental)", variable=self.use_ai_var, command=self.toggle_ai_options)
        self.chk_use_ai.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(self.frame_ai, text="Gemini API Key:").grid(row=1, column=0, padx=10, pady=10)
        self.entry_api_key = ctk.CTkEntry(self.frame_ai, placeholder_text="AIzaSy...", show="*")
        self.entry_api_key.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.entry_api_key.configure(state="disabled") # Disabled by default

        # Convert Button
        self.btn_convert = ctk.CTkButton(self, text="Convert to EPUB", command=self.start_conversion)
        self.btn_convert.grid(row=4, column=0, padx=20, pady=20, sticky="ew")

        # Progress / Status
        self.progressbar = ctk.CTkProgressBar(self)
        self.progressbar.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progressbar.set(0)

        self.textbox_log = ctk.CTkTextbox(self, height=150)
        self.textbox_log.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.textbox_log.insert("0.0", "Welcome! Select a file to start.\n")

    def toggle_ai_options(self):
        state = "normal" if self.use_ai_var.get() else "disabled"
        self.entry_api_key.configure(state=state)

    def log(self, message):
        self.textbox_log.insert("end", message + "\n")
        self.textbox_log.see("end")

    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if filename:
            self.input_file_path.set(filename)
            # Auto-fill title from filename if empty
            if not self.entry_title.get():
                basename = os.path.basename(filename)
                self.entry_title.insert(0, os.path.splitext(basename)[0])

    def start_conversion(self):
        input_path = self.input_file_path.get()
        title = self.entry_title.get()
        author = self.entry_author.get()
        use_ai = self.use_ai_var.get()
        api_key = self.entry_api_key.get()

        if not input_path:
            messagebox.showerror("Error", "Please select an input file.")
            return
        
        if use_ai and not api_key:
            messagebox.showerror("Error", "API Key is required for AI cleaning.")
            return
        
        if not title:
            title = "Untitled"
        if not author:
            author = "Unknown"

        self.btn_convert.configure(state="disabled")
        self.progressbar.set(0)
        self.log("Starting conversion...")
        
        # Run in separate thread to keep UI responsive
        threading.Thread(target=self.run_conversion, args=(input_path, title, author, use_ai, api_key)).start()

    def run_conversion(self, input_path, title, author, use_ai, api_key):
        try:
            self.log(f"Reading {input_path}...")
            self.progressbar.set(0.1)
            
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()

            final_text = ""

            if use_ai:
                self.log("AI Cleaning started. This may take a while depending on file size...")
                self.progressbar.set(0.2)
                
                def progress_cb(val):
                    # Update progress in main thread context if strict but tkinter is loose on this usually
                    # Ideally use after() but for simple updates:
                    self.progressbar.set(val)

                try:
                    final_text = clean_text_with_ai(raw_text, api_key, progress_callback=progress_cb)
                    self.log("AI Cleaning completed.")
                except Exception as e:
                    self.log(f"AI Error: {str(e)}")
                    self.log("Falling back to standard cleaning...")
                    # Fallback
                    cleaned_text = clean_structure(raw_text)
                    final_text = merge_paragraphs(cleaned_text)
            else:
                self.log("Cleaning structure (removing page numbers, headers)...")
                self.progressbar.set(0.3)
                cleaned_text = clean_structure(raw_text)

                self.log("Merging paragraphs...")
                self.progressbar.set(0.5)
                final_text = merge_paragraphs(cleaned_text)

            self.log("Creating EPUB structure...")
            self.progressbar.set(0.9)
            
            output_path = os.path.splitext(input_path)[0] + ".epub"
            self.create_epub(final_text, output_path, title, author)

            self.progressbar.set(1.0)
            self.log(f"Success! Saved to {output_path}")
            messagebox.showinfo("Success", f"Converted successfully!\nFile saved at: {output_path}")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            self.btn_convert.configure(state="normal")


    def create_epub(self, text, output_path, title, author):
        book = epub.EpubBook()

        # Metadata
        book.set_identifier('id_123456') # Random ID
        book.set_title(title)
        book.set_language('en') # Defaulting to en, could be passed or detected
        book.add_author(author)

        # Create Content
        # Simple strategy: One single chapter for now, or split by double newlines?
        # The merger puts double newlines between paragraphs.
        # HTML conversion: replace \n\n with <p> tags.
        
        # Basic HTML formatting
        # We need to escape HTML characters if manual, but EbookLib might handle some?
        # Better to construct HTML safely.
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        html_content = "<h1>{}</h1>".format(title)
        
        # Regex for common chapter headers
        # 1. "Chapter N" or "Chapter N: Title"
        # 2. "1. Title"
        # 3. "제N장" (Korean)
        # 4. "N." (just number and dot)
        header_pattern = re.compile(r'^(Chapter\s+\d+|^\d+\.\s+|제\s*\d+\s*장|^\d+$)', re.IGNORECASE)

        for p in paragraphs:
            clean_p = p.strip()
            if not clean_p:
                continue
                
            # Check if this paragraph is actually a header
            # Heuristic: Short length AND matches pattern
            if len(clean_p) < 100 and header_pattern.match(clean_p):
                html_content += f"<h2 id='{clean_p[:10].replace(' ', '_')}'>{clean_p}</h2>"
            else:
                html_content += f"<p>{clean_p}</p>"

        # Create a chapter
        c1 = epub.EpubHtml(title='Main Content', file_name='content.xhtml', lang='en')
        c1.content = html_content
        
        book.add_item(c1)

        # TOC
        book.toc = (c1,)
        
        # Navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Spine
        book.spine = ['nav', c1]

        # Write
        epub.write_epub(output_path, book)

if __name__ == "__main__":
    app = TextToEpubApp()
    app.mainloop()

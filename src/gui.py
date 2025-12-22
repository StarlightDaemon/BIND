import tkinter as tk
from tkinter import scrolledtext, ttk
import logging
import threading
import time
import queue
from src.core.scraper import AbmgScraper

# Custom Log Handler
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        # Thread-safe GUI update
        self.text_widget.after(0, append)

class ABMG_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AudioBookBay Media Grabber (Beta)")
        self.root.geometry("700x500")
        
        self.is_running = False
        self.scraper = AbmgScraper()
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        
        # Header
        lbl_header = ttk.Label(root, text="ABMG Beta Scraper Check", font=("Segoe UI", 16, "bold"))
        lbl_header.pack(pady=10)

        # Controls
        frame_controls = ttk.Frame(root, padding=10)
        frame_controls.pack(fill=tk.X)
        
        self.btn_start = ttk.Button(frame_controls, text="Start Scraper", command=self.start_scraper)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(frame_controls, text="Stop", command=self.stop_scraper, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.lbl_status = ttk.Label(frame_controls, text="Status: Idle", foreground="gray")
        self.lbl_status.pack(side=tk.LEFT, padx=20)

        # Logs
        frame_logs = ttk.LabelFrame(root, text="Activity Log", padding=10)
        frame_logs.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.txt_logs = scrolledtext.ScrolledText(frame_logs, state='disabled', height=15, font=("Consolas", 9))
        self.txt_logs.pack(fill=tk.BOTH, expand=True)
        
        # Setup Logging
        self.logger = logging.getLogger("ABMG")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers = [] # Clear existing
        
        handler = TextHandler(self.txt_logs)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Scraper Logger
        scraper_logger = logging.getLogger("Scraper")
        scraper_logger.handlers = []
        scraper_logger.addHandler(handler)
        scraper_logger.setLevel(logging.DEBUG)

    def start_scraper(self):
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_status.config(text="Status: Running", foreground="green")
        self.logger.info("--- Starting Service ---")
        
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

    def stop_scraper(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_status.config(text="Status: Stopping...", foreground="orange")
        self.logger.info("--- Stopping Service (finishing current task) ---")

    def run_loop(self):
        # Run immediately
        self.job()
        
        while self.is_running:
            # Sleep loop (60s) with check
            for _ in range(60): 
                if not self.is_running: break
                time.sleep(1)
            
            if self.is_running:
                self.job()
        
        # On Stop
        time.sleep(0.5)
        try:
             self.root.after(0, lambda: self.lbl_status.config(text="Status: Stopped", foreground="red"))
        except:
            pass

    def job(self):
        self.logger.info("Checking for new uploads...")
        try:
            books = self.scraper.get_recent_books()
            self.logger.info(f"Found {len(books)} recent books.")
            
            for book in books:
                if not self.is_running: break
                
                self.logger.info(f"Processing: {book['title']}")
                info_hash = self.scraper.extract_info_hash(book['link'])
                
                if info_hash:
                    magnet = self.scraper.generate_magnet(info_hash, book['title'])
                    
                    with open("magnets.txt", "a", encoding="utf-8") as f:
                        f.write(f"{magnet}\n")
                    self.logger.info(f"Saved Magnet to file.")
                else:
                    self.logger.warning(f"Could not extract hash.")
                    
        except Exception as e:
            self.logger.error(f"Error in job: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ABMG_GUI(root)
    root.mainloop()

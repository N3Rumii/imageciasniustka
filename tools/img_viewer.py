import os
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import threading
import queue

# --- Configuration ---
BG_COLOR = "#222222"      # Main background
SIDEBAR_COLOR = "#181818" # Sidebar background
BTN_COLOR = "#181818"     # Button background
BTN_HOVER = "#333333"     # Hover effect
THUMB_BG = "#333333"
CACHE_SIZE = 150
MIN_WIDTH = 500
FALLBACK_WIDTH = 900
SCROLL_SPEED = 40

# --- Icon Generator (No external assets needed) ---
class IconGenerator:
    """ Generates minimal pixel icons for the UI """
    @staticmethod
    def create_icons():
        icons = {}
        # 1. Folder Icon
        img = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
        pixels = img.load()
        for x in range(2, 22):
            for y in range(6, 20): pixels[x, y] = (220, 200, 100, 255)
        for x in range(2, 10):
            for y in range(4, 6):  pixels[x, y] = (220, 200, 100, 255)
        icons["folder"] = ImageTk.PhotoImage(img)

        # 2. Clear/Trash Icon
        img = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
        pixels = img.load()
        for x in range(6, 18):
            for y in range(6, 20): pixels[x, y] = (200, 80, 80, 255)
        for x in range(4, 20): pixels[x, 5] = (200, 80, 80, 255)
        icons["clear"] = ImageTk.PhotoImage(img)

        # 3. Back Icon
        img = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
        pixels = img.load()
        for i in range(10):
            pixels[12 - i, 12] = (255, 255, 255, 255)
            pixels[12 - i, 11 - i] = (255, 255, 255, 255)
            pixels[12 - i, 13 + i] = (255, 255, 255, 255)
        icons["back"] = ImageTk.PhotoImage(img)

        # 4. Settings Icon
        img = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
        pixels = img.load()
        for x in range(6, 18):
            for y in range(6, 18): pixels[x, y] = (180, 180, 180, 255)
        icons["cog"] = ImageTk.PhotoImage(img)

        return icons


class IconButton(tk.Button):
    def __init__(self, parent, image, cmd, **kwargs):
        super().__init__(parent, image=image, command=cmd,
                         bg=SIDEBAR_COLOR, activebackground=BTN_HOVER,
                         bd=0, relief="flat", cursor="hand2", **kwargs)
        self.image = image
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e): self['bg'] = BTN_HOVER
    def on_leave(self, e): self['bg'] = SIDEBAR_COLOR


class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Infinite Viewer")
        self.root.geometry("1100x900")
        self.root.configure(bg=BG_COLOR)

        self.icons = IconGenerator.create_icons()
        self.image_paths = []
        self.thumbnails = []

        # Prefs
        self.snap_enabled = tk.BooleanVar(value=False)
        self.fit_screen = tk.BooleanVar(value=False)
        self.current_snap_index = 0

        # Virtual Scroll State
        self.scroll_y = 0
        self.total_cycle_height = 0  # Height of one full loop
        self.known_heights = {}
        
        # We store loaded widgets by a unique ID now, not just index
        # Format: "index_screenY"
        self.loaded_blocks = {} 

        # Threading
        self.image_cache = {}
        self.request_queue = queue.PriorityQueue()
        self.result_queue = queue.Queue()
        self.active_requests = set()
        self.stop_thread = False

        self.worker = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker.start()
        self.check_results()

        self._setup_layout()

        # Bindings
        self.root.bind("<Up>", self.on_arrow_up)
        self.root.bind("<Down>", self.on_arrow_down)
        self.root.bind("<Left>", self.on_arrow_up)
        self.root.bind("<Right>", self.on_arrow_down)
        self.root.bind_all("<MouseWheel>", self.on_mousewheel)
        self.root.bind_all("<Button-4>", self.on_mousewheel)
        self.root.bind_all("<Button-5>", self.on_mousewheel)
        self.dragging_scrollbar = False

    def _setup_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=SIDEBAR_COLOR, width=50)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Main Area
        self.container = tk.Frame(self.root, bg=BG_COLOR)
        self.container.pack(side="right", fill="both", expand=True)

        # Buttons
        self.btn_folder = IconButton(self.sidebar, self.icons["folder"], self.add_folder)
        self.btn_clear = IconButton(self.sidebar, self.icons["clear"], self.clear)
        self.btn_back = IconButton(self.sidebar, self.icons["back"], self.close_reader)
        self.btn_cog = IconButton(self.sidebar, self.icons["cog"], self.show_options)

        self.show_main_sidebar()

        # Thumbnail View
        self.thumb_frame = tk.Frame(self.container, bg=BG_COLOR)
        self.thumb_canvas = tk.Canvas(self.thumb_frame, bg=BG_COLOR, highlightthickness=0)
        self.thumb_scroll = ttk.Scrollbar(self.thumb_frame, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_content = tk.Frame(self.thumb_canvas, bg=BG_COLOR)

        self.thumb_content.bind("<Configure>",
                                lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_content, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)

        self.thumb_canvas.pack(side="left", fill="both", expand=True)
        self.thumb_scroll.pack(side="right", fill="y")
        self.thumb_frame.pack(fill="both", expand=True)

        # Reader View
        self.reader_frame = tk.Frame(self.container, bg=BG_COLOR)
        self.reader_canvas = tk.Canvas(self.reader_frame, bg=BG_COLOR, highlightthickness=0)
        self.reader_canvas.pack(side="left", fill="both", expand=True)

        self.custom_scroll = tk.Canvas(self.reader_frame, width=15, bg="#333", highlightthickness=0)
        self.custom_scroll.pack(side="right", fill="y")
        self.scroll_handle = self.custom_scroll.create_rectangle(0, 0, 15, 50, fill="#666", outline="")

        self.reader_canvas.bind("<Configure>", self.on_resize)
        self.custom_scroll.bind("<Button-1>", self.on_scroll_click)
        self.custom_scroll.bind("<B1-Motion>", self.on_scroll_drag)
        self.custom_scroll.bind("<ButtonRelease-1>", self.on_scroll_release)

    def show_main_sidebar(self):
        for widget in self.sidebar.winfo_children(): widget.pack_forget()
        self.btn_folder.pack(pady=(20, 10), padx=5)
        self.btn_clear.pack(pady=10, padx=5)

    def show_reader_sidebar(self):
        for widget in self.sidebar.winfo_children(): widget.pack_forget()
        self.btn_back.pack(pady=(20, 10), padx=5)
        self.btn_cog.pack(pady=10, padx=5)

    def show_options(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_checkbutton(label="Fit to Screen", variable=self.fit_screen, command=self.toggle_setting)
        menu.add_checkbutton(label="Snap to Grid", variable=self.snap_enabled, command=self.toggle_setting)
        x = self.root.winfo_rootx() + 50
        y = self.root.winfo_rooty() + self.btn_cog.winfo_y()
        menu.post(x, y)

    # --- Threading ---
    def worker_loop(self):
        while not self.stop_thread:
            try:
                priority, idx, path, req_w, req_h = self.request_queue.get(timeout=0.1)
                # If priority > 0, it's a prefetch, skip if queue busy? (Simple queue here is fine)
                try:
                    img = Image.open(path)
                    orig_w, orig_h = img.size
                    aspect = orig_h / orig_w
                    
                    if req_h is not None: # Fit Screen Mode
                        scale_h = req_h
                        scale_w = int(scale_h / aspect)
                        if scale_w > req_w: # If still too wide
                            scale_w = req_w
                            scale_h = int(scale_w * aspect)
                        final_w, final_h = scale_w, scale_h
                    else: # Fit Width Mode
                        final_w = req_w
                        final_h = int(final_w * aspect)

                    if final_w < 1: final_w = 1
                    if final_h < 1: final_h = 1
                    
                    img_r = img.resize((final_w, final_h), Image.Resampling.BILINEAR)
                    self.result_queue.put((idx, img_r, final_w, final_h))
                except Exception as e:
                    print(f"Error loading {idx}: {e}")
            except queue.Empty:
                continue

    def check_results(self):
        try:
            for _ in range(10):
                idx, pil_img, w, h = self.result_queue.get_nowait()
                photo = ImageTk.PhotoImage(pil_img)
                self.image_cache[idx] = photo
                self.known_heights[idx] = h
                
                # Cleanup cache
                if len(self.image_cache) > CACHE_SIZE: 
                    # Remove random old item
                    del self.image_cache[next(iter(self.image_cache))]
                
                if idx in self.active_requests:
                    self.active_requests.remove(idx)
                    # Trigger render update immediately upon load
                    self.render_virtual_view()
        except queue.Empty:
            pass
        self.root.after(20, self.check_results)

    # --- Input Handling ---
    def on_mousewheel(self, event):
        if not self.reader_frame.winfo_ismapped(): return
        if event.num == 4:   delta = -SCROLL_SPEED
        elif event.num == 5: delta = SCROLL_SPEED
        else:                delta = int(-1 * (event.delta / 120)) * SCROLL_SPEED
        self.scroll_by(delta)
        # Note: Snap logic is tricky in endless scroll, simplified to update index
        self.update_snap_index_from_pos()

    def on_arrow_down(self, event):
        if not self.reader_frame.winfo_ismapped(): return
        if self.snap_enabled.get():
            # Simply move to next index in the cycle
            next_idx = (self.current_snap_index + 1) % len(self.image_paths)
            self.snap_to_image(next_idx)
        else:
            self.scroll_by(100)

    def on_arrow_up(self, event):
        if not self.reader_frame.winfo_ismapped(): return
        if self.snap_enabled.get():
            prev_idx = (self.current_snap_index - 1) % len(self.image_paths)
            self.snap_to_image(prev_idx)
        else:
            self.scroll_by(-100)

    # --- Infinite Virtual Scroll Logic ---
    def get_view_dims(self):
        w = self.reader_canvas.winfo_width()
        h = self.root.winfo_height()
        if w < MIN_WIDTH: w = FALLBACK_WIDTH
        if h < 100: h = 800
        return w, h

    def get_image_height(self, idx):
        if idx in self.known_heights: return self.known_heights[idx]
        w, h = self.get_view_dims()
        # Estimate: Screen height if fitting, else 1.4 aspect ratio assumption
        return h if self.fit_screen.get() else int(w * 1.4)

    def scroll_by(self, delta):
        self.scroll_y += delta
        # We NO LONGER clamp. Scroll Y can be infinite or negative.
        self.render_virtual_view()
        self.update_scrollbar_handle()

    def snap_to_image(self, index):
        # Calculate where this image sits in the "base" cycle (0 to cycle_height)
        target_y = 0
        for i in range(len(self.image_paths)):
            if i == index: break
            target_y += self.get_image_height(i)
        
        self.scroll_y = target_y
        self.current_snap_index = index
        self.render_virtual_view()
        self.update_scrollbar_handle()

    def update_snap_index_from_pos(self):
        # Reverse map current cycle-normalized scroll to an index
        if self.total_cycle_height == 0: return
        normalized_y = self.scroll_y % self.total_cycle_height
        
        curr_y = 0
        for i in range(len(self.image_paths)):
            h = self.get_image_height(i)
            if curr_y <= normalized_y < curr_y + h:
                self.current_snap_index = i
                return
            curr_y += h

    def on_resize(self, event):
        self.known_heights.clear()
        self.render_virtual_view()

    def toggle_setting(self):
        self.image_cache.clear()
        self.known_heights.clear()
        # Destroy all existing blocks to force full redraw
        for b in self.loaded_blocks.values(): b.destroy()
        self.loaded_blocks.clear()
        self.render_virtual_view()

    def render_virtual_view(self):
        """ The Core Infinite Loop Logic """
        if not self.image_paths: return
        view_w, view_h = self.get_view_dims()

        # 1. Calculate heights of the full list (The Cycle)
        heights = []
        cycle_h = 0
        for i in range(len(self.image_paths)):
             h = self.get_image_height(i)
             heights.append(h)
             cycle_h += h
        
        self.total_cycle_height = cycle_h
        if cycle_h == 0: return

        # 2. Normalize Scroll Position
        # This gives us the position within a single cycle [0, cycle_h)
        # Even if self.scroll_y is negative or huge, modulo handles the wrapping.
        current_offset = self.scroll_y % cycle_h
        
        # 3. Find the Start Image
        # Which image overlaps with 'current_offset'?
        start_idx = 0
        accum_y = 0
        for i, h in enumerate(heights):
            if accum_y + h > current_offset:
                start_idx = i
                break
            accum_y += h
        
        # 'accum_y' is the top Y of 'start_idx' in the cycle.
        # Screen Y is relative to the current offset.
        screen_y = accum_y - current_offset

        # 4. Loop to fill screen
        visible_items = [] # Stores (index, y, h, unique_id)
        curr_idx = start_idx
        
        # We loop until we fill the screen height (plus a small buffer)
        # This handles wrapping: if we hit the end of the list, curr_idx resets to 0
        loop_safe_guard = 0
        
        while screen_y < view_h:
            h = heights[curr_idx]
            
            # Create a unique ID for this specific block on screen
            # Necessary because the same image (index) might appear twice (top & bottom)
            unique_id = f"{curr_idx}_{int(screen_y)}"
            visible_items.append((curr_idx, screen_y, h, unique_id))

            # Queue loading if needed
            if curr_idx not in self.image_cache and curr_idx not in self.active_requests:
                self.active_requests.add(curr_idx)
                req_h = view_h if self.fit_screen.get() else None
                self.request_queue.put((0, curr_idx, self.image_paths[curr_idx], view_w, req_h))

            screen_y += h
            curr_idx = (curr_idx + 1) % len(self.image_paths) # Wrap Index
            
            # Safety break for degenerate cases (e.g. 0 height or huge screen relative to content)
            loop_safe_guard += 1
            if loop_safe_guard > len(self.image_paths) + 5: break 

        # 5. Widget Management (Reconciliation)
        active_ids = {item[3] for item in visible_items}
        
        # Cleanup old widgets that moved off screen
        # We create a new dict to replace self.loaded_blocks
        new_loaded_blocks = {}
        for uid, widget in list(self.loaded_blocks.items()):
            if uid not in active_ids:
                widget.destroy()
            else:
                new_loaded_blocks[uid] = widget
        self.loaded_blocks = new_loaded_blocks

        # Create or Update widgets
        for idx, y, h, uid in visible_items:
            # Centering logic for 'Fit Screen' mode
            x_pos, block_w = 0, view_w
            if self.fit_screen.get() and idx in self.image_cache:
                img_w = self.image_cache[idx].width()
                if img_w < view_w:
                    x_pos = (view_w - img_w) // 2
                    block_w = img_w

            if uid in self.loaded_blocks:
                # Update existing
                lbl = self.loaded_blocks[uid]
                lbl.place(x=x_pos, y=y, width=block_w, height=h)
                # Check if image loaded since last frame
                if idx in self.image_cache:
                    # Tkinter string representation check is a quick way to see if image changed
                    if str(lbl.cget("image")) != str(self.image_cache[idx]):
                        lbl.config(image=self.image_cache[idx], text="")
            else:
                # Create new
                lbl = tk.Label(self.reader_canvas, text="Loading...", bg=BG_COLOR, fg="#555")
                if idx in self.image_cache:
                    lbl.config(image=self.image_cache[idx], text="", bg=BG_COLOR)
                lbl.place(x=x_pos, y=y, width=block_w, height=h)
                self.loaded_blocks[uid] = lbl

        self.update_scrollbar_handle()

    # --- Scrollbar ---
    def update_scrollbar_handle(self):
        if self.total_cycle_height == 0: return
        view_h = self.root.winfo_height()
        
        # The scrollbar represents "Where are we in the current cycle?"
        normalized_y = self.scroll_y % self.total_cycle_height
        
        ratio = view_h / self.total_cycle_height
        # Clamp handle size so it doesn't disappear
        handle_h = max(30, min(view_h, view_h * ratio))
        
        scroll_ratio = normalized_y / self.total_cycle_height
        handle_y = scroll_ratio * view_h
        
        self.custom_scroll.coords(self.scroll_handle, 0, handle_y, 15, handle_y + handle_h)

    def on_scroll_click(self, event):
        self.dragging_scrollbar = True
        self.on_scroll_drag(event)

    def on_scroll_drag(self, event):
        if not self.dragging_scrollbar: return
        if self.total_cycle_height == 0: return
        view_h = self.root.winfo_height()
        
        # Map drag percentage to the Cycle Height
        # This sets the scroll to a specific point in the current loop
        target_in_cycle = (event.y / view_h) * self.total_cycle_height
        
        # We need to preserve the "number of loops" we are currently in
        # so the screen doesn't jump wildly, but simpler is just resetting to the base cycle:
        self.scroll_y = target_in_cycle
        self.render_virtual_view()

    def on_scroll_release(self, event):
        self.dragging_scrollbar = False

    # --- Actions ---
    def add_folder(self):
        d = filedialog.askdirectory()
        if d:
            valid = ('.jpg', '.png', '.jpeg', '.webp', '.bmp', '.gif')
            paths = []
            for r, _, f in os.walk(d):
                for file in f:
                    if file.lower().endswith(valid): paths.append(os.path.join(r, file))
            paths.sort()
            self.image_paths.extend(paths)
            self.render_thumbs()

    def clear(self):
        self.image_paths = []
        self.loaded_blocks.clear()
        self.render_thumbs()

    def render_thumbs(self):
        for w in self.thumb_content.winfo_children(): w.destroy()
        self.thumbnails.clear()
        cols, row, col = 6, 0, 0
        # Limit thumbnails to 100 to prevent startup lag on huge folders
        for i, p in enumerate(self.image_paths[:100]):
            try:
                img = Image.open(p)
                img.thumbnail((140, 140))
                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo)
                l = tk.Label(self.thumb_content, image=photo, bg=THUMB_BG, bd=2)
                l.grid(row=row, column=col, padx=4, pady=4)
                l.bind("<Button-1>", lambda e, idx=i: self.open_reader(idx))
                col += 1
                if col >= cols: col, row = 0, row + 1
            except:
                pass

    def open_reader(self, start_index):
        self.thumb_frame.pack_forget()
        self.show_reader_sidebar()
        self.reader_frame.pack(fill="both", expand=True)
        self.current_snap_index = start_index
        
        # Calculate initial scroll position
        # Just sum heights up to start_index
        # (Heights might be estimates initially, that's fine)
        est_h = 800 if self.fit_screen.get() else int(self.get_view_dims()[0] * 1.4)
        
        # Better initial calc:
        start_y = 0
        for i in range(start_index):
             # Try to get cached, else estimate
             start_y += self.known_heights.get(i, est_h)
        
        self.scroll_y = start_y
        self.render_virtual_view()

    def close_reader(self):
        self.active_requests.clear()
        self.reader_frame.pack_forget()
        self.show_main_sidebar()
        self.thumb_frame.pack(fill="both", expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageViewerApp(root)
    root.mainloop()

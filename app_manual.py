import cv2
import numpy as np
import json
import os
import time
import calendar
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime, date
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- SYSTEM SETTINGS ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")
DB_FILE = "patient_database.json"
SETTINGS_FILE = "system_settings.json"
TEMP_CROP_FILE = "temp_cropped_wound.jpg"

# Colors
BG_COLOR = "#F4F7F9"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#1F2937"
SUBTEXT_COLOR = "#4B5563"
PRIMARY_BLUE = "#2563EB"
HOVER_BLUE = "#1D4ED8"
BORDER_COLOR = "#E5E7EB"
SUCCESS_GREEN = "#10B981"
SUCCESS_HOVER = "#059669"

# --- DEFAULT ALGORITHM THRESHOLDS ---
DEFAULT_SETTINGS = {
    "necrotic_v_max": 85, "necrotic_s_max": 255,
    "slough_h_min": 10, "slough_h_max": 60, "slough_s_min": 5,
    "gran_h_low_max": 10, "gran_h_high_min": 160, "gran_s_min": 40
}

class ClinicalAssessmentModal(ctk.CTkToplevel):
    def __init__(self, parent, save_callback, existing_data=None):
        super().__init__(parent)
        self.title("Comprehensive Clinical Assessment")
        self.geometry("480x780")  # Widened and heightened to fit checkboxes
        self.grab_set()  
        self.attributes("-topmost", True)

        # Title
        ctk.CTkLabel(self, text="Standardized Wound Assessment", font=("Arial", 18, "bold")).pack(pady=(20, 10))

        # 1. Exudate (Drainage) Amount
        ctk.CTkLabel(self, text="Exudate Amount:").pack(anchor="w", padx=20)
        self.exudate_amount = ctk.CTkOptionMenu(self, values=["None", "Scant", "Moderate", "Heavy"])
        self.exudate_amount.pack(fill="x", padx=20, pady=(0, 12))

        # 2. Exudate Type
        ctk.CTkLabel(self, text="Exudate Type:").pack(anchor="w", padx=20)
        self.exudate_type = ctk.CTkOptionMenu(self, values=["None", "Serous (Clear)", "Sanguineous (Bloody)", "Serosanguineous", "Purulent (Pus)"])
        self.exudate_type.pack(fill="x", padx=20, pady=(0, 12))

        # 3. Odor
        ctk.CTkLabel(self, text="Wound Odor:").pack(anchor="w", padx=20)
        self.odor = ctk.CTkOptionMenu(self, values=["None", "Mild", "Strong", "Foul"])
        self.odor.pack(fill="x", padx=20, pady=(0, 12))

        # 4. Pain Scale
        ctk.CTkLabel(self, text="Pain Scale (0-10):").pack(anchor="w", padx=20)
        self.pain_scale = ctk.CTkSlider(self, from_=0, to=10, number_of_steps=10)
        self.pain_scale.set(0)
        self.pain_scale.pack(fill="x", padx=20, pady=(0, 2))
        
        # Display the slider number dynamically
        self.pain_label = ctk.CTkLabel(self, text="0")
        self.pain_label.pack(pady=(0, 12))
        self.pain_scale.configure(command=lambda v: self.pain_label.configure(text=str(int(v))))

        # --- NEW: TREATMENT INTERVENTIONS SECTION ---
        ctk.CTkLabel(self, text="Clinical Interventions Applied:", font=("Arial", 13, "bold")).pack(anchor="w", padx=20, pady=(5, 5))
        
        # A clean 2-column frame for the checkboxes
        self.treatment_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.treatment_frame.pack(fill="x", padx=20, pady=(0, 12))
        self.treatment_frame.columnconfigure((0, 1), weight=1)

        self.cb_cleansing = ctk.CTkCheckBox(self.treatment_frame, text="Cleansing / Irrigation")
        self.cb_cleansing.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.cb_debridement = ctk.CTkCheckBox(self.treatment_frame, text="Debridement")
        self.cb_debridement.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.cb_antimicrobial = ctk.CTkCheckBox(self.treatment_frame, text="Antimicrobial / Silver")
        self.cb_antimicrobial.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.cb_moisture = ctk.CTkCheckBox(self.treatment_frame, text="Moisture Retentive")
        self.cb_moisture.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.cb_antibiotic = ctk.CTkCheckBox(self.treatment_frame, text="Topical Antibiotic")
        self.cb_antibiotic.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.cb_offloading = ctk.CTkCheckBox(self.treatment_frame, text="Offloading / Compression")
        self.cb_offloading.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # 5. Additional Notes
        ctk.CTkLabel(self, text="Additional Clinical Observations:").pack(anchor="w", padx=20)
        self.notes = ctk.CTkTextbox(self, height=70)
        self.notes.pack(fill="x", padx=20, pady=(0, 15))

        # Save Button
        self.save_callback = save_callback
        self.save_btn = ctk.CTkButton(self, text="Save Assessment", fg_color="#2ecc71", hover_color="#27ae60", command=self.save_data)
        self.save_btn.pack(pady=5)

        # --- PRE-FILL SAVED DATA (INCLUDING CHECKBOXES) ---
        if existing_data:
            self.exudate_amount.set(existing_data.get("exudate_amount", "None"))
            self.exudate_type.set(existing_data.get("exudate_type", "None"))
            self.odor.set(existing_data.get("odor", "None"))
            
            pain_val = existing_data.get("pain_scale", 0)
            self.pain_scale.set(pain_val)
            self.pain_label.configure(text=str(int(pain_val)))
            
            # Load treatments map safely
            treatments = existing_data.get("treatments", {})
            if treatments.get("cleansing"): self.cb_cleansing.select()
            if treatments.get("debridement"): self.cb_debridement.select()
            if treatments.get("antimicrobial"): self.cb_antimicrobial.select()
            if treatments.get("moisture_retentive"): self.cb_moisture.select()
            if treatments.get("topical_antibiotic"): self.cb_antibiotic.select()
            if treatments.get("offloading"): self.cb_offloading.select()

            notes_val = existing_data.get("additional_notes", "")
            if notes_val:
                self.notes.insert("1.0", notes_val)

    def save_data(self):
        # Package everything up including our checkbox state (1 = checked, 0 = unchecked)
        assessment_data = {
            "exudate_amount": self.exudate_amount.get(),
            "exudate_type": self.exudate_type.get(),
            "odor": self.odor.get(),
            "pain_scale": int(self.pain_scale.get()),
            "treatments": {
                "cleansing": bool(self.cb_cleansing.get()),
                "debridement": bool(self.cb_debridement.get()),
                "antimicrobial": bool(self.cb_antimicrobial.get()),
                "moisture_retentive": bool(self.cb_moisture.get()),
                "topical_antibiotic": bool(self.cb_antibiotic.get()),
                "offloading": bool(self.cb_offloading.get())
            },
            "additional_notes": self.notes.get("1.0", "end-1c").strip()
        }
        self.save_callback(assessment_data)
        self.destroy()
        
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    with open(SETTINGS_FILE, 'r') as f: return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f: json.dump(data, f, indent=4)

def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
        for pid, data in db.items():
            if isinstance(data, list):
                db[pid] = {"info": {"first_name": "Unknown", "last_name": "", "age": "N/A", "sex": "Male"}, "records": data}
            elif "name" in data["info"]:
                old_name = data["info"].pop("name")
                parts = old_name.split(" ", 1)
                data["info"]["first_name"] = parts[0]
                data["info"]["last_name"] = parts[1] if len(parts) > 1 else ""
                
                if data["info"].get("sex") not in ["Male", "Female"]:
                    data["info"]["sex"] = "Male"
        return db

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

def get_next_auto_id():
    db = load_db()
    numeric_ids = [int(pid) for pid in db.keys() if pid.isdigit()]
    return str(max(numeric_ids) + 1) if numeric_ids else "1"


# --- CORE ALGORITHMS ---
def phase_1_preprocessing(image_path):
    """
    Phase 1: Pre-Processing (Lighting Correction)
    Utilizes CLAHE to normalize extreme clinical lighting variations.
    """
    img = cv2.imread(image_path)
    if img is None: raise ValueError("Image not found.")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    img_clahe = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    img_blur = cv2.GaussianBlur(img_clahe, (5, 5), 0)
    return img_rgb, img_blur

def phase_2_segmentation(img_blur):
    """
    Phase 2: Original Manual Crop Segmentation
    Uses Otsu's Thresholding to isolate the wound from healthy skin 
    inside the manual bounding box.
    """
    # 1. Color Space Conversion
    hsv_img = cv2.cvtColor(img_blur, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_img)
    
    # 2. Original Otsu's Thresholding (Applied to Saturation)
    _, mask_base = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 3. Original Aggressive Morphological Closing to bridge gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    mask_cleaned = cv2.morphologyEx(mask_base, cv2.MORPH_CLOSE, kernel)
    
    # 4. Contour Filling
    contours, _ = cv2.findContours(mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask_filled = np.zeros_like(mask_cleaned)
    if contours:
        cv2.drawContours(mask_filled, contours, -1, 255, thickness=cv2.FILLED)
        
    return hsv_img, mask_filled

def phase_3_classification(hsv_img, mask):
    """
    Phase 3: Classification Engine
    Applies strict, 8-bit integer HSV thresholds (0-255) to mathematically
    quantify Necrotic, Slough, and Granulation tissues, and calculates footprint.
    """
    cfg = load_settings()
    height, width, _ = hsv_img.shape
    tissue_map = np.zeros((height, width, 3), dtype=np.uint8)
    tissue_map[:] = [240, 240, 240] 
    
    H, S, V_chan = cv2.split(hsv_img)
    
    # Strict Integer Threshold Rules
    is_necrotic = (V_chan <= cfg["necrotic_v_max"]) & (S <= cfg["necrotic_s_max"])
    
    # Broaden the "Pale" saturation threshold to catch washed-out tissue
    is_yellow_slough = (H >= cfg["slough_h_min"]) & (H <= cfg["slough_h_max"]) & (S >= cfg["slough_s_min"])
    is_pale_slough = (S < 95) & (V_chan > 150) 
    is_slough = is_yellow_slough | is_pale_slough
    
    is_granulation = ((H >= cfg["gran_h_high_min"]) | (H <= cfg["gran_h_low_max"])) & (S >= cfg["gran_s_min"])

    # Apply wound mask to ensure background skin is ignored
    binary_mask_bool = mask.astype(bool)
    
    final_necrotic = is_necrotic & binary_mask_bool
    final_slough = is_slough & binary_mask_bool & ~final_necrotic
    final_granulation = is_granulation & binary_mask_bool & ~final_necrotic & ~final_slough

    # Visualization Colors
    tissue_map[final_necrotic] = [30, 30, 40]   
    tissue_map[final_slough] = [250, 200, 20]    
    tissue_map[final_granulation] = [220, 38, 38] 

    # Quantification (Pixel Counting)
    total_wound_pixels = np.count_nonzero(mask)
    if total_wound_pixels == 0:
        return tissue_map, {"Necrotic": 0, "Slough": 0, "Granulation": 0, "Width_px": 0, "Length_px": 0}

    # --- STRATEGY 1: SIZE TRACKING ---
    # Calculate the bounding rectangle of the active wound mask pixels
    rect_x, rect_y, rect_w, rect_h = cv2.boundingRect(mask)

    stats = {
        "Necrotic": (np.count_nonzero(final_necrotic) / total_wound_pixels) * 100,
        "Slough": (np.count_nonzero(final_slough) / total_wound_pixels) * 100,
        "Granulation": (np.count_nonzero(final_granulation) / total_wound_pixels) * 100,
        "Width_px": rect_w,
        "Length_px": rect_h
    }
    return tissue_map, stats

def phase_4_decision_support(patient_id, patient_info, current_stats, current_date_str, clinical_assessment=None, image_path=""):
    """
    Phase 4: Clinical Decision Support & Longitudinal Tracking
    Calculates healing velocity between visits and generates automated alerts.
    """
    db = load_db()
    alerts = []
    should_save = True 
    
    clean_current_date = current_date_str[:10] 
    try: current_date_obj = datetime.strptime(clean_current_date, "%Y-%m-%d")
    except ValueError: raise ValueError("Invalid date format. Use YYYY-MM-DD.")
    
    if patient_id in db and len(db[patient_id]['records']) > 0:
        past_visit = db[patient_id]['records'][-1]
        past_stats = past_visit['stats']
        
        clean_past_date = past_visit['date'][:10]
        past_date_obj = datetime.strptime(clean_past_date, "%Y-%m-%d")
        delta_days = (current_date_obj - past_date_obj).days
        
        if delta_days < 0: raise ValueError("Date is older than last recorded visit!")
        if delta_days > 0:
            gran_vel = (current_stats["Granulation"] - past_stats.get("Granulation", 0)) / delta_days
            if gran_vel > 0:
                alerts.append({"type": "success", "icon": "↗️", "title": "Positive Trend", "text": f"Healing Velocity: +{gran_vel:.1f}% Granulation per day."})
            else:
                alerts.append({"type": "warning", "icon": "⚠️", "title": "Stagnation Detected", "text": f"Healing Velocity: {gran_vel:.1f}% over {delta_days} days.\nObjective data suggests current protocol\nhas failed to progress the wound."})
                
            # --- NEW STRATEGY 1: SIZE REDUCTION LOGIC ---
            curr_area = current_stats.get("Width_px", 0) * current_stats.get("Length_px", 0)
            past_area = past_stats.get("Width_px", 0) * past_stats.get("Length_px", 0)
            
            if past_area > 0 and curr_area > 0:
                if curr_area < past_area:
                    reduction = ((past_area - curr_area) / past_area) * 100
                    alerts.append({"type": "success", "icon": "📏", "title": "Wound Contraction", "text": f"Physical footprint has decreased by {reduction:.1f}% since the last scan."})
                elif curr_area > past_area:
                    expansion = ((curr_area - past_area) / past_area) * 100
                    alerts.append({"type": "warning", "icon": "⚠️", "title": "Wound Expansion", "text": f"Physical footprint has increased by {expansion:.1f}% since the last scan."})

        else:
            alerts.append({"type": "info", "icon": "ℹ️", "title": "Insufficient Time (Not Saved)", "text": "A scan for this patient already exists today.\nThis analysis is for viewing only and will NOT\nbe saved to the permanent timeline."})
            should_save = False 
    else:
        if current_stats.get("Granulation", 0) >= 50:
            alerts.append({"type": "success", "icon": "✓", "title": "Baseline Recorded", "text": "Favorable viable tissue present.\nTrend analysis pending subsequent scans."})
        else:
            alerts.append({"type": "warning", "icon": "⚠️", "title": "Baseline Recorded", "text": "High non-viable tissue burden.\nTrend analysis pending subsequent scans."})
        
    if should_save:
        if patient_id not in db: 
            db[patient_id] = {"info": patient_info, "records": []}
        else:
            db[patient_id]["info"] = patient_info 
            
        db[patient_id]['records'].append({
            "date": clean_current_date, 
            "stats": current_stats, 
            "clinical_assessment": clinical_assessment,
            "image_path": image_path  
        })
        save_db(db)
        
    return alerts

# --- NEW: MODERN WARNING MODAL ---
class CustomWarningModal(ctk.CTkToplevel):
    def __init__(self, master, title, message):
        super().__init__(master)
        self.title(title)
        self.geometry("450x220")
        self.configure(fg_color=CARD_COLOR)
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() // 2) - (self.winfo_width() // 2)
            y = master.winfo_rooty() + (master.winfo_height() // 2) - (self.winfo_height() // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        icon_lbl = ctk.CTkLabel(self, text="⚠️", font=ctk.CTkFont(size=40), text_color="#D97706")
        icon_lbl.pack(pady=(20, 5))

        title_lbl = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR)
        title_lbl.pack(pady=(0, 10))

        msg_lbl = ctk.CTkLabel(self, text=message, font=ctk.CTkFont(size=14), text_color=SUBTEXT_COLOR, wraplength=400, justify="center")
        msg_lbl.pack(padx=20, pady=(0, 20))

        btn = ctk.CTkButton(self, text="Got it", width=120, height=35, font=ctk.CTkFont(weight="bold"), fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, command=self.destroy)
        btn.pack(pady=(0, 20))

# --- NATIVE MODERN CALENDAR WIDGET ---
class CTkCalendar(ctk.CTkToplevel):
    def __init__(self, master, on_date_selected):
        super().__init__(master)
        self.title("Select Scan Date")
        self.geometry("320x360")
        self.configure(fg_color=CARD_COLOR)
        self.resizable(False, False)
        self.grab_set() 
        self.on_date_selected = on_date_selected

        self.current_date = date.today()
        self.view_month = self.current_date.month
        self.view_year = self.current_date.year
        self.setup_ui()

    def setup_ui(self):
        for widget in self.winfo_children(): widget.destroy()
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(15, 10), padx=20)
        ctk.CTkButton(header, text="<", width=30, height=30, fg_color=BG_COLOR, text_color=TEXT_COLOR, hover_color=BORDER_COLOR, command=self.prev_month).pack(side="left")
        month_year_text = f"{calendar.month_name[self.view_month]} {self.view_year}"
        ctk.CTkLabel(header, text=month_year_text, font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_COLOR).pack(side="left", expand=True)
        ctk.CTkButton(header, text=">", width=30, height=30, fg_color=BG_COLOR, text_color=TEXT_COLOR, hover_color=BORDER_COLOR, command=self.next_month).pack(side="right")

        days_frame = ctk.CTkFrame(self, fg_color="transparent")
        days_frame.pack(fill="x", padx=20, pady=(0, 10))
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for day in days:
            ctk.CTkLabel(days_frame, text=day, width=38, font=ctk.CTkFont(size=12, weight="bold"), text_color=SUBTEXT_COLOR).pack(side="left", padx=1)

        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=5)

        cal = calendar.monthcalendar(self.view_year, self.view_month)
        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day != 0:
                    btn = ctk.CTkButton(grid_frame, text=str(day), width=38, height=38, fg_color="transparent", text_color=TEXT_COLOR, hover_color=BG_COLOR, corner_radius=19, command=lambda d=day: self.select_date(d))
                    if self.view_year == self.current_date.year and self.view_month == self.current_date.month and day == self.current_date.day:
                        btn.configure(fg_color=PRIMARY_BLUE, text_color="white", hover_color=HOVER_BLUE)
                    btn.grid(row=r, column=c, padx=1, pady=1)

    def prev_month(self):
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else: self.view_month -= 1
        self.setup_ui()

    def next_month(self):
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else: self.view_month += 1
        self.setup_ui()

    def select_date(self, day):
        selected = f"{self.view_year}-{self.view_month:02d}-{day:02d}"
        self.on_date_selected(selected)
        self.destroy()

# --- CUSTOM IMAGE CROPPER MODAL ---
class ImageCropperModal(ctk.CTkToplevel):
    def __init__(self, master, original_path, on_crop_done):
        super().__init__(master)
        self.title("Crop Wound Area")
        self.geometry("850x650")
        self.configure(fg_color=CARD_COLOR)
        self.resizable(False, False)
        self.grab_set() 

        self.on_crop_done = on_crop_done
        self.original_path = original_path

        self.cv_img = cv2.imread(original_path)
        if self.cv_img is None:
            messagebox.showerror("Error", "Could not load the image for cropping.")
            self.destroy()
            return
            
        self.cv_img_rgb = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2RGB)
        self.pil_img = Image.fromarray(self.cv_img_rgb)

        img_w, img_h = self.pil_img.size
        max_w, max_h = 800, 500
        self.scale = min(max_w / img_w, max_h / img_h)
        new_w, new_h = int(img_w * self.scale), int(img_h * self.scale)

        self.display_img = self.pil_img.resize((new_w, new_h))
        self.tk_img = ImageTk.PhotoImage(self.display_img) 

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", pady=(20, 5))
        
        ctk.CTkLabel(top_frame, text="Please click and drag to draw a box around the wound bed.", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).pack()
        ctk.CTkLabel(top_frame, text="Exclude as much background and healthy skin as possible for accurate analysis.", font=ctk.CTkFont(size=14), text_color=SUBTEXT_COLOR).pack()

        self.canvas_frame = ctk.CTkFrame(self, fg_color=BG_COLOR, border_width=1, border_color=BORDER_COLOR)
        self.canvas_frame.pack(pady=10)
        
        self.canvas = tk.Canvas(self.canvas_frame, width=new_w, height=new_h, cursor="crosshair", bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(padx=5, pady=5)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.rect = None
        self.start_x = None
        self.start_y = None
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 20))
        
        ctk.CTkButton(btn_frame, text="Cancel", fg_color=BG_COLOR, text_color=TEXT_COLOR, border_width=1, border_color=BORDER_COLOR, hover_color="#E5E7EB", command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="✂️ Crop & Use Image", font=ctk.CTkFont(weight="bold"), fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, command=self.crop_and_save).pack(side="left", padx=10)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y  
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='#10B981', width=3, dash=(4, 4)) 

    def on_move_press(self, event):
        curX, curY = (event.x, event.y)
        curX = max(0, min(self.canvas.winfo_width(), curX))
        curY = max(0, min(self.canvas.winfo_height(), curY))
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)

    def crop_and_save(self):
        if not self.rect:
            messagebox.showinfo("Draw a Box", "Please click and drag over the image to draw a crop box before saving.")
            return

        coords = self.canvas.coords(self.rect)
        if not coords or len(coords) != 4: return

        x1, y1, x2, y2 = coords
        left, right = sorted([x1, x2])
        top, bottom = sorted([y1, y2])

        orig_left = int(left / self.scale)
        orig_right = int(right / self.scale)
        orig_top = int(top / self.scale)
        orig_bottom = int(bottom / self.scale)

        if orig_right <= orig_left or orig_bottom <= orig_top: return

        cropped_cv_img = self.cv_img[orig_top:orig_bottom, orig_left:orig_right]
        
        unique_crop_file = f"cropped_wound_{int(time.time())}.jpg"
        cv2.imwrite(unique_crop_file, cropped_cv_img)
        
        self.on_crop_done(unique_crop_file)
        self.destroy()

# --- HISTORICAL IMAGE VIEWER MODAL ---
class ImageViewerModal(ctk.CTkToplevel):
    def __init__(self, master, image_path, date_str):
        super().__init__(master)
        self.title(f"Scan Images - {date_str}")
        self.geometry("1000x420")
        self.configure(fg_color=CARD_COLOR)
        self.resizable(False, False)
        self.grab_set() 

        ctk.CTkLabel(self, text=f"Analysis Imagery: {date_str}", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_COLOR).pack(pady=(20, 10))

        img_container = ctk.CTkFrame(self, fg_color="transparent")
        img_container.pack(fill="both", expand=True, padx=20, pady=10)

        lbl_img1 = ctk.CTkLabel(img_container, text="Loading...", width=300, height=220, fg_color=BG_COLOR, corner_radius=5)
        lbl_img1.grid(row=0, column=0, padx=10)
        lbl_img2 = ctk.CTkLabel(img_container, text="Loading...", width=300, height=220, fg_color=BG_COLOR, corner_radius=5)
        lbl_img2.grid(row=0, column=1, padx=10)
        lbl_img3 = ctk.CTkLabel(img_container, text="Loading...", width=300, height=220, fg_color=BG_COLOR, corner_radius=5)
        lbl_img3.grid(row=0, column=2, padx=10)

        ctk.CTkLabel(img_container, text="Original Image", text_color=SUBTEXT_COLOR, font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, pady=5)
        ctk.CTkLabel(img_container, text="Segmentation", text_color=SUBTEXT_COLOR, font=ctk.CTkFont(weight="bold")).grid(row=1, column=1, pady=5)
        ctk.CTkLabel(img_container, text="Tissue Map", text_color=SUBTEXT_COLOR, font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, pady=5)

        try:
            original, blurred = phase_1_preprocessing(image_path)
            hsv_image, wound_mask = phase_2_segmentation(blurred)
            tissue_visual, _ = phase_3_classification(hsv_image, wound_mask)

            master.display_image(original, lbl_img1)
            master.display_image(wound_mask, lbl_img2, is_gray=True)
            master.display_image(tissue_visual, lbl_img3)
        except Exception:
            lbl_img1.configure(text="Image File Not Found")
            lbl_img2.configure(text="Image File Not Found")
            lbl_img3.configure(text="Image File Not Found")

        ctk.CTkButton(self, text="Close", width=120, fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, command=self.destroy).pack(pady=(10, 20))

# --- MODERN GRAPHICAL USER INTERFACE ---
class WoundAssessmentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WoundQuant - Automated Tissue Quantification")
        self.geometry("1200x900")
        self.configure(fg_color=BG_COLOR)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) 
        
        self.current_image_path = None 
        self.current_clinical_assessment = None 
        
        self.header_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0, height=70)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.logo = ctk.CTkLabel(self.header_frame, text=" 📈 WoundQuant", font=ctk.CTkFont(size=24, weight="bold"), text_color=PRIMARY_BLUE)
        self.logo.grid(row=0, column=0, padx=30, pady=20)
        
        self.nav_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.nav_frame.grid(row=0, column=1, sticky="e", padx=30)
        
        ctk.CTkButton(self.nav_frame, text="Home", fg_color="transparent", text_color=TEXT_COLOR, hover_color=BG_COLOR, font=ctk.CTkFont(weight="bold"), command=self.show_home).pack(side="left", padx=5)
        ctk.CTkLabel(self.nav_frame, text="|", text_color="gray").pack(side="left")
        ctk.CTkButton(self.nav_frame, text="New Analysis", fg_color="transparent", text_color=TEXT_COLOR, hover_color=BG_COLOR, command=lambda: self.show_analysis("")).pack(side="left", padx=5)
        ctk.CTkLabel(self.nav_frame, text="|", text_color="gray").pack(side="left")
        ctk.CTkButton(self.nav_frame, text="Patient Directory", fg_color="transparent", text_color=TEXT_COLOR, hover_color=BG_COLOR, command=self.show_directory).pack(side="left", padx=5)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=1, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.setup_home_page()
        self.setup_directory_page()
        self.setup_analysis_page()
        self.setup_tracker_page()
        
        self.show_home()

    def open_image_viewer(self, image_path, date_str):
        ImageViewerModal(self, image_path, date_str)

    def open_view_note_modal(self, assessment_data, date_str):
        modal = ctk.CTkToplevel(self)
        modal.title("Clinical Assessment Details")
        modal.geometry("500x580")
        modal.configure(fg_color=CARD_COLOR)
        modal.resizable(False, False)
        modal.grab_set()

        # Header
        ctk.CTkLabel(modal, text=f"Clinical Assessment: {date_str}", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).pack(pady=(20, 10), padx=20, anchor="w")

        # Scrollable Container for the Cards
        container = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        if isinstance(assessment_data, dict):
            # --- CARD 1: WOUND CHARACTERISTICS ---
            char_frame = ctk.CTkFrame(container, fg_color=BG_COLOR, corner_radius=8)
            char_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(char_frame, text="📋 Wound Characteristics", font=ctk.CTkFont(size=14, weight="bold"), text_color=PRIMARY_BLUE).pack(anchor="w", padx=15, pady=(10, 5))
            
            def add_row(parent, label, value):
                row = ctk.CTkFrame(parent, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=2)
                ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
                ctk.CTkLabel(row, text=str(value), font=ctk.CTkFont(size=13), text_color=SUBTEXT_COLOR).pack(side="right")

            add_row(char_frame, "Exudate Amount:", assessment_data.get('exudate_amount', 'N/A'))
            add_row(char_frame, "Exudate Type:", assessment_data.get('exudate_type', 'N/A'))
            add_row(char_frame, "Wound Odor:", assessment_data.get('odor', 'N/A'))
            add_row(char_frame, "Pain Scale (0-10):", assessment_data.get('pain_scale', 'N/A'))
            ctk.CTkFrame(char_frame, height=5, fg_color="transparent").pack() # Bottom padding

            # --- CARD 2: INTERVENTIONS APPLIED ---
            interv_frame = ctk.CTkFrame(container, fg_color=BG_COLOR, corner_radius=8)
            interv_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(interv_frame, text="🩺 Interventions Applied", font=ctk.CTkFont(size=14, weight="bold"), text_color=PRIMARY_BLUE).pack(anchor="w", padx=15, pady=(10, 5))
            
            tx = assessment_data.get("treatments", {})
            applied = []
            if tx.get("cleansing"): applied.append("• Cleansing / Irrigation")
            if tx.get("debridement"): applied.append("• Debridement")
            if tx.get("antimicrobial"): applied.append("• Antimicrobial / Silver Dressing")
            if tx.get("moisture_retentive"): applied.append("• Moisture Retentive Dressing")
            if tx.get("topical_antibiotic"): applied.append("• Topical Antibiotic / Ointment")
            if tx.get("offloading"): applied.append("• Offloading / Compression")
            
            if not applied:
                applied.append("• None recorded")
                
            for item in applied:
                ctk.CTkLabel(interv_frame, text=item, font=ctk.CTkFont(size=13), text_color=SUBTEXT_COLOR).pack(anchor="w", padx=25, pady=1)
            ctk.CTkFrame(interv_frame, height=5, fg_color="transparent").pack() # Bottom padding

            # --- CARD 3: ADDITIONAL NOTES ---
            notes_text = assessment_data.get('additional_notes', '').strip()
            if notes_text:
                notes_frame = ctk.CTkFrame(container, fg_color=BG_COLOR, corner_radius=8)
                notes_frame.pack(fill="x", padx=10, pady=5)
                ctk.CTkLabel(notes_frame, text="📝 Additional Notes", font=ctk.CTkFont(size=14, weight="bold"), text_color=PRIMARY_BLUE).pack(anchor="w", padx=15, pady=(10, 0))
                ctk.CTkLabel(notes_frame, text=notes_text, font=ctk.CTkFont(size=13), text_color=SUBTEXT_COLOR, justify="left", wraplength=400).pack(anchor="w", padx=15, pady=(5, 10))

        else:
            # Smart Fallback: If viewing an old legacy text note, format it cleanly anyway
            legacy_frame = ctk.CTkFrame(container, fg_color=BG_COLOR, corner_radius=8)
            legacy_frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(legacy_frame, text="📝 Clinical Note", font=ctk.CTkFont(size=14, weight="bold"), text_color=PRIMARY_BLUE).pack(anchor="w", padx=15, pady=(10, 0))
            ctk.CTkLabel(legacy_frame, text=str(assessment_data), font=ctk.CTkFont(size=13), text_color=SUBTEXT_COLOR, justify="left", wraplength=400).pack(anchor="w", padx=15, pady=(5, 10))

        # Close Button
        ctk.CTkButton(modal, text="Close", height=40, font=ctk.CTkFont(size=14, weight="bold"), fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, command=modal.destroy).pack(pady=(10, 20), padx=20, fill="x")

    def open_note_modal(self):
        # Pass self.current_clinical_assessment into the modal so it knows what to pre-fill!
        self.modal = ClinicalAssessmentModal(self, self.receive_assessment_data, self.current_clinical_assessment)

    def receive_assessment_data(self, data):
        # Store the dictionary temporarily in the app
        self.current_clinical_assessment = data
        
        if self.current_clinical_assessment:
            self.lbl_note_status.configure(text="✓ Assessment attached", text_color=SUCCESS_GREEN)
            self.btn_add_note.configure(text="✏️ Edit Assessment")
        else:
            self.lbl_note_status.configure(text="")
            self.btn_add_note.configure(text="➕ Add Clinical Note")
    
    def clear_image(self):
        self.current_image_path = None
        self.lbl_filename.configure(text="No image selected")
        self.btn_clear_image.pack_forget()

        self.lbl_img1.configure(image="", text="Original Image")
        self.lbl_img2.configure(image="", text="Segmentation")
        self.lbl_img3.configure(image="", text="Tissue Map")

        for widget in self.results_container.winfo_children(): widget.destroy()
        self.placeholder_lbl = ctk.CTkLabel(self.results_container, text="Awaiting image analysis...", font=ctk.CTkFont(size=14), text_color=SUBTEXT_COLOR)
        self.placeholder_lbl.pack(pady=40)

        for widget in self.chart_container.winfo_children(): widget.destroy()

    def setup_home_page(self):
        self.home_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        # Changed to a ScrollableFrame to fit the new Guide comfortably
        center_frame = ctk.CTkScrollableFrame(self.home_frame, fg_color="transparent")
        center_frame.pack(expand=True, fill="both", padx=40, pady=(20, 10))

        title = ctk.CTkLabel(center_frame, text="Automated Chronic Wound Tissue\nQuantification", font=ctk.CTkFont(family="Segoe UI", size=38, weight="bold"), text_color=TEXT_COLOR)
        title.pack(pady=(20, 15))

        sub_text = "A rule-based image processing system using HSV color-space conversion to\nobjectively quantify granulation, slough, and necrotic tissues in diabetic ulcers and pressure sores."
        sub = ctk.CTkLabel(center_frame, text=sub_text, font=ctk.CTkFont(family="Segoe UI", size=16), text_color=SUBTEXT_COLOR, justify="center")
        sub.pack(pady=(0, 30))

        action_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        action_frame.pack(pady=(0, 40))
        
        btn_new_analysis = ctk.CTkButton(action_frame, text="➕ New Analysis", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, height=55, width=220, command=lambda: self.show_analysis(""))
        btn_new_analysis.pack(side="left", padx=15)
        
        btn_directory = ctk.CTkButton(action_frame, text="📁 Patient Directory", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, text_color=TEXT_COLOR, hover_color="#F3F4F6", height=55, width=220, command=self.show_directory)
        btn_directory.pack(side="left", padx=15)

        # --- NEW: 4-STEP QUICK START GUIDE FOR CLINICIANS ---
        guide_title = ctk.CTkLabel(center_frame, text="Quick Start Guide for Clinicians", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=TEXT_COLOR)
        guide_title.pack(pady=(10, 15))

        guide_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        guide_frame.pack(pady=(0, 30))

        def create_step(parent, step_num, icon, title_text, desc_text):
            card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=10, width=230, height=190)
            card.pack_propagate(False)
            card.pack(side="left", padx=10)
            
            top_f = ctk.CTkFrame(card, fg_color="transparent")
            top_f.pack(fill="x", padx=15, pady=(15, 5))
            
            ctk.CTkLabel(top_f, text=f"Step {step_num}", font=ctk.CTkFont(size=12, weight="bold"), text_color=PRIMARY_BLUE, fg_color="#E1EFFE", corner_radius=4, padx=8, pady=2).pack(side="left")
            ctk.CTkLabel(top_f, text=icon, font=ctk.CTkFont(size=20)).pack(side="right")
            
            ctk.CTkLabel(card, text=title_text, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=15, pady=(5, 5))
            ctk.CTkLabel(card, text=desc_text, font=ctk.CTkFont(family="Segoe UI", size=13), text_color=SUBTEXT_COLOR, wraplength=190, justify="left").pack(anchor="w", padx=15)

        create_step(guide_frame, "1", "✂️", "Upload & Crop", "Upload a clean wound scan and draw a bounding box to exclude healthy skin.")
        create_step(guide_frame, "2", "🩺", "Clinical Assessment", "Log standard exudate, odor, and applied interventions before analyzing.")
        create_step(guide_frame, "3", "📊", "Run Analysis", "Instantly generate objective tissue metrics and geometric size calculations.")
        create_step(guide_frame, "4", "📈", "Track Timeline", "Navigate to the Directory to view historical charts and healing velocity alerts.")

        # --- EXISTING DEEP LEARNING SECTION ---
        section_title = ctk.CTkLabel(center_frame, text="Why Traditional Image Processing Over Deep Learning?", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=TEXT_COLOR)
        section_title.pack(pady=(10, 20))

        cards_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        cards_frame.pack(pady=(0, 20))

        def create_card(parent, icon, title_text, desc_text):
            card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=10, width=240, height=200)
            card.pack_propagate(False)
            card.pack(side="left", padx=15)
            icon_box = ctk.CTkFrame(card, fg_color=BG_COLOR, corner_radius=8, width=40, height=40)
            icon_box.pack_propagate(False)
            icon_box.pack(anchor="w", padx=20, pady=(20, 15))
            ctk.CTkLabel(icon_box, text=icon, font=ctk.CTkFont(size=20), text_color=PRIMARY_BLUE).pack(expand=True)
            ctk.CTkLabel(card, text=title_text, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=(0, 5))
            ctk.CTkLabel(card, text=desc_text, font=ctk.CTkFont(family="Segoe UI", size=13), text_color=SUBTEXT_COLOR, wraplength=200, justify="left").pack(anchor="w", padx=20)

        create_card(cards_frame, "∿", "HSV Color-Space Analysis", "Rule-based algorithm using HSV conversion for precise tissue identification.")
        create_card(cards_frame, "🛡", "Objective Quantification", "Eliminates subjective 'naked-eye' assessment variability between observers.")
        create_card(cards_frame, "⏱", "Instant Tissue Breakdown", "Automated calculation of granulation, slough, and necrotic tissue percentages.")
        create_card(cards_frame, "↗", "Longitudinal Tracking", "Monitor healing progression through standardized measurements over time.")
    
    def setup_directory_page(self):
        self.directory_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.directory_frame.grid_columnconfigure(0, weight=1)
        
        top_bar = ctk.CTkFrame(self.directory_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=40, pady=(40, 10))
        
        title_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(title_frame, text="Patient Directory", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", pady=(0, 8))
        
        self.total_patients_lbl = ctk.CTkLabel(
            title_frame, 
            text="Total Patients: 0", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color="white",
            fg_color=SUCCESS_GREEN,
            corner_radius=12,
            padx=12,
            pady=4
        )
        self.total_patients_lbl.pack(anchor="w")
        
        self.search_entry = ctk.CTkEntry(top_bar, placeholder_text="Search Patient ID or Name...", width=250, border_color=BORDER_COLOR)
        self.search_entry.pack(side="right", padx=(10, 0))
        self.search_entry.bind("<Return>", self.refresh_patient_list)
        ctk.CTkButton(top_bar, text="Search", width=80, fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, command=self.refresh_patient_list).pack(side="right")

        self.patient_list_frame = ctk.CTkScrollableFrame(self.directory_frame, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        self.patient_list_frame.pack(fill="both", expand=True, padx=40, pady=10)

    def setup_analysis_page(self):
        self.analysis_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.analysis_frame.grid_columnconfigure(0, weight=1)
        self.analysis_frame.grid_rowconfigure(2, weight=1)

        self.input_frame = ctk.CTkFrame(self.analysis_frame, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=10)
        self.input_frame.grid(row=0, column=0, padx=40, pady=(20,10), sticky="ew")
        
        self.row0_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.row0_frame.pack(fill="x", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(self.row0_frame, text="Patient ID:", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 5))
        
        self.patient_id_entry = ctk.CTkEntry(self.row0_frame, placeholder_text="Auto-Assign", width=115)
        self.patient_id_entry.pack(side="left", padx=(0, 15))
        
        self.patient_id_entry.bind("<Return>", self.on_patient_id_enter)
        self.patient_id_entry.bind("<FocusOut>", self.on_patient_id_enter)
        
        ctk.CTkLabel(self.row0_frame, text="First Name:", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 5))
        self.first_name_entry = ctk.CTkEntry(self.row0_frame, placeholder_text="John", width=120)
        self.first_name_entry.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.row0_frame, text="Last Name:", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 5))
        self.last_name_entry = ctk.CTkEntry(self.row0_frame, placeholder_text="Doe", width=120)
        self.last_name_entry.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.row0_frame, text="Age:", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 5))
        self.patient_age_entry = ctk.CTkEntry(self.row0_frame, placeholder_text="Yrs", width=50)
        self.patient_age_entry.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.row0_frame, text="Sex:", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 5))
        self.patient_sex_combo = ctk.CTkComboBox(self.row0_frame, values=["Male", "Female"], width=100)
        self.patient_sex_combo.pack(side="left", padx=(0, 20))

        self.btn_edit_info = ctk.CTkButton(self.row0_frame, text="✏️ Edit", width=70, height=30, fg_color=BG_COLOR, text_color=TEXT_COLOR, border_width=1, border_color=BORDER_COLOR, hover_color="#E5E7EB", command=self.toggle_edit_mode)

        self.note_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.note_frame.pack(fill="x", padx=20, pady=(5, 10))

        self.btn_add_note = ctk.CTkButton(self.note_frame, text="➕ Add Clinical Note", width=160, fg_color=CARD_COLOR, text_color=TEXT_COLOR, border_width=1, border_color=BORDER_COLOR, hover_color="#F3F4F6", command=self.open_note_modal)
        self.btn_add_note.pack(side="left", padx=(0, 10))

        self.lbl_note_status = ctk.CTkLabel(self.note_frame, text="", font=ctk.CTkFont(size=12, slant="italic"), text_color=SUCCESS_GREEN)
        self.lbl_note_status.pack(side="left")

        self.divider = ctk.CTkFrame(self.input_frame, height=2, fg_color=BORDER_COLOR)
        self.divider.pack(fill="x", padx=20, pady=(5, 15))

        row1_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        row1_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(row1_frame, text="Scan Date:", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 5))
        self.date_entry = ctk.CTkEntry(row1_frame, width=120, border_color=BORDER_COLOR)
        self.date_entry.pack(side="left", padx=(0, 5))
        self.btn_calendar = ctk.CTkButton(row1_frame, text="📅", width=40, height=40, fg_color=BG_COLOR, text_color=TEXT_COLOR, hover_color="#E5E7EB", border_width=1, border_color=BORDER_COLOR, command=self.open_calendar)
        self.btn_calendar.pack(side="left", padx=(0, 20))
        
        self.btn_analyze = ctk.CTkButton(row1_frame, text="Analyze Wound", font=ctk.CTkFont(size=14, weight="bold"), fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, height=40, command=self.run_assessment)
        self.btn_analyze.pack(side="right", padx=(10, 0))

        self.btn_upload = ctk.CTkButton(row1_frame, text="Upload Image", font=ctk.CTkFont(size=14, weight="bold"), fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, text_color=TEXT_COLOR, hover_color="#F3F4F6", height=40, command=self.upload_image)
        self.btn_upload.pack(side="right", padx=(10, 0))
        
        self.btn_new_scan = ctk.CTkButton(row1_frame, text="➕ Scan Another Wound", font=ctk.CTkFont(size=14, weight="bold"), fg_color=SUCCESS_GREEN, text_color="white", hover_color=SUCCESS_HOVER, height=40, command=self.prepare_next_scan)

        self.file_info_container = ctk.CTkFrame(row1_frame, fg_color="transparent")
        self.file_info_container.pack(side="right", padx=(0, 15))

        self.lbl_filename = ctk.CTkLabel(self.file_info_container, text="No image selected", text_color=SUBTEXT_COLOR, font=ctk.CTkFont(size=12))
        self.lbl_filename.pack(side="left")

        self.btn_clear_image = ctk.CTkButton(self.file_info_container, text="✖", width=20, height=20, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#FEE2E2", text_color="#9B1C1C", hover_color="#FCA5A5", command=self.clear_image)

        self.image_panel = ctk.CTkFrame(self.analysis_frame, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=10)
        self.image_panel.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        self.image_panel.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.lbl_img1 = ctk.CTkLabel(self.image_panel, text="Original Image", width=300, height=220, fg_color=BG_COLOR, text_color="gray", corner_radius=5)
        self.lbl_img1.grid(row=0, column=0, padx=20, pady=20)
        self.lbl_img2 = ctk.CTkLabel(self.image_panel, text="Segmentation", width=300, height=220, fg_color=BG_COLOR, text_color="gray", corner_radius=5)
        self.lbl_img2.grid(row=0, column=1, padx=20, pady=20)
        self.lbl_img3 = ctk.CTkLabel(self.image_panel, text="Tissue Map", width=300, height=220, fg_color=BG_COLOR, text_color="gray", corner_radius=5)
        self.lbl_img3.grid(row=0, column=2, padx=20, pady=20)

        self.bottom_frame = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
        self.bottom_frame.grid(row=2, column=0, padx=40, pady=10, sticky="nsew")
        self.bottom_frame.grid_columnconfigure(0, weight=4) 
        self.bottom_frame.grid_columnconfigure(1, weight=6) 
        self.bottom_frame.grid_rowconfigure(0, weight=1)

        self.chart_panel = ctk.CTkFrame(self.bottom_frame, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=10)
        self.chart_panel.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ctk.CTkLabel(self.chart_panel, text="Tissue Composition", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_COLOR).pack(pady=(15, 0), anchor="w", padx=20)
        self.chart_container = ctk.CTkFrame(self.chart_panel, fg_color="transparent")
        self.chart_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.report_panel = ctk.CTkFrame(self.bottom_frame, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=10)
        self.report_panel.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        self.report_panel.grid_rowconfigure(1, weight=1)
        self.report_panel.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.report_panel, text="Healing Velocity Analysis", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=(15, 5), sticky="w", padx=20)
        
        self.results_container = ctk.CTkScrollableFrame(self.report_panel, fg_color="transparent")
        self.results_container.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        
        self.placeholder_lbl = ctk.CTkLabel(self.results_container, text="Awaiting image analysis...", font=ctk.CTkFont(size=14), text_color=SUBTEXT_COLOR)
        self.placeholder_lbl.pack(pady=40)

    def setup_tracker_page(self):
        self.tracker_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tracker_frame.grid_columnconfigure(0, weight=1)
        self.tracker_frame.grid_rowconfigure(2, weight=1)

        top_bar = ctk.CTkFrame(self.tracker_frame, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=40, pady=(20,0))
        
        btn_back = ctk.CTkButton(top_bar, text="← Back to Directory", fg_color="transparent", text_color=PRIMARY_BLUE, hover_color=BG_COLOR, font=ctk.CTkFont(weight="bold"), command=self.show_directory)
        btn_back.pack(side="left", anchor="n", pady=5)
        
        self.tracker_header_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        self.tracker_header_frame.pack(side="left", padx=20)

        self.tracker_chart_container = ctk.CTkFrame(self.tracker_frame, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR, height=350)
        self.tracker_chart_container.grid(row=1, column=0, sticky="ew", padx=40, pady=15)
        self.tracker_chart_container.pack_propagate(False)

        self.tracker_timeline_frame = ctk.CTkScrollableFrame(self.tracker_frame, fg_color="transparent")
        self.tracker_timeline_frame.grid(row=2, column=0, sticky="nsew", padx=40, pady=(0, 20))

    # ================= UI LOGIC & STATE MANAGEMENT =================
    
    def set_form_mode(self, mode):
        bg = CARD_COLOR 
        if mode == "read_only":
            self.patient_id_entry.configure(state="disabled", fg_color=bg, border_color=bg)
            self.first_name_entry.configure(state="disabled", fg_color=bg, border_color=bg)
            self.last_name_entry.configure(state="disabled", fg_color=bg, border_color=bg)
            self.patient_age_entry.configure(state="disabled", fg_color=bg, border_color=bg)
            self.patient_sex_combo.configure(state="disabled", fg_color=bg, border_color=bg, button_color=bg)
            self.btn_add_note.configure(state="disabled") 
            self.btn_clear_image.pack_forget() 
            
            self.btn_edit_info.pack(side="left", padx=(15, 0))
            self.btn_edit_info.configure(text="✏️ Edit Info", fg_color=BG_COLOR, text_color=TEXT_COLOR)
            
        elif mode == "editable":
            self.patient_id_entry.configure(state="disabled", fg_color=bg, border_color=bg) 
            
            self.first_name_entry.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR)
            self.last_name_entry.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR)
            self.patient_age_entry.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR)
            self.patient_sex_combo.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR, button_color=PRIMARY_BLUE)
            self.btn_add_note.configure(state="normal")
            
            self.btn_edit_info.pack(side="left", padx=(15, 0))
            self.btn_edit_info.configure(text="💾 Save Changes", fg_color=PRIMARY_BLUE, text_color="white")
            
        elif mode == "new":
            self.patient_id_entry.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR)
            self.first_name_entry.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR)
            self.last_name_entry.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR)
            self.patient_age_entry.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR)
            self.patient_sex_combo.configure(state="normal", fg_color=CARD_COLOR, border_color=BORDER_COLOR, button_color=PRIMARY_BLUE)
            self.btn_add_note.configure(state="normal")
            
            self.btn_edit_info.pack_forget() 

    def toggle_edit_mode(self):
        if self.first_name_entry.cget("state") == "disabled":
            self.set_form_mode("editable")
        else:
            confirm = messagebox.askyesno("Confirm Changes", "Are you sure you want to save these changes to the patient's record?")
            if confirm:
                pat_id = self.patient_id_entry.get().strip()
                db = load_db()
                if pat_id in db:
                    db[pat_id]["info"]["first_name"] = self.first_name_entry.get().strip()
                    db[pat_id]["info"]["last_name"] = self.last_name_entry.get().strip()
                    db[pat_id]["info"]["age"] = self.patient_age_entry.get().strip()
                    db[pat_id]["info"]["sex"] = self.patient_sex_combo.get()
                    save_db(db)
                self.set_form_mode("read_only")
                
                self.btn_add_note.configure(state="normal")

    def on_patient_id_enter(self, event=None):
        pat_id = self.patient_id_entry.get().strip()
        if not pat_id: return
        
        db = load_db()
        if pat_id in db:
            info = db[pat_id].get("info", {})
            self.first_name_entry.delete(0, 'end')
            self.first_name_entry.insert(0, info.get("first_name", ""))
            
            self.last_name_entry.delete(0, 'end')
            self.last_name_entry.insert(0, info.get("last_name", ""))
            
            self.patient_age_entry.delete(0, 'end')
            self.patient_age_entry.insert(0, info.get("age", ""))
            
            self.patient_sex_combo.set(info.get("sex", "Male"))
            
            self.set_form_mode("read_only")
        else:
            self.set_form_mode("new")

    def open_calendar(self):
        def set_date(selected_date):
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, selected_date)
        CTkCalendar(self, set_date)
    
    def hide_all_frames(self):
        self.home_frame.grid_forget()
        self.analysis_frame.grid_forget()
        self.directory_frame.grid_forget()
        self.tracker_frame.grid_forget()

    def show_home(self):
        self.hide_all_frames()
        self.home_frame.grid(row=0, column=0, sticky="nsew")

    def show_directory(self):
        self.hide_all_frames()
        self.directory_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_patient_list()

    def show_analysis(self, patient_id=""):
        self.hide_all_frames()
        self.analysis_frame.grid(row=0, column=0, sticky="nsew")
        
        self.set_form_mode("new") 
        self.btn_new_scan.pack_forget() 
        
        self.clear_image()
        
        self.patient_id_entry.delete(0, 'end')
        
        if not patient_id:
            next_id = get_next_auto_id()
            self.patient_id_entry.configure(placeholder_text=f"Auto: {next_id}")
        else:
            self.patient_id_entry.configure(placeholder_text="ID")
            
        self.first_name_entry.delete(0, 'end')
        self.last_name_entry.delete(0, 'end')
        self.patient_age_entry.delete(0, 'end')
        self.patient_sex_combo.set("Male")
        self.date_entry.delete(0, 'end')
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self.current_clinical_assessment = None
        self.lbl_note_status.configure(text="")
        self.btn_add_note.configure(text="➕ Add Clinical Note")

        for widget in self.results_container.winfo_children(): widget.destroy()
        self.placeholder_lbl = ctk.CTkLabel(self.results_container, text="Awaiting image analysis...", font=ctk.CTkFont(size=14), text_color=SUBTEXT_COLOR)
        self.placeholder_lbl.pack(pady=40)
        for widget in self.chart_container.winfo_children(): widget.destroy()

        if patient_id:
            self.patient_id_entry.insert(0, patient_id)
            db = load_db()
            if patient_id in db:
                info = db[patient_id].get("info", {})
                self.first_name_entry.insert(0, info.get("first_name", ""))
                self.last_name_entry.insert(0, info.get("last_name", ""))
                self.patient_age_entry.insert(0, info.get("age", ""))
                self.patient_sex_combo.set(info.get("sex", "Male"))
            self.set_form_mode("read_only")
            self.btn_add_note.configure(state="normal") 

    def prepare_next_scan(self):
        self.clear_image()
        
        self.current_clinical_assessment = None
        self.lbl_note_status.configure(text="")
        self.btn_add_note.configure(state="normal", text="➕ Add Clinical Note")
        
        self.btn_new_scan.pack_forget()

    def show_tracker(self, patient_id):
        self.hide_all_frames()
        self.tracker_frame.grid(row=0, column=0, sticky="nsew")
        db = load_db()
        if patient_id in db:
            fn = db[patient_id]['info'].get('first_name', 'Unknown')
            ln = db[patient_id]['info'].get('last_name', '')
            age = db[patient_id]['info'].get('age', 'N/A')
            sex = db[patient_id]['info'].get('sex', 'N/A')
            full_name = f"{fn} {ln}".strip()
        else:
            full_name = 'Unknown'
            age = 'N/A'
            sex = 'N/A'
            
        for widget in self.tracker_header_frame.winfo_children():
            widget.destroy()

        title_row = ctk.CTkFrame(self.tracker_header_frame, fg_color="transparent")
        title_row.pack(fill="x", anchor="w")
        ctk.CTkLabel(title_row, text="Healing Timeline", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_COLOR).pack(side="left", pady=(0, 5))

        info_row = ctk.CTkFrame(self.tracker_header_frame, fg_color="transparent")
        info_row.pack(fill="x", anchor="w")
        
        ctk.CTkLabel(info_row, text=f"👤 {full_name}", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 10))
        
        id_badge = ctk.CTkFrame(info_row, fg_color="#E1EFFE", corner_radius=4, border_width=1, border_color="#76A9FA")
        id_badge.pack(side="left", padx=(0, 15))
        ctk.CTkLabel(id_badge, text=f"ID: {patient_id}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#1E429F").pack(padx=6, pady=1)

        ctk.CTkLabel(info_row, text=f"{age} yrs  •  {sex}", font=ctk.CTkFont(size=13), text_color=SUBTEXT_COLOR).pack(side="left")
        
        self.load_tracker_data(patient_id)

    # ================= APP LOGIC =================
    
    def delete_patient(self, pat_id, full_name):
        confirm = messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to permanently delete the entire record for {full_name} (ID: {pat_id})?\n\nThis action cannot be undone."
        )
        if confirm:
            db = load_db()
            if pat_id in db:
                del db[pat_id]
                save_db(db)
                self.refresh_patient_list() 
    
    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file_path:
            # Reverted back to the original manual cropping UI
            ImageCropperModal(self, file_path, self.handle_cropped_image)
            
    def handle_cropped_image(self, final_cropped_path):
        self.current_image_path = final_cropped_path
        self.lbl_filename.configure(text="cropped_wound.jpg")
        
        self.btn_clear_image.pack(side="left", padx=(8, 0))
        
        try:
            img = cv2.imread(final_cropped_path)
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.display_image(img_rgb, self.lbl_img1)
                
                self.lbl_img2.configure(image="", text="Segmentation Pending...")
                self.lbl_img3.configure(image="", text="Tissue Map Pending...")
        except Exception:
            pass

    def refresh_patient_list(self, event=None):
        for widget in self.patient_list_frame.winfo_children(): widget.destroy()

        db = load_db()
        total_count = len(db)
        self.total_patients_lbl.configure(text=f"Total Patients: {total_count}")
        
        search_query = self.search_entry.get().strip().lower()
        search_terms = search_query.split() 

        if not db:
            ctk.CTkLabel(self.patient_list_frame, text="No patients found. Click 'New Analysis' to start tracking.", text_color=SUBTEXT_COLOR).pack(pady=40)
            return

        for pat_id, data in db.items():
            fn = data['info'].get('first_name', 'Unknown')
            ln = data['info'].get('last_name', '')
            full_name = f"{fn} {ln}".strip()
            
            if search_terms:
                match = all((term in pat_id.lower() or term in full_name.lower()) for term in search_terms)
                if not match: 
                    continue 
                
            records = data['records']
            last_date = records[-1]['date'][:10] if records else "N/A"
            total_scans = len(records)
            
            card = ctk.CTkFrame(self.patient_list_frame, fg_color=BG_COLOR, corner_radius=8)
            card.pack(fill="x", pady=5, padx=10)
            
            first_initial = fn[0].upper() if fn and fn != "Unknown" else "?"
            last_initial = ln[0].upper() if ln else ""
            initials = f"{first_initial}{last_initial}" if first_initial != "?" else "U"
            
            avatar_frame = ctk.CTkFrame(card, width=48, height=48, corner_radius=24, fg_color=PRIMARY_BLUE)
            avatar_frame.pack(side="left", padx=(20, 10), pady=15)
            avatar_frame.pack_propagate(False)
            ctk.CTkLabel(avatar_frame, text=initials, font=ctk.CTkFont(size=18, weight="bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=15)
            
            name_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            name_row.pack(fill="x", anchor="w")
            
            ctk.CTkLabel(name_row, text=full_name, font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(0, 10))
            
            id_badge = ctk.CTkFrame(name_row, fg_color="#E1EFFE", corner_radius=4, border_width=1, border_color="#76A9FA")
            id_badge.pack(side="left", pady=2)
            ctk.CTkLabel(id_badge, text=f"ID: {pat_id}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#1E429F").pack(padx=6, pady=1)

            meta_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            meta_row.pack(fill="x", pady=(2, 0))
            
            age_sex = f"👤 {data['info'].get('age', 'N/A')} yrs  •  {data['info'].get('sex', 'N/A')}"
            scans_date = f"📊 {total_scans} Scans  •  🕒 Last Update: {last_date}"
            
            ctk.CTkLabel(meta_row, text=age_sex, text_color=SUBTEXT_COLOR, font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 15))
            ctk.CTkLabel(meta_row, text=scans_date, text_color=SUBTEXT_COLOR, font=ctk.CTkFont(size=12)).pack(side="left")
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=20, pady=15)
            
            ctk.CTkButton(btn_frame, text="Delete", fg_color="#FEE2E2", text_color="#9B1C1C", hover_color="#FCA5A5", border_width=1, border_color="#F98080", width=60, height=28, command=lambda p=pat_id, n=full_name: self.delete_patient(p, n)).pack(side="right", padx=(10, 0))
            ctk.CTkButton(btn_frame, text="+ Add Follow-Up", fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE, command=lambda p=pat_id: self.show_analysis(p)).pack(side="right", padx=(10, 0))
            ctk.CTkButton(btn_frame, text="View Timeline", fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_COLOR, hover_color="#E5E7EB", command=lambda p=pat_id: self.show_tracker(p)).pack(side="right")
            
    def load_tracker_data(self, pat_id):
        db = load_db()
        for widget in self.tracker_chart_container.winfo_children(): widget.destroy()
        for widget in self.tracker_timeline_frame.winfo_children(): widget.destroy()
        
        if pat_id not in db or not db[pat_id]['records']:
            ctk.CTkLabel(self.tracker_timeline_frame, text="No records found.", text_color="gray").pack(pady=20)
            return

        records = db[pat_id]['records']
        display_dates = [rec['date'][:10] for rec in records]
        gran_vals = [rec['stats']['Granulation'] for rec in records]
        slough_vals = [rec['stats']['Slough'] for rec in records]
        nec_vals = [rec['stats']['Necrotic'] for rec in records]

        fig, ax = plt.subplots(figsize=(10, 3.5), facecolor='#FFFFFF')
        ax.plot(display_dates, gran_vals, color='#DC2626', marker='o', markersize=8, markeredgecolor='white', markeredgewidth=2, linewidth=3, label='Granulation')
        ax.plot(display_dates, slough_vals, color='#D97706', marker='o', markersize=8, markeredgecolor='white', markeredgewidth=2, linewidth=3, label='Slough')
        ax.plot(display_dates, nec_vals, color='#1F2937', marker='o', markersize=8, markeredgecolor='white', markeredgewidth=2, linewidth=3, label='Necrotic')
        
        ax.set_ylim(-5, 105)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.yaxis.grid(True, linestyle='-', color='#E5E7EB')
        ax.tick_params(axis='y', length=0, colors='#6B7280', labelsize=10)
        ax.tick_params(axis='x', length=0, colors='#4B5563', labelsize=10, pad=10)
        plt.xticks(rotation=0 if len(display_dates) <= 4 else 15, ha='center' if len(display_dates) <= 4 else 'right')
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=3, frameon=False, fontsize=11)
        
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.tracker_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

        for i, record in enumerate(reversed(records)): 
            actual_visit_num = len(records) - i
            idx = len(records) - 1 - i 
            stats = record['stats']
            curr_date_str = record['date'][:10]
            
            img_path = record.get('image_path', '')
            
            card = ctk.CTkFrame(self.tracker_timeline_frame, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=8, padx=5)
            
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 5))
            ctk.CTkLabel(header, text=f"Visit {actual_visit_num}", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
            
            right_header = ctk.CTkFrame(header, fg_color="transparent")
            right_header.pack(side="right")
            
            if img_path and os.path.exists(img_path):
                btn_view_img = ctk.CTkButton(right_header, text="🖼️ View Images", width=110, height=26, font=ctk.CTkFont(size=12, weight="bold"), fg_color=BG_COLOR, text_color=PRIMARY_BLUE, border_width=1, border_color=PRIMARY_BLUE, hover_color="#E1EFFE", command=lambda p=img_path, d=curr_date_str: self.open_image_viewer(p, d))
                btn_view_img.pack(side="left", padx=(0, 15))
                
            # SMART LOAD: Grab new dict format OR fallback to old text string format
            assessment_data = record.get('clinical_assessment')
            old_note = record.get('note', '').strip()
            display_data = assessment_data if assessment_data else old_note
            
            if display_data:
                btn_view_note = ctk.CTkButton(right_header, text="📝 View Assessment", width=120, height=26, font=ctk.CTkFont(size=12, weight="bold"), fg_color=BG_COLOR, text_color="#059669", border_width=1, border_color="#059669", hover_color="#DEF7EC", command=lambda a=display_data, d=curr_date_str: self.open_view_note_modal(a, d))
                btn_view_note.pack(side="left", padx=(0, 15))
                
            ctk.CTkLabel(right_header, text=f"Recorded: {curr_date_str}", font=ctk.CTkFont(size=14), text_color=SUBTEXT_COLOR).pack(side="left")
            
            bar_container = ctk.CTkFrame(card, fg_color="transparent")
            bar_container.pack(fill="x", padx=20, pady=(5, 10)) 
            
            labels_frame = ctk.CTkFrame(bar_container, fg_color="transparent")
            labels_frame.pack(fill="x", pady=(0, 8))
            ctk.CTkLabel(labels_frame, text=f"Granulation {stats.get('Granulation', 0):.1f}%", text_color="#DC2626", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            ctk.CTkLabel(labels_frame, text=f"Slough {stats.get('Slough', 0):.1f}%", text_color="#D97706", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=20)
            ctk.CTkLabel(labels_frame, text=f"Necrotic {stats.get('Necrotic', 0):.1f}%", text_color="#1F2937", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

            # --- STRATEGY 1: SIZE IN TIMELINE ---
            w_px = stats.get('Width_px', 0)
            h_px = stats.get('Length_px', 0)
            if w_px > 0 or h_px > 0:
                ctk.CTkLabel(labels_frame, text=f"|  📏 Size: {w_px}x{h_px} px", text_color=SUBTEXT_COLOR, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(20, 0))

            bar_bg = ctk.CTkFrame(bar_container, height=12, fg_color="#E5E7EB", corner_radius=6)
            bar_bg.pack(fill="x")
            
            g_pct = stats.get('Granulation', 0) / 100.0
            s_pct = stats.get('Slough', 0) / 100.0
            n_pct = stats.get('Necrotic', 0) / 100.0
            
            if g_pct > 0: ctk.CTkFrame(bar_bg, height=12, fg_color="#DC2626", corner_radius=6).place(relx=0, rely=0, relwidth=g_pct, relheight=1)
            if s_pct > 0: ctk.CTkFrame(bar_bg, height=12, fg_color="#D97706", corner_radius=6).place(relx=g_pct, rely=0, relwidth=s_pct, relheight=1)
            if n_pct > 0: ctk.CTkFrame(bar_bg, height=12, fg_color="#1F2937", corner_radius=6).place(relx=g_pct+s_pct, rely=0, relwidth=n_pct, relheight=1)

            alert_bg, alert_border, alert_text_color = "#E1EFFE", "#76A9FA", "#1E429F"
            icon, title, text = "ℹ️", "", ""

            if idx == 0:
                if stats.get("Granulation", 0) >= 50:
                    icon, title = "✓", "Baseline Recorded"
                    text = "Favorable viable tissue. Trend analysis pending."
                    alert_bg, alert_border, alert_text_color = "#DEF7EC", "#31C48D", "#03543F"
                else:
                    icon, title = "⚠️", "Baseline Recorded"
                    text = "High non-viable tissue. Trend analysis pending."
                    alert_bg, alert_border, alert_text_color = "#FDE8E8", "#F98080", "#9B1C1C"
            else:
                past_stats = records[idx - 1]['stats']
                past_date_str = records[idx - 1]['date'][:10]
                
                try:
                    d1 = datetime.strptime(past_date_str, "%Y-%m-%d")
                    d2 = datetime.strptime(curr_date_str, "%Y-%m-%d")
                    delta_days = (d2 - d1).days
                    
                    if delta_days > 0:
                        gran_vel = (stats.get("Granulation", 0) - past_stats.get("Granulation", 0)) / delta_days
                        if gran_vel > 0:
                            icon, title = "↗️", "Positive Trend"
                            text = f"Healing Velocity: +{gran_vel:.1f}% Granulation/day."
                            alert_bg, alert_border, alert_text_color = "#DEF7EC", "#31C48D", "#03543F"
                        else:
                            icon, title = "⚠️", "Stagnation Detected"
                            text = f"Velocity: {gran_vel:.1f}% over {delta_days} days."
                            alert_bg, alert_border, alert_text_color = "#FDE8E8", "#F98080", "#9B1C1C"
                except Exception:
                    pass

            alert_f = ctk.CTkFrame(card, fg_color=alert_bg, border_width=1, border_color=alert_border, corner_radius=6)
            alert_f.pack(fill="x", padx=20, pady=(0, 15))
            ctk.CTkLabel(alert_f, text=f"{icon} {title} — {text}", font=ctk.CTkFont(size=12, weight="bold"), text_color=alert_text_color).pack(anchor="w", padx=10, pady=6)

    def run_assessment(self):
        if not self.current_image_path:
            CustomWarningModal(self, "Missing Data", "Please upload a wound image before running the analysis.")
            return

        first_name = self.first_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
        patient_age = self.patient_age_entry.get().strip()
        
        if not first_name or not last_name or not patient_age:
            CustomWarningModal(self, "Missing Information", "Please fill up all the necessary information\n(First Name, Last Name, and Age).")
            return
            
        patient_id = self.patient_id_entry.get().strip()
        db = load_db()

        if patient_id and patient_id in db and self.patient_id_entry.cget("state") == "normal":
            CustomWarningModal(
                self,
                "Duplicate Patient ID", 
                f"The Patient ID '{patient_id}' already exists in the system!\n\nIf you are creating a new patient, please use a unique ID.\nIf you want to add a scan, go to the Directory and click '+ Add Follow-Up'."
            )
            return

        if not patient_id:
            patient_id = get_next_auto_id() 
            messagebox.showinfo("ID Auto-Generated", f"No ID was entered.\n\nThe system has automatically assigned this scan to Patient ID: {patient_id}")
            
            self.patient_id_entry.delete(0, 'end')
            self.patient_id_entry.insert(0, patient_id)
        
        patient_sex = self.patient_sex_combo.get()
        scan_date = self.date_entry.get().strip()
        
        clinical_assessment = self.current_clinical_assessment
        
        try:
            original, blurred = phase_1_preprocessing(self.current_image_path)
            hsv_image, wound_mask = phase_2_segmentation(blurred)
            tissue_visual, results = phase_3_classification(hsv_image, wound_mask)
            
            patient_info = {"first_name": first_name, "last_name": last_name, "age": patient_age, "sex": patient_sex}
            alerts = phase_4_decision_support(patient_id, patient_info, results, scan_date, clinical_assessment, self.current_image_path)
            
            self.display_image(original, self.lbl_img1)
            self.display_image(wound_mask, self.lbl_img2, is_gray=True)
            self.display_image(tissue_visual, self.lbl_img3)
            self.draw_horizontal_bar_chart(results)

            for widget in self.results_container.winfo_children(): widget.destroy()

            full_name = f"{first_name} {last_name}".strip()

            meta_frame = ctk.CTkFrame(self.results_container, fg_color=BG_COLOR, corner_radius=6)
            meta_frame.pack(fill="x", pady=(0, 15))
            
            ctk.CTkLabel(meta_frame, text=f"👤 {full_name} (ID: {patient_id})", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_COLOR).pack(side="left", padx=(15, 5), pady=8)
            ctk.CTkLabel(meta_frame, text=f"Age: {patient_age} • Sex: {patient_sex}", font=ctk.CTkFont(size=12), text_color=SUBTEXT_COLOR).pack(side="left", padx=5, pady=8)
            
            ctk.CTkLabel(meta_frame, text=f"📅 Date: {scan_date[:10]}", font=ctk.CTkFont(size=13, weight="bold"), text_color=SUBTEXT_COLOR).pack(side="right", padx=15, pady=8)

            # --- STRATEGY 1: NEW SIZE FRAME IN RESULTS ---
            size_frame = ctk.CTkFrame(self.results_container, fg_color="#E1EFFE", corner_radius=6)
            size_frame.pack(fill="x", pady=(0, 15))
            ctk.CTkLabel(size_frame, text=f"📏 Wound Footprint: {results.get('Width_px', 0)}px (W) × {results.get('Length_px', 0)}px (L)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#1E429F").pack(pady=8)

            for alert in alerts:
                if alert["type"] == "success":
                    bg_c, border_c, text_c = "#DEF7EC", "#31C48D", "#03543F" 
                elif alert["type"] == "warning":
                    bg_c, border_c, text_c = "#FDE8E8", "#F98080", "#9B1C1C" 
                else:
                    bg_c, border_c, text_c = "#E1EFFE", "#76A9FA", "#1E429F" 

                alert_card = ctk.CTkFrame(self.results_container, fg_color=bg_c, border_width=1, border_color=border_c, corner_radius=8)
                alert_card.pack(fill="x", pady=5)

                header_f = ctk.CTkFrame(alert_card, fg_color="transparent")
                header_f.pack(fill="x", padx=15, pady=(12, 5))
                ctk.CTkLabel(header_f, text=f"{alert['icon']} {alert['title']}", font=ctk.CTkFont(size=14, weight="bold"), text_color=text_c).pack(side="left")

                ctk.CTkLabel(alert_card, text=alert['text'], font=ctk.CTkFont(size=13), text_color=text_c, justify="left").pack(anchor="w", padx=15, pady=(0, 15))

            disclaimer = ctk.CTkLabel(self.results_container, text="* This is a diagnostic decision-support tool. Final diagnosis remains with the clinician.", font=ctk.CTkFont(size=11, slant="italic"), text_color=SUBTEXT_COLOR, wraplength=380, justify="left")
            disclaimer.pack(side="bottom", anchor="w", pady=(15, 0))
            
            self.btn_new_scan.pack(side="right", padx=(10, 10))
            self.set_form_mode("read_only")
            
        except Exception as e: messagebox.showerror("Processing Error", str(e))

    def draw_horizontal_bar_chart(self, stats):
        for widget in self.chart_container.winfo_children(): widget.destroy()
        colors = ['#DC2626', '#EAB308', '#1F2937'] 
        bg_bar = '#E5E7EB'
        labels = ['Granulation (Red)', 'Slough (Yellow)', 'Necrotic (Black)']
        values = [stats.get('Granulation', 0), stats.get('Slough', 0), stats.get('Necrotic', 0)]

        fig, ax = plt.subplots(figsize=(5, 3), facecolor='#FFFFFF') 
        y_pos = [2, 1, 0] 
        ax.barh(y_pos, [100, 100, 100], color=bg_bar, height=0.3)
        bars = ax.barh(y_pos, values, color=colors, height=0.3)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontdict={'fontsize': 10, 'color': '#374151'})
        ax.tick_params(axis='y', length=0, pad=15) 
        ax.xaxis.set_visible(False) 
        ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False) 

        for i, v in enumerate(values):
            ax.text(102, y_pos[i], f"{v:.0f}%", va='center', fontdict={'fontsize': 10, 'fontweight': 'bold', 'color': colors[i]})

        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def display_image(self, cv_img, label_widget, is_gray=False):
        h, w = cv_img.shape[:2]
        ratio = 300 / float(w) 
        new_h = int(h * ratio)
        resized = cv2.resize(cv_img, (300, new_h))
        if is_gray: img_pil = Image.fromarray(resized)
        else: img_pil = Image.fromarray(resized) 
        ctk_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(300, new_h))
        label_widget.configure(image=ctk_img, text="")

if __name__ == "__main__":
    app = WoundAssessmentApp()
    app.mainloop()
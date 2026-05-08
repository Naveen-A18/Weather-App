import requests
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from datetime import datetime, timedelta
import csv
import os
import pyttsx3
import threading

# --------------- CONFIG -----------------

API_KEY = "0c5e8afbf6717ef81df162c66364fbee"
CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
CSV_FILE = "data/weather_data.csv"

ICON_MAP = {
    "Clear": ("icons/sun.gif", "icons/sun.png"),
    "Clouds": ("icons/cloud.gif", "icons/cloud.png"),
    "Rain": ("icons/rain.gif", "icons/rain.png"),
    "Thunderstorm": ("icons/storm.gif", "icons/storm.png"),
    "Drizzle": ("icons/rain.gif", "icons/rain.png"),
}

# THEMES
DARK_THEME = {
    "bg": "#0f172a",
    "text": "white",
    "accent": "#7ec8ff",
    "muted": "#c0c0c0",
    "advice": "#8be9fd",
    "frame_bg": "#0f172a",
    "entry_bg": "#020617",
    "entry_fg": "#e5e7eb",
    "entry_cursor": "#38bdf8",
    "button_bg": "#1d4ed8",
    "button_hover": "#2563eb",
    "button_fg": "white",
    "status": "#a5b4fc",
    "footer": "#64748b",
    "forecast_bg": "#020617",
    "forecast_fg": "#e5e7eb",
}

LIGHT_THEME = {
    "bg": "#f3f4f6",
    "text": "#111827",
    "accent": "#1d4ed8",
    "muted": "#4b5563",
    "advice": "#0369a1",
    "frame_bg": "#e5e7eb",
    "entry_bg": "white",
    "entry_fg": "#111827",
    "entry_cursor": "#1d4ed8",
    "button_bg": "#2563eb",
    "button_hover": "#1d4ed8",
    "button_fg": "white",
    "status": "#4b5563",
    "footer": "#6b7280",
    "forecast_bg": "white",
    "forecast_fg": "#111827",
}

current_theme = DARK_THEME
BG_COLOR = current_theme["bg"]

# --------------- GLOBALS -----------------

previous_temp = None
loading = False
loading_job = None
VOICE_ENABLED = True
theme_mode = "dark"  # or "light"

# --------------- VOICE ENGINE -----------------

engine = pyttsx3.init()
engine.setProperty("rate", 165)

engine_lock = threading.Lock()  # to avoid conflicts


def speak(text: str):
    """Speak in a background thread so GUI doesn't freeze."""
    if not VOICE_ENABLED:
        return

    def _worker():
        try:
            with engine_lock:
                engine.say(text)
                engine.runAndWait()
        except Exception as e:
            print("Voice error:", e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# --------------- API FUNCTIONS -----------------

def fetch_current_weather(city: str) -> dict:
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    r = requests.get(CURRENT_URL, params=params)
    if r.status_code != 200:
        raise Exception(r.json().get("message", "API error"))

    data = r.json()
    weather = {
        "city": data["name"],
        "temp": data["main"]["temp"],
        "feels": data["main"]["feels_like"],
        "temp_min": data["main"]["temp_min"],
        "temp_max": data["main"]["temp_max"],
        "humidity": data["main"]["humidity"],
        "wind": data["wind"]["speed"],
        "main": data["weather"][0]["main"],
        "desc": data["weather"][0]["description"].title(),
        "timezone": data.get("timezone", 0),  # seconds offset from UTC
    }
    return weather


def fetch_forecast(city: str):
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    r = requests.get(FORECAST_URL, params=params)
    if r.status_code != 200:
        raise Exception(r.json().get("message", "Forecast API error"))

    data = r.json()
    list_data = data["list"]

    daily = {}
    for item in list_data:
        dt_txt = item["dt_txt"]  # "YYYY-MM-DD HH:MM:SS"
        date_str, time_str = dt_txt.split()
        if time_str.startswith("12:00"):
            daily[date_str] = {
                "temp": item["main"]["temp"],
                "desc": item["weather"][0]["description"].title(),
            }

    forecast_list = []
    for date_str in sorted(daily.keys())[:5]:
        forecast_list.append(
            {"date": date_str, "temp": daily[date_str]["temp"], "desc": daily[date_str]["desc"]}
        )
    return forecast_list


# --------------- SMART ADVICE -----------------

def health_advice(temp: float, main_cond: str) -> str:
    if "Rain" in main_cond or "Drizzle" in main_cond:
        return "It may rain. Carry an umbrella and avoid getting drenched ☔"
    if "Thunderstorm" in main_cond:
        return "Thunderstorm expected. Stay indoors and avoid open areas ⛈️"
    if temp >= 35:
        return "Very hot! Drink plenty of water and avoid going out at noon 🥵"
    if 30 <= temp < 35:
        return "Quite warm. Stay hydrated and wear light clothes 🥤"
    if temp <= 10:
        return "Very cold. Wear warm clothes, jacket and cover your ears 🧥"
    if 10 < temp <= 18:
        return "Cool weather. A light jacket or hoodie is recommended 🙂"
    return "Weather looks pleasant. Perfect for a walk or light exercise 😊"


# --------------- DATA LOGGING -----------------

def log_weather(data: dict):
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["timestamp", "city", "temp", "feels", "temp_min", "temp_max",
                 "humidity", "wind", "main", "desc"]
            )
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data["city"],
                data["temp"],
                data["feels"],
                data["temp_min"],
                data["temp_max"],
                data["humidity"],
                data["wind"],
                data["main"],
                data["desc"],
            ]
        )


# --------------- ANIMATIONS (subtle) -----------------

def animate_temp(final_value: float):
    """Smooth count animation for temperature (no flashing)."""
    global previous_temp

    try:
        start = previous_temp if previous_temp is not None else final_value
        start = float(start)
    except Exception:
        start = final_value

    step = 0.4 if final_value > start else -0.4

    def _step(value):
        nonlocal step
        if (step > 0 and value < final_value) or (step < 0 and value > final_value):
            temp_label.config(text=f"{value:.1f}°C")
            root.after(20, _step, value + step)
        else:
            temp_label.config(text=f"{final_value:.1f}°C")

    _step(start)
    previous_temp = final_value


def slide_in_icon():
    """Simple slide-in from left once per update."""
    icon_frame.update_idletasks()
    target_x = (icon_frame.winfo_width() - 80) // 2
    x = -80

    def _move():
        nonlocal x
        if x < target_x:
            x += 6
            icon_label.place(x=x, y=0)
            icon_frame.after(15, _move)
        else:
            icon_label.place(x=target_x, y=0)

    _move()


def start_loading_animation():
    global loading, loading_job
    loading = True
    base = "Fetching latest data"

    def _animate(i=0):
        global loading_job
        if not loading:
            status_label.config(text="")
            return
        dots = "." * (i % 4)
        status_label.config(text=base + dots)
        loading_job = root.after(300, _animate, i + 1)

    _animate()


def stop_loading_animation():
    global loading, loading_job
    loading = False
    if loading_job is not None:
        try:
            root.after_cancel(loading_job)
        except Exception:
            pass
        loading_job = None
    status_label.config(text="")


# --------------- GUI UPDATE -----------------

def load_icon(main_cond: str):
    """Use GIF if available, else PNG."""
    gif_path, png_path = ICON_MAP.get(main_cond, ("", "icons/cloud.png"))

    # Try GIF
    if gif_path and os.path.isfile(gif_path):
        try:
            frames = []
            gif = Image.open(gif_path)
            try:
                while True:
                    frame = gif.copy().resize((80, 80))
                    frames.append(ImageTk.PhotoImage(frame))
                    gif.seek(len(frames))
            except EOFError:
                pass

            if frames:
                def _animate_gif(idx=0):
                    icon_label.config(image=frames[idx])
                    icon_label.image = frames[idx]
                    icon_label.after(120, _animate_gif, (idx + 1) % len(frames))

                _animate_gif()
                return
        except Exception:
            pass

    # Fallback PNG
    if os.path.isfile(png_path):
        img = Image.open(png_path).resize((80, 80))
        img_tk = ImageTk.PhotoImage(img)
        icon_label.config(image=img_tk)
        icon_label.image = img_tk
    else:
        icon_label.config(image="", text=main_cond)


def update_main_weather_ui(weather: dict):
    advice = health_advice(weather["temp"], weather["main"])
    city_label.config(text=weather["city"])
    desc_label.config(text=weather["desc"])

    details_label.config(
        text=(
            f"Feels like: {weather['feels']:.1f}°C\n"
            f"Min: {weather['temp_min']:.1f}°C   |   "
            f"Max: {weather['temp_max']:.1f}°C\n"
            f"Humidity: {weather['humidity']}%   |   Wind: {weather['wind']} m/s"
        )
    )

    # Local time using timezone offset (seconds from UTC)
    offset_sec = weather.get("timezone", 0)
    utc_now = datetime.utcnow()
    local_time = utc_now + timedelta(seconds=offset_sec)
    time_label.config(text=f"Local time: {local_time.strftime('%I:%M %p')}")

    advice_label.config(text=advice)

    load_icon(weather["main"])
    slide_in_icon()
    animate_temp(weather["temp"])

    speak(
        f"Weather in {weather['city']}. "
        f"Temperature {weather['temp']:.0f} degrees Celsius. "
        f"{weather['desc']}. {advice}"
    )


def update_forecast_ui(forecast_list):
    forecast_text.config(state="normal")
    forecast_text.delete("1.0", tk.END)

    if not forecast_list:
        forecast_text.insert(tk.END, "No forecast data available.\n")
    else:
        forecast_text.insert(tk.END, "5-Day Forecast:\n\n")
        for item in forecast_list:
            date_obj = datetime.strptime(item["date"], "%Y-%m-%d").date()
            line = f"{date_obj.strftime('%d %b %Y')}: {item['temp']:.1f}°C, {item['desc']}\n"
            forecast_text.insert(tk.END, line)

    forecast_text.config(state="disabled")


# --------------- EVENT HANDLERS -----------------

def run_weather_fetch(city: str):
    try:
        weather = fetch_current_weather(city)
        forecast = fetch_forecast(city)
        log_weather(weather)

        def on_success():
            stop_loading_animation()
            update_main_weather_ui(weather)
            update_forecast_ui(forecast)
            last_updated_label.config(
                text=f"Last update: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
            )

        root.after(0, on_success)

    except Exception as e:
        def on_error():
            stop_loading_animation()
            messagebox.showerror("Error", f"Could not get weather.\n{e}")

        root.after(0, on_error)


def on_search():
    city = city_entry.get().strip()
    if not city:
        messagebox.showwarning("Input Error", "Please enter a city name.")
        return

    temp_label.config(text="--°C")
    city_label.config(text="City Name")
    desc_label.config(text="Condition")
    details_label.config(text="")
    advice_label.config(text="")
    time_label.config(text="")
    forecast_text.config(state="normal")
    forecast_text.delete("1.0", tk.END)
    forecast_text.insert(tk.END, "Loading forecast...\n")
    forecast_text.config(state="disabled")
    last_updated_label.config(text="Last update: --")

    start_loading_animation()

    t = threading.Thread(target=run_weather_fetch, args=(city,), daemon=True)
    t.start()


def on_button_enter(event):
    search_btn.config(bg=current_theme["button_hover"])


def on_button_leave(event):
    search_btn.config(bg=current_theme["button_bg"])


def toggle_voice():
    global VOICE_ENABLED
    VOICE_ENABLED = not VOICE_ENABLED
    if VOICE_ENABLED:
        voice_btn.config(text="🔊 Voice On")
    else:
        voice_btn.config(text="🔇 Voice Off")


def show_history():
    """Show last few logged weather entries in a new window."""
    if not os.path.isfile(CSV_FILE):
        messagebox.showinfo("History", "No history found yet.")
        return

    entries = []
    try:
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            if len(reader) <= 1:
                messagebox.showinfo("History", "No data rows found in history.")
                return
            header = reader[0]
            rows = reader[1:]
            entries = rows[-20:]  # last 20 entries
    except Exception as e:
        messagebox.showerror("Error", f"Could not read history.\n{e}")
        return

    hist_win = tk.Toplevel(root)
    hist_win.title("Weather History (Last 20)")
    hist_win.geometry("500x350")
    hist_win.configure(bg=current_theme["bg"])

    title = tk.Label(
        hist_win,
        text="Recent Weather History",
        font=("Segoe UI", 11, "bold"),
        bg=current_theme["bg"],
        fg=current_theme["text"],
    )
    title.pack(pady=5)

    text = tk.Text(
        hist_win,
        font=("Consolas", 9),
        bg=current_theme["forecast_bg"],
        fg=current_theme["forecast_fg"],
        bd=0,
    )
    text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # header
    text.insert(tk.END, ", ".join(header) + "\n")
    text.insert(tk.END, "-" * 80 + "\n")
    for row in entries:
        text.insert(tk.END, ", ".join(row) + "\n")

    text.config(state="disabled")


def toggle_theme():
    """Switch between dark and light themes."""
    global theme_mode, current_theme
    if theme_mode == "dark":
        theme_mode = "light"
        current_theme = LIGHT_THEME
        theme_btn.config(text="☾ Dark Mode")
    else:
        theme_mode = "dark"
        current_theme = DARK_THEME
        theme_btn.config(text="☀ Light Mode")
    apply_theme()


def apply_theme():
    """Apply current theme to all widgets."""
    root.configure(bg=current_theme["bg"])

    top_frame.config(bg=current_theme["bg"])
    title_label.config(bg=current_theme["bg"], fg=current_theme["text"])

    city_frame.config(bg=current_theme["frame_bg"])
    city_entry.config(
        bg=current_theme["entry_bg"],
        fg=current_theme["entry_fg"],
        insertbackground=current_theme["entry_cursor"],
    )

    search_btn.config(
        bg=current_theme["button_bg"],
        fg=current_theme["button_fg"],
        activebackground=current_theme["button_bg"],
        activeforeground=current_theme["button_fg"],
    )

    voice_btn.config(
        bg=current_theme["button_bg"],
        fg=current_theme["button_fg"],
        activebackground=current_theme["button_bg"],
        activeforeground=current_theme["button_fg"],
    )

    history_btn.config(
        bg=current_theme["button_bg"],
        fg=current_theme["button_fg"],
        activebackground=current_theme["button_bg"],
        activeforeground=current_theme["button_fg"],
    )

    icon_frame.config(bg=current_theme["bg"])
    icon_label.config(bg=current_theme["bg"])

    temp_label.config(bg=current_theme["bg"], fg=current_theme["text"])
    city_label.config(bg=current_theme["bg"], fg=current_theme["accent"])
    desc_label.config(bg=current_theme["bg"], fg=current_theme["text"])
    time_label.config(bg=current_theme["bg"], fg=current_theme["muted"])

    details_label.config(bg=current_theme["bg"], fg=current_theme["muted"])
    advice_label.config(bg=current_theme["bg"], fg=current_theme["advice"])

    forecast_frame.config(bg=current_theme["bg"])
    forecast_title.config(bg=current_theme["bg"], fg=current_theme["text"])

    forecast_text.config(
        bg=current_theme["forecast_bg"],
        fg=current_theme["forecast_fg"],
    )

    status_label.config(bg=current_theme["bg"], fg=current_theme["status"])
    last_updated_label.config(bg=current_theme["bg"], fg=current_theme["status"])
    footer_label.config(bg=current_theme["bg"], fg=current_theme["footer"])


# --------------- GUI SETUP -----------------

root = tk.Tk()
root.title("Smart Weather & Health Assistant")
root.geometry("450x680")
root.resizable(False, False)
root.configure(bg=BG_COLOR)

# Top bar: title + theme toggle
top_frame = tk.Frame(root, bg=BG_COLOR)
top_frame.pack(fill=tk.X, pady=5)

title_label = tk.Label(
    top_frame,
    text="Smart Weather & Health Assistant",
    font=("Segoe UI", 14, "bold"),
    bg=BG_COLOR,
    fg=current_theme["text"],
)
title_label.pack(side=tk.LEFT, padx=10)

theme_btn = tk.Button(
    top_frame,
    text="☀ Light Mode",
    font=("Segoe UI", 9),
    bg=current_theme["button_bg"],
    fg=current_theme["button_fg"],
    activebackground=current_theme["button_bg"],
    activeforeground=current_theme["button_fg"],
    relief="flat",
    command=toggle_theme,
)
theme_btn.pack(side=tk.RIGHT, padx=10)

city_frame = tk.Frame(root, bg=current_theme["frame_bg"])
city_frame.pack(pady=5)

city_entry = tk.Entry(
    city_frame,
    font=("Segoe UI", 12),
    width=18,
    bg=current_theme["entry_bg"],       # textbox background
    fg=current_theme["entry_fg"],       # textbox text color
    insertbackground=current_theme["entry_cursor"],  # cursor color
    relief="flat",
)
city_entry.pack(side=tk.LEFT, padx=5)

search_btn = tk.Button(
    city_frame,
    text="Check",
    font=("Segoe UI", 11, "bold"),
    bg=current_theme["button_bg"],
    fg=current_theme["button_fg"],
    activebackground=current_theme["button_bg"],
    activeforeground=current_theme["button_fg"],
    relief="flat",
    padx=8,
    command=on_search,
)
search_btn.pack(side=tk.LEFT, padx=3)
search_btn.bind("<Enter>", on_button_enter)
search_btn.bind("<Leave>", on_button_leave)

voice_btn = tk.Button(
    city_frame,
    text="🔊 Voice On",
    font=("Segoe UI", 9),
    bg=current_theme["button_bg"],
    fg=current_theme["button_fg"],
    activebackground=current_theme["button_bg"],
    activeforeground=current_theme["button_fg"],
    relief="flat",
    command=toggle_voice,
)
voice_btn.pack(side=tk.LEFT, padx=3)

icon_frame = tk.Frame(root, bg=current_theme["bg"], height=90)
icon_frame.pack(pady=10, fill=tk.X)
icon_frame.pack_propagate(False)

icon_label = tk.Label(icon_frame, bg=current_theme["bg"])
icon_label.place(x=0, y=0)

temp_label = tk.Label(
    root,
    text="--°C",
    font=("Segoe UI", 38, "bold"),
    bg=current_theme["bg"],
    fg=current_theme["text"],
)
temp_label.pack()

city_label = tk.Label(
    root,
    text="City Name",
    font=("Segoe UI", 15),
    bg=current_theme["bg"],
    fg=current_theme["accent"],
)
city_label.pack()

time_label = tk.Label(
    root,
    text="",
    font=("Segoe UI", 9),
    bg=current_theme["bg"],
    fg=current_theme["muted"],
)
time_label.pack()

desc_label = tk.Label(
    root,
    text="Condition",
    font=("Segoe UI", 11),
    bg=current_theme["bg"],
    fg=current_theme["text"],
)
desc_label.pack(pady=4)

details_label = tk.Label(
    root,
    text="",
    font=("Segoe UI", 10),
    bg=current_theme["bg"],
    fg=current_theme["muted"],
    justify=tk.CENTER,
)
details_label.pack(pady=4)

advice_label = tk.Label(
    root,
    text="Advice will appear here.",
    font=("Segoe UI", 11, "italic"),
    bg=current_theme["bg"],
    fg=current_theme["advice"],
    wraplength=400,
    justify=tk.LEFT,
)
advice_label.pack(pady=10)

forecast_frame = tk.Frame(root, bg=current_theme["bg"])
forecast_frame.pack(pady=10, fill=tk.BOTH, expand=True)

forecast_title = tk.Label(
    forecast_frame,
    text="5-Day Forecast",
    font=("Segoe UI", 12, "bold"),
    bg=current_theme["bg"],
    fg=current_theme["text"],
)
forecast_title.pack(anchor="w", padx=10)

forecast_text = tk.Text(
    forecast_frame,
    height=8,
    width=50,
    font=("Consolas", 10),
    bg=current_theme["forecast_bg"],
    fg=current_theme["forecast_fg"],
    bd=0,
)
forecast_text.pack(padx=10, pady=5)
forecast_text.config(state="disabled")

history_btn = tk.Button(
    root,
    text="📜 View History",
    font=("Segoe UI", 9),
    bg=current_theme["button_bg"],
    fg=current_theme["button_fg"],
    activebackground=current_theme["button_bg"],
    activeforeground=current_theme["button_fg"],
    relief="flat",
    command=show_history,
)
history_btn.pack(pady=3)

status_label = tk.Label(
    root,
    text="",
    font=("Segoe UI", 9),
    bg=current_theme["bg"],
    fg=current_theme["status"],
)
status_label.pack(pady=1)

last_updated_label = tk.Label(
    root,
    text="Last update: --",
    font=("Segoe UI", 8),
    bg=current_theme["bg"],
    fg=current_theme["status"],
)
last_updated_label.pack(pady=1)

footer_label = tk.Label(
    root,
    text="Data from OpenWeather • Built in Python",
    font=("Segoe UI", 8),
    bg=current_theme["bg"],
    fg=current_theme["footer"],
)
footer_label.pack(pady=5)

# Apply initial theme (already dark, but keeps consistency)
apply_theme()

# Press Enter to search
root.bind("<Return>", lambda event: on_search())

root.mainloop()

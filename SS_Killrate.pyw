import tkinter as tk
from tkinter import Menu, Toplevel, Scale
import json, os, asyncio, websockets, threading, re

CONFIG_PATH = "killrate_config.json"
WIDTH, HEIGHT = 350, 60

# 設定読み書き
def load_config():
    default = {"x": 100, "y": 100, "alpha": 0.92, "bg": "#222233"}
    if os.path.exists(CONFIG_PATH):
        try:
            conf = json.load(open(CONFIG_PATH, encoding="utf-8"))
            for k in default:
                conf.setdefault(k, default[k])
            return conf
        except:
            pass
    return default

def save_config(x, y, alpha, bg):
    try:
        json.dump({"x": x, "y": y, "alpha": alpha, "bg": bg},
                  open(CONFIG_PATH, "w", encoding="utf-8"))
    except:
        pass

conf = load_config()
root = tk.Tk()
root.geometry(f"{WIDTH}x{HEIGHT}+{conf['x']}+{conf['y']}")
root.title("Killrate HUD")
root.configure(bg=conf["bg"])
root.attributes("-topmost", True)
root.attributes("-alpha", conf["alpha"])
root.overrideredirect(True)

label = tk.Label(root, text="待機中…", font=("Meiryo", 18, "bold"),
                 fg="white", bg=conf["bg"])
label.pack(fill="both", expand=True)

# メニューとドラッグ
menu = Menu(root, tearoff=0)
menu.add_command(label="終了", command=root.quit)
label.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))
label.bind("<ButtonPress-1>", lambda e: setattr(root, "_drag", (e.x, e.y)))
label.bind("<B1-Motion>", lambda e: (
    root.geometry(f"+{root.winfo_x()+e.x-root._drag[0]}+{root.winfo_y()+e.y-root._drag[1]}"),
    save_config(root.winfo_x()+e.x-root._drag[0], root.winfo_y()+e.y-root._drag[1],
                root.attributes("-alpha"), conf["bg"])
))

# 透過率設定UI（中クリック）
def show_alpha_settings(e=None):
    win = Toplevel(root)
    win.title("透過率設定")
    win.geometry(f"+{root.winfo_x()+WIDTH+10}+{root.winfo_y()}")
    win.attributes("-topmost", True)
    tk.Label(win, text="透明度 (0.3〜1.0)", font=("Meiryo", 10)).pack()
    s = Scale(win, from_=0.3, to=1.0, resolution=0.01, orient="horizontal", length=200)
    s.set(root.attributes("-alpha"))
    s.pack()
    s.configure(command=lambda val: (
        root.attributes("-alpha", float(val)),
        save_config(root.winfo_x(), root.winfo_y(), float(val), conf["bg"])
    ))
label.bind("<Button-2>", show_alpha_settings)

# 時間パース：h/m/s対応
def parse_time_to_minutes(t):
    h = m = s = 0
    if match := re.search(r"(\d+)h", t): h = int(match.group(1))
    if match := re.search(r"(\d+)m", t): m = int(match.group(1))
    if match := re.search(r"(\d+)s", t): s = int(match.group(1))
    return h * 60 + m + s / 60

# キルレート計算
def calculate_efficiency(payload):
    try:
        data = json.loads(payload)
        kills = int(data.get("kill", "0").replace(",", ""))
        minutes = parse_time_to_minutes(data.get("time", "0m 0s"))
        if minutes == 0:
            return "未計測"
        return f"{kills / minutes:.2f} 体/分"
    except Exception as e:
        print("計算エラー:", e)
        return "未計測"

# WebSocket受信
async def handle_connection(websocket):
    async for message in websocket:
        result = calculate_efficiency(message)
        label.config(text=f"キルレート: {result}")
        print("受信:", message, "→", result)

async def websocket_server():
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()

def start_ws_thread():
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(websocket_server())
        loop.run_forever()
    threading.Thread(target=run, daemon=True).start()

start_ws_thread()
root.mainloop()

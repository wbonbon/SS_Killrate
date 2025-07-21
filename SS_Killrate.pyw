import tkinter as tk, json, os, asyncio, websockets, threading, re, time
from pywinauto import Desktop
import pystray
from PIL import Image, ImageDraw
from tkinter import Menu, Toplevel, Scale

conf = json.load(open("killrate_config.json", encoding="utf-8")) if os.path.exists("killrate_config.json") else {
  "x":100, "y":100, "alpha":0.92, "bg":"#222233", "parent":"", "dx":10, "dy":10, "follow":False}
def save(): json.dump(conf, open("killrate_config.json", "w", encoding="utf-8"))

W,H=350,80; root=tk.Tk()
root.geometry(f"{W}x{H}+{conf['x']}+{conf['y']}"); root.configure(bg=conf["bg"])
root.attributes("-topmost",1); root.attributes("-alpha",conf["alpha"]); root.overrideredirect(True)

border = tk.Frame(root,bg="#888888")
label = tk.Label(root,text="待機中…",font=("Meiryo",18,"bold"),fg="white",bg=conf["bg"])
border.place(x=0,y=0,width=W,height=H) if not conf["follow"] else None
label.place(relx=0.5,rely=0.5,anchor="center")

def update_border(): border.place(x=0,y=0,width=W,height=H) if not conf["follow"] else border.place_forget()

def find_window(partial_title):
    for w in Desktop(backend="uia").windows():
        if partial_title in w.window_text():
            print(f"✅ 部分一致ヒット: '{w.window_text()}'")
            return w
    return None

def auto_detect_parent():
    rx, ry = root.winfo_x(), root.winfo_y()
    for w in Desktop(backend="uia").windows():
        title = w.window_text()
        if title == "tk": continue  # HUD自身を除外
        try:
            rect = w.rectangle()
            if rect.left <= rx <= rect.right and rect.top <= ry <= rect.bottom:
                print(f"🎯 検出: '{title}' at {rect}")
                return title if title else None
        except: pass
    return None

def set_follow_auto():
    title = auto_detect_parent()
    if title:
        conf["parent"] = title
        set_follow(True)
        print(f"✅ 自動設定 parent: '{title}'")
    else:
        print("❌ HUDの下にウインドウが見つかりません")

def set_follow(enabled):
    conf["follow"] = enabled
    print(f"🔁 set_follow({enabled}) → parent: '{conf['parent']}'")
    if enabled:
        win = find_window(conf["parent"])
        if win:
            r = root.winfo_x(), root.winfo_y()
            p = win.rectangle()
            conf["dx"], conf["dy"] = p.width() - r[0] + p.left - W, p.height() - r[1] + p.top - H
            print(f"📍 dx/dy更新: {conf['dx']}, {conf['dy']}")
        else:
            print("⚠️ parentウインドウが見つかりません")
            conf["follow"] = False
    save(); update_border(); update_menu()

def move_zero(): root.geometry("+0+0"); conf["follow"]=False; save(); update_border(); update_menu()

menu=Menu(root,tearoff=0)
def update_menu():
    menu.delete(0,"end")
    menu.add_command(label="自動追従ON", command=set_follow_auto)
    menu.add_command(label="追従OFF（枠あり）" if conf["follow"] else "追従ON（枠なし）",
                     command=lambda: set_follow(not conf["follow"]))
    menu.add_separator(); menu.add_command(label="終了", command=root.quit)
label.bind("<Button-3>", lambda e: (update_menu(), menu.post(e.x_root, e.y_root)))

def show_alpha(e=None):
    win=Toplevel(root); win.title("透明度"); win.geometry(f"+{root.winfo_x()+W+10}+{root.winfo_y()}"); win.attributes("-topmost",True)
    tk.Label(win,text="透明度").pack()
    s=Scale(win,from_=0.3,to=1.0,resolution=0.01,orient="horizontal",length=200)
    s.set(root.attributes("-alpha")); s.pack()
    s.configure(command=lambda val: root.attributes("-alpha", float(val)) or (conf.update({"alpha":float(val)}), save()))
label.bind("<Button-2>", show_alpha)

label.bind("<ButtonPress-1>", lambda e: setattr(root,"_drag",(e.x,e.y)))
label.bind("<B1-Motion>", lambda e: not conf["follow"] and (
  root.geometry(f"+{root.winfo_x()+e.x-root._drag[0]}+{root.winfo_y()+e.y-root._drag[1]}"),
  conf.update({"x":root.winfo_x()+e.x-root._drag[0],"y":root.winfo_y()+e.y-root._drag[1]}), save())
)

def calc_eff(p):
  try:
    d=json.loads(p); k=int(d.get("kill","0").replace(",","")); t=d.get("time","")
    m=sum(int(v[:-1])*{"h":60,"m":1,"s":1/60}[v[-1]] for v in re.findall(r"\d+[hms]",t))
    return f"{k/m:.2f} 体/分" if m else "未計測"
  except: return "未計測"

async def handle(ws):
    async for msg in ws:
        label.config(text=f"キルレート: {calc_eff(msg)}")

async def websocket_server():
    async with websockets.serve(handle, "localhost", 8765):
        await asyncio.Future()

def ws_thread(): threading.Thread(target=lambda: asyncio.run(websocket_server()), daemon=True).start()

def follow_loop():
    def loop():
        while True:
            if conf["follow"]:
                win = find_window(conf["parent"])
                if win:
                    p = win.rectangle()
                    root.geometry(f"+{p.left+p.width()-W-conf['dx']}+{p.top+p.height()-H-conf['dy']}")
                else:
                    print(f"❌ 追従失敗 → '{conf['parent']}' が見つからない")
            time.sleep(0.5)
    threading.Thread(target=loop, daemon=True).start()

def tray_thread():
  img=Image.new('RGB',(16,16),(30,30,30)); ImageDraw.Draw(img).rectangle([2,2,13,13], fill=(255,255,255))
  icon=pystray.Icon("KillrateHUD", icon=img, title="SS_KillrateHUD",
    menu=pystray.Menu(
      pystray.MenuItem("自動追従ON", lambda: set_follow_auto()),
      pystray.MenuItem("追従OFF（枠あり）" if conf["follow"] else "追従ON（枠なし）", lambda: set_follow(not conf["follow"])),
      pystray.MenuItem("位置を(0,0)に戻す", move_zero),
      pystray.MenuItem("終了", lambda: (icon.stop(), root.quit()))
  )); icon.run()

ws_thread(); follow_loop(); threading.Thread(target=tray_thread, daemon=True).start()
root.mainloop()

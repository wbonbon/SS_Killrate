import websocket
import obspython as obs
import json

# ==== ASS変数を取得する関数 ====
def advss_get_variable_value(name):
    proc_handler = obs.obs_get_proc_handler()
    data = obs.calldata_create()
    obs.calldata_set_string(data, "name", name)
    obs.proc_handler_call(proc_handler, "advss_get_variable_value", data)

    if not obs.calldata_bool(data, "success"):
        obs.script_log(obs.LOG_WARNING, f"変数取得失敗: {name}")
        obs.calldata_destroy(data)
        return None

    value = obs.calldata_string(data, "value")
    obs.calldata_destroy(data)
    return value

# ==== HUDに値を送信する関数 ====
def safe_send(payload):
    try:
        ws = websocket.create_connection("ws://localhost:8765", timeout=1)
        ws.send(payload)
        ws.close()
        return True
    except Exception as e:
        #obs.script_log(obs.LOG_WARNING, f"WebSocket送信失敗: {e}")
        return False

# ==== メイン処理 ====
def run():
    kill = advss_get_variable_value("kill")     # 例: "12,345"
    time = advss_get_variable_value("time")     # 例: "36m 24s"

    if kill is None or time is None:
        obs.script_log(obs.LOG_WARNING, "kill または time の取得に失敗")
        return True

    data = {
        "kill": kill,
        "time": time
    }

    payload = json.dumps(data)
    safe_send(payload)
    obs.script_log(obs.LOG_INFO, f"送信データ: {payload}")
    return True

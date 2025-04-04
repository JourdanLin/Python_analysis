import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import socket
import threading
import time
import queue
import traceback # 用於更詳細的錯誤日誌
from efem_error_codes import get_error_description
# --- 後端通訊邏輯 (與之前相同) ---

# EFEM 預設連接資訊
DEFAULT_EFEM_IP = "192.168.1.1"
DEFAULT_EFEM_PORT = 6000

# 全域變數
efem_socket = None
is_connected = False
receive_thread = None
message_queue = queue.Queue() # 用於執行緒間通訊

def connect_efem(ip, port, status_callback, log_callback):
    """建立與 EFEM 的 TCP/IP 連接，並透過回呼更新 GUI"""
    global efem_socket, is_connected, receive_thread
    try:
        if is_connected:
            log_callback("已連接，請先斷線。\n")
            return False

        log_callback(f"嘗試連接到 {ip}:{port}...\n")
        efem_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        efem_socket.settimeout(5) # 設定連接超時
        efem_socket.connect((ip, port))
        is_connected = True
        status_callback("已連接", "green")
        log_callback(f"成功連接到 EFEM: {ip}:{port}\n")

        # 清空佇列
        while not message_queue.empty():
            try:
                message_queue.get_nowait()
            except queue.Empty:
                break

        # 啟動接收執行緒
        receive_thread = threading.Thread(target=receive_data, args=(log_callback,), daemon=True)
        receive_thread.start()
        return True
    except socket.timeout:
        log_callback(f"連接超時: 無法連接到 {ip}:{port}\n")
        status_callback("已斷線", "red")
        efem_socket = None
        is_connected = False
        return False
    except socket.error as e:
        log_callback(f"連接 EFEM 失敗: {e}\n")
        status_callback("已斷線", "red")
        efem_socket = None
        is_connected = False
        return False
    except Exception as e:
        log_callback(f"連接過程中發生未預期錯誤: {e}\n")
        log_callback(traceback.format_exc() + "\n") # 打印更詳細的錯誤
        status_callback("已斷線", "red")
        efem_socket = None
        is_connected = False
        return False


def disconnect_efem(status_callback, log_callback):
    """斷開與 EFEM 的連接"""
    global efem_socket, is_connected, receive_thread
    if not is_connected:
        log_callback("目前未連接。\n")
        return

    was_connected = is_connected # 記錄斷線前的狀態
    is_connected = False # 先設置狀態，讓接收執行緒停止

    if receive_thread and receive_thread.is_alive():
         # 短暫等待執行緒自然結束
         time.sleep(0.2)

    if efem_socket:
        try:
            # 嘗試更安全地關閉 socket
            efem_socket.shutdown(socket.SHUT_RDWR)
        except (socket.error, OSError) as e:
             # 忽略 shutdown 可能引發的錯誤 (例如 socket 已被對方關閉)
             # log_callback(f"關閉 socket shutdown 時出錯: {e}\n")
             pass
        finally:
             try:
                 efem_socket.close()
                 if was_connected: # 只有在之前確實是連接狀態時才打印斷線訊息
                     log_callback("已斷開與 EFEM 的連接\n")
             except socket.error as e:
                 log_callback(f"關閉 socket close 時出錯: {e}\n")
             except Exception as e:
                 log_callback(f"關閉 socket 時發生未預期錯誤: {e}\n")
             finally:
                 efem_socket = None


    status_callback("已斷線", "red")
    receive_thread = None # 清除執行緒引用


def send_command(command, log_callback, use_at_prefix=False):
    """發送指令到 EFEM"""
    if not is_connected or not efem_socket:
        log_callback("錯誤：未連接到 EFEM\n")
        return False

    # 根據手冊格式化指令
    prefix = "#@" if use_at_prefix else "#"
    formatted_command = f"{prefix}{command}$"

    try:
        log_callback(f"發送: {formatted_command}\n") # **記錄實際發送的內容**
        efem_socket.sendall(formatted_command.encode('utf-8'))
        return True
    except socket.error as e:
        log_callback(f"發送指令失敗: {e}\n")
        # 發送失敗通常意味著連接已斷開
        message_queue.put(("disconnect", None)) # 通知主線程斷線
        return False
    except Exception as e:
        log_callback(f"發送指令時發生未預期錯誤: {e}\n")
        log_callback(traceback.format_exc() + "\n")
        message_queue.put(("disconnect", None))
        return False

def receive_data(log_callback):
    """在獨立執行緒中持續接收 EFEM 的數據，並將訊息放入佇列"""
    global efem_socket, is_connected
    buffer = ""
    while is_connected: # 使用 is_connected 作為迴圈條件
        try:
            if not efem_socket: # 再次檢查 socket 是否存在
                 break
            # 設定短超時以允許檢查 is_connected 狀態
            efem_socket.settimeout(0.2)
            data_chunk = efem_socket.recv(1024)

            if not data_chunk:
                if is_connected: # 只有在預期連接時才顯示關閉訊息
                    log_callback("EFEM 連接已由對方關閉。\n")
                    message_queue.put(("disconnect", None)) # 通知主線程斷線
                break # 退出迴圈

            buffer += data_chunk.decode('utf-8')

            # 處理接收到的完整訊息 (以 $ 結尾)
            while '$' in buffer:
                message, buffer = buffer.split('$', 1)
                message += '$' # 將結束符加回來
                message_queue.put(("message", message)) # 將訊息放入佇列

        except socket.timeout:
            # 只是超時，繼續檢查 is_connected 狀態
            continue
        except socket.error as e:
            # 捕捉連接被重設的錯誤
            if is_connected and isinstance(e, ConnectionResetError):
                 log_callback(f"接收數據時連接被重設: {e}\n")
                 message_queue.put(("disconnect", None))
            elif is_connected: # 只有在預期連接時才報告其他 socket 錯誤
                 log_callback(f"接收數據時出錯: {e}\n")
                 message_queue.put(("disconnect", None))
            break # 發生錯誤，退出迴圈
        except Exception as e:
            if is_connected:
                log_callback(f"處理接收數據時發生未預期錯誤: {e}\n")
                log_callback(traceback.format_exc() + "\n")
                message_queue.put(("disconnect", None))
            break

    # 確保即使發生異常，也會嘗試通知主線程斷開
    # if is_connected: # 這裡不再需要，因為斷線會在異常處理中放入佇列
    #     message_queue.put(("disconnect", None))
    # log_callback("接收執行緒已停止。\n") # 移到 disconnect_efem 中打印


def process_received_message(message, log_callback):
    """處理從佇列中取出的單條完整訊息，並更新日誌"""
    log_callback(f"收到: {message}") # 直接在日誌中顯示原始訊息

    try:
        content = message.strip('#@$')
        parts = content.split(',')
        if len(parts) > 0:
            cmd_event = parts[0]
            details = parts[1:]

            if cmd_event == "Event":
                source = details[0] if len(details) > 0 else "未知"
                event_type = details[1] if len(details) > 1 else "未知"
                data = ",".join(details[2:]) if len(details) > 2 else ""
                log_callback(f"  -> 事件: 來源={source}, 類型={event_type}, 數據={data}\n")
            elif "Error" in details:
                # 嘗試提取最後一個元素作為錯誤代碼
                error_code = ""
                if details:
                    error_code = details[-1]
                # 使用導入的函數獲取描述
                error_desc = get_error_description(error_code)
                log_callback(f"  -> 錯誤: 指令={cmd_event}, 代碼={error_code} ({error_desc})\n") # **加入錯誤描述**
            elif "OK" in details:
                result_data = ",".join(d for d in details if d != "OK")
                if result_data:
                    log_callback(f"  -> 成功: 指令={cmd_event}, 結果={result_data}\n")
                else:
                    log_callback(f"  -> 成功: 指令={cmd_event}\n")
            # else: # 其他未識別格式，只打印原始訊息即可
            #     pass
    except Exception as e:
        log_callback(f"  -> 解析訊息時發生錯誤: {e}\n")
        log_callback(traceback.format_exc() + "\n")


# --- GUI ---
class EfemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EFEM 測試程式 v1.1 (使用 Combobox)")
        self.root.geometry("850x650") # 稍微加大視窗

        # --- 連接框架 ---
        connection_frame = ttk.LabelFrame(root, text="連線設定")
        connection_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(connection_frame, text="IP 位址:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ip_entry = ttk.Entry(connection_frame, width=15)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)
        self.ip_entry.insert(0, DEFAULT_EFEM_IP)

        ttk.Label(connection_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.port_entry = ttk.Entry(connection_frame, width=7)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        self.port_entry.insert(0, str(DEFAULT_EFEM_PORT))

        self.connect_button = ttk.Button(connection_frame, text="連線", command=self.connect)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)

        self.disconnect_button = ttk.Button(connection_frame, text="斷線", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=5, padx=5, pady=5)

        self.connection_status_label = ttk.Label(connection_frame, text="已斷線", foreground="red", font=("Arial", 10, "bold"))
        self.connection_status_label.grid(row=0, column=6, padx=10, pady=5)

        # --- 主控制區 (使用 Notebook) ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(padx=10, pady=5, expand=True, fill="both")

        # 建立各裝置的頁籤
        self.efem_tab = ttk.Frame(self.notebook)
        self.loadport_tab = ttk.Frame(self.notebook)
        self.aligner_tab = ttk.Frame(self.notebook)
        self.robot_tab = ttk.Frame(self.notebook)
        self.sequence_tab = ttk.Frame(self.notebook) # 指令序列頁籤

        self.notebook.add(self.efem_tab, text=' EFEM ')
        self.notebook.add(self.loadport_tab, text=' Load Port ')
        self.notebook.add(self.aligner_tab, text=' Aligner ')
        self.notebook.add(self.robot_tab, text=' Robot ')
        self.notebook.add(self.sequence_tab, text=' 指令序列 ')

        # --- 填充各頁籤內容 ---
        self._create_efem_tab()
        self._create_loadport_tab()
        self._create_aligner_tab()
        self._create_robot_tab()
        self._create_sequence_tab()


        # --- 日誌框架 ---
        log_frame = ttk.LabelFrame(root, text="日誌輸出")
        log_frame.pack(padx=10, pady=5, expand=True, fill="both")

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, width=90) # 加寬
        self.log_text.pack(padx=5, pady=5, expand=True, fill="both")
        self.log_text.configure(state='disabled') # 初始設為不可編輯

        # 啟動佇列檢查
        self.check_queue()

    def _create_efem_tab(self):
        """建立 EFEM 頁籤的內容 (保持按鈕為主)"""
        frame = self.efem_tab
        # 將按鈕稍微分組
        control_frame = ttk.LabelFrame(frame, text="基本控制")
        control_frame.pack(pady=10, padx=10, fill="x")
        ttk.Button(control_frame, text="Home EFEM", command=lambda: self.trigger_action("EFEM", "Home EFEM", "Home,EFEM")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="GetStatus EFEM", command=lambda: self.trigger_action("EFEM", "GetStatus EFEM", "GetStatus,EFEM")).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(control_frame, text="GetVersion EFEM", command=lambda: self.trigger_action("EFEM", "GetVersion EFEM", "GetVersion,EFEM")).grid(row=0, column=2, padx=5, pady=5)

        mode_frame = ttk.LabelFrame(frame, text="模式切換")
        mode_frame.pack(pady=10, padx=10, fill="x")
        ttk.Button(mode_frame, text="切換到 Remote 模式", command=lambda: self.trigger_action("EFEM", "切換到 Remote 模式", "Remote,EFEM")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(mode_frame, text="切換到 Local 模式", command=lambda: self.trigger_action("EFEM", "切換到 Local 模式", "Local,EFEM")).grid(row=0, column=1, padx=5, pady=5)

        tower_frame = ttk.LabelFrame(frame, text="塔燈/蜂鳴器")
        tower_frame.pack(pady=10, padx=10, fill="x")
        ttk.Button(tower_frame, text="塔燈 (紅燈閃爍)", command=lambda: self.trigger_action("EFEM", "塔燈 (紅燈閃爍)", "SignalTower,EFEM,Red,Flash")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(tower_frame, text="塔燈 (綠燈常亮)", command=lambda: self.trigger_action("EFEM", "塔燈 (綠燈常亮)", "SignalTower,EFEM,Green,On")).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(tower_frame, text="塔燈 (全滅)", command=lambda: self.trigger_action("EFEM", "塔燈 (全滅)", "SignalTower,EFEM,All,Off")).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(tower_frame, text="蜂鳴器 (On)", command=lambda: self.trigger_action("EFEM", "蜂鳴器 (On)", "SetBuzzer,EFEM,1,On")).grid(row=1, column=0, padx=5, pady=5) # 假設蜂鳴器編號為 1
        ttk.Button(tower_frame, text="蜂鳴器 (Off)", command=lambda: self.trigger_action("EFEM", "蜂鳴器 (Off)", "SetBuzzer,EFEM,1,Off")).grid(row=1, column=1, padx=5, pady=5)


    def _create_loadport_tab(self):
        """建立 Load Port 頁籤的內容 (使用 Combobox)"""
        frame = self.loadport_tab

        # --- 參數區 ---
        param_frame = ttk.LabelFrame(frame, text="參數")
        param_frame.pack(pady=5, padx=10, fill="x")
        ttk.Label(param_frame, text="Loadport 編號 [n]:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.lp_num_entry = ttk.Entry(param_frame, width=5)
        self.lp_num_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.lp_num_entry.insert(0, "1")

        ttk.Label(param_frame, text="Slot (用於 GotoSlot):").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.lp_slot_entry = ttk.Entry(param_frame, width=5)
        self.lp_slot_entry.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        self.lp_slot_entry.insert(0, "1")

        # --- Combobox 動作區 ---
        action_frame = ttk.LabelFrame(frame, text="選擇動作")
        action_frame.pack(pady=5, padx=10, fill="x")

        self.lp_action_var = tk.StringVar()
        lp_actions = [
            "Load", "Unload", "Map", "Clamp", "Unclamp", "Dock", "Undock",
            "DoorOpen", "DoorClose", "DoorUp", "DoorDown", "HoldPlate", "Unholdplate",
            "GotoSlot" # 需要 Slot 參數
        ]
        ttk.Label(action_frame, text="選擇 Load Port 動作:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.lp_action_combo = ttk.Combobox(action_frame, textvariable=self.lp_action_var, values=lp_actions, width=18, state="readonly")
        self.lp_action_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        if lp_actions: self.lp_action_combo.current(0) # 設置預設選項

        ttk.Button(action_frame, text="執行選擇的動作", command=self.execute_loadport_action).grid(row=0, column=2, padx=10, pady=5)

        # --- 獨立按鈕區 ---
        button_frame = ttk.LabelFrame(frame, text="常用查詢/控制")
        button_frame.pack(pady=5, padx=10, fill="x")
        ttk.Button(button_frame, text="Home [n]", command=lambda: self.trigger_loadport_action("Home")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="GetStatus [n]", command=lambda: self.trigger_loadport_action("GetStatus")).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="ResetError [n]", command=lambda: self.trigger_loadport_action("ResetError")).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="GetMapResult [n]", command=lambda: self.trigger_loadport_action("GetMapResult")).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="ReadFoupID [n]", command=lambda: self.trigger_loadport_action("ReadFoupID")).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="GetCurrentLPWaferSize [n]", command=lambda: self.trigger_loadport_action("GetCurrentLPWaferSize")).grid(row=1, column=2, padx=5, pady=5)
        # 可以添加 GetLPWaferSize, GetInfoPad, GetLamp 等按鈕


    def _create_aligner_tab(self):
        """建立 Aligner 頁籤的內容 (使用 Combobox)"""
        frame = self.aligner_tab

        # --- 參數區 ---
        param_frame = ttk.LabelFrame(frame, text="參數")
        param_frame.pack(pady=5, padx=10, fill="x")
        ttk.Label(param_frame, text="Aligner 編號 [n]:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.al_num_entry = ttk.Entry(param_frame, width=5)
        self.al_num_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.al_num_entry.insert(0, "1")

        ttk.Label(param_frame, text="角度 (0.1度):").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.al_degree_entry = ttk.Entry(param_frame, width=7)
        self.al_degree_entry.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        self.al_degree_entry.insert(0, "900") # 預設 90.0 度

        # --- Combobox 動作區 ---
        action_frame = ttk.LabelFrame(frame, text="選擇動作")
        action_frame.pack(pady=5, padx=10, fill="x")

        self.al_action_var = tk.StringVar()
        al_actions = [
            "Alignment",
            "Vacuum On", # 將 On/Off 分開
            "Vacuum Off",
            "Clamp",
            "Unclamp",
            "MoveToLoadPosition",
            "SetAlignmentAngle", # 需要角度參數
            "MoveRelativeAngle" # 需要角度參數
        ]
        ttk.Label(action_frame, text="選擇 Aligner 動作:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.al_action_combo = ttk.Combobox(action_frame, textvariable=self.al_action_var, values=al_actions, width=20, state="readonly")
        self.al_action_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        if al_actions: self.al_action_combo.current(0) # 設置預設選項

        ttk.Button(action_frame, text="執行選擇的動作", command=self.execute_aligner_action).grid(row=0, column=2, padx=10, pady=5)

        # --- 獨立按鈕區 ---
        button_frame = ttk.LabelFrame(frame, text="常用查詢/控制/設定")
        button_frame.pack(pady=5, padx=10, fill="x")
        ttk.Button(button_frame, text="Home [n]", command=lambda: self.trigger_aligner_action("Home")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="GetStatus [n]", command=lambda: self.trigger_aligner_action("GetStatus")).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="ResetError [n]", command=lambda: self.trigger_aligner_action("ResetError")).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="CheckWaferPresence [n]", command=lambda: self.trigger_aligner_action("CheckWaferPresence")).grid(row=1, column=0, padx=5, pady=5)
        # 保留需要彈出對話框的設定按鈕
        ttk.Button(button_frame, text="SetWaferType [n]...", command=lambda: self.trigger_aligner_prompt_action("SetWaferType", "輸入類型 (Notch/Flat/Neither):")).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="SetWaferMode [n]...", command=lambda: self.trigger_aligner_prompt_action("SetWaferMode", "輸入模式 (Transparent/Nontransparent):")).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="SetWaferSize [n]...", command=lambda: self.trigger_aligner_prompt_action("SetWaferSize", "輸入尺寸 (4/6/8/12):")).grid(row=2, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="SetSpeed [n]...", command=lambda: self.trigger_aligner_prompt_action("SetSpeed", "輸入速度百分比 (5%~100%):")).grid(row=3, column=0, padx=5, pady=5)


    def _create_robot_tab(self):
        """建立 Robot 頁籤的內容 (使用 Combobox)"""
        frame = self.robot_tab

        # --- 參數區 ---
        param_frame = ttk.LabelFrame(frame, text="參數")
        param_frame.pack(pady=5, padx=10, fill="x")

        ttk.Label(param_frame, text="Robot 編號 [n] (空=1):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.rb_num_entry = ttk.Entry(param_frame, width=5)
        self.rb_num_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.rb_num_entry.insert(0, "") # 預設空值

        ttk.Label(param_frame, text="手臂 [Arm]:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.rb_arm_var = tk.StringVar(value="UpArm")
        ttk.Combobox(param_frame, textvariable=self.rb_arm_var, values=["UpArm", "LowArm"], width=8, state="readonly").grid(row=0, column=3, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="目標 [Dest]:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.rb_dest_entry = ttk.Entry(param_frame, width=12)
        self.rb_dest_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.rb_dest_entry.insert(0, "Loadport1") # 預設目標

        ttk.Label(param_frame, text="Slot:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.rb_slot_entry = ttk.Entry(param_frame, width=5)
        self.rb_slot_entry.grid(row=1, column=3, padx=5, pady=2, sticky="w")
        self.rb_slot_entry.insert(0, "1")

        # --- Combobox 動作區 ---
        action_frame = ttk.LabelFrame(frame, text="選擇動作")
        action_frame.pack(pady=5, padx=10, fill="x")

        self.rb_action_var = tk.StringVar()
        rb_actions = [
            # 需要 Arm, Dest, Slot
            "SmartGet", "SmartPut", "GetStandby", "PutStandby", "DoubleGet", "DoublePut",
            "TwoStepGet", "TwoStepPut", "GetStep", "PutStep", # Get/PutStep 還需要 Step 參數
            # 需要 Arm, Dest
            "MoveToStation",
            # 需要 Arm, SW
            "Vacuum On", "Vacuum Off", "EdgeGrip On", "EdgeGrip Off",
            # 需要 Arm, Direction
            "FlipWafer Front", "FlipWafer Back",
             # 需要 Arm
            "GetFlipDirection",
            # MultiGet/Put 需要 Forks 參數
            "MultiGet", "MultiPut"
        ]
        ttk.Label(action_frame, text="選擇 Robot 動作:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.rb_action_combo = ttk.Combobox(action_frame, textvariable=self.rb_action_var, values=rb_actions, width=20, state="readonly")
        self.rb_action_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        if rb_actions: self.rb_action_combo.current(0) # 設置預設選項

        ttk.Button(action_frame, text="執行選擇的動作", command=self.execute_robot_action).grid(row=0, column=2, padx=10, pady=5)

        # --- 獨立按鈕區 ---
        button_frame = ttk.LabelFrame(frame, text="常用查詢/控制")
        button_frame.pack(pady=5, padx=10, fill="x")
        ttk.Button(button_frame, text="Home [n]", command=lambda: self.trigger_robot_action("Home")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Stop [n]", command=lambda: self.trigger_robot_action("Stop")).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="GetStatus [n]", command=lambda: self.trigger_robot_action("GetStatus")).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="CheckWaferPresence [n]", command=lambda: self.trigger_robot_action("CheckWaferPresence")).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="GetForkInfo [n]", command=lambda: self.trigger_robot_action("GetForkInfo")).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="GetForkStatus [n]", command=lambda: self.trigger_robot_action("GetForkStatus")).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="GetErrorCode [n]", command=lambda: self.trigger_robot_action("GetErrorCode")).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="GetVersion [n]", command=lambda: self.trigger_robot_action("GetVersion")).grid(row=2, column=1, padx=5, pady=5)


    def _create_sequence_tab(self):
        """建立指令序列頁籤的內容 (保持不變)"""
        frame = self.sequence_tab

        ttk.Label(frame, text="在此處輸入指令序列 (一行一個指令，不含 # 和 $):").pack(pady=5, anchor="w")

        self.sequence_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, width=80)
        self.sequence_text.pack(padx=5, pady=5, expand=True, fill="both")
        # 插入範例序列
        example_sequence = """# === EFEM 初始化 ===
Remote,EFEM
Home,EFEM
GetStatus,EFEM
# === Loadport1 操作 ===
# 假設已放置 FOUP
ReadFoupID,Loadport1
Load,Loadport1
GetMapResult,Loadport1
# === Robot 取放流程 ===
SmartGet,Robot,UpArm,Loadport1,1
SmartPut,Robot,UpArm,Aligner1,1
Alignment,Aligner1
SmartGet,Robot,UpArm,Aligner1,1
SmartPut,Robot,UpArm,Loadport1,1
# === 結束 ===
Unload,Loadport1
"""
        self.sequence_text.insert(tk.END, example_sequence)


        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="執行序列", command=self.run_sequence).pack(side=tk.LEFT, padx=5)
        # ttk.Button(button_frame, text="停止序列").pack(side=tk.LEFT, padx=5) # 停止功能較複雜，暫緩

    def run_sequence(self):
        """執行指令序列文字區域中的指令"""
        sequence = self.sequence_text.get("1.0", tk.END).strip()
        if not sequence:
            self.log_message("指令序列為空。\n")
            return

        commands = sequence.splitlines()
        if not is_connected:
             self.log_message("錯誤：執行序列前請先連接到 EFEM。\n")
             messagebox.showerror("錯誤", "執行序列前請先連接到 EFEM。")
             return

        self.log_message("--- 開始執行指令序列 ---\n")
        # 在新執行緒中執行，避免阻塞 GUI
        threading.Thread(target=self._execute_sequence_thread, args=(commands,), daemon=True).start()

    def _execute_sequence_thread(self, commands):
         """在背景執行緒中執行指令序列"""
         try:
             for cmd_line in commands:
                 # 檢查是否已請求斷線 (雖然沒有停止按鈕，但可以在此檢查全局標誌)
                 if not is_connected:
                     self.log_message("錯誤：連接已斷開，序列中止。\n")
                     break

                 cmd_line = cmd_line.strip()
                 if not cmd_line: # 跳過空行
                     continue

                 if cmd_line.startswith('#'): # 跳過註解行
                     # 使用 after 將日誌更新安排在主線程中執行
                     self.root.after(0, self.log_message, f"註解: {cmd_line}\n")
                     continue

                 # 檢查是否為 Wait 指令
                 if cmd_line.lower().startswith("wait,"):
                     try:
                         parts = cmd_line.split(',')
                         delay = float(parts[1].strip())
                         self.root.after(0, self.log_message, f"等待 {delay} 秒...\n")
                         time.sleep(delay)
                         self.root.after(0, self.log_message, "等待結束。\n")
                     except (IndexError, ValueError):
                         self.root.after(0, self.log_message, f"錯誤：無效的 Wait 指令格式 '{cmd_line}'\n")
                     continue # 處理完 Wait 指令後繼續下一行

                 # 判斷是否使用 #@ 前綴
                 use_at = cmd_line.startswith('@')
                 actual_cmd = cmd_line[1:] if use_at else cmd_line

                 # **記錄準備發送的指令 (包含符號)**
                 prefix = "#@" if use_at else "#"
                 formatted_cmd_for_log = f"{prefix}{actual_cmd}$"
                 self.root.after(0, self.log_message, f"序列指令 -> 準備發送: {formatted_cmd_for_log}\n")

                 # 發送指令 (send_command 內部會處理日誌和斷線通知)
                 if not send_command(actual_cmd, lambda msg: self.root.after(0, self.log_message, msg), use_at_prefix=use_at):
                     self.root.after(0, self.log_message, f"錯誤：發送指令 '{cmd_line}' 失敗，序列中止。\n")
                     break # 發送失敗則中止序列

                 # 在指令之間加入短暫延遲
                 time.sleep(0.8) # 可以調整這個延遲時間

             # 確保在序列結束後更新日誌
             self.root.after(100, lambda: self.log_message("--- 指令序列執行完畢 ---\n"))
         except Exception as e:
             self.root.after(0, self.log_message, f"執行序列時發生未預期錯誤: {e}\n")
             self.root.after(0, self.log_message, traceback.format_exc() + "\n")


    # --- GUI 回呼函數 ---
    def log_message(self, message):
        """安全地更新日誌文字區域"""
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            try:
                self.log_text.configure(state='normal')
                self.log_text.insert(tk.END, message)
                self.log_text.see(tk.END) # 自動滾動到底部
                self.log_text.configure(state='disabled')
                # self.root.update_idletasks() # 在 after 回呼中不需要強制更新
            except tk.TclError as e:
                # 捕捉視窗已銷毀的錯誤
                if "invalid command name" not in str(e):
                     print(f"更新日誌時出錯: {e}") # 打印到控制台
            except Exception as e:
                 print(f"更新日誌時發生未預期錯誤: {e}")
                 print(traceback.format_exc())


    def update_status_label(self, text, color):
        """更新連接狀態標籤"""
        if hasattr(self, 'connection_status_label') and self.connection_status_label.winfo_exists():
             try:
                 self.connection_status_label.config(text=text, foreground=color)
                 # self.root.update_idletasks()
             except tk.TclError as e:
                 if "invalid command name" not in str(e):
                      print(f"更新狀態標籤時出錯: {e}")
             except Exception as e:
                 print(f"更新狀態標籤時發生未預期錯誤: {e}")
                 print(traceback.format_exc())


    def connect(self):
        ip = self.ip_entry.get()
        port_str = self.port_entry.get()
        try:
            port = int(port_str)
            # 禁用連接按鈕，顯示嘗試連接狀態
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.DISABLED)
            self.update_status_label("連接中...", "orange")
            # 在新執行緒中連接
            threading.Thread(target=connect_efem, args=(ip, port, self.update_status_label, lambda msg: self.root.after(0, self.log_message, msg)), daemon=True).start()
        except ValueError:
            messagebox.showerror("錯誤", "Port 必須是有效的數字。")
            self.log_message("錯誤：Port 輸入無效。\n")
            # 恢復按鈕狀態
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.update_status_label("已斷線", "red")


    def disconnect(self):
        # 禁用按鈕，顯示斷線中狀態
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.DISABLED)
        self.update_status_label("斷線中...", "orange")
        # 在新執行緒中斷線
        threading.Thread(target=disconnect_efem, args=(self.update_status_label, lambda msg: self.root.after(0, self.log_message, msg)), daemon=True).start()


    def send_gui_command(self, command, use_at_prefix=False):
        """從 GUI 發送簡單指令 (安排在主線程記錄日誌)"""
        # 使用 after 將日誌和發送操作安排在主線程，或確保 send_command 是線程安全的
        # 這裡假設 send_command 是線程安全的，但日誌記錄透過 after
        # **注意: 這裡不記錄日誌，由觸發它的函數記錄**
        send_command(command, lambda msg: self.root.after(0, self.log_message, msg), use_at_prefix=use_at_prefix) # **修正: 確保傳遞 use_at_prefix**

    def trigger_action(self, device_name, action_description, command, use_at_prefix=False):
        """通用函數，用於記錄按鈕觸發並發送指令"""
        prefix = "#@" if use_at_prefix else "#"
        formatted_cmd = f"{prefix}{command}$"
        self.log_message(f"按下按鈕 ({device_name}): {action_description} -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
        self.send_gui_command(command, use_at_prefix) # **修正: 傳遞 use_at_prefix**

    # --- Combobox 執行按鈕的回呼 ---

    def execute_loadport_action(self):
        """執行 Load Port Combobox 中選擇的動作"""
        selected_action = self.lp_action_var.get()
        lp_num = self.lp_num_entry.get().strip()
        slot = self.lp_slot_entry.get().strip() # 獲取 slot

        if not selected_action:
            self.log_message("錯誤：請先在下拉選單中選擇一個 Load Port 動作。\n")
            return
        if not lp_num:
            self.log_message("錯誤：請輸入 Loadport 編號 [n]。\n")
            return

        command = None
        log_action_desc = f"{selected_action} [n={lp_num}"
        # 處理需要額外參數的指令
        if selected_action == "GotoSlot":
            if not slot:
                self.log_message("錯誤：GotoSlot 指令需要輸入 Slot。\n")
                return
            command = f"{selected_action},Loadport{lp_num},{slot}"
            log_action_desc += f", Slot={slot}"
        else:
            # 其他指令只需要 Loadport 編號
            command = f"{selected_action},Loadport{lp_num}"

        log_action_desc += "]"
        if command:
            formatted_cmd = f"#{command}$" # 假設 GUI 觸發都用 #
            self.log_message(f"執行 Load Port 動作: {log_action_desc} -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
            self.send_gui_command(command)

    def execute_aligner_action(self):
        """執行 Aligner Combobox 中選擇的動作"""
        selected_action = self.al_action_var.get()
        al_num = self.al_num_entry.get().strip()
        degree = self.al_degree_entry.get().strip() # 獲取角度

        if not selected_action:
            self.log_message("錯誤：請先在下拉選單中選擇一個 Aligner 動作。\n")
            return
        if not al_num:
            self.log_message("錯誤：請輸入 Aligner 編號 [n]。\n")
            return

        command = None
        log_action_desc = f"{selected_action} [n={al_num}"
        # 處理需要額外參數的指令
        if selected_action in ["SetAlignmentAngle", "MoveRelativeAngle"]:
            if not degree:
                self.log_message(f"錯誤：{selected_action} 指令需要輸入角度。\n")
                return
            command = f"{selected_action},Aligner{al_num},{degree}"
            log_action_desc += f", Degree={degree}"
        elif selected_action == "Vacuum On":
            command = f"Vacuum,Aligner{al_num},On"
            log_action_desc = f"Vacuum On [n={al_num}" # 更新描述
        elif selected_action == "Vacuum Off":
            command = f"Vacuum,Aligner{al_num},Off"
            log_action_desc = f"Vacuum Off [n={al_num}" # 更新描述
        else:
            # 其他指令只需要 Aligner 編號
            command = f"{selected_action},Aligner{al_num}"

        log_action_desc += "]"
        if command:
            formatted_cmd = f"#{command}$" # 假設 GUI 觸發都用 #
            self.log_message(f"執行 Aligner 動作: {log_action_desc} -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
            self.send_gui_command(command)

    def execute_robot_action(self):
        """執行 Robot Combobox 中選擇的動作"""
        selected_action_raw = self.rb_action_var.get()
        robot_prefix = self.get_robot_prefix()
        arm = self.rb_arm_var.get()
        dest = self.rb_dest_entry.get().strip()
        slot = self.rb_slot_entry.get().strip()

        if not selected_action_raw:
            self.log_message("錯誤：請先在下拉選單中選擇一個 Robot 動作。\n")
            return
        if not robot_prefix: # get_robot_prefix 內部會記錄錯誤
             return

        command = None
        log_action_desc = f"{selected_action_raw} [n={robot_prefix}" # 初始日誌描述
        base_command = selected_action_raw.split(" ")[0] # 提取基礎指令名稱

        # 添加參數到日誌描述 (如果適用)
        if base_command not in ["GetFlipDirection"]: # 這些只需要 Arm
             log_action_desc += f", Arm={arm}"
        if base_command in ["SmartGet", "SmartPut", "GetStandby", "PutStandby", "DoubleGet", "DoublePut", "TwoStepGet", "TwoStepPut", "GetStep", "PutStep", "MoveToStation", "MultiGet", "MultiPut"]:
             log_action_desc += f", Dest={dest if dest else '未指定'}"
        if base_command in ["SmartGet", "SmartPut", "GetStandby", "PutStandby", "DoubleGet", "DoublePut", "TwoStepGet", "TwoStepPut", "GetStep", "PutStep", "MultiGet", "MultiPut"]:
             log_action_desc += f", Slot={slot if slot else '未指定'}"


        # 根據選擇的動作構建指令
        if base_command in ["SmartGet", "SmartPut", "GetStandby", "PutStandby", "DoubleGet", "DoublePut", "TwoStepGet", "TwoStepPut"]:
            if not dest or not slot:
                self.log_message(f"錯誤：{base_command} 指令需要目標 [Dest] 和 Slot。\n")
                return
            command = f"{base_command},{robot_prefix},{arm},{dest},{slot}"
        elif base_command == "MoveToStation":
            if not dest:
                self.log_message("錯誤：MoveToStation 指令需要目標 [Dest]。\n")
                return
            command = f"{base_command},{robot_prefix},{arm},{dest}"
        elif selected_action_raw == "Vacuum On":
            command = f"Vacuum,{robot_prefix},{arm},On"
        elif selected_action_raw == "Vacuum Off":
            command = f"Vacuum,{robot_prefix},{arm},Off"
        elif selected_action_raw == "EdgeGrip On":
            command = f"EdgeGrip,{robot_prefix},{arm},On"
        elif selected_action_raw == "EdgeGrip Off":
            command = f"EdgeGrip,{robot_prefix},{arm},Off"
        elif selected_action_raw == "FlipWafer Front":
             command = f"FlipWafer,{robot_prefix},{arm},Front"
        elif selected_action_raw == "FlipWafer Back":
             command = f"FlipWafer,{robot_prefix},{arm},Back"
        elif base_command == "GetFlipDirection":
             command = f"{base_command},{robot_prefix},{arm}"
        elif base_command in ["GetStep", "PutStep"]:
             if not dest or not slot:
                 self.log_message(f"錯誤：{base_command} 指令需要目標 [Dest] 和 Slot。\n")
                 return
             step = simpledialog.askstring("輸入 Step", f"請輸入 {base_command} 的 Step (1-4):", parent=self.root)
             if step and step.isdigit() and 1 <= int(step) <= 4:
                 command = f"{base_command},{robot_prefix},{arm},{dest},{slot},{step}"
                 log_action_desc += f", Step={step}" # 添加 Step 到日誌
             else:
                 self.log_message(f"錯誤：無效的 Step 輸入 '{step}'。\n")
                 return # 中止操作
        elif base_command in ["MultiGet", "MultiPut"]:
             if not dest or not slot:
                 self.log_message(f"錯誤：{base_command} 指令需要目標 [Dest] 和 Slot。\n")
                 return
             forks = simpledialog.askstring("輸入 Forks", f"請輸入 {base_command} 的 Forks (位元表示):", parent=self.root)
             if forks and forks.isdigit():
                 command = f"{base_command},{robot_prefix},{arm},{dest},{slot},{forks}"
                 log_action_desc += f", Forks={forks}" # 添加 Forks 到日誌
             else:
                 self.log_message(f"錯誤：無效的 Forks 輸入 '{forks}'。\n")
                 return # 中止操作
        else:
            self.log_message(f"錯誤：未處理的 Robot 動作 '{selected_action_raw}'。\n")
            return

        log_action_desc += "]"
        if command:
            formatted_cmd = f"#{command}$" # 假設 GUI 觸發都用 #
            self.log_message(f"執行 Robot 動作: {log_action_desc} -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
            self.send_gui_command(command)


    # --- Helper 函數 ---
    def get_robot_prefix(self):
        """獲取 Robot 指令的前綴 (Robot 或 Robot2)"""
        rb_num = self.rb_num_entry.get().strip()
        if rb_num == '2':
            return "Robot2"
        elif rb_num == '1' or rb_num == '': # 預設或明確指定 1
            return "Robot"
        else:
            self.log_message(f"錯誤：無效的 Robot 編號 '{rb_num}'，請輸入 1, 2 或留空。\n")
            return None # 返回 None 表示錯誤

    # --- Load Port Helper ---
    def trigger_loadport_action(self, base_command):
        """觸發 Load Port 獨立按鈕動作"""
        lp_num = self.lp_num_entry.get().strip()
        if not lp_num:
            self.log_message("錯誤：請輸入 Loadport 編號 [n]。\n")
            return
        command = f"{base_command},Loadport{lp_num}"
        formatted_cmd = f"#{command}$" # 假設 GUI 觸發都用 #
        self.log_message(f"按下按鈕 (Load Port): {base_command} [n={lp_num}] -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
        self.send_gui_command(command)

    # --- Aligner Helper ---
    def trigger_aligner_action(self, base_command):
        """觸發 Aligner 獨立按鈕動作"""
        al_num = self.al_num_entry.get().strip()
        if not al_num:
            self.log_message("錯誤：請輸入 Aligner 編號 [n]。\n")
            return
        command = f"{base_command},Aligner{al_num}"
        formatted_cmd = f"#{command}$" # 假設 GUI 觸發都用 #
        self.log_message(f"按下按鈕 (Aligner): {base_command} [n={al_num}] -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
        self.send_gui_command(command)

    def trigger_aligner_prompt_action(self, base_command, prompt_message):
         """觸發需要彈出對話框的 Aligner 按鈕動作"""
         al_num = self.al_num_entry.get().strip()
         if not al_num:
             self.log_message("錯誤：請輸入 Aligner 編號 [n]。\n")
             return

         param = simpledialog.askstring("輸入參數", prompt_message, parent=self.root)
         if param is not None and param.strip(): # 檢查使用者是否輸入且非空
             param = param.strip()
             command = f"{base_command},Aligner{al_num},{param}"
             formatted_cmd = f"#{command}$" # 假設 GUI 觸發都用 #
             self.log_message(f"按下按鈕 (Aligner): {base_command} [n={al_num}, Param={param}] -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
             self.send_gui_command(command)
         elif param is not None: # 使用者輸入了空字串
              self.log_message(f"錯誤：{base_command} 指令需要一個有效的參數。\n")
         # else: 使用者點了取消

    # --- Robot Helper ---
    def trigger_robot_action(self, base_command):
        """觸發 Robot 獨立按鈕動作"""
        robot_prefix = self.get_robot_prefix()
        if robot_prefix:
            command = f"{base_command},{robot_prefix}"
            formatted_cmd = f"#{command}$" # 假設 GUI 觸發都用 #
            self.log_message(f"按下按鈕 (Robot): {base_command} [n={robot_prefix}] -> 準備發送: {formatted_cmd}\n") # **記錄格式化指令**
            self.send_gui_command(command)

    # --- 佇列檢查 ---
    def check_queue(self):
        """定期檢查訊息佇列並更新 GUI"""
        try:
            while True: # 處理佇列中的所有訊息
                msg_type, data = message_queue.get_nowait()
                if msg_type == "message":
                    process_received_message(data, self.log_message)
                elif msg_type == "disconnect":
                    # 由接收執行緒觸發的斷線
                    if is_connected: # 避免重複操作
                        disconnect_efem(self.update_status_label, self.log_message)
        except queue.Empty:
            pass # 佇列空了，不做任何事
        except Exception as e:
             self.log_message(f"檢查佇列時發生錯誤: {e}\n")
             self.log_message(traceback.format_exc() + "\n")

        # 更新按鈕狀態 (確保在主線程中更新)
        if is_connected:
            if self.connect_button['state'] != tk.DISABLED:
                 self.connect_button.config(state=tk.DISABLED)
            if self.disconnect_button['state'] != tk.NORMAL:
                 self.disconnect_button.config(state=tk.NORMAL)
        else:
            if self.connect_button['state'] != tk.NORMAL:
                 self.connect_button.config(state=tk.NORMAL)
            if self.disconnect_button['state'] != tk.DISABLED:
                 self.disconnect_button.config(state=tk.DISABLED)

        # 設定下一次檢查
        self.root.after(100, self.check_queue) # 每 100ms 檢查一次


# --- 主程式 ---
if __name__ == "__main__":
    root = tk.Tk()
    app = EfemApp(root)

    # 處理關閉視窗事件
    def on_closing():
        if is_connected:
             # 確保斷線操作在主線程或以安全方式觸發
             if messagebox.askokcancel("退出", "目前仍與 EFEM 連接中，確定要斷線並退出嗎？"):
                 app.disconnect() # 觸發斷線流程
                 # 給予一點時間處理斷線
                 root.after(500, root.destroy) # 延遲銷毀視窗
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

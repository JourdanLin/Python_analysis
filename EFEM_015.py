import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, Listbox, END, SINGLE, EXTENDED, ANCHOR, LEFT, RIGHT, TOP, BOTTOM, X, Y, BOTH
import tkinter.filedialog as fd
import tkinter.font as tkFont
import socket
import threading
import time
import queue
import traceback
import os

# 導入錯誤代碼查找函數
try:
    from efem_error_codes import get_error_description
except ImportError:
    print("警告: 無法導入 efem_error_codes.py，將使用預設錯誤訊息。")
    def get_error_description(error_code):
        return f"未知錯誤代碼 ({error_code})"

# --- 後端通訊邏輯 ---
DEFAULT_EFEM_IP = "192.168.1.1"
DEFAULT_EFEM_PORT = 6000
efem_socket = None
is_connected = False
receive_thread = None
message_queue = queue.Queue()
sequence_stop_flag = threading.Event()

# --- 新增：用於序列執行緒和主執行緒通信 ---
command_result_event = threading.Event()
command_result = None # 儲存結果: "OK", "Error", "Timeout", None
waiting_for_response = False
last_sent_command_base = None # 儲存等待回應的指令基礎名稱

# ... (connect_efem, disconnect_efem, send_command, receive_data 函數保持不變) ...
def connect_efem(ip, port, status_callback, log_callback):
    """建立與 EFEM 的 TCP/IP 連接"""
    global efem_socket, is_connected, receive_thread
    try:
        if is_connected:
            log_callback("已連接，請先斷線。\n")
            return False
        log_callback(f"嘗試連接到 {ip}:{port}...\n")
        efem_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        efem_socket.settimeout(5)
        efem_socket.connect((ip, port))
        is_connected = True
        status_callback("已連接", "green")
        log_callback(f"成功連接到 EFEM: {ip}:{port}\n")
        while not message_queue.empty():
            try: message_queue.get_nowait()
            except queue.Empty: break
        # **重置序列等待狀態**
        global waiting_for_response, last_sent_command_base, command_result
        waiting_for_response = False
        last_sent_command_base = None
        command_result = None
        command_result_event.clear()

        receive_thread = threading.Thread(target=receive_data, args=(log_callback,), daemon=True)
        receive_thread.start()
        return True
    except socket.timeout:
        log_callback(f"連接超時: 無法連接到 {ip}:{port}\n")
        status_callback("已斷線", "red")
        efem_socket = None; is_connected = False; return False
    except socket.error as e:
        log_callback(f"連接 EFEM 失敗: {e}\n")
        status_callback("已斷線", "red")
        efem_socket = None; is_connected = False; return False
    except Exception as e:
        log_callback(f"連接過程中發生未預期錯誤: {e}\n")
        log_callback(traceback.format_exc() + "\n")
        status_callback("已斷線", "red")
        efem_socket = None; is_connected = False; return False

def disconnect_efem(status_callback, log_callback):
    """斷開與 EFEM 的連接"""
    global efem_socket, is_connected, receive_thread, waiting_for_response, last_sent_command_base, command_result
    if not is_connected:
        log_callback("目前未連接。\n"); return
    was_connected = is_connected
    is_connected = False
    sequence_stop_flag.set() # 請求停止序列
    command_result_event.set() # 釋放可能正在等待的序列執行緒
    if receive_thread and receive_thread.is_alive(): time.sleep(0.2)
    if efem_socket:
        try: efem_socket.shutdown(socket.SHUT_RDWR)
        except (socket.error, OSError): pass
        finally:
             try:
                 efem_socket.close()
                 if was_connected: log_callback("已斷開與 EFEM 的連接\n")
             except socket.error as e: log_callback(f"關閉 socket close 時出錯: {e}\n")
             except Exception as e: log_callback(f"關閉 socket 時發生未預期錯誤: {e}\n")
             finally: efem_socket = None
    status_callback("已斷線", "red")
    receive_thread = None
    # **重置序列等待狀態**
    waiting_for_response = False
    last_sent_command_base = None
    command_result = None


def send_command(command, log_callback, use_at_prefix=False):
    """發送指令到 EFEM"""
    if not is_connected or not efem_socket:
        log_callback("錯誤：未連接到 EFEM\n"); return False
    prefix = "#@" if use_at_prefix else "#"
    formatted_command = f"{prefix}{command}$"
    try:
        log_callback(f"發送: {formatted_command}\n")
        efem_socket.sendall(formatted_command.encode('utf-8'))
        return True
    except socket.error as e:
        log_callback(f"發送指令失敗: {e}\n")
        message_queue.put(("disconnect", None)); return False
    except Exception as e:
        log_callback(f"發送指令時發生未預期錯誤: {e}\n")
        log_callback(traceback.format_exc() + "\n")
        message_queue.put(("disconnect", None)); return False

def receive_data(log_callback):
    """在獨立執行緒中持續接收 EFEM 的數據"""
    global efem_socket, is_connected
    buffer = ""
    while is_connected:
        try:
            if not efem_socket: break
            efem_socket.settimeout(0.2)
            data_chunk = efem_socket.recv(1024)
            if not data_chunk:
                if is_connected:
                    log_callback("EFEM 連接已由對方關閉。\n")
                    message_queue.put(("disconnect", None))
                break
            buffer += data_chunk.decode('utf-8')
            while '$' in buffer:
                message, buffer = buffer.split('$', 1)
                message += '$'
                message_queue.put(("message", message)) # 將消息放入主線程處理
        except socket.timeout: continue
        except socket.error as e:
            if is_connected and isinstance(e, ConnectionResetError):
                 log_callback(f"接收數據時連接被重設: {e}\n")
                 message_queue.put(("disconnect", None))
            elif is_connected:
                 log_callback(f"接收數據時出錯: {e}\n")
                 message_queue.put(("disconnect", None))
            break
        except Exception as e:
            if is_connected:
                log_callback(f"處理接收數據時發生未預期錯誤: {e}\n")
                log_callback(traceback.format_exc() + "\n")
                message_queue.put(("disconnect", None))
            break

def process_received_message(message, log_callback):
    """處理從佇列中取出的單條完整訊息 (主執行緒)"""
    global waiting_for_response, last_sent_command_base, command_result

    log_callback(f"收到: {message}")
    try:
        content = message.strip('#@$')
        parts = content.split(',')
        is_response = False # 標記是否為等待的回應

        if len(parts) > 0:
            cmd_event = parts[0]
            details = parts[1:]

            # 檢查是否為正在等待的回應
            if waiting_for_response and last_sent_command_base and cmd_event == last_sent_command_base:
                if "Error" in details:
                    error_code = details[-1] if details else ""
                    error_desc = get_error_description(error_code)
                    log_callback(f"  -> 錯誤回應: 指令={cmd_event}, 代碼={error_code} ({error_desc})\n")
                    command_result = "Error" # 設定結果
                    command_result_event.set() # 通知序列執行緒
                    waiting_for_response = False # 重置等待狀態
                    last_sent_command_base = None
                    is_response = True
                elif "OK" in details:
                    result_data = ",".join(d for d in details if d != "OK")
                    log_callback(f"  -> 成功回應: 指令={cmd_event}{f', 結果={result_data}' if result_data else ''}\n")
                    command_result = "OK" # 設定結果
                    command_result_event.set() # 通知序列執行緒
                    waiting_for_response = False # 重置等待狀態
                    last_sent_command_base = None
                    is_response = True

            # 如果不是正在等待的回應，或者已經處理完畢，則按常規處理
            if not is_response:
                if cmd_event == "Event":
                    source = details[0] if len(details) > 0 else "未知"
                    event_type = details[1] if len(details) > 1 else "未知"
                    data = ",".join(details[2:]) if len(details) > 2 else ""
                    log_callback(f"  -> 事件: 來源={source}, 類型={event_type}, 數據={data}\n")
                # 可以選擇性地記錄非預期的成功或錯誤訊息
                # elif "Error" in details:
                #     log_callback(f"  -> (非預期)錯誤: {content}\n")
                # elif "OK" in details:
                #     log_callback(f"  -> (非預期)成功: {content}\n")

    except Exception as e:
        log_callback(f"  -> 解析訊息時發生錯誤: {e}\n")
        log_callback(traceback.format_exc() + "\n")


# --- GUI ---
class EfemApp:
    # ... (__init__ 與 V3 版本相同) ...
    def __init__(self, root):
        self.root = root
        self.root.title("EFEM 測試程式 v1.4 (20秒超時)") # 更新標題
        self.root.geometry("700x590")

        # --- 設定統一字型為 Calibri ---
        self.app_font_family = "Calibri"
        self.app_font_size = 9
        self.log_font_size = 9 # 日誌字體大小
        self.app_font = (self.app_font_family, self.app_font_size)
        self.log_font = (self.app_font_family, self.log_font_size) # 日誌也使用 Calibri

        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            default_font.configure(family=self.app_font_family, size=self.app_font_size)
            self.root.option_add("*Font", self.app_font)
        except tk.TclError:
            print(f"警告：無法設定 TkDefaultFont，某些 tk 元件可能不會使用 {self.app_font_family} 字型。")

        style = ttk.Style()
        try:
             current_theme = style.theme_use()
             style.configure('.', font=self.app_font)
             style.configure("TButton", font=self.app_font)
             style.configure("TLabel", font=self.app_font)
             style.configure("TEntry", font=self.app_font)
             style.configure("TCombobox", font=self.app_font)
             style.configure("TLabelFrame.Label", font=self.app_font)
             style.configure("TCheckbutton", font=self.app_font)
        except tk.TclError as e:
             print(f"警告：設定 ttk 樣式時出錯: {e}。介面可能部分使用預設字型。")


        # --- 最上方連線狀態 ---
        top_frame = ttk.Frame(root)
        top_frame.pack(side=TOP, fill=X, padx=5, pady=3)
        ttk.Label(top_frame, text="IP:").pack(side=LEFT, padx=2)
        self.ip_entry = ttk.Entry(top_frame, width=12); self.ip_entry.pack(side=LEFT, padx=2); self.ip_entry.insert(0, DEFAULT_EFEM_IP)
        ttk.Label(top_frame, text="Port:").pack(side=LEFT, padx=2)
        self.port_entry = ttk.Entry(top_frame, width=6); self.port_entry.pack(side=LEFT, padx=2); self.port_entry.insert(0, str(DEFAULT_EFEM_PORT))
        self.connect_button = ttk.Button(top_frame, text="連線", command=self.connect, width=5); self.connect_button.pack(side=LEFT, padx=3)
        self.disconnect_button = ttk.Button(top_frame, text="斷線", command=self.disconnect, state=tk.DISABLED, width=5); self.disconnect_button.pack(side=LEFT, padx=3)
        self.connection_status_label = ttk.Label(top_frame, text="已斷線", foreground="red", font=(self.app_font_family, self.app_font_size, "bold")); self.connection_status_label.pack(side=LEFT, padx=5)

        # --- 主內容框架 (左右分割) ---
        main_frame = ttk.Frame(root)
        main_frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=3)

        # --- 左側控制面板 ---
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 3), anchor='nw')
        left_panel.pack_propagate(False)

        # --- 右側序列面板 ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True, padx=(3, 0))

        # --- 填充左側面板 ---
        self._create_efem_panel(left_panel)
        self._create_loadport_panel(left_panel)
        self._create_aligner_panel(left_panel)
        self._create_robot_panel(left_panel)

        # --- 填充右側面板 ---
        self._create_sequence_panel(right_panel)

        # --- 底部日誌框架 ---
        log_frame = ttk.LabelFrame(root, text="日誌輸出", height=135)
        log_frame.pack(side=BOTTOM, fill=X, padx=5, pady=3)
        log_frame.pack_propagate(False)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=80, height=9, font=self.log_font)
        self.log_text.pack(padx=3, pady=3, expand=True, fill=BOTH)
        self.log_text.configure(state='disabled')

        # 啟動佇列檢查
        self.check_queue()

    # --- 左側面板建立函數 (與 V3 版本相同) ---
    def _create_efem_panel(self, parent):
        """建立 EFEM 整體控制面板"""
        frame = ttk.LabelFrame(parent, text="EFEM 整體控制")
        frame.pack(pady=3, padx=3, fill=X)

        action_frame = ttk.Frame(frame); action_frame.pack(fill=X, pady=1)
        self.efem_action_var = tk.StringVar()
        efem_actions = [ "Home,EFEM", "GetStatus,EFEM", "GetVersion,EFEM", "Remote,EFEM", "Local,EFEM",
                         "SignalTower,EFEM,Red,On", "SignalTower,EFEM,Red,Off", "SignalTower,EFEM,Red,Flash",
                         "SignalTower,EFEM,Yellow,On", "SignalTower,EFEM,Yellow,Off", "SignalTower,EFEM,Yellow,Flash",
                         "SignalTower,EFEM,Green,On", "SignalTower,EFEM,Green,Off", "SignalTower,EFEM,Green,Flash",
                         "SignalTower,EFEM,Blue,On", "SignalTower,EFEM,Blue,Off", "SignalTower,EFEM,Blue,Flash",
                         "SignalTower,EFEM,All,Off", "SetBuzzer,EFEM,1,On", "SetBuzzer,EFEM,1,Off", "SetBuzzer,EFEM,1,Flash"]
        ttk.Label(action_frame, text="動作:").pack(side=LEFT, padx=2)
        self.efem_action_combo = ttk.Combobox(action_frame, textvariable=self.efem_action_var, values=efem_actions, width=30, state="readonly")
        self.efem_action_combo.pack(side=LEFT, padx=2, fill=X, expand=True)
        if efem_actions: self.efem_action_combo.current(0)

        button_frame = ttk.Frame(frame); button_frame.pack(fill=X, pady=3)
        ttk.Button(button_frame, text="加入", width=6, command=self.add_efem_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(button_frame, text="插入", width=6, command=self.insert_efem_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(button_frame, text="執行", width=6, command=self.execute_efem_action_directly).pack(side=LEFT, padx=3)

    def _create_loadport_panel(self, parent):
        """建立 Load Port 控制面板"""
        frame = ttk.LabelFrame(parent, text="Load Port")
        frame.pack(pady=3, padx=3, fill=X)

        row1 = ttk.Frame(frame); row1.pack(fill=X, pady=1)
        self.lp_action_var = tk.StringVar()
        lp_actions = [ "Home", "Load", "Unload", "Map", "Clamp", "Unclamp", "Dock", "Undock",
                       "DoorOpen", "DoorClose", "DoorUp", "DoorDown", "HoldPlate", "Unholdplate",
                       "GotoSlot", "GetStatus", "ResetError", "GetMapResult", "ReadFoupID", "GetCurrentLPWaferSize"]
        self.lp_action_combo = ttk.Combobox(row1, textvariable=self.lp_action_var, values=lp_actions, width=15, state="readonly")
        self.lp_action_combo.pack(side=LEFT, padx=2)
        if lp_actions: self.lp_action_combo.current(0)

        ttk.Label(row1, text="裝置:").pack(side=LEFT, padx=(5, 2))
        self.lp_device_var = tk.StringVar(value="Loadport1")
        ttk.Combobox(row1, textvariable=self.lp_device_var, values=[f"Loadport{i}" for i in range(1, 5)], width=9, state="readonly").pack(side=LEFT, padx=2)

        row2 = ttk.Frame(frame); row2.pack(fill=X, pady=1)
        ttk.Label(row2, text="Slot:").pack(side=LEFT, padx=2)
        self.lp_slot_entry = ttk.Entry(row2, width=4); self.lp_slot_entry.pack(side=LEFT); self.lp_slot_entry.insert(0, "1")

        row3 = ttk.Frame(frame); row3.pack(fill=X, pady=3)
        ttk.Button(row3, text="加入", width=6, command=self.add_loadport_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(row3, text="插入", width=6, command=self.insert_loadport_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(row3, text="執行", width=6, command=self.execute_loadport_action_directly).pack(side=LEFT, padx=3)

    def _create_aligner_panel(self, parent):
        """建立 Aligner 控制面板"""
        frame = ttk.LabelFrame(parent, text="Aligner")
        frame.pack(pady=3, padx=3, fill=X)

        row1 = ttk.Frame(frame); row1.pack(fill=X, pady=1)
        self.al_action_var = tk.StringVar()
        al_actions = ["Home", "GetStatus", "ResetError", "CheckWaferPresence", "Alignment",
                      "Vacuum On", "Vacuum Off", "Clamp", "Unclamp", "MoveToLoadPosition",
                      "SetAlignmentAngle", "MoveRelativeAngle", "SetWaferType",
                      "SetWaferMode", "SetWaferSize", "SetSpeed"]
        self.al_action_combo = ttk.Combobox(row1, textvariable=self.al_action_var, values=al_actions, width=15, state="readonly")
        self.al_action_combo.pack(side=LEFT, padx=2)
        if al_actions: self.al_action_combo.current(0)

        ttk.Label(row1, text="裝置:").pack(side=LEFT, padx=(5, 2))
        self.al_device_var = tk.StringVar(value="Aligner1")
        ttk.Combobox(row1, textvariable=self.al_device_var, values=[f"Aligner{i}" for i in range(1, 3)], width=9, state="readonly").pack(side=LEFT, padx=2)

        row2 = ttk.Frame(frame); row2.pack(fill=X, pady=1)
        ttk.Label(row2, text="模式:").pack(side=LEFT, padx=2)
        self.al_mode_var = tk.StringVar(value="Transparent")
        ttk.Combobox(row2, textvariable=self.al_mode_var, values=["Transparent", "Nontransparent"], width=11, state="readonly").pack(side=LEFT, padx=2)
        ttk.Label(row2, text="類型:").pack(side=LEFT, padx=2)
        self.al_type_var = tk.StringVar(value="Notch")
        ttk.Combobox(row2, textvariable=self.al_type_var, values=["Notch", "Flat", "Neither"], width=7, state="readonly").pack(side=LEFT, padx=2)

        row3 = ttk.Frame(frame); row3.pack(fill=X, pady=1)
        ttk.Label(row3, text="尺寸:").pack(side=LEFT, padx=2)
        self.al_size_entry = ttk.Entry(row3, width=4); self.al_size_entry.pack(side=LEFT, padx=2); self.al_size_entry.insert(0, "8")
        ttk.Label(row3, text="角度:").pack(side=LEFT, padx=(5, 2))
        self.al_degree_entry = ttk.Entry(row3, width=6); self.al_degree_entry.pack(side=LEFT, padx=2); self.al_degree_entry.insert(0, "900")

        row4 = ttk.Frame(frame); row4.pack(fill=X, pady=3)
        ttk.Button(row4, text="加入", width=6, command=self.add_aligner_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(row4, text="插入", width=6, command=self.insert_aligner_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(row4, text="執行", width=6, command=self.execute_aligner_action_directly).pack(side=LEFT, padx=3)

    def _create_robot_panel(self, parent):
        """建立 Robot 控制面板"""
        frame = ttk.LabelFrame(parent, text="Robot")
        frame.pack(pady=3, padx=3, fill=X)

        row1 = ttk.Frame(frame); row1.pack(fill=X, pady=1)
        self.rb_action_var = tk.StringVar()
        rb_actions = [ "Home", "Stop", "GetStatus", "CheckWaferPresence", "GetForkInfo", "GetForkStatus", "GetErrorCode", "GetVersion",
                       "SetSpeed", "SmartGet", "SmartPut", "GetStandby", "PutStandby", "DoubleGet", "DoublePut",
                       "TwoStepGet", "TwoStepPut", "GetStep", "PutStep", "MultiGet", "MultiPut",
                       "MoveToStation", "Vacuum On", "Vacuum Off", "EdgeGrip On", "EdgeGrip Off",
                       "FlipWafer Front", "FlipWafer Back", "GetFlipDirection"]
        self.rb_action_combo = ttk.Combobox(row1, textvariable=self.rb_action_var, values=rb_actions, width=15, state="readonly")
        self.rb_action_combo.pack(side=LEFT, padx=2)
        if rb_actions: self.rb_action_combo.current(0)

        ttk.Label(row1, text="裝置:").pack(side=LEFT, padx=(5, 2))
        self.rb_device_var = tk.StringVar(value="Robot")
        ttk.Combobox(row1, textvariable=self.rb_device_var, values=["Robot", "Robot2"], width=7, state="readonly").pack(side=LEFT, padx=2)

        row2 = ttk.Frame(frame); row2.pack(fill=X, pady=1)
        ttk.Label(row2, text="手臂:").pack(side=LEFT, padx=2)
        self.rb_arm_var = tk.StringVar(value="UpArm")
        ttk.Combobox(row2, textvariable=self.rb_arm_var, values=["UpArm", "LowArm"], width=7, state="readonly").pack(side=LEFT, padx=2)
        ttk.Label(row2, text="目標:").pack(side=LEFT, padx=(5, 2))
        self.rb_dest_entry = ttk.Entry(row2, width=10); self.rb_dest_entry.pack(side=LEFT, padx=2); self.rb_dest_entry.insert(0, "Loadport1")

        row3 = ttk.Frame(frame); row3.pack(fill=X, pady=1)
        ttk.Label(row3, text="Slot:").pack(side=LEFT, padx=2)
        self.rb_slot_entry = ttk.Entry(row3, width=4); self.rb_slot_entry.pack(side=LEFT, padx=2); self.rb_slot_entry.insert(0, "1")
        ttk.Label(row3, text="速度(%):").pack(side=LEFT, padx=(5, 2))
        self.rb_speed_entry = ttk.Entry(row3, width=18); self.rb_speed_entry.pack(side=LEFT, padx=2); self.rb_speed_entry.insert(0, "100,100,100,100,100")

        row4 = ttk.Frame(frame); row4.pack(fill=X, pady=3)
        ttk.Button(row4, text="加入", width=6, command=self.add_robot_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(row4, text="插入", width=6, command=self.insert_robot_action_to_sequence).pack(side=LEFT, padx=3)
        ttk.Button(row4, text="執行", width=6, command=self.execute_robot_action_directly).pack(side=LEFT, padx=3)

    # --- 右側面板建立函數 ---
    def _create_sequence_panel(self, parent):
        """建立指令序列控制面板"""
        frame = ttk.LabelFrame(parent, text="指令序列控制")
        frame.pack(fill=BOTH, expand=True)

        top_button_frame = ttk.Frame(frame); top_button_frame.pack(fill=X, padx=3, pady=3)
        ttk.Button(top_button_frame, text="匯入", command=self.import_sequence, width=6).pack(side=LEFT, padx=3)
        ttk.Button(top_button_frame, text="匯出", command=self.export_sequence, width=6).pack(side=LEFT, padx=3)
        ttk.Button(top_button_frame, text="清除", command=self.clear_sequence, width=6).pack(side=LEFT, padx=3)

        listbox_frame = ttk.Frame(frame); listbox_frame.pack(fill=BOTH, expand=True, padx=3, pady=3)
        self.sequence_listbox = Listbox(listbox_frame, height=10, selectmode=EXTENDED, font=(self.app_font_family, self.app_font_size))
        self.sequence_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        listbox_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.sequence_listbox.yview)
        listbox_scrollbar.pack(side=RIGHT, fill=tk.Y); self.sequence_listbox.config(yscrollcommand=listbox_scrollbar.set)

        mid_control_frame = ttk.Frame(frame); mid_control_frame.pack(fill=X, padx=3, pady=3)
        ttk.Label(mid_control_frame, text="等待(ms):").pack(side=LEFT, padx=2)
        self.wait_entry = ttk.Entry(mid_control_frame, width=6); self.wait_entry.pack(side=LEFT, padx=2); self.wait_entry.insert(0, "1000")
        ttk.Button(mid_control_frame, text="加入W", command=self.add_wait_to_sequence, width=6).pack(side=LEFT, padx=2)
        ttk.Button(mid_control_frame, text="插入W", command=lambda: self.add_wait_to_sequence(insert=True), width=6).pack(side=LEFT, padx=2)
        self.cycle_var = tk.BooleanVar()
        ttk.Checkbutton(mid_control_frame, text="循環", variable=self.cycle_var).pack(side=LEFT, padx=5)
        ttk.Button(mid_control_frame, text="刪除", command=self.delete_selected_from_sequence, width=6).pack(side=RIGHT, padx=2)

        move_button_frame = ttk.Frame(frame); move_button_frame.pack(fill=X, padx=3, pady=(0, 3))
        ttk.Button(move_button_frame, text="↑", command=self.move_item_up, width=3).pack(side=LEFT, padx=2)
        ttk.Button(move_button_frame, text="↓", command=self.move_item_down, width=3).pack(side=LEFT, padx=2)

        bottom_button_frame = ttk.Frame(frame); bottom_button_frame.pack(fill=X, padx=3, pady=3)
        self.run_button = ttk.Button(bottom_button_frame, text="開始", command=self.run_sequence)
        self.run_button.pack(side=LEFT, padx=2, fill=X, expand=True)
        self.stop_button = ttk.Button(bottom_button_frame, text="停止", command=self.stop_sequence, state=tk.DISABLED)
        self.stop_button.pack(side=RIGHT, padx=2, fill=X, expand=True)

        example_sequence = [ "Remote,EFEM", "Home,EFEM", "Wait,1000", "Load,Loadport1", "SmartGet,Robot,UpArm,Loadport1,1", "Unload,Loadport1"]
        for cmd in example_sequence: self.sequence_listbox.insert(END, cmd)

    # --- 序列管理函數 (與 V3 版本相同) ---
    def add_command_to_sequence(self, command_string, insert=False):
        """將指令字串加入或插入到序列 Listbox"""
        if not command_string: return
        try:
            if insert:
                selected_indices = self.sequence_listbox.curselection()
                insert_index = selected_indices[0] if selected_indices else 0
                self.sequence_listbox.insert(insert_index, command_string)
                self.log_message(f"已插入序列 ({insert_index}): {command_string}\n")
            else:
                self.sequence_listbox.insert(END, command_string)
                self.log_message(f"已加入序列: {command_string}\n")
            self.sequence_listbox.see(END)
        except Exception as e:
            self.log_message(f"加入/插入序列時出錯: {e}\n"); self.log_message(traceback.format_exc() + "\n")

    def delete_selected_from_sequence(self):
        """刪除 Listbox 中選定的項目"""
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            self.log_message("提示：請先在序列列表中選擇要刪除的指令。\n"); return
        for i in reversed(selected_indices):
            item = self.sequence_listbox.get(i)
            self.sequence_listbox.delete(i)
            self.log_message(f"已從序列刪除: {item}\n")

    def add_wait_to_sequence(self, insert=False):
        """從輸入框獲取毫秒數，並加入 Wait 指令"""
        ms_str = self.wait_entry.get()
        try:
            ms = int(ms_str)
            if ms <= 0: raise ValueError("等待時間必須是正整數")
            command = f"Wait,{ms}"
            self.add_command_to_sequence(command, insert)
        except ValueError:
             messagebox.showerror("錯誤", "請在 '等待(ms)' 輸入框中輸入有效的正整數毫秒。")
             self.log_message("錯誤：無效的 Wait 時間輸入。\n")

    def clear_sequence(self):
        """清除序列 Listbox 中的所有項目"""
        if messagebox.askokcancel("確認", "確定要清除序列中的所有指令嗎？"):
            self.sequence_listbox.delete(0, END); self.log_message("已清除所有序列指令。\n")

    def move_item_up(self):
        """將選定項目上移"""
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices: return
        new_selection = []
        for index in selected_indices:
            if index > 0:
                item = self.sequence_listbox.get(index)
                self.sequence_listbox.delete(index)
                self.sequence_listbox.insert(index - 1, item)
                new_selection.append(index - 1)
            else: new_selection.append(index)
        self.sequence_listbox.selection_clear(0, END)
        for idx in new_selection: self.sequence_listbox.selection_set(idx)
        if new_selection: self.sequence_listbox.activate(new_selection[0]); self.sequence_listbox.see(new_selection[0])

    def move_item_down(self):
        """將選定項目下移"""
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices: return
        new_selection = []
        for index in reversed(selected_indices):
            if index < self.sequence_listbox.size() - 1:
                item = self.sequence_listbox.get(index)
                self.sequence_listbox.delete(index)
                self.sequence_listbox.insert(index + 1, item)
                new_selection.append(index + 1)
            else: new_selection.append(index)
        self.sequence_listbox.selection_clear(0, END)
        new_selection.reverse()
        for idx in new_selection: self.sequence_listbox.selection_set(idx)
        if new_selection: self.sequence_listbox.activate(new_selection[-1]); self.sequence_listbox.see(new_selection[-1])

    # --- 序列執行/停止函數 (加入成功/超時判斷) ---
    def run_sequence(self):
        """執行指令序列 Listbox 中的指令"""
        commands = self.sequence_listbox.get(0, END)
        if not commands: self.log_message("指令序列為空。\n"); return
        if not is_connected:
             self.log_message("錯誤：執行序列前請先連接到 EFEM。\n"); messagebox.showerror("錯誤", "執行序列前請先連接到 EFEM。"); return
        self.log_message("--- 開始執行指令序列 ---\n")
        sequence_stop_flag.clear(); self.run_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL)
        threading.Thread(target=self._execute_sequence_thread, args=(list(commands), self.cycle_var.get()), daemon=True).start()

    def stop_sequence(self):
        """設置停止標誌以停止序列執行"""
        self.log_message("--- 請求停止序列執行 ---\n"); sequence_stop_flag.set(); self.stop_button.config(state=tk.DISABLED)

    def _execute_sequence_thread(self, commands, cycle):
         """在背景執行緒中執行指令序列 (加入成功/超時判斷)"""
         global waiting_for_response, last_sent_command_base, command_result
         try:
             while True: # 外層循環用於處理 cycle
                 for i, cmd_line in enumerate(commands):
                     if sequence_stop_flag.is_set(): self.root.after(0, self.log_message, "序列執行已停止。\n"); break
                     if not is_connected: self.root.after(0, self.log_message, "錯誤：連接已斷開，序列中止。\n"); sequence_stop_flag.set(); break

                     self.root.after(0, self.highlight_sequence_line, i)
                     cmd_line = cmd_line.strip()
                     if not cmd_line or cmd_line.startswith('#'):
                         if cmd_line.startswith('#'): self.root.after(0, self.log_message, f"註解: {cmd_line}\n")
                         time.sleep(0.05); continue

                     # --- Wait 指令處理 ---
                     if cmd_line.lower().startswith("wait,"):
                         try:
                             parts = cmd_line.split(','); ms = int(parts[1].strip())
                             self.root.after(0, self.log_message, f"等待 {ms} ms...\n")
                             end_time = time.time() + ms / 1000.0
                             while time.time() < end_time:
                                 if sequence_stop_flag.is_set(): break
                                 time.sleep(0.1) # 分段等待檢查停止
                             if sequence_stop_flag.is_set(): self.root.after(0, self.log_message, "等待被中斷。\n"); break
                             self.root.after(0, self.log_message, "等待結束。\n")
                         except (IndexError, ValueError): self.root.after(0, self.log_message, f"錯誤：無效的 Wait 指令格式 '{cmd_line}'\n")
                         continue # 繼續下一條指令

                     # --- 一般指令處理 ---
                     use_at = cmd_line.startswith('@'); actual_cmd = cmd_line[1:] if use_at else cmd_line
                     prefix = "#@" if use_at else "#"; formatted_cmd_for_log = f"{prefix}{actual_cmd}$"
                     self.root.after(0, self.log_message, f"序列指令 -> 準備發送: {formatted_cmd_for_log}\n")

                     # 設定等待狀態
                     command_result_event.clear()
                     command_result = None
                     # 提取基礎指令用於匹配回應
                     base_cmd_for_match = actual_cmd.split(',')[0]
                     last_sent_command_base = base_cmd_for_match
                     waiting_for_response = True

                     # 發送指令
                     if not send_command(actual_cmd, lambda msg: self.root.after(0, self.log_message, msg), use_at_prefix=use_at):
                         self.root.after(0, self.log_message, f"錯誤：發送指令 '{cmd_line}' 失敗，序列中止。\n"); sequence_stop_flag.set(); break

                     # 等待回應或超時 (修改為 20 秒)
                     timeout_seconds = 20.0 # **設定超時時間**
                     self.root.after(0, self.log_message, f"等待指令 '{base_cmd_for_match}' 回應 (超時 {int(timeout_seconds)} 秒)...\n") # **更新日誌**
                     event_set = command_result_event.wait(timeout=timeout_seconds) # **使用新的超時時間**
                     waiting_for_response = False # 無論結果如何，都結束等待狀態
                     last_sent_command_base = None

                     if sequence_stop_flag.is_set(): # 檢查等待期間是否被外部停止
                          self.root.after(0, self.log_message, "等待期間序列被停止。\n"); break

                     if event_set: # 收到了回應 (OK 或 Error)
                         if command_result == "OK":
                             self.root.after(0, self.log_message, f"指令 '{base_cmd_for_match}' 執行成功。\n")
                             # 短暫延遲後繼續
                             time.sleep(0.2)
                         elif command_result == "Error":
                             self.root.after(0, self.log_message, f"指令 '{base_cmd_for_match}' 執行失敗，序列中止。\n")
                             sequence_stop_flag.set(); break # 出錯則停止
                         else: # 不應該發生，但以防萬一
                              self.root.after(0, self.log_message, f"指令 '{base_cmd_for_match}' 收到未知結果 '{command_result}'，序列中止。\n")
                              sequence_stop_flag.set(); break
                     else: # 超時
                         self.root.after(0, self.log_message, f"錯誤：等待指令 '{base_cmd_for_match}' 回應超時 ({int(timeout_seconds)}秒)，序列中止。\n") # **更新日誌**
                         command_result = "Timeout" # 標記為超時
                         sequence_stop_flag.set(); break # 超時則停止

                 # 內層循環結束
                 if sequence_stop_flag.is_set() or not cycle: break # 跳出外層循環
                 self.root.after(0, self.log_message, "--- 序列循環執行 ---\n"); time.sleep(1) # 循環間隔

         except Exception as e:
             self.root.after(0, self.log_message, f"執行序列時發生未預期錯誤: {e}\n"); self.root.after(0, self.log_message, traceback.format_exc() + "\n")
         finally:
             # **確保重置等待狀態**
             waiting_for_response = False
             last_sent_command_base = None
             self.root.after(0, self.highlight_sequence_line, -1)
             self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
             self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
             if not sequence_stop_flag.is_set(): self.root.after(100, lambda: self.log_message("--- 指令序列執行完畢 ---\n"))

    def highlight_sequence_line(self, index):
         """在 Listbox 中高亮指定行"""
         if hasattr(self, 'sequence_listbox') and self.sequence_listbox.winfo_exists():
             try:
                 for i in range(self.sequence_listbox.size()): self.sequence_listbox.itemconfig(i, bg='white', fg='black')
                 if index >= 0 and index < self.sequence_listbox.size():
                     self.sequence_listbox.itemconfig(index, bg='lightblue', fg='black'); self.sequence_listbox.see(index)
             except tk.TclError: pass

    # --- GUI 回呼函數 (與 V3 版本相同) ---
    def log_message(self, message):
        """安全地更新日誌文字區域"""
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            try:
                self.log_text.configure(state='normal'); self.log_text.insert(tk.END, message)
                self.log_text.see(tk.END); self.log_text.configure(state='disabled')
            except tk.TclError as e:
                if "invalid command name" not in str(e): print(f"更新日誌時出錯: {e}")
            except Exception as e: print(f"更新日誌時發生未預期錯誤: {e}"); print(traceback.format_exc())

    def update_status_label(self, text, color):
        """更新連接狀態標籤"""
        if hasattr(self, 'connection_status_label') and self.connection_status_label.winfo_exists():
             try: self.connection_status_label.config(text=text, foreground=color)
             except tk.TclError as e:
                 if "invalid command name" not in str(e): print(f"更新狀態標籤時出錯: {e}")
             except Exception as e: print(f"更新狀態標籤時發生未預期錯誤: {e}"); print(traceback.format_exc())

    def connect(self):
        ip = self.ip_entry.get(); port_str = self.port_entry.get()
        try:
            port = int(port_str)
            self.connect_button.config(state=tk.DISABLED); self.disconnect_button.config(state=tk.DISABLED)
            self.update_status_label("連接中...", "orange")
            threading.Thread(target=connect_efem, args=(ip, port, self.update_status_label, lambda msg: self.root.after(0, self.log_message, msg)), daemon=True).start()
        except ValueError:
            messagebox.showerror("錯誤", "Port 必須是有效的數字。"); self.log_message("錯誤：Port 輸入無效。\n")
            self.connect_button.config(state=tk.NORMAL); self.disconnect_button.config(state=tk.DISABLED)
            self.update_status_label("已斷線", "red")

    def disconnect(self):
        self.connect_button.config(state=tk.DISABLED); self.disconnect_button.config(state=tk.DISABLED)
        self.update_status_label("斷線中...", "orange")
        threading.Thread(target=disconnect_efem, args=(self.update_status_label, lambda msg: self.root.after(0, self.log_message, msg)), daemon=True).start()

    # --- 獲取指令字串的輔助函數 (與 V3 版本相同) ---
    def _get_loadport_command_string(self):
        """根據 Load Port 面板設定獲取指令字串"""
        selected_action = self.lp_action_var.get(); device = self.lp_device_var.get(); slot = self.lp_slot_entry.get().strip()
        if not selected_action or not device: return None
        if selected_action == "GotoSlot":
            if not slot: return None
            return f"{selected_action},{device},{slot}"
        else: return f"{selected_action},{device}"

    def _get_aligner_command_string(self):
        """根據 Aligner 面板設定獲取指令字串"""
        selected_action = self.al_action_var.get(); device = self.al_device_var.get()
        degree = self.al_degree_entry.get().strip(); mode = self.al_mode_var.get()
        type_ = self.al_type_var.get(); size = self.al_size_entry.get().strip() # **讀取尺寸**
        if not selected_action or not device: return None
        if selected_action in ["SetAlignmentAngle", "MoveRelativeAngle"]:
            if not degree: return None
            return f"{selected_action},{device},{degree}"
        elif selected_action == "Vacuum On": return f"Vacuum,{device},On"
        elif selected_action == "Vacuum Off": return f"Vacuum,{device},Off"
        elif selected_action == "SetWaferType": return f"{selected_action},{device},{type_}"
        elif selected_action == "SetWaferMode": return f"{selected_action},{device},{mode}"
        elif selected_action == "SetWaferSize": # **使用 Entry 的值**
            if not size: return None
            return f"{selected_action},{device},{size}"
        elif selected_action == "SetSpeed":
             speed = simpledialog.askstring("輸入參數", "輸入速度百分比 (5%~100%):", parent=self.root)
             if speed and speed.strip(): return f"{selected_action},{device},{speed.strip()}"
             else: return None
        else: return f"{selected_action},{device}"

    def _get_robot_command_string(self):
        """根據 Robot 面板設定獲取指令字串"""
        selected_action_raw = self.rb_action_var.get(); robot_prefix = self.rb_device_var.get()
        arm = self.rb_arm_var.get(); dest = self.rb_dest_entry.get().strip(); slot = self.rb_slot_entry.get().strip()
        speed_str = self.rb_speed_entry.get().strip()
        if not selected_action_raw or not robot_prefix: return None
        base_command = selected_action_raw.split(" ")[0]

        if base_command == "SetSpeed": # **處理 SetSpeed**
            speeds = [s.strip() for s in speed_str.split(',')]
            if len(speeds) == 5 and all(s.isdigit() or (s.endswith('%') and s[:-1].isdigit()) for s in speeds):
                 speeds_cleaned = [s.replace('%','') for s in speeds]
                 return f"{base_command},{robot_prefix},{','.join(speeds_cleaned)}"
            else:
                 messagebox.showerror("錯誤", "速度格式錯誤，請輸入 5 個以逗號分隔的百分比數值 (例如 100,100,100,100,100)")
                 return None
        elif base_command in ["SmartGet", "SmartPut", "GetStandby", "PutStandby", "DoubleGet", "DoublePut", "TwoStepGet", "TwoStepPut"]:
            if not dest or not slot: return None
            return f"{base_command},{robot_prefix},{arm},{dest},{slot}"
        elif base_command == "MoveToStation":
            if not dest: return None
            return f"{base_command},{robot_prefix},{arm},{dest}"
        elif selected_action_raw == "Vacuum On": return f"Vacuum,{robot_prefix},{arm},On"
        elif selected_action_raw == "Vacuum Off": return f"Vacuum,{robot_prefix},{arm},Off"
        elif selected_action_raw == "EdgeGrip On": return f"EdgeGrip,{robot_prefix},{arm},On"
        elif selected_action_raw == "EdgeGrip Off": return f"EdgeGrip,{robot_prefix},{arm},Off"
        elif selected_action_raw == "FlipWafer Front": return f"FlipWafer,{robot_prefix},{arm},Front"
        elif selected_action_raw == "FlipWafer Back": return f"FlipWafer,{robot_prefix},{arm},Back"
        elif base_command == "GetFlipDirection": return f"{base_command},{robot_prefix},{arm}"
        elif base_command in ["GetStep", "PutStep"]:
             if not dest or not slot: return None
             step = simpledialog.askstring("輸入 Step", f"請為序列中的 {base_command} 輸入 Step (1-4):", parent=self.root)
             if step and step.isdigit() and 1 <= int(step) <= 4: return f"{base_command},{robot_prefix},{arm},{dest},{slot},{step}"
             else: return None
        elif base_command in ["MultiGet", "MultiPut"]:
             if not dest or not slot: return None
             forks = simpledialog.askstring("輸入 Forks", f"請為序列中的 {base_command} 輸入 Forks (位元表示):", parent=self.root)
             if forks and forks.isdigit(): return f"{base_command},{robot_prefix},{arm},{dest},{slot},{forks}"
             else: return None
        elif base_command in ["Home", "Stop", "GetStatus", "CheckWaferPresence", "GetForkInfo", "GetForkStatus", "GetErrorCode", "GetVersion"]:
             return f"{base_command},{robot_prefix}"
        else: return None

    # --- 按鈕回呼：加入/插入序列 (與 V3 版本相同) ---
    def add_efem_action_to_sequence(self):
        """將 EFEM 動作加入序列"""
        cmd = self.efem_action_var.get()
        if cmd: self.add_command_to_sequence(cmd)
        else: self.log_message("錯誤：請選擇一個 EFEM 動作。\n")

    def insert_efem_action_to_sequence(self):
        """將 EFEM 動作插入序列"""
        cmd = self.efem_action_var.get()
        if cmd: self.add_command_to_sequence(cmd, insert=True)
        else: self.log_message("錯誤：請選擇一個 EFEM 動作。\n")

    def add_loadport_action_to_sequence(self):
        cmd = self._get_loadport_command_string()
        if cmd: self.add_command_to_sequence(cmd)
        else: self.log_message("錯誤：無法生成 Load Port 指令，請檢查參數。\n")

    def insert_loadport_action_to_sequence(self):
        cmd = self._get_loadport_command_string()
        if cmd: self.add_command_to_sequence(cmd, insert=True)
        else: self.log_message("錯誤：無法生成 Load Port 指令，請檢查參數。\n")

    def add_aligner_action_to_sequence(self):
        cmd = self._get_aligner_command_string()
        if cmd: self.add_command_to_sequence(cmd)
        else: self.log_message("錯誤：無法生成 Aligner 指令，請檢查參數或輸入。\n")

    def insert_aligner_action_to_sequence(self):
        cmd = self._get_aligner_command_string()
        if cmd: self.add_command_to_sequence(cmd, insert=True)
        else: self.log_message("錯誤：無法生成 Aligner 指令，請檢查參數或輸入。\n")

    def add_robot_action_to_sequence(self):
        cmd = self._get_robot_command_string()
        if cmd: self.add_command_to_sequence(cmd)
        else: self.log_message("錯誤：無法生成 Robot 指令，請檢查參數或輸入。\n")

    def insert_robot_action_to_sequence(self):
        cmd = self._get_robot_command_string()
        if cmd: self.add_command_to_sequence(cmd, insert=True)
        else: self.log_message("錯誤：無法生成 Robot 指令，請檢查參數或輸入。\n")

    # --- 按鈕回呼：直接執行 (與 V3 版本相同) ---
    def execute_efem_action_directly(self):
        """直接執行 EFEM Combobox 中選擇的動作"""
        command = self.efem_action_var.get()
        if command:
            self.log_message(f"直接執行 (EFEM): #{command}$\n")
            send_command(command, lambda msg: self.root.after(0, self.log_message, msg))
        else: self.log_message("錯誤：請選擇一個 EFEM 動作。\n")

    def execute_loadport_action_directly(self):
        command = self._get_loadport_command_string()
        if command:
            self.log_message(f"直接執行 (Load Port): #{command}$\n")
            send_command(command, lambda msg: self.root.after(0, self.log_message, msg))
        else: self.log_message("錯誤：無法生成 Load Port 指令，請檢查參數。\n")

    def execute_aligner_action_directly(self):
        command = self._get_aligner_command_string()
        if command:
            self.log_message(f"直接執行 (Aligner): #{command}$\n")
            send_command(command, lambda msg: self.root.after(0, self.log_message, msg))
        else: self.log_message("錯誤：無法生成 Aligner 指令，請檢查參數或輸入。\n")

    def execute_robot_action_directly(self):
        command = self._get_robot_command_string()
        if command:
            self.log_message(f"直接執行 (Robot): #{command}$\n")
            send_command(command, lambda msg: self.root.after(0, self.log_message, msg))
        else: self.log_message("錯誤：無法生成 Robot 指令，請檢查參數或輸入。\n")

    # --- 匯入/匯出 (與 V3 版本相同) ---
    def import_sequence(self):
        filepath = fd.askopenfilename(title="匯入指令序列", filetypes=[("文字檔案", "*.txt"), ("所有檔案", "*.*")])
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: commands = f.readlines()
            self.sequence_listbox.delete(0, END)
            for cmd in commands:
                cmd = cmd.strip()
                if cmd and not cmd.startswith(';'): self.sequence_listbox.insert(END, cmd)
            self.log_message(f"已從 {os.path.basename(filepath)} 匯入序列。\n")
        except Exception as e:
            messagebox.showerror("匯入錯誤", f"無法讀取檔案: {e}"); self.log_message(f"錯誤：匯入序列失敗 - {e}\n"); self.log_message(traceback.format_exc() + "\n")

    def export_sequence(self):
        filepath = fd.asksaveasfilename(title="匯出指令序列", defaultextension=".txt", filetypes=[("文字檔案", "*.txt"), ("所有檔案", "*.*")])
        if not filepath: return
        try:
            commands = self.sequence_listbox.get(0, END)
            with open(filepath, 'w', encoding='utf-8') as f:
                for cmd in commands: f.write(cmd + '\n')
            self.log_message(f"序列已匯出至 {os.path.basename(filepath)}。\n")
        except Exception as e:
            messagebox.showerror("匯出錯誤", f"無法寫入檔案: {e}"); self.log_message(f"錯誤：匯出序列失敗 - {e}\n"); self.log_message(traceback.format_exc() + "\n")

    # --- 佇列檢查 (與 V3 版本相同) ---
    def check_queue(self):
        """定期檢查訊息佇列並更新 GUI"""
        try:
            while True:
                msg_type, data = message_queue.get_nowait()
                if msg_type == "message": process_received_message(data, self.log_message)
                elif msg_type == "disconnect":
                    if is_connected: disconnect_efem(self.update_status_label, self.log_message)
        except queue.Empty: pass
        except Exception as e: self.log_message(f"檢查佇列時發生錯誤: {e}\n"); self.log_message(traceback.format_exc() + "\n")
        # 更新按鈕狀態
        is_running = self.run_button['state'] == tk.DISABLED and self.stop_button['state'] == tk.NORMAL
        if is_connected:
            if self.connect_button['state'] != tk.DISABLED: self.connect_button.config(state=tk.DISABLED)
            if self.disconnect_button['state'] != tk.NORMAL: self.disconnect_button.config(state=tk.NORMAL)
        else:
            if self.connect_button['state'] != tk.NORMAL: self.connect_button.config(state=tk.NORMAL)
            if self.disconnect_button['state'] != tk.DISABLED: self.disconnect_button.config(state=tk.DISABLED)
            if self.stop_button['state'] != tk.DISABLED: self.stop_button.config(state=tk.DISABLED) # 斷線時禁用停止
            if is_running: self.run_button.config(state=tk.NORMAL) # 如果運行中斷線，恢復開始按鈕

        self.root.after(100, self.check_queue)

# --- 主程式 ---
if __name__ == "__main__":
    root = tk.Tk()
    app = EfemApp(root)
    def on_closing():
        app.stop_sequence() # 嘗試停止序列
        if is_connected:
             if messagebox.askokcancel("退出", "目前仍與 EFEM 連接中，確定要斷線並退出嗎？"):
                 app.disconnect(); root.after(500, root.destroy)
        else: root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

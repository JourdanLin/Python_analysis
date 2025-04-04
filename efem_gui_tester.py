import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import socket
import threading
import time
import queue

# --- 後端通訊邏輯 (與之前類似，但加入佇列用於 GUI 更新) ---

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

    is_connected = False # 先設置狀態，讓接收執行緒停止
    if receive_thread and receive_thread.is_alive():
         # 短暫等待執行緒自然結束
         time.sleep(0.2)


    if efem_socket:
        try:
            efem_socket.shutdown(socket.SHUT_RDWR) # 嘗試優雅關閉
            efem_socket.close()
            log_callback("已斷開與 EFEM 的連接\n")
        except socket.error as e:
            log_callback(f"斷開連接時出錯: {e}\n")
        except Exception as e:
            log_callback(f"斷開連接時發生未預期錯誤: {e}\n")
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
        log_callback(f"發送: {formatted_command}\n")
        efem_socket.sendall(formatted_command.encode('utf-8'))
        return True
    except socket.error as e:
        log_callback(f"發送指令失敗: {e}\n")
        # 在這裡可以考慮觸發自動斷線或重連
        # disconnect_efem(...) # 需要傳遞回呼
        return False
    except Exception as e:
        log_callback(f"發送指令時發生未預期錯誤: {e}\n")
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
            if is_connected: # 只有在預期連接時才報告錯誤
                 log_callback(f"接收數據時出錯: {e}\n")
                 message_queue.put(("disconnect", None)) # 通知主線程斷線
            break # 發生錯誤，退出迴圈
        except Exception as e:
            if is_connected:
                log_callback(f"處理接收數據時發生未預期錯誤: {e}\n")
                message_queue.put(("disconnect", None))
            break

    # 確保即使發生異常，也會嘗試通知主線程斷開
    if is_connected:
        message_queue.put(("disconnect", None))
    log_callback("接收執行緒已停止。\n")


def process_received_message(message, log_callback):
    """處理從佇列中取出的單條完整訊息，並更新日誌"""
    log_callback(f"收到: {message}") # 直接在日誌中顯示原始訊息

    # 可以在這裡添加更詳細的解析邏輯，例如區分事件、錯誤、成功回覆等
    # content = message.strip('#@$')
    # parts = content.split(',')
    # ... (之前的解析邏輯) ...


# --- GUI ---
class EfemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EFEM 測試程式")
        self.root.geometry("800x600")

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

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, width=80)
        self.log_text.pack(padx=5, pady=5, expand=True, fill="both")
        self.log_text.configure(state='disabled') # 初始設為不可編輯

        # 啟動佇列檢查
        self.check_queue()

    def _create_efem_tab(self):
        """建立 EFEM 頁籤的內容"""
        frame = self.efem_tab
        ttk.Button(frame, text="Home EFEM", command=lambda: self.send_gui_command("Home,EFEM")).pack(pady=5)
        ttk.Button(frame, text="GetStatus EFEM", command=lambda: self.send_gui_command("GetStatus,EFEM")).pack(pady=5)
        ttk.Button(frame, text="切換到 Remote 模式", command=lambda: self.send_gui_command("Remote,EFEM")).pack(pady=5)
        ttk.Button(frame, text="切換到 Local 模式", command=lambda: self.send_gui_command("Local,EFEM")).pack(pady=5)
        ttk.Button(frame, text="GetVersion EFEM", command=lambda: self.send_gui_command("GetVersion,EFEM")).pack(pady=5)
        # 添加更多 EFEM 指令...
        ttk.Button(frame, text="設定塔燈 (紅燈閃爍)", command=lambda: self.send_gui_command("SignalTower,EFEM,Red,Flash")).pack(pady=5)
        ttk.Button(frame, text="設定塔燈 (綠燈常亮)", command=lambda: self.send_gui_command("SignalTower,EFEM,Green,On")).pack(pady=5)
        ttk.Button(frame, text="設定塔燈 (全滅)", command=lambda: self.send_gui_command("SignalTower,EFEM,All,Off")).pack(pady=5)

    def _create_loadport_tab(self):
        """建立 Load Port 頁籤的內容"""
        frame = self.loadport_tab

        param_frame = ttk.Frame(frame)
        param_frame.pack(pady=5)
        ttk.Label(param_frame, text="Loadport 編號 [n]:").pack(side=tk.LEFT, padx=5)
        self.lp_num_entry = ttk.Entry(param_frame, width=5)
        self.lp_num_entry.pack(side=tk.LEFT)
        self.lp_num_entry.insert(0, "1")

        ttk.Label(param_frame, text="Slot:").pack(side=tk.LEFT, padx=5)
        self.lp_slot_entry = ttk.Entry(param_frame, width=5)
        self.lp_slot_entry.pack(side=tk.LEFT)
        self.lp_slot_entry.insert(0, "1")

        cmd_frame = ttk.Frame(frame)
        cmd_frame.pack(pady=5)

        # 模擬 UI.pdf 中的按鈕 [970]
        commands = ["Load", "Unload", "Map", "GetStatus", "ResetError", "GetMapResult", "ReadFoupID", "GetLPWaferSize", "GetCurrentLPWaferSize", "Clamp", "Unclamp", "Dock", "Undock", "DoorOpen", "DoorClose"]
        row, col = 0, 0
        max_cols = 4
        for cmd in commands:
             # 特殊指令需要 Slot 參數
             if cmd == "GotoSlot":
                 ttk.Button(cmd_frame, text=f"{cmd} [n],[Slot]", command=lambda c=cmd: self.send_loadport_command_with_slot(c)).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
             else:
                 ttk.Button(cmd_frame, text=f"{cmd} [n]", command=lambda c=cmd: self.send_loadport_command(c)).grid(row=row, column=col, padx=3, pady=3, sticky="ew")

             col += 1
             if col >= max_cols:
                 col = 0
                 row += 1

        # Home 按鈕 (雖然 UI.pdf 沒單獨列出，但通常需要)
        ttk.Button(cmd_frame, text="Home [n]", command=lambda: self.send_loadport_command("Home")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")


    def _create_aligner_tab(self):
        """建立 Aligner 頁籤的內容"""
        frame = self.aligner_tab

        param_frame = ttk.Frame(frame)
        param_frame.pack(pady=5)
        ttk.Label(param_frame, text="Aligner 編號 [n]:").pack(side=tk.LEFT, padx=5)
        self.al_num_entry = ttk.Entry(param_frame, width=5)
        self.al_num_entry.pack(side=tk.LEFT)
        self.al_num_entry.insert(0, "1")

        ttk.Label(param_frame, text="角度 (0.1度):").pack(side=tk.LEFT, padx=5)
        self.al_degree_entry = ttk.Entry(param_frame, width=7)
        self.al_degree_entry.pack(side=tk.LEFT)
        self.al_degree_entry.insert(0, "900") # 預設 90.0 度

        cmd_frame = ttk.Frame(frame)
        cmd_frame.pack(pady=5)

        # 模擬 UI.pdf 中的按鈕 [970]
        commands_no_param = ["Home", "GetStatus", "ResetError", "Alignment", "MoveToLoadPosition", "CheckWaferPresence", "Clamp", "Unclamp"]
        commands_with_degree = ["SetAlignmentAngle", "MoveRelativeAngle"]
        commands_with_type = ["SetWaferType"] # Type: Notch/Flat/Neither
        commands_with_mode = ["SetWaferMode"] # Mode: Transparent/Nontransparent
        commands_with_size = ["SetWaferSize"] # Size: 4/6/8/12
        commands_with_speed = ["SetSpeed"] # Speed: 5%~100%
        commands_with_sw = ["Vacuum"] # SW: On/Off

        row, col = 0, 0
        max_cols = 3

        for cmd in commands_no_param:
             ttk.Button(cmd_frame, text=f"{cmd} [n]", command=lambda c=cmd: self.send_aligner_command(c)).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
             col = (col + 1) % max_cols
             if col == 0: row += 1

        for cmd in commands_with_degree:
             ttk.Button(cmd_frame, text=f"{cmd} [n],[Degree]", command=lambda c=cmd: self.send_aligner_command_with_degree(c)).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
             col = (col + 1) % max_cols
             if col == 0: row += 1

        # 簡化處理 Type/Mode/Size/Speed/SW，使用簡單對話框獲取參數
        ttk.Button(cmd_frame, text="SetWaferType [n]", command=lambda: self.send_aligner_prompt_command("SetWaferType", "輸入類型 (Notch/Flat/Neither):")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1
        ttk.Button(cmd_frame, text="SetWaferMode [n]", command=lambda: self.send_aligner_prompt_command("SetWaferMode", "輸入模式 (Transparent/Nontransparent):")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1
        ttk.Button(cmd_frame, text="SetWaferSize [n]", command=lambda: self.send_aligner_prompt_command("SetWaferSize", "輸入尺寸 (4/6/8/12):")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1
        ttk.Button(cmd_frame, text="SetSpeed [n]", command=lambda: self.send_aligner_prompt_command("SetSpeed", "輸入速度百分比 (5%~100%):")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1
        ttk.Button(cmd_frame, text="Vacuum [n]", command=lambda: self.send_aligner_prompt_command("Vacuum", "輸入開關 (On/Off):")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1


    def _create_robot_tab(self):
        """建立 Robot 頁籤的內容"""
        frame = self.robot_tab

        param_frame = ttk.Frame(frame)
        param_frame.pack(pady=5, fill="x")

        ttk.Label(param_frame, text="Robot 編號 [n]:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.rb_num_entry = ttk.Entry(param_frame, width=5)
        self.rb_num_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.rb_num_entry.insert(0, "") # 預設空值，讓使用者選擇 1 或 2

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

        cmd_frame = ttk.Frame(frame)
        cmd_frame.pack(pady=5, fill="x")

        # 模擬 UI.pdf 中的按鈕 [970]
        commands_simple = ["Home", "Stop", "GetStatus", "CheckWaferPresence", "GetForkInfo", "GetForkStatus", "GetErrorCode"]
        commands_arm_dest_slot = ["SmartGet", "SmartPut", "GetStandby", "PutStandby", "DoubleGet", "DoublePut"]
        commands_arm_dest = ["MoveToStation"] # 通常用於 Aligner, Stage, Buffer
        commands_arm_sw = ["Vacuum", "EdgeGrip"]

        row, col = 0, 0
        max_cols = 4

        for cmd in commands_simple:
             ttk.Button(cmd_frame, text=f"{cmd} [n]", command=lambda c=cmd: self.send_robot_command_simple(c)).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
             col = (col + 1) % max_cols
             if col == 0: row += 1

        for cmd in commands_arm_dest_slot:
             ttk.Button(cmd_frame, text=f"{cmd} [n],[Arm],[Dest],[Slot]", command=lambda c=cmd: self.send_robot_command_full(c)).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
             col = (col + 1) % max_cols
             if col == 0: row += 1

        # MoveToStation 通常不需要 Slot
        ttk.Button(cmd_frame, text="MoveToStation [n],[Arm],[Dest]", command=lambda c="MoveToStation": self.send_robot_command_arm_dest(c)).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1

        # Vacuum/EdgeGrip 需要 Arm 和 SW (On/Off)
        ttk.Button(cmd_frame, text="Vacuum [n],[Arm],On", command=lambda: self.send_robot_command_arm_sw("Vacuum", "On")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1
        ttk.Button(cmd_frame, text="Vacuum [n],[Arm],Off", command=lambda: self.send_robot_command_arm_sw("Vacuum", "Off")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1
        ttk.Button(cmd_frame, text="EdgeGrip [n],[Arm],On", command=lambda: self.send_robot_command_arm_sw("EdgeGrip", "On")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1
        ttk.Button(cmd_frame, text="EdgeGrip [n],[Arm],Off", command=lambda: self.send_robot_command_arm_sw("EdgeGrip", "Off")).grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        col = (col + 1) % max_cols
        if col == 0: row += 1

        # MultiGet/MultiPut/SetSpeed 等更複雜的指令暫未加入，可後續擴充

    def _create_sequence_tab(self):
        """建立指令序列頁籤的內容"""
        frame = self.sequence_tab

        ttk.Label(frame, text="在此處輸入指令序列 (一行一個指令，不含 # 和 $):").pack(pady=5, anchor="w")

        self.sequence_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, width=70)
        self.sequence_text.pack(padx=5, pady=5, expand=True, fill="both")
        # 插入範例序列
        example_sequence = """Remote,EFEM
Home,EFEM
GetStatus,EFEM
# 等待 2 秒
Wait,2
Load,Loadport1
GetMapResult,Loadport1
SmartGet,Robot,UpArm,Loadport1,1
SmartPut,Robot,UpArm,Aligner1,1
Alignment,Aligner1
SmartGet,Robot,UpArm,Aligner1,1
SmartPut,Robot,UpArm,Loadport1,1
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
             return

        self.log_message("--- 開始執行指令序列 ---\n")
        # 在新執行緒中執行，避免阻塞 GUI
        threading.Thread(target=self._execute_sequence_thread, args=(commands,), daemon=True).start()

    def _execute_sequence_thread(self, commands):
         """在背景執行緒中執行指令序列"""
         for cmd_line in commands:
             cmd_line = cmd_line.strip()
             if not cmd_line: # 跳過空行
                 continue

             if cmd_line.startswith('#'): # 跳過註解行
                 self.log_message(f"註解: {cmd_line}\n")
                 continue

             # 檢查是否為 Wait 指令
             if cmd_line.lower().startswith("wait,"):
                 try:
                     parts = cmd_line.split(',')
                     delay = float(parts[1].strip())
                     self.log_message(f"等待 {delay} 秒...\n")
                     time.sleep(delay)
                     self.log_message("等待結束。\n")
                 except (IndexError, ValueError):
                     self.log_message(f"錯誤：無效的 Wait 指令格式 '{cmd_line}'\n")
                 continue # 處理完 Wait 指令後繼續下一行

             # 判斷是否使用 #@ 前綴
             use_at = cmd_line.startswith('@')
             actual_cmd = cmd_line[1:] if use_at else cmd_line

             if not send_command(actual_cmd, self.log_message, use_at_prefix=use_at):
                 self.log_message(f"錯誤：發送指令 '{cmd_line}' 失敗，序列中止。\n")
                 break # 發送失敗則中止序列

             # 在指令之間加入短暫延遲，給 EFEM 反應時間，並讓接收執行緒有機會處理
             time.sleep(0.8) # 可以調整這個延遲時間

             # 檢查是否已斷線 (可能由接收執行緒觸發)
             if not is_connected:
                 self.log_message("錯誤：連接已斷開，序列中止。\n")
                 break

         # 確保在序列結束後更新日誌
         self.root.after(100, lambda: self.log_message("--- 指令序列執行完畢 ---\n"))


    # --- GUI 回呼函數 ---
    def log_message(self, message):
        """安全地更新日誌文字區域"""
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, message)
            self.log_text.see(tk.END) # 自動滾動到底部
            self.log_text.configure(state='disabled')
            self.root.update_idletasks() # 強制更新介面

    def update_status_label(self, text, color):
        """更新連接狀態標籤"""
        if hasattr(self, 'connection_status_label') and self.connection_status_label.winfo_exists():
            self.connection_status_label.config(text=text, foreground=color)
            self.root.update_idletasks()

    def connect(self):
        ip = self.ip_entry.get()
        port_str = self.port_entry.get()
        try:
            port = int(port_str)
            # 在新執行緒中連接，避免阻塞 GUI
            threading.Thread(target=connect_efem, args=(ip, port, self.update_status_label, self.log_message), daemon=True).start()
            # 暫時禁用連接按鈕，啟用斷線按鈕
            self.connect_button.config(state=tk.DISABLED)
            # self.disconnect_button.config(state=tk.NORMAL) # 在 connect_efem 成功後啟用
        except ValueError:
            messagebox.showerror("錯誤", "Port 必須是有效的數字。")
            self.log_message("錯誤：Port 輸入無效。\n")

    def disconnect(self):
        # 在新執行緒中斷線，避免阻塞 GUI
        threading.Thread(target=disconnect_efem, args=(self.update_status_label, self.log_message), daemon=True).start()
        # 禁用斷線按鈕，啟用連接按鈕
        # self.connect_button.config(state=tk.NORMAL) # 在 disconnect_efem 執行後啟用
        # self.disconnect_button.config(state=tk.DISABLED)


    def send_gui_command(self, command, use_at_prefix=False):
        """從 GUI 發送簡單指令"""
        send_command(command, self.log_message, use_at_prefix=use_at)

    def get_robot_prefix(self):
        """獲取 Robot 指令的前綴 (Robot 或 Robot2)"""
        rb_num = self.rb_num_entry.get().strip()
        if rb_num == '2':
            return "Robot2"
        elif rb_num == '1' or rb_num == '': # 預設或明確指定 1
            return "Robot"
        else:
            self.log_message(f"錯誤：無效的 Robot 編號 '{rb_num}'，將使用預設 Robot。\n")
            return "Robot" # 或者返回 None 並中止操作

    def send_robot_command_simple(self, base_command):
        """發送只需要 Robot 編號的指令"""
        robot_prefix = self.get_robot_prefix()
        if robot_prefix:
            command = f"{base_command},{robot_prefix}"
            self.send_gui_command(command)

    def send_robot_command_full(self, base_command):
        """發送需要 Arm, Dest, Slot 的 Robot 指令"""
        robot_prefix = self.get_robot_prefix()
        arm = self.rb_arm_var.get()
        dest = self.rb_dest_entry.get().strip()
        slot = self.rb_slot_entry.get().strip()
        if not dest:
             self.log_message("錯誤：請輸入目標 [Dest]。\n")
             return
        if not slot:
             self.log_message("錯誤：請輸入 Slot。\n")
             return
        if robot_prefix:
            command = f"{base_command},{robot_prefix},{arm},{dest},{slot}"
            self.send_gui_command(command)

    def send_robot_command_arm_dest(self, base_command):
         """發送需要 Arm, Dest 的 Robot 指令"""
         robot_prefix = self.get_robot_prefix()
         arm = self.rb_arm_var.get()
         dest = self.rb_dest_entry.get().strip()
         if not dest:
             self.log_message("錯誤：請輸入目標 [Dest]。\n")
             return
         if robot_prefix:
            command = f"{base_command},{robot_prefix},{arm},{dest}"
            self.send_gui_command(command)

    def send_robot_command_arm_sw(self, base_command, sw):
         """發送需要 Arm 和 SW (On/Off) 的 Robot 指令"""
         robot_prefix = self.get_robot_prefix()
         arm = self.rb_arm_var.get()
         if robot_prefix:
            command = f"{base_command},{robot_prefix},{arm},{sw}"
            self.send_gui_command(command)


    def send_loadport_command(self, base_command):
        """發送需要 Loadport 編號的指令"""
        lp_num = self.lp_num_entry.get().strip()
        if not lp_num:
            self.log_message("錯誤：請輸入 Loadport 編號 [n]。\n")
            return
        command = f"{base_command},Loadport{lp_num}"
        self.send_gui_command(command)

    def send_loadport_command_with_slot(self, base_command):
         """發送需要 Loadport 編號和 Slot 的指令"""
         lp_num = self.lp_num_entry.get().strip()
         slot = self.lp_slot_entry.get().strip()
         if not lp_num:
             self.log_message("錯誤：請輸入 Loadport 編號 [n]。\n")
             return
         if not slot:
             self.log_message("錯誤：請輸入 Slot。\n")
             return
         command = f"{base_command},Loadport{lp_num},{slot}"
         self.send_gui_command(command)

    def send_aligner_command(self, base_command):
        """發送需要 Aligner 編號的指令"""
        al_num = self.al_num_entry.get().strip()
        if not al_num:
            self.log_message("錯誤：請輸入 Aligner 編號 [n]。\n")
            return
        command = f"{base_command},Aligner{al_num}"
        self.send_gui_command(command)

    def send_aligner_command_with_degree(self, base_command):
        """發送需要 Aligner 編號和角度的指令"""
        al_num = self.al_num_entry.get().strip()
        degree = self.al_degree_entry.get().strip()
        if not al_num:
            self.log_message("錯誤：請輸入 Aligner 編號 [n]。\n")
            return
        if not degree:
            self.log_message("錯誤：請輸入角度。\n")
            return
        command = f"{base_command},Aligner{al_num},{degree}"
        self.send_gui_command(command)

    def send_aligner_prompt_command(self, base_command, prompt_message):
         """發送需要 Aligner 編號和額外參數（透過對話框獲取）的指令"""
         al_num = self.al_num_entry.get().strip()
         if not al_num:
             self.log_message("錯誤：請輸入 Aligner 編號 [n]。\n")
             return

         param = simpledialog.askstring("輸入參數", prompt_message, parent=self.root)
         if param is not None and param.strip(): # 檢查使用者是否輸入且非空
             param = param.strip()
             command = f"{base_command},Aligner{al_num},{param}"
             self.send_gui_command(command)
         elif param is not None: # 使用者輸入了空字串
              self.log_message(f"錯誤：{base_command} 指令需要一個有效的參數。\n")
         # else: 使用者點了取消


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

        # 更新按鈕狀態
        if is_connected:
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
        else:
            self.connect_button.config(state=tk.NORMAL)
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
             if messagebox.askokcancel("退出", "目前仍與 EFEM 連接中，確定要斷線並退出嗎？"):
                 app.disconnect()
                 # 等待斷線完成
                 time.sleep(0.5)
                 root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
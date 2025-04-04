#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import socket
import threading
import time
import queue
from datetime import datetime

# 確保已安裝 PyQt5: pip install PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QGridLayout, QGroupBox,
                             QMessageBox, QComboBox, QTabWidget, QSplitter, QFrame)
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, Qt
from PyQt5.QtGui import QTextCursor, QColor, QFont

# --- 常數 ---
DEFAULT_IP = "192.168.1.1"
DEFAULT_PORT = 6000
BUFFER_SIZE = 4096
CONNECT_TIMEOUT = 5  # 連線超時 (秒)
COMMAND_TIMEOUT = 10 # 指令回應超時 (秒)
CONFIRMATION_TIMEOUT = 60 # 使用者確認超時 (秒)

# --- 錯誤代碼映射 (部分範例，需要從 API 手冊 1.4 完整填充) ---
ERROR_CODES = {
    "0001": "未定義指令 (Undefine command)",
    "0002": "未定義裝置名稱 (Undefine device name)",
    "0003": "無效參數 (Invalid parameters)",
    "0004": "非遠端模式 (Not in Remote mode)",
    "0005": "EFEM 未就緒 (EFEM not ready)",
    "1001": "緊急停止觸發 (Emergency stop on)",
    "3001": "機器人通訊錯誤 (Robot communication error)",
    "3002": "機器人未分類錯誤 (Robot unclassified error)",
    "3003": "機器人教導器使用中 (Robot teach-pendant is using)",
    "4001": "Aligner 通訊錯誤 (Aligner communication error)",
    "5001": "Loadport 通訊錯誤 (Loadport communication error)",
    "5002": "RFID 通訊錯誤 (RFID communication error)",
    "5004": "RFID 讀取失敗 (RFID read fail)",
    "6001": "OCR 未分類錯誤 (OCR unclassified error)",
    "6002": "OCR 通訊錯誤 (OCR communication error)",
    "6003": "OCR 讀取失敗 (OCR Read failed)",
    # ... 在此處添加更多來自 API 手冊的錯誤代碼 ...
}

# --- 網路通訊執行緒 ---
class EFemClientThread(QThread):
    """處理與 EFEM 的 TCP/IP 通訊"""
    # 信號定義
    connection_status_signal = pyqtSignal(str) # 'Connected', 'Disconnected', 'Connecting', 'Error: ...'
    received_data_signal = pyqtSignal(str)     # 收到的原始資料
    log_signal = pyqtSignal(str, str)          # (訊息, 顏色)

    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port
        self.sock = None
        self.is_running = False
        self.command_queue = queue.Queue() # 用於從主執行緒接收指令

    def connect_to_efem(self):
        """嘗試連接到 EFEM"""
        self.log_signal.emit(f"嘗試連線到 {self.ip}:{self.port}...", "blue")
        self.connection_status_signal.emit("Connecting")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(CONNECT_TIMEOUT) # 設定連線超時
            self.sock.connect((self.ip, self.port))
            self.sock.settimeout(None) # 取消超時，改為阻塞接收
            self.is_running = True
            self.connection_status_signal.emit("Connected")
            self.log_signal.emit("連線成功.", "green")
            return True
        except socket.timeout:
            self.log_signal.emit(f"連線超時 ({CONNECT_TIMEOUT}秒).", "red")
            self.connection_status_signal.emit(f"Error: 連線超時")
            self.sock = None
            return False
        except Exception as e:
            error_msg = f"連線錯誤: {e}"
            self.log_signal.emit(error_msg, "red")
            self.connection_status_signal.emit(f"Error: {e}")
            self.sock = None
            return False

    def send_command(self, command):
        """將指令放入佇列等待發送"""
        if command:
            self.command_queue.put(command)

    def _send(self, command):
        """實際發送指令 (在執行緒內部呼叫)"""
        if self.sock and self.is_running:
            try:
                formatted_command = f"#{command}$".encode('utf-8')
                self.sock.sendall(formatted_command)
                self.log_signal.emit(f"發送: #{command}$", "purple")
                return True
            except Exception as e:
                error_msg = f"發送指令 '{command}' 失敗: {e}"
                self.log_signal.emit(error_msg, "red")
                self.stop() # Assume connection lost on send error
                return False
        else:
            self.log_signal.emit(f"無法發送 '{command}': 未連線.", "orange")
            return False

    def run(self):
        """執行緒主循環：連接、發送指令、接收資料"""
        if not self.connect_to_efem():
            return # 連線失敗則退出執行緒

        while self.is_running:
            # 檢查是否有指令要發送
            try:
                command_to_send = self.command_queue.get_nowait()
                if not self._send(command_to_send):
                    break # 發送失敗則退出
            except queue.Empty:
                pass # 沒有指令要發送，繼續接收

            # 嘗試接收資料
            try:
                # 使用 select 實現非阻塞檢查是否有資料可讀
                import select
                ready_to_read, _, _ = select.select([self.sock], [], [], 0.1) # 100ms 超時

                if ready_to_read:
                    data_bytes = self.sock.recv(BUFFER_SIZE)
                    if data_bytes:
                        try:
                            # 嘗試用 UTF-8 解碼，如果失敗則用預設方式 (可能包含原始位元組)
                            raw_data = data_bytes.decode('utf-8', errors='replace')
                            # --- 資料處理 ---
                            # EFEM 回應可能包含多個以 '$' 分隔的訊息
                            parts = raw_data.split('$')
                            full_message = ""
                            for part in parts:
                                if part.strip(): # 忽略空部分
                                    # 重新加上結束符號以便解析
                                    message = part.strip() + "$"
                                    # 去掉起始的 '#' (如果有的話)
                                    if message.startswith('#'):
                                        message = message[1:]
                                    self.received_data_signal.emit(message)
                                    full_message += message # 用於日誌
                            if full_message:
                                self.log_signal.emit(f"收到: {full_message.rstrip('$')}", "blue")

                        except UnicodeDecodeError:
                             self.log_signal.emit(f"收到無法解碼的資料: {data_bytes!r}", "orange")
                             self.received_data_signal.emit(f"RAW_DATA:{data_bytes!r}") # 發送原始資料標記
                    else:
                        # 對方關閉連線
                        self.log_signal.emit("偵測到遠端連線關閉.", "orange")
                        self.stop()
                        break
            except socket.error as e:
                # 連線中斷等錯誤
                if self.is_running: # 避免重複報告已手動停止的錯誤
                    self.log_signal.emit(f"接收錯誤: {e}", "red")
                    self.stop()
                break
            except Exception as e:
                 if self.is_running:
                    self.log_signal.emit(f"執行緒發生未預期錯誤: {e}", "red")
                    # Consider stopping based on error type
                    # self.stop()
                 break

            # 短暫休眠避免 CPU 占用過高
            # time.sleep(0.01) # select 已經有超時，可能不需要

        # 執行緒結束前的清理
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        if self.is_running: # 如果不是被外部 stop() 呼叫而結束
            self.connection_status_signal.emit("Disconnected")
            self.log_signal.emit("連線已中斷.", "red")
        self.is_running = False # 確保狀態更新

    def stop(self):
        """停止執行緒並關閉連線"""
        if self.is_running:
            self.log_signal.emit("正在停止通訊執行緒...", "orange")
            self.is_running = False
            # 清空指令佇列，避免關閉後還嘗試發送
            while not self.command_queue.empty():
                try:
                    self.command_queue.get_nowait()
                except queue.Empty:
                    break
            # 不需要 join，因為 run() 循環會自己結束
            self.connection_status_signal.emit("Disconnected") # 確保 UI 更新


# --- 流程控制執行緒 ---
class FlowControlThread(QThread):
    """管理自動化流程的狀態機"""
    # 信號定義
    update_step_signal = pyqtSignal(str)            # 更新流程步驟描述
    request_confirmation_signal = pyqtSignal(str, str) # (類型, 資料) 請求使用者確認
    send_efem_command_signal = pyqtSignal(str)      # 發送指令到 EFEM
    flow_finished_signal = pyqtSignal(str)          # (狀態: Completed/Error/Stopped) 流程結束
    log_signal = pyqtSignal(str, str)               # (訊息, 顏色)

    def __init__(self, num_loadports=1, num_aligners=1, num_ocrs=1): # 範例配置
        super().__init__()
        self.is_running = False
        self.current_step = 0
        # 使用 Queue 來安全地在執行緒間傳遞回應和確認結果
        self.efem_response_queue = queue.Queue(maxsize=1)
        self.user_confirmation_queue = queue.Queue(maxsize=1)
        self.num_loadports = num_loadports
        self.current_slot = 1 # 假設從第一個 slot 開始
        self.max_slots = 25   # 假設最多 25 個 slot
        self.map_result_data = "" # 儲存 Map 結果

    def set_efem_response(self, data):
        """從主執行緒接收 EFEM 回應"""
        try:
            # 清空舊的回應 (如果有的話) 以確保只處理最新的
            while not self.efem_response_queue.empty():
                self.efem_response_queue.get_nowait()
            self.efem_response_queue.put(data, block=False)
        except queue.Full:
            self.log_signal.emit("警告: EFEM 回應佇列已滿，可能遺失回應", "orange")

    def set_user_confirmation(self, result):
        """從主執行緒接收使用者確認結果"""
        try:
             # 清空舊的確認
            while not self.user_confirmation_queue.empty():
                self.user_confirmation_queue.get_nowait()
            self.user_confirmation_queue.put(result, block=False)
        except queue.Full:
             self.log_signal.emit("警告: 使用者確認佇列已滿", "orange")

    def _wait_for_efem_response(self, timeout=COMMAND_TIMEOUT):
        """等待 EFEM 回應"""
        try:
            response = self.efem_response_queue.get(timeout=timeout)
            return response
        except queue.Empty:
            return None # 超時

    def _wait_for_user_confirmation(self, timeout=CONFIRMATION_TIMEOUT):
        """等待使用者確認"""
        try:
            result = self.user_confirmation_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            return None # 超時

    def _send_cmd_and_wait(self, command, step_desc):
        """發送指令並等待回應的輔助函數"""
        self.update_step_signal.emit(f"步驟 {self.current_step}: {step_desc} (發送: {command})")
        self.send_efem_command_signal.emit(command)
        response = self._wait_for_efem_response()
        if response is None:
            self.log_signal.emit(f"錯誤: 等待 '{command}' 回應超時 ({COMMAND_TIMEOUT}秒)", "red")
            return None, "Timeout"
        if ",Error," in response:
            self.log_signal.emit(f"錯誤: 指令 '{command}' 收到錯誤回應: {response.strip()}", "red")
            return None, "EFEM Error"
        if ",OK" in response:
             self.log_signal.emit(f"指令 '{command}' 成功: {response.strip()}", "green")
             return response, "OK"

        self.log_signal.emit(f"警告: 指令 '{command}' 收到未預期的回應: {response.strip()}", "orange")
        return None, "Unexpected Response"

    def _request_user_confirm(self, confirm_type, data, step_desc):
        """請求使用者確認的輔助函數"""
        self.update_step_signal.emit(f"步驟 {self.current_step}: {step_desc} ({confirm_type}: {data})")
        self.request_confirmation_signal.emit(confirm_type, data)
        confirmation = self._wait_for_user_confirmation()
        if confirmation is None:
            self.log_signal.emit(f"錯誤: 等待使用者確認 '{confirm_type}' 超時 ({CONFIRMATION_TIMEOUT}秒)", "red")
            return False, "Timeout"
        if confirmation:
            self.log_signal.emit(f"使用者確認 '{confirm_type}' 資料正確", "green")
            return True, "Confirmed"
        else:
            self.log_signal.emit(f"使用者確認 '{confirm_type}' 資料錯誤", "orange")
            return False, "Rejected"

    def run(self):
        """執行流程狀態機"""
        self.is_running = True
        self.current_step = 0
        self.current_slot = 1 # 重設起始 slot
        error_occurred = False

        # --- 流程開始 ---
        self.log_signal.emit("自動流程啟動...", "green")

        # 步驟 1-4: 假設 UI 已處理 (準備送貨/接收貨命令/回覆/完成)

        # 步驟 5: 取得 Loadport 狀態 (假設 Port 1)
        # 通常在 FoupPlace 事件後觸發，這裡為簡化直接執行
        self.current_step = 5
        _, status = self._send_cmd_and_wait("GetStatus,Loadport1", "取得 Loadport1 狀態")
        if status != "OK": error_occurred = True;

        # 步驟 7: 讀取 RFID
        if not error_occurred:
            self.current_step = 7
            response, status = self._send_cmd_and_wait("ReadFoupID,Loadport1", "讀取 Loadport1 RFID")
            if status == "OK":
                rfid = self.parse_rfid(response)
                # 步驟 9: 等待終端確認 RFID
                self.current_step = 9
                confirmed, confirm_status = self._request_user_confirm("RFID", rfid, "等待終端確認 RFID")
                if not confirmed: error_occurred = True
            else:
                error_occurred = True

        # 步驟 11: Load (含 Mapping)
        if not error_occurred:
            self.current_step = 11
            # Load 指令可能需要較長時間，增加超時
            response, status = self._send_cmd_and_wait("Load,Loadport1", "執行 Loadport1 Load (含 Mapping)")
            if status != "OK": error_occurred = True

        # 步驟 13: 取得 Map 結果
        if not error_occurred:
             self.current_step = 13
             response, status = self._send_cmd_and_wait("GetMapResult,Loadport1", "取得 Loadport1 Map 結果")
             if status == "OK":
                 self.map_result_data = self.parse_map_result(response)
                 # 步驟 15: 等待終端確認 Map 結果
                 self.current_step = 15
                 # Map 結果可能很長，顯示部分或摘要
                 display_map = self.map_result_data[:50] + "..." if len(self.map_result_data) > 50 else self.map_result_data
                 confirmed, confirm_status = self._request_user_confirm("Map Result", display_map, "等待終端確認 Map 結果")
                 if not confirmed: error_occurred = True
             else:
                 error_occurred = True

        # --- Wafer 處理循環 ---
        while self.current_slot <= self.max_slots and not error_occurred:
            # 檢查 Map Result 中當前 Slot 是否有 Wafer (需要實作 parse_map_result 和檢查邏輯)
            # has_wafer = self.check_slot_has_wafer(self.map_result_data, self.current_slot)
            has_wafer = True # 暫時假設都有 Wafer

            if not has_wafer:
                self.log_signal.emit(f"流程: Slot {self.current_slot} 無 Wafer，跳過", "gray")
                self.current_slot += 1
                continue

            self.log_signal.emit(f"流程: 開始處理 Slot {self.current_slot}", "blue")

            # 步驟 15 (文件為 15): 從 Loadport 取片
            self.current_step = 17 # 對應思考流程中的編號
            cmd = f"SmartGet,Robot1,UpArm,Loadport1,{self.current_slot}" # 假設 Robot1, UpArm
            _, status = self._send_cmd_and_wait(cmd, f"從 Loadport1 取片 (Slot {self.current_slot})")
            if status != "OK": error_occurred = True; break

            # 步驟 17 (文件為 17): 送片至 Aligner
            if not error_occurred:
                self.current_step = 19
                cmd = "SmartPut,Robot1,UpArm,Aligner1,1" # 假設 Aligner1, Slot 1
                _, status = self._send_cmd_and_wait(cmd, "送片至 Aligner1")
                if status != "OK": error_occurred = True; break

            # 步驟 19 (文件為 19): Aligner 對準
            if not error_occurred:
                self.current_step = 21
                # Alignment 可能需要較長時間
                _, status = self._send_cmd_and_wait("Alignment,Aligner1", "執行 Aligner1 對準")
                if status != "OK": error_occurred = True; break

            # 步驟 21 (文件為 21): 讀取 OCR
            if not error_occurred:
                self.current_step = 23
                cmd = "ReadID,OCR1" # 假設 OCR1
                response, status = self._send_cmd_and_wait(cmd, "讀取 OCR1 ID")
                if status == "OK":
                    ocr_id = self.parse_ocr_result(response)
                    # 步驟 25: 等待終端確認 OCR
                    self.current_step = 25
                    confirmed, confirm_status = self._request_user_confirm("OCR", ocr_id, "等待終端確認 OCR")
                    if not confirmed: error_occurred = True; break
                else:
                     error_occurred = True; break

            # 步驟 25 (文件為 25): 從 Aligner 取片
            if not error_occurred:
                self.current_step = 27
                cmd = "SmartGet,Robot1,UpArm,Aligner1,1"
                _, status = self._send_cmd_and_wait(cmd, "從 Aligner1 取片")
                if status != "OK": error_occurred = True; break

            # 步驟 27 (文件為 27): 放片至 Stage (或 Buffer)
            if not error_occurred:
                self.current_step = 29
                # 目的地根據實際情況修改，這裡用 Stage1
                cmd = "SmartPut,Robot1,UpArm,Stage1,1" # 假設 Stage1, Slot 1
                _, status = self._send_cmd_and_wait(cmd, "放片至 Stage1")
                if status != "OK": error_occurred = True; break

            # 步驟 29 & 31 (文件為 29, 31): 從 Stage 取回放至 Buffer (此處流程合併或省略，直接處理下個 slot)
            # 如果需要 Stage <-> Buffer 的交換，需在此處加入對應的 SmartGet/SmartPut

            # 處理完成，移動到下一個 Slot
            if not error_occurred:
                 self.log_signal.emit(f"流程: Slot {self.current_slot} 處理完成", "green")
                 self.current_slot += 1

        # --- 循環結束 ---

        # 步驟 33 (文件為 33): Unload
        if not error_occurred:
            self.current_step = 32
            # Unload 可能需要較長時間
            _, status = self._send_cmd_and_wait("Unload,Loadport1", "執行 Loadport1 Unload")
            if status != "OK": error_occurred = True

        # 步驟 35-38: 假設 UI 處理 (準備收貨/接送貨命令/回覆/完成)

        # --- 流程結束 ---
        self.is_running = False
        final_status = "Completed" if not error_occurred else "Error"
        self.update_step_signal.emit(f"流程結束 ({final_status})")
        self.flow_finished_signal.emit(final_status)
        self.log_signal.emit(f"自動流程結束 ({final_status}).", "green" if not error_occurred else "red")

    def stop(self):
        """停止流程執行"""
        if self.is_running:
            self.log_signal.emit("正在中止自動流程...", "orange")
            self.is_running = False
            # 可以在此處發送 Robot Stop 指令 (如果需要立即停止機器人)
            # self.send_efem_command_signal.emit("Stop,Robot1")
            # 喚醒可能在等待的事件，讓 run() 循環可以檢查 is_running 狀態並退出
            self.efem_response_queue.put("STOP_REQUESTED")
            self.user_confirmation_queue.put(False) # 以 'False' 喚醒確認等待

    def parse_rfid(self, response):
        """從 ReadFoupID 回應中解析 RFID"""
        # 範例: ReadFoupID,Loadport1,OK,F18$
        parts = response.strip().rstrip('$').split(',')
        if len(parts) == 4 and parts[2] == "OK":
            return parts[3]
        return "解析錯誤"

    def parse_map_result(self, response):
        """從 GetMapResult 回應中解析 Map Data"""
        # 範例: GetMapResult,Loadport1,OK,1,1,0,0,...$
        parts = response.strip().rstrip('$').split(',')
        if len(parts) >= 4 and parts[2] == "OK":
            return ",".join(parts[3:]) # 返回逗號分隔的結果字串
        return "解析錯誤"

    def parse_ocr_result(self, response):
        """從 ReadID,OCR 回應中解析 OCR 結果"""
         # 範例: ReadID,OCR1,OK,CA123456$
        parts = response.strip().rstrip('$').split(',')
        if len(parts) == 4 and parts[2] == "OK":
            return parts[3]
        return "解析錯誤"

    # def check_slot_has_wafer(self, map_data, slot_index):
    #     """檢查指定 slot 是否有 wafer (需要根據 map_data 格式實作)"""
    #     # map_data 是 '1,1,0,0,...' 的字串，Slot 25 到 Slot 1
    #     # slot_index 是 1 到 25
    #     if not map_data or map_data == "解析錯誤":
    #         return False
    #     slots = map_data.split(',')
    #     if len(slots) == 25:
    #         # 索引轉換: slot_index 1 對應 slots[24], slot_index 25 對應 slots[0]
    #         map_index = 25 - slot_index
    #         if 0 <= map_index < 25:
    #             # 1: Presence, 2: Tilted, 3: Overlapping, 4: Thin, 5: Up/Down tile
    #             return slots[map_index] in ['1', '2', '3', '4', '5']
    #     return False # 格式錯誤或索引錯誤


# --- 主 GUI 視窗 ---
class EFemApp(QMainWindow):
    """應用程式主視窗"""
    # 定義一個信號，用於從 GUI 元件觸發指令發送
    send_command_request_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("EFEM GUI 控制器 v0.1")
        self.setGeometry(50, 50, 1200, 800) # x, y, width, height

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        # 使用 QSplitter 實現可調整大小的佈局
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.central_layout = QHBoxLayout(self.central_widget)
        self.central_layout.addWidget(self.main_splitter)

        self.client_thread = None
        self.flow_thread = None

        # --- 左側面板 (控制) ---
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(5, 5, 5, 5) # 減少邊距

        self._create_connection_area()
        self._create_efem_status_area()
        self._create_flow_control_area() # 將流程控制移到左側上方
        self._create_module_tabs() # 主要控制模組

        self.left_layout.addWidget(self.connection_group)
        self.left_layout.addWidget(self.efem_status_group)
        self.left_layout.addWidget(self.flow_control_group)
        self.left_layout.addWidget(self.module_tabs) # 將 TabWidget 加入左側
        self.left_layout.addStretch(1) # 將元件推到頂部

        # --- 右側面板 (日誌) ---
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 5, 5, 5) # 減少邊距
        self._create_log_area()
        self.right_layout.addWidget(self.log_group)

        # --- 將面板加入 Splitter ---
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([450, 750]) # 初始寬度比例

        # 連接內部信號
        self.send_command_request_signal.connect(self.send_command_from_gui)

        # 設置字體
        default_font = QFont("Microsoft JhengHei UI", 9) # 微軟正黑體
        self.setFont(default_font)
        self.log_edit.setFont(QFont("Consolas", 9)) # 日誌區使用等寬字體

    def _create_connection_area(self):
        """建立連線控制區域的 GUI 元件"""
        self.connection_group = QGroupBox("連線控制")
        layout = QGridLayout()

        layout.addWidget(QLabel("IP 位址:"), 0, 0)
        self.ip_edit = QLineEdit(DEFAULT_IP)
        layout.addWidget(self.ip_edit, 0, 1)

        layout.addWidget(QLabel("埠號:"), 1, 0)
        self.port_edit = QLineEdit(str(DEFAULT_PORT))
        layout.addWidget(self.port_edit, 1, 1)

        self.connect_button = QPushButton("連線")
        self.connect_button.setStyleSheet("background-color: lightgreen;")
        self.connect_button.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_button, 2, 0, 1, 2) # Span 2 columns

        layout.addWidget(QLabel("狀態:"), 3, 0)
        self.connection_status_label = QLabel("未連線")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status_label, 3, 1)

        self.connection_group.setLayout(layout)

    def _create_efem_status_area(self):
        """建立 EFEM 整體狀態顯示與控制區域"""
        self.efem_status_group = QGroupBox("EFEM 狀態與控制")
        layout = QGridLayout()

        # 狀態顯示
        layout.addWidget(QLabel("模式:"), 0, 0)
        self.efem_mode_label = QLabel("未知")
        layout.addWidget(self.efem_mode_label, 0, 1)

        layout.addWidget(QLabel("EMO:"), 1, 0)
        self.efem_emo_label = QLabel("未知")
        layout.addWidget(self.efem_emo_label, 1, 1)

        layout.addWidget(QLabel("FFU:"), 0, 2)
        self.efem_ffu_label = QLabel("未知")
        layout.addWidget(self.efem_ffu_label, 0, 3)

        layout.addWidget(QLabel("門:"), 1, 2)
        self.efem_door_label = QLabel("未知")
        layout.addWidget(self.efem_door_label, 1, 3)

        # 控制按鈕
        self.get_efem_status_button = QPushButton("取得狀態")
        self.get_efem_status_button.clicked.connect(lambda: self.send_command_request_signal.emit("GetStatus,EFEM"))
        layout.addWidget(self.get_efem_status_button, 2, 0)

        self.remote_button = QPushButton("遠端模式")
        self.remote_button.clicked.connect(lambda: self.send_command_request_signal.emit("Remote,EFEM"))
        layout.addWidget(self.remote_button, 2, 1)

        self.local_button = QPushButton("本地模式")
        self.local_button.clicked.connect(lambda: self.send_command_request_signal.emit("Local,EFEM"))
        layout.addWidget(self.local_button, 2, 2)

        self.home_efem_button = QPushButton("EFEM 歸位")
        self.home_efem_button.clicked.connect(lambda: self.send_command_request_signal.emit("Home,EFEM"))
        layout.addWidget(self.home_efem_button, 2, 3)

        self.efem_status_group.setLayout(layout)

    def _create_module_tabs(self):
        """建立控制各模組的 Tab 頁面"""
        self.module_tabs = QTabWidget()

        # --- Load Port 1 Tab ---
        lp1_tab = QWidget()
        lp1_layout = QGridLayout(lp1_tab)

        lp1_layout.addWidget(QLabel("狀態:"), 0, 0)
        self.lp1_status_label = QLabel("模式:?, 錯誤:?, Foup:?, Clamp:?, Door:?")
        self.lp1_status_label.setWordWrap(True)
        lp1_layout.addWidget(self.lp1_status_label, 0, 1, 1, 3) # Span 3

        self.lp1_get_status_btn = QPushButton("取得狀態")
        self.lp1_get_status_btn.clicked.connect(lambda: self.send_command_request_signal.emit("GetStatus,Loadport1"))
        lp1_layout.addWidget(self.lp1_get_status_btn, 1, 0)

        self.lp1_load_btn = QPushButton("Load")
        self.lp1_load_btn.clicked.connect(lambda: self.send_command_request_signal.emit("Load,Loadport1"))
        lp1_layout.addWidget(self.lp1_load_btn, 1, 1)

        self.lp1_unload_btn = QPushButton("Unload")
        self.lp1_unload_btn.clicked.connect(lambda: self.send_command_request_signal.emit("Unload,Loadport1"))
        lp1_layout.addWidget(self.lp1_unload_btn, 1, 2)

        self.lp1_map_btn = QPushButton("Map")
        self.lp1_map_btn.clicked.connect(lambda: self.send_command_request_signal.emit("Map,Loadport1"))
        lp1_layout.addWidget(self.lp1_map_btn, 1, 3)

        self.lp1_read_rfid_btn = QPushButton("讀取 RFID")
        self.lp1_read_rfid_btn.clicked.connect(lambda: self.send_command_request_signal.emit("ReadFoupID,Loadport1"))
        lp1_layout.addWidget(self.lp1_read_rfid_btn, 2, 0)

        lp1_layout.addWidget(QLabel("RFID:"), 2, 1)
        self.lp1_rfid_label = QLineEdit("")
        self.lp1_rfid_label.setReadOnly(True)
        lp1_layout.addWidget(self.lp1_rfid_label, 2, 2, 1, 2) # Span 2

        lp1_layout.addWidget(QLabel("Map 結果:"), 3, 0, alignment=Qt.AlignTop)
        self.lp1_map_result_text = QTextEdit("")
        self.lp1_map_result_text.setReadOnly(True)
        self.lp1_map_result_text.setMaximumHeight(60) # 限制高度
        lp1_layout.addWidget(self.lp1_map_result_text, 3, 1, 1, 3) # Span 3

        self.lp1_reset_error_btn = QPushButton("重設錯誤")
        self.lp1_reset_error_btn.clicked.connect(lambda: self.send_command_request_signal.emit("ResetError,Loadport1"))
        lp1_layout.addWidget(self.lp1_reset_error_btn, 4, 0)

        # Add more buttons for Clamp, Unclamp, Dock, Undock, DoorOpen/Close if needed
        lp1_layout.setRowStretch(5, 1) # Push elements up

        self.module_tabs.addTab(lp1_tab, "Load Port 1")

        # --- Robot 1 Tab ---
        rbt1_tab = QWidget()
        rbt1_layout = QGridLayout(rbt1_tab)

        rbt1_layout.addWidget(QLabel("狀態:"), 0, 0)
        self.rbt1_status_label = QLabel("未知")
        rbt1_layout.addWidget(self.rbt1_status_label, 0, 1)
        rbt1_layout.addWidget(QLabel("上臂:"), 0, 2)
        self.rbt1_up_arm_label = QLabel("?")
        rbt1_layout.addWidget(self.rbt1_up_arm_label, 0, 3)
        rbt1_layout.addWidget(QLabel("下臂:"), 0, 4)
        self.rbt1_low_arm_label = QLabel("?")
        rbt1_layout.addWidget(self.rbt1_low_arm_label, 0, 5)

        self.rbt1_get_status_btn = QPushButton("取得狀態")
        self.rbt1_get_status_btn.clicked.connect(lambda: self.send_command_request_signal.emit("GetStatus,Robot1"))
        rbt1_layout.addWidget(self.rbt1_get_status_btn, 1, 0, 1, 2)

        self.rbt1_home_btn = QPushButton("歸位")
        self.rbt1_home_btn.clicked.connect(lambda: self.send_command_request_signal.emit("Home,Robot1"))
        rbt1_layout.addWidget(self.rbt1_home_btn, 1, 2, 1, 2)

        self.rbt1_stop_btn = QPushButton("停止")
        self.rbt1_stop_btn.clicked.connect(lambda: self.send_command_request_signal.emit("Stop,Robot1"))
        rbt1_layout.addWidget(self.rbt1_stop_btn, 1, 4, 1, 2)

        # Smart Get/Put controls
        rbt1_layout.addWidget(QLabel("手臂:"), 2, 0)
        self.rbt1_arm_combo = QComboBox()
        self.rbt1_arm_combo.addItems(["UpArm", "LowArm"])
        rbt1_layout.addWidget(self.rbt1_arm_combo, 2, 1)

        rbt1_layout.addWidget(QLabel("目的地:"), 2, 2)
        self.rbt1_dest_combo = QComboBox()
        # Add destinations dynamically later if needed, start with common ones
        self.rbt1_dest_combo.addItems(["Loadport1", "Loadport2", "Aligner1", "Stage1", "Buffer1"])
        rbt1_layout.addWidget(self.rbt1_dest_combo, 2, 3)

        rbt1_layout.addWidget(QLabel("Slot:"), 2, 4)
        self.rbt1_slot_edit = QLineEdit("1")
        rbt1_layout.addWidget(self.rbt1_slot_edit, 2, 5)

        self.rbt1_smartget_btn = QPushButton("SmartGet")
        self.rbt1_smartget_btn.clicked.connect(self.send_robot_smart_get)
        rbt1_layout.addWidget(self.rbt1_smartget_btn, 3, 0, 1, 3)

        self.rbt1_smartput_btn = QPushButton("SmartPut")
        self.rbt1_smartput_btn.clicked.connect(self.send_robot_smart_put)
        rbt1_layout.addWidget(self.rbt1_smartput_btn, 3, 3, 1, 3)

        # Add more controls (Vacuum, EdgeGrip, CheckPresence etc.) if needed
        rbt1_layout.setRowStretch(4, 1) # Push elements up

        self.module_tabs.addTab(rbt1_tab, "Robot 1")

        # --- Aligner 1 Tab ---
        al1_tab = QWidget()
        al1_layout = QGridLayout(al1_tab)
        # Add Aligner controls here...
        al1_layout.addWidget(QLabel("狀態:"), 0, 0)
        self.al1_status_label = QLabel("未知")
        al1_layout.addWidget(self.al1_status_label, 0, 1)
        al1_layout.addWidget(QLabel("Wafer:"), 0, 2)
        self.al1_wafer_label = QLabel("?")
        al1_layout.addWidget(self.al1_wafer_label, 0, 3)

        self.al1_get_status_btn = QPushButton("取得狀態")
        self.al1_get_status_btn.clicked.connect(lambda: self.send_command_request_signal.emit("GetStatus,Aligner1"))
        al1_layout.addWidget(self.al1_get_status_btn, 1, 0)

        self.al1_home_btn = QPushButton("歸位")
        self.al1_home_btn.clicked.connect(lambda: self.send_command_request_signal.emit("Home,Aligner1"))
        al1_layout.addWidget(self.al1_home_btn, 1, 1)

        self.al1_align_btn = QPushButton("對準")
        self.al1_align_btn.clicked.connect(lambda: self.send_command_request_signal.emit("Alignment,Aligner1"))
        al1_layout.addWidget(self.al1_align_btn, 1, 2)

        self.al1_reset_error_btn = QPushButton("重設錯誤")
        self.al1_reset_error_btn.clicked.connect(lambda: self.send_command_request_signal.emit("ResetError,Aligner1"))
        al1_layout.addWidget(self.al1_reset_error_btn, 1, 3)

        # Add Vacuum, Angle setting etc.
        al1_layout.setRowStretch(2, 1) # Push elements up

        self.module_tabs.addTab(al1_tab, "Aligner 1")

        # --- OCR 1 Tab ---
        ocr1_tab = QWidget()
        ocr1_layout = QGridLayout(ocr1_tab)
        # Add OCR controls here...
        self.ocr1_read_btn = QPushButton("讀取 ID")
        self.ocr1_read_btn.clicked.connect(lambda: self.send_command_request_signal.emit("ReadID,OCR1"))
        ocr1_layout.addWidget(self.ocr1_read_btn, 0, 0)
        ocr1_layout.addWidget(QLabel("結果:"), 0, 1)
        self.ocr1_result_label = QLineEdit("")
        self.ocr1_result_label.setReadOnly(True)
        ocr1_layout.addWidget(self.ocr1_result_label, 0, 2)
        ocr1_layout.setRowStretch(1, 1) # Push elements up
        ocr1_layout.setColumnStretch(2, 1) # Allow result field to expand

        self.module_tabs.addTab(ocr1_tab, "OCR 1")

        # Add more tabs for other Load Ports, Robots, Barcode, FFU etc. as needed

    def _create_flow_control_area(self):
        """建立自動流程控制區域"""
        self.flow_control_group = QGroupBox("自動流程控制")
        layout = QVBoxLayout()
        h_layout = QHBoxLayout() # Layout for buttons

        self.start_flow_button = QPushButton("開始流程")
        self.start_flow_button.setStyleSheet("background-color: lightblue;")
        self.start_flow_button.clicked.connect(self.start_flow)
        h_layout.addWidget(self.start_flow_button)

        self.stop_flow_button = QPushButton("停止流程")
        self.stop_flow_button.setStyleSheet("background-color: lightcoral;")
        self.stop_flow_button.setEnabled(False) # Initially disabled
        self.stop_flow_button.clicked.connect(self.stop_flow)
        h_layout.addWidget(self.stop_flow_button)

        # Pause/Resume button (optional)
        # self.pause_flow_button = QPushButton("暫停流程")
        # self.pause_flow_button.setEnabled(False)
        # self.pause_flow_button.clicked.connect(self.toggle_pause_flow)
        # h_layout.addWidget(self.pause_flow_button)

        layout.addLayout(h_layout)

        self.flow_step_label = QLabel("流程步驟: 待命")
        layout.addWidget(self.flow_step_label)

        # --- Confirmation Area ---
        self.confirmation_group = QGroupBox("等待終端確認")
        confirm_layout = QVBoxLayout()
        self.confirmation_info_label = QLabel("類型: -\n資料: -")
        self.confirmation_info_label.setWordWrap(True)
        confirm_layout.addWidget(self.confirmation_info_label)
        confirm_btn_layout = QHBoxLayout()
        self.confirm_ok_button = QPushButton("資料正確")
        self.confirm_ok_button.setStyleSheet("background-color: lightgreen;")
        self.confirm_ok_button.clicked.connect(lambda: self.confirm_data(True))
        confirm_btn_layout.addWidget(self.confirm_ok_button)
        self.confirm_err_button = QPushButton("資料錯誤")
        self.confirm_err_button.setStyleSheet("background-color: lightcoral;")
        self.confirm_err_button.clicked.connect(lambda: self.confirm_data(False))
        confirm_btn_layout.addWidget(self.confirm_err_button)
        confirm_layout.addLayout(confirm_btn_layout)
        self.confirmation_group.setLayout(confirm_layout)
        self.confirmation_group.setVisible(False) # Initially hidden
        layout.addWidget(self.confirmation_group)

        self.flow_control_group.setLayout(layout)

    def _create_log_area(self):
        """建立日誌顯示區域"""
        self.log_group = QGroupBox("系統日誌")
        layout = QVBoxLayout()
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        self.log_group.setLayout(layout)

    # --- Slot Methods ---

    @pyqtSlot()
    def toggle_connection(self):
        """處理連線/中斷連線按鈕點擊"""
        if self.client_thread and self.client_thread.is_running:
            # --- Disconnect ---
            self.log_message("使用者請求中斷連線...", "orange")
            self.client_thread.stop()
            # Wait for thread to actually finish if needed, but stop() should handle status update
            # self.client_thread.wait() # Blocking, maybe not ideal in GUI thread
            self.client_thread = None
            self.connect_button.setText("連線")
            self.connect_button.setStyleSheet("background-color: lightgreen;")
            self.connection_status_label.setText("未連線")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.set_controls_enabled(False) # 禁用控制項
        else:
            # --- Connect ---
            ip = self.ip_edit.text()
            port_str = self.port_edit.text()
            try:
                port = int(port_str)
                if not (0 < port < 65536):
                    raise ValueError("埠號超出範圍")

                self.connect_button.setText("連線中...")
                self.connect_button.setEnabled(False)
                self.connection_status_label.setText("連線中...")
                self.connection_status_label.setStyleSheet("color: orange; font-weight: bold;")

                # 啟動通訊執行緒
                self.client_thread = EFemClientThread(ip, port)
                # 連接信號
                self.client_thread.connection_status_signal.connect(self.update_connection_status)
                self.client_thread.received_data_signal.connect(self.handle_received_data)
                self.client_thread.log_signal.connect(self.log_message)
                # 連接完成後執行的清理
                self.client_thread.finished.connect(self.on_client_thread_finished)

                self.client_thread.start()

            except ValueError:
                QMessageBox.warning(self, "輸入錯誤", f"無效的埠號: {port_str}")
                self.connection_status_label.setText("錯誤")
                self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            except Exception as e:
                 QMessageBox.critical(self, "連線錯誤", f"建立連線時發生錯誤: {e}")
                 self.connection_status_label.setText("錯誤")
                 self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
                 self.connect_button.setText("連線")
                 self.connect_button.setEnabled(True)


    @pyqtSlot(str)
    def send_command_from_gui(self, command):
        """從 GUI 或流程執行緒發送指令到通訊執行緒"""
        if self.client_thread and self.client_thread.is_running:
            # self.log_message(f"請求發送: {command}", "gray") # Logged by client thread now
            self.client_thread.send_command(command)
        else:
            self.log_message("錯誤: 未連線到 EFEM，無法發送指令", "red")
            # QMessageBox.warning(self, "錯誤", "未連線到 EFEM") # 可能太頻繁

    @pyqtSlot()
    def start_flow(self):
        """啟動自動化流程"""
        if not self.client_thread or not self.client_thread.is_running:
             QMessageBox.warning(self, "錯誤", "請先連線到 EFEM")
             return
        if self.flow_thread and self.flow_thread.isRunning():
            QMessageBox.warning(self, "資訊", "流程已在執行中")
            return

        self.log_message("請求啟動自動流程...", "blue")
        self.flow_thread = FlowControlThread()
        # --- 連接流程執行緒信號 ---
        self.flow_thread.update_step_signal.connect(self.update_flow_step_display)
        self.flow_thread.request_confirmation_signal.connect(self.handle_confirmation_request)
        # 將流程執行緒的發送指令信號連接到主視窗的請求發送信號
        self.flow_thread.send_efem_command_signal.connect(self.send_command_request_signal)
        self.flow_thread.flow_finished_signal.connect(self.handle_flow_finished)
        self.flow_thread.log_signal.connect(self.log_message) # 連接日誌信號
        # 連接完成後清理
        self.flow_thread.finished.connect(self.on_flow_thread_finished)

        self.flow_thread.start()
        # 更新 GUI 狀態
        self.start_flow_button.setEnabled(False)
        self.stop_flow_button.setEnabled(True)
        self.confirmation_group.setVisible(False) # 確保確認區隱藏

    @pyqtSlot()
    def stop_flow(self):
        """停止自動化流程"""
        if self.flow_thread and self.flow_thread.isRunning():
             self.log_message("使用者請求停止自動流程...", "orange")
             self.flow_thread.stop()
             # GUI 更新在 handle_flow_finished 中處理
        else:
             self.log_message("流程未執行", "gray")

    @pyqtSlot(str)
    def update_connection_status(self, status):
        """更新 GUI 上的連線狀態顯示"""
        self.connection_status_label.setText(status)
        if status == "Connected":
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_button.setText("中斷連線")
            self.connect_button.setStyleSheet("background-color: lightcoral;")
            self.connect_button.setEnabled(True)
            self.set_controls_enabled(True) # 啟用控制項
            # 連線成功後自動獲取一次 EFEM 狀態
            self.send_command_request_signal.emit("GetStatus,EFEM")

        elif status == "Disconnected":
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_button.setText("連線")
            self.connect_button.setStyleSheet("background-color: lightgreen;")
            self.connect_button.setEnabled(True)
            self.set_controls_enabled(False) # 禁用控制項
            # 清理狀態顯示
            self.efem_mode_label.setText("未知")
            self.efem_emo_label.setText("未知")
            self.efem_ffu_label.setText("未知")
            self.efem_door_label.setText("未知")
            # 清理模組狀態...

        elif status == "Connecting":
             self.connection_status_label.setStyleSheet("color: orange; font-weight: bold;")
             self.connect_button.setEnabled(False) # 連線中禁用按鈕
             self.set_controls_enabled(False)
        else: # Error
             self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
             self.connect_button.setText("連線")
             self.connect_button.setStyleSheet("background-color: lightgreen;")
             self.connect_button.setEnabled(True)
             self.set_controls_enabled(False)

    @pyqtSlot()
    def on_client_thread_finished(self):
        """通訊執行緒結束時的清理"""
        self.log_message("通訊執行緒已結束.", "gray")
        # 確保 UI 狀態正確 (如果不是正常斷開)
        if self.connection_status_label.text() == "Connected" or self.connection_status_label.text() == "Connecting":
            self.update_connection_status("Disconnected") # 強制更新狀態
        self.client_thread = None # 清除執行緒對象引用


    @pyqtSlot()
    def on_flow_thread_finished(self):
        """流程執行緒結束時的清理"""
        self.log_message("流程執行緒已結束.", "gray")
        self.flow_thread = None # 清除執行緒對象引用
        # 確保按鈕狀態正確
        if not (self.client_thread and self.client_thread.is_running):
             self.start_flow_button.setEnabled(False) # 如果斷線了，開始按鈕還是禁用
        else:
             self.start_flow_button.setEnabled(True)
        self.stop_flow_button.setEnabled(False)
        self.confirmation_group.setVisible(False)


    @pyqtSlot(str)
    def handle_received_data(self, data):
        """處理從通訊執行緒收到的原始資料"""
        # self.log_message(f"處理: {data.strip()}", "gray") # Logged by client thread now
        # 解析資料: 檢查 #Event, OK, Error
        # 注意：EFEM 可能一次發送多個訊息，以 '$' 分隔，ClientThread 已處理拆分
        message = data.strip().rstrip('$') # ClientThread 已經去掉了 '#' 和加上了 '$'，這裡去掉 '$'

        if message.startswith("Event,"):
            self.handle_event(message)
        elif ",OK" in message:
            # 將回應傳遞給流程執行緒 (如果正在執行)
            if self.flow_thread and self.flow_thread.isRunning():
                 self.flow_thread.set_efem_response(message + "$") # 傳回包含結束符的完整訊息
            # 同時更新 GUI 狀態 (如果需要)
            self.update_status_from_response(message + "$")
        elif ",Error," in message:
            self.handle_error(message + "$")
            # 將錯誤回應也傳遞給流程執行緒
            if self.flow_thread and self.flow_thread.isRunning():
                 self.flow_thread.set_efem_response(message + "$")
        elif message.startswith("RAW_DATA:"):
             # 處理無法解碼的原始資料 (如果需要)
             pass
        else:
            # 其他未識別的訊息
             self.log_message(f"收到未識別訊息: {message}", "orange")

    @pyqtSlot(str, str)
    def log_message(self, message, color="black"):
        """將訊息附加到日誌區域"""
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{now}] {message}"

        self.log_edit.moveCursor(QTextCursor.End)
        self.log_edit.setTextColor(QColor(color))
        self.log_edit.insertPlainText(log_entry + "\n")
        self.log_edit.setTextColor(QColor("black")) # 恢復預設顏色
        self.log_edit.ensureCursorVisible() # 自動滾動到底部

    def handle_event(self, event_data):
        """解析事件並更新 GUI"""
        self.log_message(f"事件: {event_data}", "darkgreen")
        parts = event_data.split(',')
        event_type = parts[0] # "Event"
        source = parts[1]     # "EFEM", "Loadport1", "Robot", etc.

        # --- EFEM 事件 ---
        if source == "EFEM":
            if len(parts) >= 3:
                event_name = parts[2]
                if event_name == "Mode":
                    mode = parts[3] if len(parts) > 3 else "未知"
                    self.efem_mode_label.setText(f"{mode}")
                elif event_name == "Power":
                    # Handle Power On/Off event if needed
                    pass
                elif event_name == "Run":
                    self.log_message("EFEM 開始執行...", "darkblue")
                elif event_name == "Idle":
                     self.log_message("EFEM 執行完畢/閒置", "darkblue")
                elif event_name == "Error":
                     self.log_message("EFEM 報告錯誤狀態", "red")
                     # Maybe trigger GetStatus?
                # Add more EFEM events (RepairMode, Vibration, Temp...)

        # --- Loadport 事件 ---
        elif source.startswith("Loadport"):
            lp_name = source # e.g., "Loadport1"
            if len(parts) >= 3:
                event_name = parts[2]
                if event_name == "FoupPlace":
                     self.log_message(f"{lp_name} Foup 放置", "darkmagenta")
                     # 可以觸發 GetStatus 或 ReadFoupID
                     self.send_command_request_signal.emit(f"GetStatus,{lp_name}")
                elif event_name == "FoupRemove":
                     self.log_message(f"{lp_name} Foup 移除", "darkmagenta")
                elif event_name == "PresenceSignal" or event_name == "PlacementSignal":
                    signal_status = parts[3] if len(parts) > 3 else "?"
                    self.log_message(f"{lp_name} {event_name}: {signal_status}", "gray")
                    # 更新對應 Loadport 的狀態顯示 (需要找到對應的標籤)
                elif event_name == "MapResult":
                     map_data = ",".join(parts[3:]) if len(parts) > 3 else "無資料"
                     self.log_message(f"{lp_name} Map 結果事件: {map_data[:30]}...", "darkcyan")
                     # 更新對應 Loadport 的 Map 結果顯示
                     if lp_name == "Loadport1": # 假設更新 LP1
                         self.lp1_map_result_text.setText(map_data)
                # Add more Loadport events (RobotMappingStart/End...)

        # --- Robot 事件 ---
        elif source.startswith("Robot"):
             # 範例: #Event,Robot,[LowArm],[UpArm]$
             if len(parts) == 4:
                 low_arm_status = parts[2]
                 up_arm_status = parts[3]
                 self.log_message(f"{source} 手臂狀態事件: 下={low_arm_status}, 上={up_arm_status}", "darkblue")
                 # 更新 Robot 狀態顯示
                 if source == "Robot1":
                     self.rbt1_low_arm_label.setText(low_arm_status)
                     self.rbt1_up_arm_label.setText(up_arm_status)
             # Add more Robot events (Axis Vibration/Temp/Maintain...)

        # --- Aligner 事件 ---
        elif source.startswith("Aligner"):
             # 範例: #Event,Aligner[n],[Result]$
             if len(parts) == 3:
                 result = parts[2] # Presence/Absence
                 self.log_message(f"{source} Wafer 狀態事件: {result}", "darkblue")
                 # 更新 Aligner 狀態顯示
                 if source == "Aligner1":
                     self.al1_wafer_label.setText(result)
             # Add more Aligner events (Vacuum, CDA...)

        # --- Barcode 事件 ---
        elif source.startswith("Barcode"):
            # 範例: #Event,Barcode[n],[ID]$ (Handheld type)
             if len(parts) == 3:
                 barcode_id = parts[2]
                 self.log_message(f"{source} 手持掃描事件: {barcode_id}", "darkmagenta")
                 # 可能需要顯示在某個地方或傳遞給 Host

        # --- E84 事件 ---
        elif source.endswith("E84"): # e.g., Loadport1E84
            if len(parts) >= 3:
                 e84_event_code = parts[2] # Evt9, Evt10 etc.
                 e84_event_desc = ",".join(parts[3:]) if len(parts) > 3 else e84_event_code
                 self.log_message(f"{source} 事件: {e84_event_desc}", "darkgray")

        # --- Flipper 事件 ---
        elif source.startswith("Flipper"):
             if len(parts) >= 3 and parts[2] == "BatteryVoltage" and parts[3] == "Low":
                 self.log_message(f"警告: {source} 電池電壓低", "orange")

        # --- 其他事件 ---
        else:
            self.log_message(f"收到未處理事件來源: {event_data}", "orange")


    def handle_error(self, error_data):
        """解析錯誤回應並顯示"""
        parts = error_data.strip().rstrip('$').split(',')
        # 格式: Command,Device,Error,[ErrorCode]$
        if len(parts) >= 4 and parts[-2] == "Error":
            error_code = parts[-1].strip()
            command_sent = parts[0]
            device = parts[1]
            error_desc = ERROR_CODES.get(error_code, f"未知錯誤碼 ({error_code})")
            full_error_msg = f"指令錯誤: [{device}] {command_sent} -> {error_desc}"
            self.log_message(full_error_msg, "red")
            # 可以考慮更新對應模組的狀態為錯誤
            # QMessageBox.warning(self, "EFEM 錯誤", full_error_msg) # 可能太頻繁
        else:
            self.log_message(f"收到未解析錯誤回應: {error_data.strip()}", "red")

    def update_status_from_response(self, response_data):
        """根據成功的指令回應更新 GUI 狀態"""
        parts = response_data.strip().rstrip('$').split(',')
        command = parts[0]
        device = parts[1]

        if command == "GetStatus":
            if device == "EFEM" and len(parts) >= 13 and parts[2] == "OK":
                # GetStatus,EFEM,OK,[EMO],[FFU PD],[PosPress],[NegPress],[Ionizer],[LC],[FFU],[Mode],[RobotEn],[Door]$
                # 索引:                3      4         5          6           7        8      9     10       11       12
                emo_status = "觸發" if parts[3] == '0' else "正常"
                ffu_pd_status = "過高" if parts[4] == '0' else "正常"
                # ... 其他狀態解析 ...
                mode = "本地 (Local)" if parts[10] == '0' else "遠端 (Remote)"
                robot_en = "禁用" if parts[11] == '0' else "啟用"
                door = "開啟" if parts[12] == '0' else "關閉"

                self.efem_emo_label.setText(emo_status)
                self.efem_ffu_label.setText(f"FFU PD:{ffu_pd_status}") # 簡化顯示
                self.efem_mode_label.setText(mode)
                self.efem_door_label.setText(door)
                self.log_message(f"EFEM 狀態更新: EMO={emo_status}, Mode={mode}, Door={door}", "darkgray")

            elif device.startswith("Loadport") and len(parts) >= 8 and parts[2] == "OK":
                # GetStatus,Loadport[n],OK,[Mode],[Error],[Foup],[Clamp],[Door]$
                # 索引:                      3      4        5       6        7
                lp_name = device
                mode, error, foup, clamp, door = parts[3:8]
                status_text = f"模式:{mode}, 錯誤:{error}, Foup:{foup}, Clamp:{clamp}, Door:{door}"
                # 更新對應的 Loadport 狀態標籤
                if lp_name == "Loadport1":
                    self.lp1_status_label.setText(status_text)
                # Add elif for Loadport2 etc.
                self.log_message(f"{lp_name} 狀態更新: {status_text}", "darkgray")

            elif device.startswith("Robot") and len(parts) >= 6 and parts[2] == "OK":
                 # GetStatus,Robot[n],OK,[StatusCode],[UpPresence],[LowPresence]$ (S/E Series)
                 # GetStatus,Robot[n],OK,[StatusCode],[UpPresence],[LowPresence]$ (A Series) - StatusCode 不同
                 rbt_name = device
                 status_code = parts[3]
                 up_presence = parts[4]
                 low_presence = parts[5]
                 # 更新對應的 Robot 狀態標籤
                 if rbt_name == "Robot1":
                     self.rbt1_status_label.setText(f"代碼:{status_code}")
                     self.rbt1_up_arm_label.setText(up_presence)
                     self.rbt1_low_arm_label.setText(low_presence)
                 # Add elif for Robot2 etc.
                 self.log_message(f"{rbt_name} 狀態更新: Code={status_code}, Up={up_presence}, Low={low_presence}", "darkgray")

            elif device.startswith("Aligner") and len(parts) >= 6 and parts[2] == "OK":
                 # GetStatus,Aligner[n],OK,[Mode],[WaferPresence],[Status of Vacuum/CDA]$
                 al_name = device
                 mode = parts[3]
                 wafer = parts[4]
                 vac_cda = parts[5] # True/False/Unknown
                 # 更新對應的 Aligner 狀態標籤
                 if al_name == "Aligner1":
                     self.al1_status_label.setText(mode)
                     self.al1_wafer_label.setText(wafer)
                 # Add elif for Aligner2 etc.
                 self.log_message(f"{al_name} 狀態更新: Mode={mode}, Wafer={wafer}, Vac/CDA={vac_cda}", "darkgray")

        elif command == "ReadFoupID" and device.startswith("Loadport") and len(parts) == 4 and parts[2] == "OK":
            lp_name = device
            rfid = parts[3]
            # 更新對應 Loadport 的 RFID 顯示
            if lp_name == "Loadport1":
                self.lp1_rfid_label.setText(rfid)
            self.log_message(f"{lp_name} RFID 讀取成功: {rfid}", "darkcyan")

        elif command == "GetMapResult" and device.startswith("Loadport") and len(parts) >= 4 and parts[2] == "OK":
            lp_name = device
            map_data = ",".join(parts[3:])
             # 更新對應 Loadport 的 Map 結果顯示
            if lp_name == "Loadport1":
                self.lp1_map_result_text.setText(map_data)
            self.log_message(f"{lp_name} Map 結果讀取成功: {map_data[:30]}...", "darkcyan")

        elif command == "ReadID" and device.startswith("OCR") and len(parts) == 4 and parts[2] == "OK":
            ocr_name = device
            ocr_result = parts[3]
            # 更新對應 OCR 的結果顯示
            if ocr_name == "OCR1":
                 self.ocr1_result_label.setText(ocr_result)
            self.log_message(f"{ocr_name} OCR 讀取成功: {ocr_result}", "darkcyan")

        elif command == "GetCurrentMode" and device == "EFEM" and len(parts) == 4 and parts[2] == "OK":
            mode = parts[3]
            self.efem_mode_label.setText(mode)
            self.log_message(f"EFEM 目前模式: {mode}", "darkgray")

        # Add more handlers for other command responses if needed


    @pyqtSlot(str)
    def update_flow_step_display(self, step_description):
        """更新流程步驟顯示標籤"""
        self.flow_step_label.setText(f"流程步驟: {step_description}")
        # self.log_message(f"流程步驟: {step_description}", "blue") # Logged by flow thread

    @pyqtSlot(str, str)
    def handle_confirmation_request(self, confirmation_type, data_to_confirm):
        """顯示等待使用者確認的介面"""
        self.confirmation_info_label.setText(f"類型: {confirmation_type}\n資料: {data_to_confirm}")
        self.confirmation_group.setVisible(True)
        self.log_message(f"流程暫停: 等待使用者確認 {confirmation_type}", "darkorange")

    def confirm_data(self, confirmed_ok):
        """處理使用者點擊確認按鈕"""
        if self.flow_thread and self.flow_thread.isRunning():
            result_text = "正確" if confirmed_ok else "錯誤"
            self.log_message(f"使用者確認資料: {result_text}", "blue")
            self.flow_thread.set_user_confirmation(confirmed_ok)
            self.confirmation_group.setVisible(False) # 隱藏確認區
        else:
             self.log_message("警告: 在非流程執行狀態下收到確認", "orange")

    @pyqtSlot(str)
    def handle_flow_finished(self, status):
        """處理流程結束事件"""
        self.log_message(f"自動流程結束: {status}", "green" if status == "Completed" else "red")
        if self.flow_thread:
             # 確保執行緒對象在自然結束後被清理 (finished 信號會處理)
             pass
        # 更新 GUI 狀態
        if not (self.client_thread and self.client_thread.is_running):
            self.start_flow_button.setEnabled(False) # 如果斷線了，開始按鈕還是禁用
        else:
            self.start_flow_button.setEnabled(True)
        self.stop_flow_button.setEnabled(False)
        self.confirmation_group.setVisible(False) # 確保確認區隱藏
        self.flow_step_label.setText(f"流程步驟: 結束 ({status})")

    def set_controls_enabled(self, enabled):
        """啟用或禁用需要連線才能操作的控制項"""
        # EFEM 控制
        self.get_efem_status_button.setEnabled(enabled)
        self.remote_button.setEnabled(enabled)
        self.local_button.setEnabled(enabled)
        self.home_efem_button.setEnabled(enabled)
        # 流程控制
        self.start_flow_button.setEnabled(enabled)
        # 如果正在執行流程，停止按鈕的狀態由流程本身控制
        if not (self.flow_thread and self.flow_thread.isRunning()):
             self.stop_flow_button.setEnabled(False)
        # 模組控制 (Tabs)
        self.module_tabs.setEnabled(enabled)
        # 可以更細緻地啟用/禁用 Tab 內的按鈕
        self.lp1_get_status_btn.setEnabled(enabled)
        self.lp1_load_btn.setEnabled(enabled)
        self.lp1_unload_btn.setEnabled(enabled)
        self.lp1_map_btn.setEnabled(enabled)
        self.lp1_read_rfid_btn.setEnabled(enabled)
        self.lp1_reset_error_btn.setEnabled(enabled)
        # ... 其他模組的按鈕 ...
        self.rbt1_get_status_btn.setEnabled(enabled)
        self.rbt1_home_btn.setEnabled(enabled)
        self.rbt1_stop_btn.setEnabled(enabled)
        self.rbt1_smartget_btn.setEnabled(enabled)
        self.rbt1_smartput_btn.setEnabled(enabled)
        # ...
        self.al1_get_status_btn.setEnabled(enabled)
        self.al1_home_btn.setEnabled(enabled)
        self.al1_align_btn.setEnabled(enabled)
        self.al1_reset_error_btn.setEnabled(enabled)
        # ...
        self.ocr1_read_btn.setEnabled(enabled)


    def send_robot_smart_get(self):
        """發送 SmartGet 指令"""
        arm = self.rbt1_arm_combo.currentText()
        dest = self.rbt1_dest_combo.currentText()
        slot = self.rbt1_slot_edit.text()
        if not slot.isdigit():
            QMessageBox.warning(self, "輸入錯誤", "Slot 必須是數字")
            return
        command = f"SmartGet,Robot1,{arm},{dest},{slot}"
        self.send_command_request_signal.emit(command)

    def send_robot_smart_put(self):
        """發送 SmartPut 指令"""
        arm = self.rbt1_arm_combo.currentText()
        dest = self.rbt1_dest_combo.currentText()
        slot = self.rbt1_slot_edit.text()
        if not slot.isdigit():
            QMessageBox.warning(self, "輸入錯誤", "Slot 必須是數字")
            return
        command = f"SmartPut,Robot1,{arm},{dest},{slot}"
        self.send_command_request_signal.emit(command)


    def closeEvent(self, event):
        """關閉視窗前的清理"""
        self.log_message("關閉應用程式...", "gray")
        # 停止執行緒
        if self.flow_thread and self.flow_thread.isRunning():
            self.flow_thread.stop()
            self.flow_thread.wait(500) # 等待最多 0.5 秒
        if self.client_thread and self.client_thread.is_running:
            self.client_thread.stop()
            self.client_thread.wait(500) # 等待最多 0.5 秒

        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 設定應用程式樣式 (可選)
    # app.setStyle('Fusion')
    mainWin = EFemApp()
    mainWin.show()
    sys.exit(app.exec_())

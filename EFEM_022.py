#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import socket
import threading
import time
import queue
from datetime import datetime
import json # 用於美化字典輸出

# 確保已安裝 PyQt5: pip install PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QGridLayout, QGroupBox,
                             QMessageBox, QComboBox, QTabWidget, QSplitter, QFrame,
                             QListWidget, QListWidgetItem)
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, Qt, QRect, QPoint
from PyQt5.QtGui import QTextCursor, QColor, QFont, QPalette

# --- 常數 ---
DEFAULT_IP = "192.168.1.1"
DEFAULT_PORT = 6000
BUFFER_SIZE = 4096
CONNECT_TIMEOUT = 5  # 連線超時 (秒)
COMMAND_TIMEOUT = 25 # 指令回應超時 (秒)
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

# --- 流程步驟描述 ---
# (與 v1.12 版本相同，省略)
NORMAL_FLOW_STEPS = {
    1: "終端 -> UI: 準備送貨", 2: "UI -> EFEM: 接收貨命令 (GetStatus)",
    3: "EFEM -> UI: 接收貨完成回覆 (GetStatus OK)", 4: "UI -> 終端: 收貨完成",
    5: "UI -> EFEM: 讀取RFID命令 (ReadFoupID)", 6: "EFEM -> UI: 回覆讀取RFID命令",
    7: "UI -> 終端: RFID資料核對", 8: "終端 -> UI: RFID資料正確",
    9: "UI -> EFEM: 開門命令 (Load)", 10: "EFEM -> UI: 回覆開門完成",
    11: "UI -> EFEM: Slot Mapping (GetMapResult)", 12: "EFEM -> UI: Slot Mapping完成",
    13: "UI -> 終端: 層數資料核對", 14: "終端 -> UI: 層數資料正確",
    15: "UI -> EFEM: 取LOADPORT1第{slot}層 (SmartGet)", 16: "EFEM -> UI: 取完WAFER片",
    17: "UI -> EFEM: 送片至ALIGNER (SmartPut)", 18: "EFEM -> UI: 放至ALIGNER完成",
    19: "UI -> EFEM: ALIGNER進行Align (Alignment)", 20: "EFEM -> UI: ALIGNER進行Align完成",
    21: "UI -> EFEM: 讀取OCR (ReadID)", 22: "EFEM -> UI: 讀取OCR並回傳給UI",
    23: "UI -> 終端: OCR核對", 24: "終端 -> UI: OCR正確",
    25: "UI -> EFEM: 從ALIGNER取片 (SmartGet)", 26: "EFEM -> UI: 從ALIGNER取片完成",
    27: "UI -> EFEM: 放片至STAGE (SmartPut)", 28: "EFEM -> UI: 放片至STAGE完成",
    29: "UI -> EFEM: 從STAGE取回 (SmartGet)", 30: "EFEM -> UI: 從STAGE取回完成",
    31: "UI -> EFEM: 放至Buffer (SmartPut)", 32: "EFEM -> UI: 放至Buffer完成 / 檢查循環",
    33: "UI -> EFEM: 關門命令 (Unload)", 34: "EFEM -> UI: 回覆關門完成",
    35: "UI -> 終端: 準備收貨", 36: "UI -> EFEM: 接送貨命令 (GetStatus)",
    37: "EFEM -> UI: 接送貨完成回覆", 38: "終端 -> UI: 收貨完成",
    0: "流程待命", 99: "流程完成", -1: "流程錯誤中止", -2: "流程使用者中止"
}

RECOVERY_FLOW_STEPS = {
    101: "開始異常恢復流程", 102: "檢查是否為 Remote 模式",
    103: "執行 Load Port1 狀態檢查 (GetMapResult)", 104: "等待 Map 結果回覆",
    105: "找出 Load Port1 空 Slot", 106: "執行機械臂狀態確認 (CheckWaferPresence)",
    107: "等待機械臂狀態回覆", 108: "檢查手臂是否有 Wafer",
    109: "手臂有料片，放至 Load Port1 空 Slot (SmartPut)", 110: "等待手臂放片完成",
    111: "執行 Aligner 狀態確認 (CheckWaferPresence)", 112: "等待 Aligner 狀態回覆",
    113: "檢查 Aligner 是否有 Wafer", 114: "Aligner 有料片，從 Aligner 取片 (SmartGet)",
    115: "等待 Aligner 取片完成", 116: "將 Aligner 料片放至 Load Port1 空 Slot (SmartPut)",
    117: "等待放片完成", 118: "重新檢查所有設備狀態 (GetStatus)",
    119: "等待狀態回覆", 120: "評估恢復結果", 121: "恢復成功，亮綠燈",
    122: "恢復成功，執行 EFEM Home", 123: "等待 Home 完成",
    124: "恢復失敗，亮紅燈閃爍+警報", 199: "恢復流程完成",
    -101: "恢復流程錯誤中止", -102: "恢復流程使用者中止"
}
ALL_STEP_DESCRIPTIONS = {**NORMAL_FLOW_STEPS, **RECOVERY_FLOW_STEPS}

def get_step_description(step_num, **kwargs):
    """獲取步驟描述，支持格式化"""
    desc_template = ALL_STEP_DESCRIPTIONS.get(step_num, f"未知步驟 {step_num}")
    try:
        return desc_template.format(**kwargs)
    except KeyError:
        return desc_template

# --- 網路通訊執行緒 (EFemClientThread) ---
# (省略...)
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

# --- 流程控制執行緒 (FlowControlThread) ---
# (省略...)
class FlowControlThread(QThread):
    """管理【正常】自動化流程的狀態機"""
    update_step_signal = pyqtSignal(int)
    request_confirmation_signal = pyqtSignal(str, str)
    send_efem_command_signal = pyqtSignal(str)
    flow_finished_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str, str)

    def __init__(self, num_loadports=1, num_aligners=1, num_ocrs=1):
        super().__init__()
        self.is_running = False
        self.current_pdf_step = 0
        self.efem_response_queue = queue.Queue(maxsize=1)
        self.user_confirmation_queue = queue.Queue(maxsize=1)
        self.num_loadports = num_loadports
        self.current_slot = 1
        self.max_slots = 25
        self.map_result_data = ""
        # 不再需要 self.step_descriptions

    # set_efem_response, set_user_confirmation, _wait_for_efem_response,
    # _wait_for_user_confirmation, _send_cmd_and_wait, _request_user_confirm,
    # run, stop, parse_*, check_slot_has_wafer
    # (邏輯與 v1.11 基本相同，但 run 方法中的步驟編號和描述獲取使用全局函數，
    #  且不再發送 visual_update_signal，此處省略以節省空間)
    def set_efem_response(self, data):
        """從主執行緒接收 EFEM 回應"""
        try:
            while not self.efem_response_queue.empty(): self.efem_response_queue.get_nowait()
            self.efem_response_queue.put(data, block=False)
        except queue.Full:
            self.log_signal.emit("警告: EFEM 回應佇列已滿，可能遺失回應", "orange")

    def set_user_confirmation(self, result):
        """從主執行緒接收使用者確認結果"""
        try:
            while not self.user_confirmation_queue.empty(): self.user_confirmation_queue.get_nowait()
            self.user_confirmation_queue.put(result, block=False)
        except queue.Full:
             self.log_signal.emit("警告: 使用者確認佇列已滿", "orange")

    def _wait_for_efem_response(self, timeout=COMMAND_TIMEOUT):
        """等待 EFEM 回應 (檢查停止標誌)"""
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            if not self.is_running: return "STOP_REQUESTED"
            try:
                return self.efem_response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
        return None # 超時

    def _wait_for_user_confirmation(self, timeout=CONFIRMATION_TIMEOUT):
        """等待使用者確認 (檢查停止標誌)"""
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
             if not self.is_running: return "STOP_REQUESTED"
             try:
                 return self.user_confirmation_queue.get(timeout=0.1)
             except queue.Empty:
                 continue
        return None # 超時

    def _send_cmd_and_wait(self, command, pdf_step_num_action, **kwargs):
        """發送指令並等待 'OK' 回應的輔助函數，使用 PDF 動作步驟編號"""
        if not self.is_running: return None, "Stopped"

        self.current_pdf_step = pdf_step_num_action
        step_desc = get_step_description(pdf_step_num_action, **kwargs) # 使用全局函數
        self.update_step_signal.emit(pdf_step_num_action) # 高亮動作步驟
        self.log_signal.emit(f"步驟 {pdf_step_num_action}: {step_desc} (發送: {command})", "darkMagenta")
        self.send_efem_command_signal.emit(command)

        # 更新狀態為等待回應 (高亮等待步驟)
        pdf_step_num_wait = pdf_step_num_action + 1
        wait_desc = get_step_description(pdf_step_num_wait, **kwargs) # 使用全局函數
        if "等待" in wait_desc or "回覆" in wait_desc: # 檢查描述是否為等待/回覆類型
             self.update_step_signal.emit(pdf_step_num_wait) # 高亮等待步驟
             self.log_signal.emit(f"步驟 {pdf_step_num_wait}: {wait_desc}", "darkMagenta")

        response = self._wait_for_efem_response()

        if response == "STOP_REQUESTED":
            self.log_signal.emit(f"指令 '{command}' 在等待回應時被中止", "orange")
            return None, "Stopped"
        if response is None:
            self.log_signal.emit(f"錯誤: 等待 '{command}' 回應超時 ({COMMAND_TIMEOUT}秒)", "red")
            return None, "Timeout"
        if ",OK" in response:
             self.log_signal.emit(f"指令 '{command}' 成功: {response.strip()}", "green")
             return response, "OK"
        elif ",Error," in response:
            self.log_signal.emit(f"錯誤: 指令 '{command}' 收到錯誤回應: {response.strip()}", "red")
            return None, "EFEM Error"
        else:
            self.log_signal.emit(f"警告: 指令 '{command}' 收到非 OK 回應: {response.strip()}", "orange")
            return None, "Not OK"

    def _request_user_confirm(self, confirm_type, data, pdf_step_num_request, **kwargs):
        """請求使用者確認的輔助函數，使用 PDF 請求步驟編號"""
        if not self.is_running: return False, "Stopped"

        self.current_pdf_step = pdf_step_num_request
        step_desc = get_step_description(pdf_step_num_request, **kwargs) # 使用全局函數
        self.update_step_signal.emit(pdf_step_num_request) # 高亮請求步驟
        self.log_signal.emit(f"步驟 {pdf_step_num_request}: {step_desc} ({confirm_type}: {data})", "darkMagenta")
        self.request_confirmation_signal.emit(confirm_type, data)

        # 更新狀態為等待使用者回應 (高亮等待步驟)
        pdf_step_num_wait = pdf_step_num_request + 1
        wait_desc = get_step_description(pdf_step_num_wait, **kwargs) # 使用全局函數
        if "等待" in wait_desc or "正確" in wait_desc: # 檢查描述是否為等待/確認類型
             self.update_step_signal.emit(pdf_step_num_wait) # 高亮等待步驟
             self.log_signal.emit(f"步驟 {pdf_step_num_wait}: {wait_desc}", "darkMagenta")

        confirmation = self._wait_for_user_confirmation()

        if confirmation == "STOP_REQUESTED": return False, "Stopped"
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
        """執行【正常】流程狀態機"""
        self.is_running = True
        self.current_slot = 1
        error_occurred = False
        final_status_code = 0 # 初始狀態碼

        try:
            self.log_signal.emit("自動流程啟動...", "green")
            self.update_step_signal.emit(0) # 顯示待命

            # PDF 步驟 5: 讀取RFID命令 (ReadFoupID)
            response, status = self._send_cmd_and_wait("ReadFoupID,Loadport1", 5)
            if status == "OK":
                rfid = self.parse_rfid(response)
                # PDF 步驟 7: RFID資料核對
                confirmed, confirm_status = self._request_user_confirm("RFID", rfid, 7)
                if not confirmed: raise RuntimeError(f"步驟 7 使用者拒絕或超時: {confirm_status}")
            else:
                raise RuntimeError(f"步驟 5 未收到 OK: {status}")

            # PDF 步驟 9: 開門命令 (Load)
            _, status = self._send_cmd_and_wait("Load,Loadport1", 9)
            if status != "OK": raise RuntimeError(f"步驟 9 未收到 OK: {status}")

            # PDF 步驟 11: Slot Mapping (GetMapResult)
            response, status = self._send_cmd_and_wait("GetMapResult,Loadport1", 11)
            if status == "OK":
                 self.map_result_data = self.parse_map_result(response)
                 # PDF 步驟 13: 層數資料核對
                 display_map = self.map_result_data[:50] + "..." if len(self.map_result_data) > 50 else self.map_result_data
                 confirmed, confirm_status = self._request_user_confirm("Map Result", display_map, 13)
                 if not confirmed: raise RuntimeError(f"步驟 13 使用者拒絕或超時: {confirm_status}")
            else:
                 raise RuntimeError(f"步驟 11 未收到 OK: {status}")

            # --- Wafer 處理循環 ---
            while self.current_slot <= self.max_slots:
                if not self.is_running: raise StopIteration("流程中止")

                has_wafer = self.check_slot_has_wafer(self.map_result_data, self.current_slot)
                if not has_wafer:
                    self.log_signal.emit(f"流程: Slot {self.current_slot} 無 Wafer，跳過", "gray")
                    self.current_slot += 1
                    continue

                self.log_signal.emit(f"流程: 開始處理 Slot {self.current_slot}", "blue")

                # PDF 步驟 15: 取LOADPORT1第{slot}層
                get_cmd = f"SmartGet,Robot1,UpArm,Loadport1,{self.current_slot}"
                _, status = self._send_cmd_and_wait(get_cmd, 15, slot=self.current_slot)
                if status != "OK": raise RuntimeError(f"步驟 15 未收到 OK: {status}")

                # PDF 步驟 17: 送片至ALIGNER
                put_cmd = "SmartPut,Robot1,UpArm,Aligner1,1"
                _, status = self._send_cmd_and_wait(put_cmd, 17)
                if status != "OK": raise RuntimeError(f"步驟 17 未收到 OK: {status}")

                # PDF 步驟 19: ALIGNER進行Align
                _, status = self._send_cmd_and_wait("Alignment,Aligner1", 19)
                if status != "OK": raise RuntimeError(f"步驟 19 未收到 OK: {status}")

                # PDF 步驟 21: 讀取OCR
                response, status = self._send_cmd_and_wait("ReadID,OCR1", 21)
                if status == "OK":
                    ocr_id = self.parse_ocr_result(response)
                    # PDF 步驟 23: OCR核對
                    confirmed, confirm_status = self._request_user_confirm("OCR", ocr_id, 23)
                    if not confirmed: raise RuntimeError(f"步驟 23 使用者拒絕或超時: {confirm_status}")
                else:
                     raise RuntimeError(f"步驟 21 未收到 OK: {status}")

                # PDF 步驟 25: 從ALIGNER取片
                get_cmd = "SmartGet,Robot1,UpArm,Aligner1,1"
                _, status = self._send_cmd_and_wait(get_cmd, 25)
                if status != "OK": raise RuntimeError(f"步驟 25 未收到 OK: {status}")

                # PDF 步驟 27: 放片至STAGE
                put_cmd = "SmartPut,Robot1,UpArm,Stage1,1"
                _, status = self._send_cmd_and_wait(put_cmd, 27)
                if status != "OK": raise RuntimeError(f"步驟 27 未收到 OK: {status}")

                self.log_signal.emit(f"流程: Slot {self.current_slot} 處理完成", "green")
                self.current_slot += 1

            # --- 循環結束 ---
            self.update_step_signal.emit(32) # 更新到檢查/準備 Unload 步驟

            # PDF 步驟 33: 關門命令 (Unload)
            _, status = self._send_cmd_and_wait("Unload,Loadport1", 33)
            if status != "OK": raise RuntimeError(f"步驟 33 未收到 OK: {status}")

            final_status_code = 99 # 完成狀態碼

        except StopIteration as e:
            final_status_code = -2 # 使用者中止
            self.log_signal.emit(f"流程已中止: {e}", "orange")
        except RuntimeError as e:
            final_status_code = -1 # 錯誤中止
            self.log_signal.emit(f"流程錯誤中止: {e}", "red")
            error_occurred = True
        except Exception as e:
             final_status_code = -1 # 未預期錯誤
             self.log_signal.emit(f"流程發生未預期錯誤: {e}", "red")
             error_occurred = True
        finally:
            self.is_running = False
            final_desc = get_step_description(final_status_code) # 使用全局函數
            self.update_step_signal.emit(final_status_code) # 發送最終狀態碼
            self.flow_finished_signal.emit(final_status_code) # 發送最終狀態碼
            self.log_signal.emit(f"【正常流程】結束 ({final_desc}).", "green" if not error_occurred else "red")


    def stop(self):
        """停止流程執行"""
        if self.is_running:
            self.log_signal.emit("正在中止自動流程...", "orange")
            self.is_running = False
            try: self.efem_response_queue.put_nowait("STOP_REQUESTED")
            except queue.Full: pass
            try: self.user_confirmation_queue.put_nowait(False)
            except queue.Full: pass

    def parse_rfid(self, response):
        """從 ReadFoupID 回應中解析 RFID"""
        parts = response.strip().rstrip('$').split(',')
        if len(parts) == 4 and parts[2] == "OK":
            return parts[3]
        return "解析錯誤"

    def parse_map_result(self, response):
        """從 GetMapResult 回應中解析 Map Data"""
        parts = response.strip().rstrip('$').split(',')
        if len(parts) >= 4 and parts[2] == "OK":
            return ",".join(parts[3:])
        return "解析錯誤"

    def parse_ocr_result(self, response):
        """從 ReadID,OCR 回應中解析 OCR 結果"""
        parts = response.strip().rstrip('$').split(',')
        if len(parts) == 4 and parts[2] == "OK":
            return parts[3]
        return "解析錯誤"

    def check_slot_has_wafer(self, map_data, slot_index):
        """檢查指定 slot 是否有 wafer"""
        if not map_data or map_data == "解析錯誤":
            self.log_signal.emit(f"警告: 無法檢查 Slot {slot_index}，Map 資料無效", "orange")
            return False
        slots = map_data.split(',')
        if len(slots) == self.max_slots:
            map_index = self.max_slots - slot_index
            if 0 <= map_index < self.max_slots:
                return slots[map_index] in ['1', '2', '3', '4', '5']
            else:
                 self.log_signal.emit(f"警告: Slot 索引 {slot_index} 計算錯誤", "orange")
                 return False
        else:
             self.log_signal.emit(f"警告: Map 資料長度 {len(slots)} 與預期 {self.max_slots} 不符", "orange")
             return False

# --- 新增：恢復流程執行緒 ---
class RecoveryFlowThread(QThread):
    """管理【異常恢復】流程的狀態機"""
    update_step_signal = pyqtSignal(int)       # 傳送恢復流程步驟編號 (101+)
    send_efem_command_signal = pyqtSignal(str) # 發送指令到 EFEM
    flow_finished_signal = pyqtSignal(int)     # 傳送最終狀態碼 (199=完成, -101=錯誤, -102=中止)
    log_signal = pyqtSignal(str, str)          # (訊息, 顏色)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.current_pdf_step = 101 # 恢復流程起始步驟
        self.efem_response_queue = queue.Queue(maxsize=1)
        self.empty_slots_lp1 = [] # 儲存 Load Port 1 的空位

    # set_efem_response, _wait_for_efem_response, stop 方法與 FlowControlThread 類似
    def set_efem_response(self, data):
        try:
            while not self.efem_response_queue.empty(): self.efem_response_queue.get_nowait()
            self.efem_response_queue.put(data, block=False)
        except queue.Full:
            self.log_signal.emit("警告: (恢復流程) EFEM 回應佇列已滿", "orange")

    def _wait_for_efem_response(self, timeout=COMMAND_TIMEOUT):
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            if not self.is_running: return "STOP_REQUESTED"
            try:
                return self.efem_response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
        return None # 超時

    def _send_cmd_and_wait(self, command, pdf_step_num_action, **kwargs):
        """(恢復流程) 發送指令並等待 'OK' 回應"""
        if not self.is_running: return None, "Stopped"

        self.current_pdf_step = pdf_step_num_action
        step_desc = get_step_description(pdf_step_num_action, **kwargs) # 使用全局函數
        self.update_step_signal.emit(pdf_step_num_action) # 高亮動作步驟
        self.log_signal.emit(f"(恢復)步驟 {pdf_step_num_action}: {step_desc} (發送: {command})", "darkCyan")
        self.send_efem_command_signal.emit(command)

        # 更新狀態為等待回應 (高亮等待步驟)
        pdf_step_num_wait = pdf_step_num_action + 1
        wait_desc = get_step_description(pdf_step_num_wait, **kwargs)
        if "等待" in wait_desc or "回覆" in wait_desc:
             self.update_step_signal.emit(pdf_step_num_wait)
             self.log_signal.emit(f"(恢復)步驟 {pdf_step_num_wait}: {wait_desc}", "darkCyan")

        response = self._wait_for_efem_response()

        if response == "STOP_REQUESTED":
            self.log_signal.emit(f"(恢復)指令 '{command}' 在等待回應時被中止", "orange")
            return None, "Stopped"
        if response is None:
            self.log_signal.emit(f"(恢復)錯誤: 等待 '{command}' 回應超時 ({COMMAND_TIMEOUT}秒)", "red")
            return None, "Timeout"
        if ",OK" in response:
             self.log_signal.emit(f"(恢復)指令 '{command}' 成功: {response.strip()}", "green")
             return response, "OK"
        elif ",Error," in response:
            self.log_signal.emit(f"(恢復)錯誤: 指令 '{command}' 收到錯誤回應: {response.strip()}", "red")
            return None, "EFEM Error"
        else:
            self.log_signal.emit(f"(恢復)警告: 指令 '{command}' 收到非 OK 回應: {response.strip()}", "orange")
            return None, "Not OK"

    def find_empty_slots(self, map_data):
        """從 Map Data 找出空 Slot 列表"""
        slots = []
        if map_data and map_data != "解析錯誤":
            map_list = map_data.split(',')
            if len(map_list) == 25: # Assuming 25 slots
                for i in range(25):
                    slot_num = 25 - i
                    if map_list[i] == '0': # 0 代表 Absence
                        slots.append(slot_num)
        return slots

    def run(self):
        """執行【恢復】流程狀態機"""
        self.is_running = True
        error_occurred = False
        final_status_code = 101 # 恢復流程起始狀態碼

        try:
            self.log_signal.emit("啟動異常恢復流程...", "blue")
            self.update_step_signal.emit(101)

            # 步驟 102: 檢查 Remote 模式 (假定已在 Remote 模式)
            self.update_step_signal.emit(102)
            # 實際應使用 GetCurrentMode 檢查，此處簡化
            self.log_signal.emit("(恢復)步驟 102: 假設已在 Remote 模式", "gray")
            time.sleep(0.5)

            # 步驟 103: 執行 Load Port1 狀態檢查 (GetMapResult)
            map_response, status = self._send_cmd_and_wait("GetMapResult,Loadport1", 103)
            if status != "OK": raise RuntimeError(f"步驟 103 未收到 OK: {status}")

            # 步驟 105: 找出 Load Port1 空 Slot
            self.update_step_signal.emit(105)
            lp1_map_data = FlowControlThread.parse_map_result(self, map_response) # 借用解析函數
            self.empty_slots_lp1 = self.find_empty_slots(lp1_map_data)
            self.log_signal.emit(f"Load Port 1 空 Slot: {self.empty_slots_lp1}", "gray")
            # 注意：如果沒有空位，後續放片會失敗

            # 步驟 106: 執行機械臂狀態確認 (CheckWaferPresence)
            robot_presence_response, status = self._send_cmd_and_wait("CheckWaferPresence,Robot1", 106)
            if status != "OK": raise RuntimeError(f"步驟 106 未收到 OK: {status}")

            # 步驟 108: 檢查手臂是否有 Wafer
            self.update_step_signal.emit(108)
            robot_has_wafer = False
            arm_with_wafer = None
            parts = robot_presence_response.strip().rstrip('$').split(',')
            if len(parts) == 5 and parts[2] == "OK":
                if parts[3] == 'Presence' or parts[4] == 'Presence':
                    robot_has_wafer = True
                    arm_with_wafer = 'UpArm' if parts[4] == 'Presence' else 'LowArm' # 假設優先檢查上臂
                    self.log_signal.emit(f"檢測到機械臂 {arm_with_wafer} 上有 Wafer", "orange")

            if robot_has_wafer:
                if not self.empty_slots_lp1:
                    raise RuntimeError("機械臂上有 Wafer，但 Load Port 1 無空位可放")
                # 步驟 109: 放至 Load Port1 空 Slot
                target_slot = self.empty_slots_lp1.pop(0) # 取第一個空位
                put_cmd = f"SmartPut,Robot1,{arm_with_wafer},Loadport1,{target_slot}"
                _, status = self._send_cmd_and_wait(put_cmd, 109)
                if status != "OK": raise RuntimeError(f"步驟 109 未收到 OK: {status}")

            # 步驟 111: 執行 Aligner 狀態確認
            aligner_presence_response, status = self._send_cmd_and_wait("CheckWaferPresence,Aligner1", 111)
            if status != "OK": raise RuntimeError(f"步驟 111 未收到 OK: {status}")

            # 步驟 113: 檢查 Aligner 是否有 Wafer
            self.update_step_signal.emit(113)
            aligner_has_wafer = False
            parts = aligner_presence_response.strip().rstrip('$').split(',')
            if len(parts) == 4 and parts[2] == "OK" and parts[3] == 'Presence':
                 aligner_has_wafer = True
                 self.log_signal.emit("檢測到 Aligner 上有 Wafer", "orange")

            if aligner_has_wafer:
                # 步驟 114: 從 Aligner 取片 (假設用 UpArm)
                get_cmd = "SmartGet,Robot1,UpArm,Aligner1,1"
                _, status = self._send_cmd_and_wait(get_cmd, 114)
                if status != "OK": raise RuntimeError(f"步驟 114 未收到 OK: {status}")

                if not self.empty_slots_lp1:
                    raise RuntimeError("從 Aligner 取回 Wafer，但 Load Port 1 無空位可放")
                # 步驟 116: 放至 Load Port1 空 Slot
                target_slot = self.empty_slots_lp1.pop(0)
                put_cmd = f"SmartPut,Robot1,UpArm,Loadport1,{target_slot}"
                _, status = self._send_cmd_and_wait(put_cmd, 116)
                if status != "OK": raise RuntimeError(f"步驟 116 未收到 OK: {status}")

            # B. 最終確認階段
            # 步驟 118: 重新檢查所有設備狀態 (簡化，實際應檢查更多)
            self.update_step_signal.emit(118)
            final_robot_presence, status_r = self._send_cmd_and_wait("CheckWaferPresence,Robot1", 118)
            final_aligner_presence, status_a = self._send_cmd_and_wait("CheckWaferPresence,Aligner1", 118) # 重複步驟號以檢查
            if status_r != "OK" or status_a != "OK":
                 self.log_signal.emit("警告: 恢復後重新檢查狀態失敗", "orange")
                 recovery_successful = False # 狀態未知，視為失敗
            else:
                # 步驟 120: 評估恢復結果
                self.update_step_signal.emit(120)
                recovery_successful = True # 初始假設成功
                parts_r = final_robot_presence.strip().rstrip('$').split(',')
                if len(parts_r) == 5 and parts_r[2] == "OK" and (parts_r[3] == 'Presence' or parts_r[4] == 'Presence'):
                    recovery_successful = False
                    self.log_signal.emit("恢復評估: 機械臂上仍有料片", "red")
                parts_a = final_aligner_presence.strip().rstrip('$').split(',')
                if len(parts_a) == 4 and parts_a[2] == "OK" and parts_a[3] == 'Presence':
                    recovery_successful = False
                    self.log_signal.emit("恢復評估: Aligner 上仍有料片", "red")

            if recovery_successful:
                # 步驟 121: 亮綠燈
                self.update_step_signal.emit(121)
                self.send_efem_command_signal.emit("SignalTower,EFEM,Green,On")
                time.sleep(0.5)
                # 步驟 122: 執行 EFEM Home
                _, status = self._send_cmd_and_wait("Home,EFEM", 122)
                if status != "OK":
                    self.log_signal.emit("警告: 恢復後執行 Home 指令失敗", "orange")
                    # 根據需求，Home 失敗也可能算恢復失敗
                    # recovery_successful = False
                    # raise RuntimeError("恢復後 Home 失敗")
                final_status_code = 199 # 恢復完成
            else:
                 # 步驟 124: 亮紅燈閃爍+警報
                 self.update_step_signal.emit(124)
                 self.send_efem_command_signal.emit("SignalTower,EFEM,Red,Flash")
                 # self.send_efem_command_signal.emit("SetBuzzer,EFEM,1,On") # 根據實際 API
                 raise RuntimeError("異常恢復失敗 (設備上仍有料片或狀態檢查失敗)")

        except StopIteration as e:
            final_status_code = -102 # 使用者中止
            self.log_signal.emit(f"(恢復)流程已中止: {e}", "orange")
        except RuntimeError as e:
            final_status_code = -101 # 錯誤中止
            self.log_signal.emit(f"(恢復)流程錯誤中止: {e}", "red")
            error_occurred = True
            # 觸發失敗狀態 (紅燈+警報)
            try:
                self.update_step_signal.emit(124)
                self.send_efem_command_signal.emit("SignalTower,EFEM,Red,Flash")
            except Exception as e_sig:
                self.log_signal.emit(f"(恢復)設置失敗信號時出錯: {e_sig}", "red")

        except Exception as e:
             final_status_code = -101 # 未預期錯誤
             self.log_signal.emit(f"(恢復)流程發生未預期錯誤: {e}", "red")
             error_occurred = True
             try:
                 self.update_step_signal.emit(124)
                 self.send_efem_command_signal.emit("SignalTower,EFEM,Red,Flash")
             except Exception as e_sig:
                 self.log_signal.emit(f"(恢復)設置失敗信號時出錯: {e_sig}", "red")
        finally:
            self.is_running = False
            final_desc = get_step_description(final_status_code) # 使用全局函數
            self.update_step_signal.emit(final_status_code) # 發送最終狀態碼
            self.flow_finished_signal.emit(final_status_code) # 發送最終狀態碼
            self.log_signal.emit(f"【恢復流程】結束 ({final_desc}).", "green" if not error_occurred else "red")


    def stop(self):
        """停止恢復流程執行"""
        if self.is_running:
            self.log_signal.emit("正在中止恢復流程...", "orange")
            self.is_running = False
            try: self.efem_response_queue.put_nowait("STOP_REQUESTED")
            except queue.Full: pass


# --- 主 GUI 視窗 (EFemApp) ---
class EFemApp(QMainWindow):
    """應用程式主視窗"""
    send_command_request_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("EFEM GUI 控制器 v1.12 (含恢復流程 800x600)") # 更新版本號
        self.setGeometry(50, 50, 800, 600) # 確認主視窗大小

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.central_layout = QHBoxLayout(self.central_widget)
        self.central_layout.addWidget(self.main_splitter)

        self.client_thread = None
        self.flow_thread = None
        self.recovery_thread = None # <--- 新增：恢復流程執行緒引用
        self.step_list_widget = None
        self.step_map = {}
        self.current_highlighted_item = None
        self.current_flow_type = 'normal' # 'normal' or 'recovery'

        # --- 左側面板 (控制) ---
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(5, 5, 5, 5)

        self._create_connection_area()
        self._create_efem_status_area()
        self._create_flow_control_area() # Flow control 區會包含恢復按鈕
        self._create_module_tabs()

        self.left_layout.addWidget(self.connection_group)
        self.left_layout.addWidget(self.efem_status_group)
        self.left_layout.addWidget(self.flow_control_group)
        self.left_layout.addWidget(self.module_tabs)
        self.left_layout.addStretch(1)

        # --- 右側面板 (作業項目列表與日誌) ---
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 5, 5, 5)

        self._create_operation_status_area() # 建立作業項目列表區域
        self._create_log_area()        # 系統日誌

        self.right_layout.addWidget(self.operation_status_group, 2) # 列表佔比例 2
        self.right_layout.addWidget(self.log_group, 3)             # 日誌佔比例 3

        # --- 將左右面板加入主 Splitter ---
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([380, 420])

        self.send_command_request_signal.connect(self.send_command_from_gui)

        default_font = QFont("Microsoft JhengHei UI", 9)
        self.setFont(default_font)
        self.log_edit.setFont(QFont("Consolas", 9))

        self.set_controls_enabled(False)
        self.populate_step_list('normal') # 初始顯示正常流程


    # --- GUI 建立函數 (_create_...) ---
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
        layout.addWidget(self.connect_button, 2, 0, 1, 2)

        layout.addWidget(QLabel("狀態:"), 3, 0)
        self.connection_status_label = QLabel("未連線")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status_label, 3, 1)

        self.connection_group.setLayout(layout)

    # _create_efem_status_area, _create_module_tabs, _create_log_area
    # (與 v1.11 版本相同，省略以節省空間)
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
        lp1_layout.setSpacing(5) # 減少元件間距

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
        self.lp1_map_result_text.setMaximumHeight(40) # 進一步限制高度
        lp1_layout.addWidget(self.lp1_map_result_text, 3, 1, 1, 3) # Span 3

        self.lp1_reset_error_btn = QPushButton("重設錯誤")
        self.lp1_reset_error_btn.clicked.connect(lambda: self.send_command_request_signal.emit("ResetError,Loadport1"))
        lp1_layout.addWidget(self.lp1_reset_error_btn, 4, 0)

        lp1_layout.setRowStretch(5, 1) # Push elements up

        self.module_tabs.addTab(lp1_tab, "Load Port 1")

        # --- Robot 1 Tab ---
        rbt1_tab = QWidget()
        rbt1_layout = QGridLayout(rbt1_tab)
        rbt1_layout.setSpacing(5) # 減少元件間距

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

        rbt1_layout.addWidget(QLabel("手臂:"), 2, 0)
        self.rbt1_arm_combo = QComboBox()
        self.rbt1_arm_combo.addItems(["UpArm", "LowArm"])
        rbt1_layout.addWidget(self.rbt1_arm_combo, 2, 1)

        rbt1_layout.addWidget(QLabel("目的地:"), 2, 2)
        self.rbt1_dest_combo = QComboBox()
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

        rbt1_layout.setRowStretch(4, 1) # Push elements up

        self.module_tabs.addTab(rbt1_tab, "Robot 1")

        # --- Aligner 1 Tab ---
        al1_tab = QWidget()
        al1_layout = QGridLayout(al1_tab)
        al1_layout.setSpacing(5) # 減少元件間距
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

        al1_layout.setRowStretch(2, 1) # Push elements up

        self.module_tabs.addTab(al1_tab, "Aligner 1")

        # --- OCR 1 Tab ---
        ocr1_tab = QWidget()
        ocr1_layout = QGridLayout(ocr1_tab)
        ocr1_layout.setSpacing(5) # 減少元件間距
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


    def _create_flow_control_area(self):
        """建立自動流程控制區域"""
        self.flow_control_group = QGroupBox("流程控制") # 修改標題
        layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        self.start_flow_button = QPushButton("開始正常流程")
        self.start_flow_button.setStyleSheet("background-color: lightblue;")
        self.start_flow_button.clicked.connect(self.start_normal_flow)
        button_layout.addWidget(self.start_flow_button)

        # --- 新增：恢復流程按鈕 ---
        self.start_recovery_button = QPushButton("啟動恢復流程")
        self.start_recovery_button.setStyleSheet("background-color: orange;")
        self.start_recovery_button.clicked.connect(self.start_recovery_flow)
        button_layout.addWidget(self.start_recovery_button)

        self.stop_flow_button = QPushButton("停止當前流程")
        self.stop_flow_button.setStyleSheet("background-color: lightcoral;")
        self.stop_flow_button.setEnabled(False) # Initially disabled
        self.stop_flow_button.clicked.connect(self.stop_current_flow)
        button_layout.addWidget(self.stop_flow_button)

        layout.addLayout(button_layout)

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


    def _create_operation_status_area(self):
        """建立顯示目前作業項目列表的區域"""
        self.operation_status_group = QGroupBox("作業項目流程")
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        self.step_list_widget = QListWidget()
        self.step_list_widget.setAlternatingRowColors(True) # 交替行顏色
        self.step_list_widget.setStyleSheet("QListWidget::item { padding: 2px; }") # 調整行間距
        self.step_list_widget.setFont(QFont("Microsoft JhengHei UI", 8)) # 列表使用稍小字體

        # 初始不填充，由 populate_step_list 填充
        self.step_list_widget.setMinimumHeight(150) # 給列表一個最小高度
        layout.addWidget(self.step_list_widget)
        self.operation_status_group.setLayout(layout)

    def populate_step_list(self, flow_type='normal'):
        """根據流程類型填充步驟列表"""
        self.step_list_widget.clear()
        self.step_map.clear()
        self.current_highlighted_item = None
        self.current_flow_type = flow_type

        if flow_type == 'normal':
            steps_to_display = range(1, 39)
            descriptions = NORMAL_FLOW_STEPS
            title = "作業項目流程 (正常)"
        elif flow_type == 'recovery':
            steps_to_display = range(101, 125) # 恢復流程步驟範圍
            descriptions = RECOVERY_FLOW_STEPS
            title = "作業項目流程 (恢復)"
        else:
            return

        self.operation_status_group.setTitle(title) # 更新 GroupBox 標題

        for step_num in steps_to_display:
             desc = get_step_description(step_num, slot='X') # 使用全局函數
             item_text = f"{step_num}. {desc}"
             list_item = QListWidgetItem(item_text)
             list_item.setData(Qt.UserRole, step_num)
             self.step_list_widget.addItem(list_item)
             self.step_map[step_num] = list_item

        # 添加結束狀態到映射 (用於結束時查找描述)
        self.step_map[0] = QListWidgetItem(get_step_description(0))
        self.step_map[99] = QListWidgetItem(get_step_description(99))
        self.step_map[-1] = QListWidgetItem(get_step_description(-1))
        self.step_map[-2] = QListWidgetItem(get_step_description(-2))
        self.step_map[199] = QListWidgetItem(get_step_description(199))
        self.step_map[-101] = QListWidgetItem(get_step_description(-101))
        self.step_map[-102] = QListWidgetItem(get_step_description(-102))


    # --- Slot Methods ---
    @pyqtSlot()
    def toggle_connection(self):
        """處理連線/中斷連線按鈕點擊"""
        if self.client_thread and self.client_thread.is_running:
            # --- Disconnect ---
            self.log_message("使用者請求中斷連線...", "orange")
            self.client_thread.stop()
            self.client_thread = None
            self.connect_button.setText("連線")
            self.connect_button.setStyleSheet("background-color: lightgreen;")
            self.connection_status_label.setText("未連線")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.set_controls_enabled(False) # 禁用控制項
            self.clear_step_highlight() # 清除高亮
            self.populate_step_list('normal') # 切回正常流程列表

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

                self.client_thread = EFemClientThread(ip, port)
                self.client_thread.connection_status_signal.connect(self.update_connection_status)
                self.client_thread.received_data_signal.connect(self.handle_received_data)
                self.client_thread.log_signal.connect(self.log_message)
                self.client_thread.finished.connect(self.on_client_thread_finished)
                self.client_thread.start()

            except ValueError:
                QMessageBox.warning(self, "輸入錯誤", f"無效的埠號: {port_str}")
                self.connection_status_label.setText("錯誤")
                self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
                self.connect_button.setText("連線")
                self.connect_button.setEnabled(True)
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
            self.client_thread.send_command(command)
        else:
            self.log_message("錯誤: 未連線到 EFEM，無法發送指令", "red")

    @pyqtSlot()
    def start_normal_flow(self):
        """啟動【正常】自動化流程"""
        if not self.client_thread or not self.client_thread.is_running:
             QMessageBox.warning(self, "錯誤", "請先連線到 EFEM")
             return
        if (self.flow_thread and self.flow_thread.isRunning()) or \
           (self.recovery_thread and self.recovery_thread.isRunning()):
            QMessageBox.warning(self, "資訊", "已有流程正在執行中")
            return

        self.log_message("請求啟動【正常】自動流程...", "blue")
        self.populate_step_list('normal') # <--- 確保顯示正常流程列表
        self.clear_step_highlight()
        self.flow_thread = FlowControlThread()
        # --- 連接正常流程執行緒信號 ---
        self.flow_thread.update_step_signal.connect(self.update_flow_step_display)
        self.flow_thread.request_confirmation_signal.connect(self.handle_confirmation_request)
        self.flow_thread.send_efem_command_signal.connect(self.send_command_request_signal)
        self.flow_thread.flow_finished_signal.connect(self.handle_flow_finished)
        self.flow_thread.log_signal.connect(self.log_message)
        # self.flow_thread.visual_update_signal 已移除
        self.flow_thread.finished.connect(self.on_flow_thread_finished)

        self.flow_thread.start()
        self.set_flow_buttons_state(is_running=True)

    @pyqtSlot()
    def start_recovery_flow(self):
        """啟動【恢復】流程"""
        if not self.client_thread or not self.client_thread.is_running:
             QMessageBox.warning(self, "錯誤", "請先連線到 EFEM")
             return
        if (self.flow_thread and self.flow_thread.isRunning()) or \
           (self.recovery_thread and self.recovery_thread.isRunning()):
            QMessageBox.warning(self, "資訊", "已有流程正在執行中")
            return

        # 可以增加一個確認對話框
        reply = QMessageBox.question(self, '確認', '確定要啟動異常恢復流程嗎？\n請確保已排除外部問題。',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        self.log_message("請求啟動【恢復】流程...", "blue")
        self.populate_step_list('recovery') # <--- 切換到恢復流程列表
        self.clear_step_highlight()
        self.recovery_thread = RecoveryFlowThread()
        # --- 連接恢復流程執行緒信號 ---
        self.recovery_thread.update_step_signal.connect(self.update_flow_step_display)
        self.recovery_thread.send_efem_command_signal.connect(self.send_command_request_signal)
        self.recovery_thread.flow_finished_signal.connect(self.handle_flow_finished) # 共用結束處理
        self.recovery_thread.log_signal.connect(self.log_message)
        self.recovery_thread.finished.connect(self.on_flow_thread_finished) # 共用結束處理

        self.recovery_thread.start()
        self.set_flow_buttons_state(is_running=True)


    @pyqtSlot()
    def stop_current_flow(self):
        """停止當前正在執行的流程（正常或恢復）"""
        stopped = False
        if self.flow_thread and self.flow_thread.isRunning():
             self.log_message("使用者請求停止【正常】流程...", "orange")
             self.flow_thread.stop()
             stopped = True
        elif self.recovery_thread and self.recovery_thread.isRunning():
             self.log_message("使用者請求停止【恢復】流程...", "orange")
             self.recovery_thread.stop()
             stopped = True
        else:
             self.log_message("目前沒有流程正在執行", "gray")

        if stopped:
            self.set_flow_buttons_state(is_running=False) # 更新按鈕狀態

    def set_flow_buttons_state(self, is_running: bool):
        """設定流程控制按鈕的啟用狀態"""
        # --- 修正 TypeError: 確保 is_running 是布林值 ---
        is_running_bool = bool(is_running)
        self.start_flow_button.setEnabled(not is_running_bool)
        self.start_recovery_button.setEnabled(not is_running_bool)
        self.stop_flow_button.setEnabled(is_running_bool)


    @pyqtSlot(str)
    def update_connection_status(self, status):
        """更新 GUI 上的連線狀態顯示"""
        self.connection_status_label.setText(status)
        if status == "Connected":
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_button.setText("中斷連線")
            self.connect_button.setStyleSheet("background-color: lightcoral;")
            self.connect_button.setEnabled(True)
            self.set_controls_enabled(True)
            self.send_command_request_signal.emit("GetStatus,EFEM")
            self.clear_step_highlight()

        elif status == "Disconnected":
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_button.setText("連線")
            self.connect_button.setStyleSheet("background-color: lightgreen;")
            self.connect_button.setEnabled(True)
            self.set_controls_enabled(False)
            self.clear_step_highlight()
            self.populate_step_list('normal') # 斷線時恢復顯示正常流程
            # 清理狀態顯示
            self.efem_mode_label.setText("未知")
            self.efem_emo_label.setText("未知")
            self.efem_ffu_label.setText("未知")
            self.efem_door_label.setText("未知")

        elif status == "Connecting":
             self.connection_status_label.setStyleSheet("color: orange; font-weight: bold;")
             self.connect_button.setEnabled(False)
             self.set_controls_enabled(False)
        else: # Error
             self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
             self.connect_button.setText("連線")
             self.connect_button.setStyleSheet("background-color: lightgreen;")
             self.connect_button.setEnabled(True)
             self.set_controls_enabled(False)
             self.clear_step_highlight()

    @pyqtSlot()
    def on_client_thread_finished(self):
        """通訊執行緒結束時的清理"""
        self.log_message("通訊執行緒已結束.", "gray")
        if self.connection_status_label.text() == "Connected" or self.connection_status_label.text() == "Connecting":
            self.update_connection_status("Disconnected")
        self.client_thread = None

    @pyqtSlot()
    def on_flow_thread_finished(self):
        """流程執行緒結束時的清理 (適用於正常和恢復流程)"""
        if self.sender() == self.flow_thread:
             self.log_message("【正常流程】執行緒已結束.", "gray")
             self.flow_thread = None
        elif self.sender() == self.recovery_thread:
             self.log_message("【恢復流程】執行緒已結束.", "gray")
             self.recovery_thread = None
             self.populate_step_list('normal') # 恢復流程結束後，切回正常列表

        # 只有當兩個流程都沒在跑時才更新按鈕
        if not (self.flow_thread and self.flow_thread.isRunning()) and \
           not (self.recovery_thread and self.recovery_thread.isRunning()):
            self.set_flow_buttons_state(is_running=False)
            self.confirmation_group.setVisible(False)


    @pyqtSlot(str)
    def handle_received_data(self, data):
        """處理從通訊執行緒收到的原始資料"""
        message = data.strip().rstrip('$')

        if message.startswith("Event,"):
            self.handle_event(message)
        elif ",OK" in message:
            # 將回應傳遞給當前活動的流程執行緒
            if self.flow_thread and self.flow_thread.isRunning():
                 self.flow_thread.set_efem_response(message + "$")
            elif self.recovery_thread and self.recovery_thread.isRunning():
                 self.recovery_thread.set_efem_response(message + "$")
            self.update_status_from_response(message + "$")
        elif ",Error," in message:
            self.handle_error(message + "$")
            # 將錯誤回應也傳遞給當前活動的流程執行緒
            if self.flow_thread and self.flow_thread.isRunning():
                 self.flow_thread.set_efem_response(message + "$")
            elif self.recovery_thread and self.recovery_thread.isRunning():
                 self.recovery_thread.set_efem_response(message + "$")
        elif message.startswith("RAW_DATA:"):
             pass
        else:
             self.log_message(f"收到未識別訊息: {message}", "orange")

    @pyqtSlot(str, str)
    def log_message(self, message, color="black"):
        """將訊息附加到日誌區域"""
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{now}] {message}"

        self.log_edit.moveCursor(QTextCursor.End)
        self.log_edit.setTextColor(QColor(color))
        self.log_edit.insertPlainText(log_entry + "\n")
        self.log_edit.setTextColor(QColor("black"))
        self.log_edit.ensureCursorVisible()

    # handle_event, handle_error, update_status_from_response (與上一版本相同，省略)
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
                    pass
                elif event_name == "Run":
                    self.log_message("EFEM 開始執行...", "darkblue")
                elif event_name == "Idle":
                     self.log_message("EFEM 執行完畢/閒置", "darkblue")
                elif event_name == "Error":
                     self.log_message("EFEM 報告錯誤狀態", "red")

        # --- Loadport 事件 ---
        elif source.startswith("Loadport"):
            lp_name = source # e.g., "Loadport1"
            if len(parts) >= 3:
                event_name = parts[2]
                if event_name == "FoupPlace":
                     self.log_message(f"{lp_name} Foup 放置", "darkmagenta")
                     # self.simulation_widget.update_simulation('FoupPlaced', {'source': lp_name}) # 移除
                     self.send_command_request_signal.emit(f"GetStatus,{lp_name}")
                elif event_name == "FoupRemove":
                     self.log_message(f"{lp_name} Foup 移除", "darkmagenta")
                     # self.simulation_widget.update_simulation('FoupRemoved', {'source': lp_name}) # 移除
                elif event_name == "PresenceSignal" or event_name == "PlacementSignal":
                    signal_status = parts[3] if len(parts) > 3 else "?"
                    self.log_message(f"{lp_name} {event_name}: {signal_status}", "gray")
                elif event_name == "MapResult":
                     map_data = ",".join(parts[3:]) if len(parts) > 3 else "無資料"
                     self.log_message(f"{lp_name} Map 結果事件: {map_data[:30]}...", "darkcyan")
                     if lp_name == "Loadport1":
                         self.lp1_map_result_text.setText(map_data)
                     # self.simulation_widget.update_simulation('MapResult', {'source': lp_name, 'map_data': map_data}) # 移除

        # --- Robot 事件 ---
        elif source.startswith("Robot"):
             if len(parts) == 4:
                 low_arm_status = parts[2]
                 up_arm_status = parts[3]
                 self.log_message(f"{source} 手臂狀態事件: 下={low_arm_status}, 上={up_arm_status}", "darkblue")
                 if source == "Robot1":
                     self.rbt1_low_arm_label.setText(low_arm_status)
                     self.rbt1_up_arm_label.setText(up_arm_status)

        # --- Aligner 事件 ---
        elif source.startswith("Aligner"):
             if len(parts) == 3:
                 result = parts[2] # Presence/Absence
                 self.log_message(f"{source} Wafer 狀態事件: {result}", "darkblue")
                 if source == "Aligner1":
                     self.al1_wafer_label.setText(result)

        # --- 其他事件 ---
        else:
            self.log_message(f"收到未處理事件來源: {event_data}", "orange")


    def handle_error(self, error_data):
        """解析錯誤回應並顯示"""
        parts = error_data.strip().rstrip('$').split(',')
        if len(parts) >= 4 and parts[-2] == "Error":
            error_code = parts[-1].strip()
            command_sent = parts[0]
            device = parts[1]
            error_desc = ERROR_CODES.get(error_code, f"未知錯誤碼 ({error_code})")
            full_error_msg = f"指令錯誤: [{device}] {command_sent} -> {error_desc}"
            self.log_message(full_error_msg, "red")
        else:
            self.log_message(f"收到未解析錯誤回應: {error_data.strip()}", "red")

    def update_status_from_response(self, response_data):
        """根據成功的指令回應更新 GUI 狀態"""
        parts = response_data.strip().rstrip('$').split(',')
        command = parts[0]
        device = parts[1]

        if command == "GetStatus":
            if device == "EFEM" and len(parts) >= 13 and parts[2] == "OK":
                emo_status = "觸發" if parts[3] == '0' else "正常"
                ffu_pd_status = "過高" if parts[4] == '0' else "正常"
                mode = "本地 (Local)" if parts[10] == '0' else "遠端 (Remote)"
                robot_en = "禁用" if parts[11] == '0' else "啟用"
                door = "開啟" if parts[12] == '0' else "關閉"
                self.efem_emo_label.setText(emo_status)
                self.efem_ffu_label.setText(f"FFU PD:{ffu_pd_status}")
                self.efem_mode_label.setText(mode)
                self.efem_door_label.setText(door)
                self.log_message(f"EFEM 狀態更新: EMO={emo_status}, Mode={mode}, Door={door}", "darkgray")

            elif device.startswith("Loadport") and len(parts) >= 8 and parts[2] == "OK":
                lp_name = device
                mode, error, foup, clamp, door = parts[3:8]
                status_text = f"模式:{mode}, 錯誤:{error}, Foup:{foup}, Clamp:{clamp}, Door:{door}"
                if lp_name == "Loadport1":
                    self.lp1_status_label.setText(status_text)
                self.log_message(f"{lp_name} 狀態更新: {status_text}", "darkgray")

            elif device.startswith("Robot") and len(parts) >= 6 and parts[2] == "OK":
                 rbt_name = device
                 status_code = parts[3]
                 up_presence = parts[4]
                 low_presence = parts[5]
                 if rbt_name == "Robot1":
                     self.rbt1_status_label.setText(f"代碼:{status_code}")
                     self.rbt1_up_arm_label.setText(up_presence)
                     self.rbt1_low_arm_label.setText(low_presence)
                 self.log_message(f"{rbt_name} 狀態更新: Code={status_code}, Up={up_presence}, Low={low_presence}", "darkgray")

            elif device.startswith("Aligner") and len(parts) >= 6 and parts[2] == "OK":
                 al_name = device
                 mode = parts[3]
                 wafer = parts[4]
                 vac_cda = parts[5]
                 if al_name == "Aligner1":
                     self.al1_status_label.setText(mode)
                     self.al1_wafer_label.setText(wafer)
                 self.log_message(f"{al_name} 狀態更新: Mode={mode}, Wafer={wafer}, Vac/CDA={vac_cda}", "darkgray")

        elif command == "ReadFoupID" and device.startswith("Loadport") and len(parts) == 4 and parts[2] == "OK":
            lp_name = device
            rfid = parts[3]
            if lp_name == "Loadport1":
                self.lp1_rfid_label.setText(rfid)
            self.log_message(f"{lp_name} RFID 讀取成功: {rfid}", "darkcyan")

        elif command == "GetMapResult" and device.startswith("Loadport") and len(parts) >= 4 and parts[2] == "OK":
            lp_name = device
            map_data = ",".join(parts[3:])
            if lp_name == "Loadport1":
                self.lp1_map_result_text.setText(map_data)
            self.log_message(f"{lp_name} Map 結果讀取成功: {map_data[:30]}...", "darkcyan")
            # self.simulation_widget.update_simulation('MapResult', {'source': lp_name, 'map_data': map_data}) # 移除

        elif command == "ReadID" and device.startswith("OCR") and len(parts) == 4 and parts[2] == "OK":
            ocr_name = device
            ocr_result = parts[3]
            if ocr_name == "OCR1":
                 self.ocr1_result_label.setText(ocr_result)
            self.log_message(f"{ocr_name} OCR 讀取成功: {ocr_result}", "darkcyan")

        elif command == "GetCurrentMode" and device == "EFEM" and len(parts) == 4 and parts[2] == "OK":
            mode = parts[3]
            self.efem_mode_label.setText(mode)
            self.log_message(f"EFEM 目前模式: {mode}", "darkgray")


    @pyqtSlot(int) # 接收 int (步驟編號)
    def update_flow_step_display(self, step_num):
        """更新流程步驟列表的高亮"""
        # 清除先前的高亮
        default_bg_color = self.step_list_widget.palette().base().color()
        if self.current_highlighted_item:
            self.current_highlighted_item.setBackground(default_bg_color)
            self.current_highlighted_item = None

        # 找到新步驟對應的列表項目
        item_to_highlight = self.step_map.get(step_num)

        if item_to_highlight and step_num > 0: # 僅高亮有效步驟編號
            # --- 使用更明顯的顏色 ---
            item_to_highlight.setBackground(QColor('yellow')) # 設定高亮背景色為黃色
            self.current_highlighted_item = item_to_highlight
            # 確保高亮項目可見
            self.step_list_widget.scrollToItem(item_to_highlight, QListWidget.ScrollHint.EnsureVisible)
        elif step_num <= 0 or step_num == 99 or step_num == 199: # 處理特殊狀態碼，不高亮列表
            pass # 可以在此處更新狀態標籤，如果需要的話
        else:
            self.log_message(f"警告: 在列表中找不到步驟 {step_num} 以高亮顯示", "orange")

        # 更新日誌
        step_desc = get_step_description(step_num) # 使用全局函數
        self.log_message(f"目前作業: ({step_num}) {step_desc}", "darkMagenta")


    @pyqtSlot(str, str)
    def handle_confirmation_request(self, confirmation_type, data_to_confirm):
        """顯示等待使用者確認的介面"""
        self.confirmation_info_label.setText(f"類型: {confirmation_type}\n資料: {data_to_confirm}")
        self.confirmation_group.setVisible(True)
        self.log_message(f"流程暫停: 等待使用者確認 {confirmation_type}", "darkorange")

    def confirm_data(self, confirmed_ok):
        """處理使用者點擊確認按鈕"""
        # 將確認結果發送給當前活動的流程執行緒
        active_thread = None
        if self.flow_thread and self.flow_thread.isRunning():
            active_thread = self.flow_thread
        elif self.recovery_thread and self.recovery_thread.isRunning():
             active_thread = self.recovery_thread

        if active_thread:
            result_text = "正確" if confirmed_ok else "錯誤"
            self.log_message(f"使用者確認資料: {result_text}", "blue")
            active_thread.set_user_confirmation(confirmed_ok)
            self.confirmation_group.setVisible(False)
        else:
             self.log_message("警告: 在非流程執行狀態下收到確認", "orange")

    @pyqtSlot(int) # 接收 int (最終狀態碼)
    def handle_flow_finished(self, final_status_code):
        """處理流程結束事件 (通用)"""
        status_description = get_step_description(final_status_code) # 使用全局函數
        log_color = "green" if final_status_code in [99, 199] else "red"

        self.log_message(f"流程結束: {status_description}", log_color)
        self.clear_step_highlight()

        # 判斷是哪個流程結束
        if self.sender() == self.recovery_thread:
             self.populate_step_list('normal') # 恢復流程結束後切回正常列表

        # 只有當兩個流程都沒在跑時才更新按鈕
        if not (self.flow_thread and self.flow_thread.isRunning()) and \
           not (self.recovery_thread and self.recovery_thread.isRunning()):
            self.set_flow_buttons_state(is_running=False)
            self.confirmation_group.setVisible(False)

    # handle_visual_update 方法已被移除

    def clear_step_highlight(self):
        """清除步驟列表中的高亮"""
        if self.current_highlighted_item:
            default_bg_color = self.step_list_widget.palette().base().color()
            self.current_highlighted_item.setBackground(default_bg_color)
            self.current_highlighted_item = None
        else: # 如果沒有追蹤的項目，遍歷清除
            default_bg_color = self.step_list_widget.palette().base().color()
            for i in range(self.step_list_widget.count()):
                item = self.step_list_widget.item(i)
                if item: # 確保項目存在
                    item.setBackground(default_bg_color)


    # set_controls_enabled, send_robot_smart_get, send_robot_smart_put (與上一版本相同，省略)
    def set_controls_enabled(self, enabled):
        """啟用或禁用需要連線才能操作的控制項"""
        self.get_efem_status_button.setEnabled(enabled)
        self.remote_button.setEnabled(enabled)
        self.local_button.setEnabled(enabled)
        self.home_efem_button.setEnabled(enabled)
        # 流程按鈕的狀態由 set_flow_buttons_state 控制
        if not enabled: # 如果是禁用所有控件
            self.start_flow_button.setEnabled(False)
            self.start_recovery_button.setEnabled(False)
            self.stop_flow_button.setEnabled(False)
        else: # 如果是啟用，則根據是否有流程在跑來決定
             is_running = (self.flow_thread and self.flow_thread.isRunning()) or \
                          (self.recovery_thread and self.recovery_thread.isRunning())
             self.set_flow_buttons_state(is_running)

        self.module_tabs.setEnabled(enabled)
        # Tab 內按鈕
        self.lp1_get_status_btn.setEnabled(enabled)
        self.lp1_load_btn.setEnabled(enabled)
        self.lp1_unload_btn.setEnabled(enabled)
        self.lp1_map_btn.setEnabled(enabled)
        self.lp1_read_rfid_btn.setEnabled(enabled)
        self.lp1_reset_error_btn.setEnabled(enabled)
        self.rbt1_get_status_btn.setEnabled(enabled)
        self.rbt1_home_btn.setEnabled(enabled)
        self.rbt1_stop_btn.setEnabled(enabled)
        self.rbt1_smartget_btn.setEnabled(enabled)
        self.rbt1_smartput_btn.setEnabled(enabled)
        self.al1_get_status_btn.setEnabled(enabled)
        self.al1_home_btn.setEnabled(enabled)
        self.al1_align_btn.setEnabled(enabled)
        self.al1_reset_error_btn.setEnabled(enabled)
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
        if self.flow_thread and self.flow_thread.isRunning():
            self.flow_thread.stop()
            self.flow_thread.wait(500)
        if self.recovery_thread and self.recovery_thread.isRunning(): # <--- 關閉恢復執行緒
            self.recovery_thread.stop()
            self.recovery_thread.wait(500)
        if self.client_thread and self.client_thread.is_running:
            self.client_thread.stop()
            self.client_thread.wait(500)

        event.accept()

    # sync_toggle_button_state 方法已被移除


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = EFemApp()
    mainWin.show()
    sys.exit(app.exec_())

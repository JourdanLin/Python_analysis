# efem_error_codes.py
# 儲存 EFEM API 的錯誤代碼及其描述

# 錯誤代碼字典 (根據 EFEM API 手冊 v1.40 整理)
# 頁碼參考手冊 PDF 頁數
ERROR_CODES = {
    # === System Error (1.4.1, p17) ===
    "0001": "未定義的指令 (Undefine command)",
    "0002": "未定義的裝置名稱 (Undefine device name)",
    "0003": "無效的參數 (Invalid parameters)",
    "0004": "非 Remote 模式 (Not in Remote mode)",
    "0005": "EFEM 尚未就緒 (EFEM not ready)",
    "0006": "內部裝置通訊錯誤 (Internal device communication error)",
    "0007": "設定檔讀取失敗 (Configuration read fail)",
    "0008": "I/O 裝置初始化失敗 (I/O device initial fail)",
    "0009": "站點檔案讀取失敗 (Station file read fail)",
    "0010": "找不到 IO.csv (IO.csv not found)",
    "0011": "DeviceInfo 檔案讀寫失敗 (DeviceInfo file read/write fail)",
    "0012": "InfoPad 檔案讀取失敗 (InfoPad file read fail)",
    "0013": "錯誤的指令長度 (Wrong command size)",
    "0014": "HAPI 初始化失敗 (HAPI initialization fail)",
    "0015": "XML 檔案讀取失敗 (Extensible Markup Language file reading failed)",
    "0016": "ForkInfo 檔案讀取失敗 (ForkInfo file read fail)",
    "0017": "UserParameter.db 讀寫失敗 (UserParameter.db read/write fail)", # 手冊 v1.35 更新

    # === EFEM IO Status Error (1.4.2, p17-18) ===
    "1001": "緊急停止按鈕觸發 (Emergency stop on)",
    "1002": "FFU 壓差異常 (FFU pressure difference error)",
    "1003": "EFEM CDA 異常 (EFEM CDA error)",
    "1004": "EFEM 真空異常 (EFEM vacuum error)",
    "1005": "Ionizer 警報 (Ionizer alarm)",
    "1006": "Ionizer 離子量警告 (Ionizer ion level warning)",
    "1007": "Ionizer 狀態警告 (Ionizer condition warning)",
    "1008": "光閘異常 (Light curtain error)",
    "1009": "錯誤的操作模式 (Wrong operation mode)",
    "1010": "門已開啟 (Door open)",
    "1011": "Robot 啟用錯誤 (Robot Enable error)",
    "1012": "等待 Stage 回應超時 (Waiting Stage response timeout)",
    "1013": "Robot 上手臂 CDA 異常 (Robot upper arm CDA error)",
    "1014": "Robot 上手臂真空異常 (Robot upper arm vacuum error)",
    "1015": "Robot 下手臂 CDA 異常 (Robot lower arm CDA error)",
    "1016": "Robot 下手臂真空異常 (Robot lower arm vacuum error)",
    "1017": "Ionizer CDA 異常 (Ionizer CDA error)", # 注意與 1005/1006/1007 的區別
    "1018": "Aligner 真空異常 (Aligner vacuum error)",
    # "1019": "已移除 (Removed Error Code)", # 手冊 v1.23 移除
    "1020": "Robot 處於旋轉極限區域 (Robot in rotate limit area)",
    "1021": "Aligner CDA 異常 (Aligner CDA error)", # 注意與 1018 的區別
    "1022": "OCR CDA 異常 (OCR CDA error)",
    "1023": "Barcode CDA 異常 (Barcode CDA error)",
    "1024": "Stage Wafer 狀態錯誤 (Stage wafer state error)",
    "1025": "Buffer 上有料 (Wafer on Buffer)",
    "1026": "安全繼電器異常 (Safety Relay Abnormality)",
    "1027": "Flipper CDA 異常 (Flipper CDA error)",
    "1028": "Stage CDA 異常 (Stage CDA error)",

    # === FFU Error (1.4.3, p18) ===
    "2001": "未分類的 FFU 錯誤 (Unclassified error)",
    "2002": "FFU 通訊錯誤 (Communication error)",
    "2003": "FFU IPM 溫度過高 (IPM Temperature detection overheating)",
    "2004": "FFU IPM 模組異常保護 (IPM Module anomaly protection)",
    "2005": "FFU 風扇啟動錯誤 (Fan startup error)",
    "2006": "FFU 速度在一分鐘內未達設定值 (The set value is not reached within one minute of the speed)",
    "2007": "FFU 通訊中斷 (Communication disconnect)",

    # === Robot Error (S/E Series) (1.4.4, p18-21) ===
    "3001": "Robot 通訊錯誤 (Robot communication error)",
    "3002": "未分類的 Robot 錯誤 (Unclassified error)",
    "3003": "教導器正在使用中 (The teach-pendant is using)",
    "3004": "Robot 末端效應器設定錯誤 (Robot end effector setting error)",
    "3005": "Robot 與 Load Port 的 Wafer 尺寸不符 (Wafer size between robot and LP not match)",
    "3006": "Robot 與 Load Port 的 Wafer 類型不符 (Wafer type between robot and LP not match)",
    "3007": "Flipper 站點上無 Wafer (Flipper station not has wafer)",
    "3008": "Flipper 站點上有 Wafer (Flipper station has wafer)",
    "3009": "Flipper 位置不安全 (Flipper position not safety)",
    "3010": "Robot 與 Load Port 的卡匣類型不符 (Cassette type between robot and LP not match)",
    "3011": "Z 軸偏移量過大 (Offset of Z is too big)",
    "3101": "巨集指令錯誤 (Command error of macro command)",
    "3102": "站點名稱錯誤 (Command error of station name)",
    "3103": "軸名稱錯誤 (Command error of axis name)",
    "3104": "群組名稱錯誤 (Command error of group name)",
    "3105": "參數錯誤 (Command error of argument)",
    "3106": "指令無回應 (Command no response)",
    "3107": "指令處理中 (Command processing)",
    "3108": "裝置處理中 (Device processing)", # v1.31 新增
    "3199": "Robot 內部錯誤 (Robot internal error)", # v1.40 新增 (可能涵蓋多種情況)
    "3201": "取片前手臂真空已作動 (Vacuum state is activated prior to pick wafer)",
    "3202": "取放片後真空無法建立/解除 (Vacuum state can not be produced or released after pick/place)",
    "3203": "Z 軸硬體上限位觸發 (Upper limit switch on the Z-axis hardware actuated)",
    "3204": "Z 軸硬體下限位觸發 (Lower limit switch on the Z-axis hardware actuated)",
    "3205": "取片前/放片後光纖感測器作動 (Optical fiber sensor activated before pick or after place)",
    "3206": "取片後/放片前光纖感測器未作動 (Optical fiber sensor deactivated after pick or before place)",
    "3207": "手臂伸出狀態的磁簧開關無法收回 (Reed switch under extended state cannot be retracted)",
    "3208": "手臂收回狀態的磁簧開關無法伸出 (Reed switch under retracted state cannot be extended)",
    "3209": "H 軸正極限觸發 (Positive limit switch of H-axis activated)",
    "3210": "H 軸負極限觸發 (Negative limit switch of H-axis activated)",
    "3211": "手臂翻轉氣缸未翻到正面 (Robotic arm flip cylinder not flipped to the front side)",
    "3212": "手臂翻轉氣缸未翻到背面 (Robotic arm flip cylinder not flipped to the back side)",
    "3213": "取放過程中 R 軸 Wafer 掉落 (Wafer fell from R axis during picking/placing)",
    "3214": "取放過程中 W 軸 Wafer 掉落 (Wafer fell from W axis during picking/placing)",
    "3215": "取片前正壓已作動 (Positive pressure state is actuated prior to picking wafer)",
    "3216": "放片前正壓無法建立 (Positive pressure state can not be produced prior to place)",
    "3219": "電動翻轉原點搜尋未完成 (Electric flip origin search not completed)",
    "3220": "電動翻轉極限觸發 (Electric flip limit has been activated)",
    "3221": "電動翻轉移動失敗 (Electric flip move failed)",
    "3222": "電動翻轉位置因外力異常 (Position of electric flip abnormal due to external force)",
    "3223": "上手臂真空狀態錯誤 (Upper arm vacuum status error)",
    "3224": "下手臂真空狀態錯誤 (Lower arm vacuum status error)",
    "3301": "馬達未啟用 (Motor has not been enabled)",
    "3302": "原點搜尋未完成 (Origin search not completed)",
    "3303": "移動中 (Moving)",
    "3304": "追隨誤差過大 (Following position error is too big)",
    "3305": "伺服馬達編碼器錯誤 (Servo motor encoder error)",
    "3306": "伺服馬達編碼器故障 (Servo motor encoder failed)",
    "3307": "伺服馬達溫度過高 (Temperature of servo motor too high)",
    "3308": "馬達移動到正極限位置 (Motor moves to the positive limit position)",
    "3309": "馬達移動到負極限位置 (Motor moves to the negative limit position)",
    "3310": "軸的速度或加減速參數異常 (Speed or acceleration/deceleration parameter abnormal)",
    "3311": "T/Z/H 軸原點搜尋時 R/W 軸未完成原點搜尋 (When T/Z/H origin search, R/W not finished origin search)",
    "3312": "T/Z/H 軸原點搜尋時 R/W 軸未回到安全位置 (When T/Z/H origin search, R/W not returned to safety position)",
    "3313": "控制器溫度過高 (Temperature of controller too high)",
    "3314": "原點位置異常 (Origin position is abnormal)", # v1.36 新增
    "3401": "Robot 緊急停止觸發 (Robot Emergency stop on)",
    "3402": "控制器電源故障 (Controller power failed)",
    "3403": "控制器電壓過低 (Voltage of controller too low)",
    "3404": "控制器電壓過高 (Voltage of controller too high)",
    "3405": "控制器檢測到驅動器故障 (Controller detect driver failed)",
    "3406": "控制器電壓異常 (Controller voltage abnormal)", # v1.23 修正描述
    "3407": "控制器無法識別驅動器 (Controller unable to identify driver)",
    "3408": "UPS 故障 (UPS failed)",
    "3409": "外部停止信號觸發 (External stop signal triggered)",
    "3999": "A 系列 Robot 錯誤代碼 (需用 GetErrorCode 查詢詳細) (Error code of A series robots)",

    # === Aligner Error (1.4.5, p21-22) ===
    "4001": "Aligner 通訊錯誤 (Aligner communication error)",
    "4002": "Aligner 內部指令執行失敗 (Aligner internal command execute fail)",
    "4003": "未分類的 Aligner 錯誤 (Unclassified error)",
    "4004": "對位失敗 (Alignment fail)",
    "4005": "初始化失敗 (Initialization fail)",
    "4006": "Aligner 不在 Home 位置 (Aligner not in home position)",
    "4007": "Aligner 上有料 (Wafer on aligner)",
    "4008": "Aligner 上無料 (No wafer on aligner)",
    "4009": "錯誤的 Wafer 狀態 (Wrong wafer status)", # v1.39 新增
    "4101": "Aligner 無回應 (Aligner no response)",
    "4102": "指令處理中 (Command processing)",
    "4103": "錯誤的 Wafer 尺寸 (Wrong wafer size)",
    "4201": "Chuck 上未感測到真空 (Vacuum not sensed on chuck)",
    "4202": "無效的 CCD 感測器數據 (Invalid CCD sensor data)",
    "4203": "Chuck 真空開關 ON (Chuck Vacuum Switch ON)",
    "4204": "Pins 真空開關 ON (Pins Vacuum Switch ON)",
    "4205": "數據擷取錯誤 (Data capture error)",
    "4206": "預對位操作中 Wafer 遺失 (Wafer lost during prealign operation)",
    "4207": "找不到平邊或 Notch (Flat or Notch not found)",
    "4208": "計算出的偏移超出限制 (Calculated offset out of limits)",
    "4301": "移動中 (Moving)",
    "4302": "量測速度未及時達到 (Measurement speed not reached on time)",
    "4303": "無法執行移動指令 (Unable to execute motion commands)",
    "4304": "移動錯誤 (Motion error)",
    "4305": "一個或多個軸 Servo OFF (Servo OFF on one or more axes)",
    "4401": "緊急停止觸發 (Emergency stop on)",
    "4402": "對位演算法被 Host 中斷 (Alignment algorithm interrupted by host)",
    "4504": "Aligner Gripper 不在釋放位置 (Aligner Gripper not on release position)",
    "4505": "Aligner Gripper 不在夾取位置 (Aligner Gripper not on grip position)",
    "4508": "Aligner 移動到極限位置 (Aligner moves to the limit position)",

    # === Load Port Error (1.4.6, p22-23) ===
    "5001": "Loadport 通訊錯誤 (Loadport communication error)",
    "5002": "RFID 通訊錯誤 (RFID communication error)",
    "5003": "未分類的 Loadport 錯誤 (Unclassified error)",
    "5004": "RFID 讀取失敗 (RFID read fail)",
    "5005": "初始化失敗 (Initialization fail)",
    "5006": "Loadport 狀態錯誤 (Loadport status error)",
    "5007": "Foup 未載入 (Foup not load)",
    "5008": "Foup Slot 狀態錯誤 (Foup slot status error)",
    "5009": "Loadport 不支援指定的燈號控制 (Loadport does not support specified lamp control)",
    "5101": "Loadport 指令無回應 (Loadport command no response)",
    "5102": "RFID 指令無回應 (RFID command no response)",
    "5103": "指令處理中 (Command Processing)",
    "5104": "處於手動操作模式 (Under manual operation)",
    "5201": "Wafer Mapping 未完成 (Wafer mapping not completed)",
    "5202": "偵測到手抓/頭抓感測器 (Detect hand-caught/head-caught sensor)",
    "5203": "偵測到 Wafer 突出感測器 (Detect wafer out sensor)",
    "5204": "Carrier 被不當取走 (Carrier improperly taken)",
    "5205": "Carrier 被不當放置 (Carrier improperly placed)",
    "5206": "FOUP 開/關門禁用 (FOUP open/close disable)",
    "5207": "Dock 軸禁用 (Dock axis disable)",
    "5208": "FOUP Map 禁用 (FOUP map disable)",
    "5209": "FOUP Clamp 禁用 (FOUP clamp disable)",
    "5210": "FOUP Unclamp 禁用 (FOUP Unclamp disable)",
    "5211": "FOUP Latch 禁用 (FOUP latch disable)",
    "5212": "FOUP Unlatch 禁用 (FOUP Unlatch disable)",
    "5213": "真空禁用 (Vacuum disable)",
    "5301": "移動中 (Moving)",
    "5302": "不正確的 FOUP 放置狀態 (Incorrect FOUP placement status)",
    "5303": "不正確的 Clamp 軸位置 (Incorrect clamp axis position)",
    "5304": "不正確的 Docking 軸位置 (Incorrect Docking axis position)",
    "5305": "不正確的真空狀態 (Incorrect vacuum status)",
    "5306": "不正確的 Latch 位置 (Incorrect latch position)",
    "5307": "不正確的門開/關位置 (Incorrect door open/close position)",
    "5308": "不正確的門上/下位置 (Incorrect door up/down position)",
    "5309": "不正確的 Mapper 位置 (Incorrect mapper position)",
    "5310": "不正確的 Z 軸位置 (Incorrect Z-axis position)",
    "5401": "緊急停止觸發 (Emergency stop on)",

    # === OCR Error (1.4.7, p23-24) ===
    "6001": "未分類的 OCR 錯誤 (Unclassified error)",
    "6002": "OCR 通訊錯誤 (OCR communication error)",
    "6003": "OCR 讀取失敗 (OCR Read failed)",
    "6004": "OCR 無回應 (OCR no response)",
    "6005": "OCR 位置移動失敗 (OCR position move failed)",
    "6006": "找不到 OCR FTP 伺服器 (OCR FTP Server not found)", # v1.36 新增

    # === Barcode Error (1.4.8, p24) ===
    "7001": "未分類的 Barcode 錯誤 (Unclassified error)",
    "7002": "Barcode 通訊錯誤 (Barcode communication error)",
    "7003": "Barcode 讀取失敗 (Barcode Read failed)",
    "7004": "Barcode 無回應 (Barcode no response)",
    "7005": "Barcode 位置移動失敗 (Barcode position move failed)",

    # === E84 Error (1.4.9, p24) ===
    "8001": "未分類的 E84 錯誤 (Unclassified error)",
    "8002": "E84 通訊錯誤 (E84 communication error)",
    "8003": "E84 無回應 (E84 no response)",
    "8004": "環境狀態未就緒，無法切換到 AUTO 模式 (Environment status not ready, can't switch to AUTO MODE)",
    "8005": "非 Manual 或 Standby 模式 (Not in Manual Mode or Standby Mode)",
    "8006": "GO 或 CS_0 非 OFF 狀態，無法切換到 Manual 模式 (GO or CS_0 not OFF status, can't switch to Manual Mode)",
    "8007": "DI 硬體輸入 ES OFF，不接受設定 ES ON 指令 (DI hardware input ES OFF, not accept set ES ON command)",
    "8008": "控制器非 ERROR 或 MANUAL 模式，指令失敗 (Controller not in ERROR status or MANUAL MODE. command Fail)",
    "8009": "環境狀態未就緒，指令失敗 (Environment status not ready, command Fail)",
    "8010": "輸入的超時值超出範圍 1~255 秒 (Input timeout value out of range 1~255 seconds)",
    "8011": "指令處理中 (Command processing)",

    # === Flipper Error (1.4.10, p25) ===
    "A001": "Flipper 通訊錯誤 (Flipper communication error)",
    "A002": "Flipper 內部指令執行失敗 (Flipper internal command execute fail)",
    "A003": "未分類的 Flipper 錯誤 (Unclassified error)",
    "A004": "Flipper 未就緒 (Flipper not ready)",
    "A005": "初始化失敗 (Initialization fail)",
    "A006": "Flipper 不在正確位置 (Flipper not in correct position)",
    "A007": "Flipper 上有料 (Wafer on flipper)",
    "A008": "Flipper 上無料 (No wafer on flipper)",
    "A101": "Flipper 無回應 (Flipper no response)",
    "A102": "指令處理中 (Command processing)",
    "A301": "移動中 (Moving)",
    "A302": "移動錯誤 (Motion error)",

    # === DP Module Error (1.4.11, p25) ===
    "B001": "未分類的 DP Module 錯誤 (Unclassified error)",
    "B002": "DP Module 通訊錯誤 (DPModule communication error)",
    "B101": "DP Module 無回應 (DPModule no response)",

    # === IO Command Error (1.4.12, p25) ===
    "C001": "未分類的 IO 指令錯誤 (Unclassified error)",
    "C002": "未知的 IO 名稱 (Unknown IO name)",

    # === Stage Error (1.4.13, p25-26) ===
    "D001": "未分類的 Stage 錯誤 (Unclassified error)",
    "D101": "Stage 無回應 (Stage no response)",
    "D102": "指令處理中 (Command processing)",
    "D103": "狀態錯誤 (Status error)",
    "D104": "Robot 在 Stage 上 (Robot on stage)",

    # === Vision Module Error (1.4.14, p26) ===
    "E001": "未分類的 Vision Module 錯誤 (Unclassified error)",
    "E002": "Vision Module 通訊錯誤 (VisionModule communication error)",
    "E003": "Vision Module 無回應 (VisionModule no response)",
    "E004": "指令處理中 (Command processing)",
    "E005": "辨識失敗 (Recognition failed)",
    "E006": "讀取參數失敗 (Read parameter failed)",
    "E007": "照片擷取失敗 (Photo retrieval failed)",

    # === Robot A Series Errors (Appendix B, p158-192) ===
    # --- System error (01-01-XX) ---
    "01-01-10": "系統初始化失敗 (System initialization failed)",
    "01-01-11": "運動學函式庫載入失敗 (The kinematics library failed to load)",
    "01-01-12": "運動功能初始化失敗 (Motion function initialization failed)",
    "01-01-13": "運動功能記憶體初始化失敗 (Motion function memory initialization failed)",
    "01-01-14": "運動功能啟動失敗 (The motion function failed to start)",
    "01-01-20": "EtherCAT 函式庫載入失敗 (Failed to load the EtherCAT library)",
    "01-01-21": "EtherCAT 連線中斷 (The EtherCAT connection is interrupted)",
    "01-01-22": "EtherCAT 初始化失敗 (EtherCAT initialization failed)",
    "01-01-23": "EtherCAT 網路線交叉警報 (EtherCAT network line cross alarm)",
    "01-01-24": "EtherCAT 無從站警報 (EtherCAT no slave alarm)",
    "01-01-25": "EtherCAT 無法辨識從站 (EtherCAT does not recognize the slave)",
    "01-01-26": "EtherCAT 從站無回應 (EtherCAT slave not responding)",
    "01-01-27": "EtherCAT 週期發生錯誤 (An error occurred in the EtherCAT cycle)",
    "01-01-28": "EtherCAT 迴圈抖動錯誤 (EtherCAT loop jitter error)",
    "01-01-29": "EtherCAT 迴圈工作計數器錯誤 (EtherCAT cycle work counter error)",
    "01-01-2A": "EtherCAT 迴圈看門狗錯誤 (EtherCAT loop watchdog error)",
    "01-01-2B": "EtherCAT INIT 狀態切換錯誤 (EtherCAT INIT state switching error)",
    "01-01-2C": "EtherCAT PREOP 狀態切換錯誤 (EtherCAT PREOP state switching error)",
    "01-01-2D": "EtherCAT SAFEOP 狀態切換錯誤 (EtherCAT SAFEOP state switching error)",
    "01-01-2E": "EtherCAT OP 狀態切換錯誤 (EtherCAT OP state switching error)",
    "01-01-2F": "EtherCAT 主站錯誤 (EtherCAT master error)", # 手冊原文只有 master
    "01-01-30": "EtherCAT 主站初始化錯誤 (EtherCAT master initialization error)",
    "01-01-31": "EtherCAT 匯流排掃描錯誤 (EtherCAT bus scan error)",
    "01-01-32": "EtherCAT 框架回應錯誤 (EtherCAT frame response error)",
    "01-01-33": "EtherCAT 框架遺失 (EtherCAT frame lost)",
    "01-01-34": "EtherCAT 主站錯誤 (EtherCAT master is wrong)", # 與 2F 相似
    "01-01-35": "EtherCAT 主站初始指令回應錯誤 (EtherCAT master responded with an error in the initial command)",
    "01-01-36": "EtherCAT 從站初始指令工作計數器錯誤 (The initial instruction work counter of the EtherCAT slave is wrong)",
    "01-01-37": "EtherCAT 從站初始指令回應錯誤 (EtherCAT slave initial command response error)",
    "01-01-38": "EtherCAT 信箱超時 (EtherCAT mailbox timed out)",
    "01-01-39": "EtherCAT 信箱 SDO 取消 (EtherCAT mailbox SDO canceled)",
    "01-01-3A": "EtherCAT 信箱 COE 工作計數器接收錯誤 (EtherCAT mailbox COE work counter received error)",
    "01-01-3B": "EtherCAT 信箱 COE 工作計數器傳輸錯誤 (EtherCAT mailbox COE work counter transmission error)",
    "01-01-3C": "EtherCAT 信箱接收到無效資料 (EtherCAT mailbox receives invalid data)",
    "01-01-3D": "EtherCAT 主站警報 (EtherCAT master alarm)",
    "01-01-3E": "系統錯誤記憶體配置 (system error memory configuration)", # 描述不完整，按原文
    "01-01-40": "軸 1 參數設定失敗 (Axis 1 parameter setting failed)",
    "01-01-41": "軸 2 參數設定失敗 (Axis 2 parameter setting failed)",
    "01-01-42": "軸 3 參數設定失敗 (Axis 3 parameter setting failed)",
    "01-01-43": "軸 4 參數設定失敗 (Axis 4 parameter setting failed)",
    "01-01-44": "軸 5 參數設定失敗 (Axis 5 parameter setting failed)",
    "01-01-54": "外部參數初始化失敗 (External parameter initialization failed)",
    "01-01-55": "HWS 載入功能失敗 (HWS loading function failed)", # v1.40 新增
    "01-01-57": "HWS 關機錯誤 (HWS shutdown error)", # v1.40 新增
    "01-01-58": "FBWF 記憶體消耗 128 MB (FBWF memory consumes 128 MB)",
    "01-01-59": "FBWF 記憶體消耗 512 MB (FBWF memory consumption 512 MB)",
    "01-01-5A": "FBWF 檔案開啟失敗 (FBWF file failed to open)",
    "01-01-60": "E-CAT 裝置錯誤 - 輸入裝置數量不一致 (E-CAT device error - Input device count inconsistent)",
    "01-01-61": "E-CAT 裝置錯誤 - 輸入裝置順序不一致 (E-CAT device error - Input device order inconsistent)",
    "01-01-62": "E-CAT 裝置錯誤 - 輸入點數不一致 (E-CAT device error - Input point count inconsistent)",
    "01-01-63": "E-CAT 裝置錯誤 - 輸出裝置數量不一致 (E-CAT device error - Output device count inconsistent)",
    "01-01-64": "E-CAT 裝置錯誤 - 輸出裝置順序不一致 (E-CAT device error - Output device order inconsistent)",
    "01-01-65": "E-CAT 裝置錯誤 - 輸出點數不一致 (E-CAT device error - Output point count inconsistent)",
    "01-01-70": "E-CAT 軸 1 斷線 (E-CAT axis 1 disconnection)",
    "01-01-71": "E-CAT 軸 2 斷線 (E-CAT axis 2 disconnection)",
    "01-01-72": "E-CAT 軸 3 斷線 (E-CAT axis 3 disconnection)",
    "01-01-73": "E-CAT 軸 4 斷線 (E-CAT axis 4 disconnection)",
    "01-01-74": "E-CAT 軸 5 斷線 (E-CAT axis 5 disconnection)",
    "01-01-76": "E-CAT E1 斷線 (E-CAT E1 disconnection)",
    "01-01-77": "E-CAT E2 斷線 (E-CAT E2 disconnection)",
    "01-01-78": "E-CAT E3 斷線 (E-CAT E3 disconnection)",
    "01-01-80": "外部軸無限旋轉設定失敗 (External axis infinite rotation setting failed)",
    "01-01-81": "外部軸必須設為同步模式 (External axes must be set to synchronous mode)",
    "01-01-82": "外部軸必須設為非同步模式 (External axes must be set to asynchronous mode)",
    "01-01-83": "外部軸運動學模式錯誤 (External axis kinematic pattern error)",
    "01-01-84": "錯誤的外部軸追蹤編號 (Wrong external axis tracking number)",
    "01-01-85": "外部軸移動基底錯誤 (External axis moving base error)",
    # --- Program error (01-02-XX) ---
    "01-02-01": "指令語法錯誤 (command syntax error)",
    "01-02-02": "指令站點錯誤 (command station error)",
    "01-02-03": "指令軸名稱錯誤 (Command axis name error)",
    "01-02-04": "指令群組錯誤 (command group error)",
    "01-02-05": "指令參數錯誤 (instruction argument error)",
    "01-02-06": "位置超出極限 (position over limit)",
    "01-02-07": "指令參數數量錯誤 (wrong number of instruction arguments)",
    "01-02-08": "指令參數類型錯誤 (wrong instruction argument type)",
    "01-02-09": "指令佇列溢位 (instruction overflows on column)",
    "01-02-0A": "瞬時掉片警報 (Instant drop alarm)",
    "01-02-0B": "指令長度過長 (Command length is too long)",
    "01-02-0C": "檢查 Wafer 錯誤 (Check for wafer errors)",
    "01-02-0D": "速度設定超出極限 (Speed setting over limit)",
    "01-02-0E": "加速度設定超出極限 (Acceleration setting over limit)",
    "01-02-0F": "減速度設定超出極限 (Deceleration setting over limit)",
    "01-02-10": "Slot 編號錯誤 (Slot number error)",
    "01-02-11": "T 軸超出極限 (T axis overlimit)",
    "01-02-12": "R 軸超出極限 (R axis overlimit)",
    "01-02-13": "Z 軸超出極限 (Z axis overlimit)",
    "01-02-14": "W 軸超出極限 (W axis overlimit)",
    "01-02-15": "H 軸超出極限 (H axis overlimit)",
    "01-02-16": "L 軸超出極限 (L axis overlimit)", # 手冊未明確定義 L 軸，可能為筆誤或特定型號
    "01-02-17": "U 軸超出極限 (U axis overlimit)", # 手冊未明確定義 U 軸，可能為筆誤或特定型號
    "01-02-20": "時間設定錯誤 (Time setting error)", # v1.40 新增
    "01-02-21": "軟體極限超出限制 (Software limit over limit)", # v1.40 新增
    "01-02-22": "交握信號輸入超時 (Handshake signal input timeout)", # v1.40 新增
    "01-02-23": "交握信號輸入檢查錯誤 (Handshake signal input check error)", # v1.40 新增
    "01-02-24": "擴展輸出未設定 (Expanded output no set)", # v1.40 新增
    "01-02-25": "擴展輸入未設定 (Expanded input no set)", # v1.40 新增
    # --- Motion Error (01-03-XX) ---
    "01-03-01": "Servo on 狀態錯誤 (Servo on wrong state)",
    "01-03-02": "對 Servo off 的軸下達運動指令 (Set Motion Command to servo off axis)",
    "01-03-03": "Servo on 超時 (Servo on time out)",
    "01-03-10": "軸 1 追隨誤差超出容許範圍 (Axis 1 following error is out of tolerance)",
    "01-03-11": "軸 2 追隨誤差超出容許範圍 (Axis 2 following error is out of tolerance)",
    "01-03-12": "軸 3 追隨誤差超出容許範圍 (Axis 3 following error is out of tolerance)",
    "01-03-13": "軸 4 追隨誤差超出容許範圍 (Axis 4 following error is out of tolerance)",
    "01-03-14": "軸 5 追隨誤差超出容許範圍 (Axis 5 following error is out of tolerance)",
    "01-03-16": "軸 1 關節超出正極限 (Axis 1 joint is out of positive limit)",
    "01-03-17": "軸 1 關節超出負極限 (Axis 1 joint is out of negative limit)",
    "01-03-18": "軸 2 關節超出正極限 (Axis 2 joint is out of positive limit)",
    "01-03-19": "軸 2 關節超出負極限 (Axis 2 joint is out of negative limit)",
    "01-03-1A": "軸 3 關節超出正極限 (Axis 3 joint is out of positive limit)",
    "01-03-1B": "軸 3 關節超出負極限 (Axis 3 joint is out of negative limit)",
    "01-03-1C": "軸 4 關節超出正極限 (Axis 4 joint is out of positive limit)",
    "01-03-1D": "軸 4 關節超出負極限 (Axis 4 joint is out of negative limit)",
    "01-03-1E": "軸 5 關節超出正極限 (Axis 5 joint is out of positive limit)",
    "01-03-1F": "軸 5 關節超出負極限 (Axis 5 joint is out of negative limit)",
    "01-03-30": "卡匣座標超出軟體極限 (Cassette coordinates exceed software limits)",
    "01-03-31": "關節旋轉過快 (The joint is spinning too fast)",
    "01-03-40": "圓弧運動指令的三個參考點在同一直線上 (The three reference points of the circular motion command are on the same straight line)",
    "01-03-41": "圓弧運動指令找不到圓心 (The arc motion command cannot find the center of the circle)",
    "01-03-42": "圓弧運動指令無法計算轉置矩陣 (The arc motion command cannot calculate the transpose matrix)",
    "01-03-50": "同步 O 點佇列溢位 (Synchronous O point queue overflow)",
    "01-03-51": "同步觸發 O 點指令超出上限 (Synchronous trigger O point command exceeds the upper limit)",
    "01-03-52": "柔性教導馬達錯誤 (Compliance teaches motor errors)",
    "01-03-53": "軸 1 碰撞行為 (Collision behavior on axis 1)",
    "01-03-54": "軸 2 碰撞行為 (Collision behavior for axis 2)",
    "01-03-55": "軸 3 碰撞行為 (Collision behavior for axis 3)",
    "01-03-56": "軸 4 碰撞行為 (Collision behavior for axis 4)",
    "01-03-57": "軸 5 碰撞行為 (Collision behavior for axis 5)",
    "01-03-59": "E1 軸碰撞行為 (Collision behavior of E1 axis)",
    "01-03-5A": "E2 軸碰撞行為 (Collision behavior of E2 axis)",
    "01-03-5B": "E3 軸碰撞行為 (Collision behavior of E3 axis)",
    "01-03-63": "軸 1 加速度過高 (Axis 1 acceleration is too high)",
    "01-03-64": "軸 2 加速度過高 (Axis 2 acceleration is too high)",
    "01-03-65": "軸 3 加速度過高 (Axis 3 acceleration is too high)",
    "01-03-66": "軸 4 加速度過高 (Axis 4 acceleration is too high)",
    "01-03-67": "軸 5 加速度過高 (Axis 5 acceleration is too high)",
    "01-03-69": "運動指令無法執行 (Motion command can not execute)",
    "01-03-70": "軸 1 超出軟體下限 (Axis 1 exceeds the lower limit of the software)",
    "01-03-71": "軸 1 超出軟體上限 (Axis 1 exceeds the upper limit of the software)",
    "01-03-72": "軸 2 超出軟體下限 (Axis 2 exceeds the lower limit of the software)",
    "01-03-73": "軸 2 超出軟體上限 (Axis 2 exceeds the upper limit of the software)",
    "01-03-74": "軸 3 超出軟體下限 (Axis 3 exceeds the lower limit of the software)",
    "01-03-75": "軸 3 超出軟體上限 (Axis 3 exceeds the upper limit of the software)",
    "01-03-76": "軸 4 超出軟體下限 (Axis 4 exceeds lower software limit)",
    "01-03-77": "軸 4 超出軟體上限 (Axis 4 exceeds the upper limit of the software)",
    "01-03-78": "軸 5 超出軟體下限 (Axis 5 exceeds lower software limit)",
    "01-03-79": "軸 5 超出軟體上限 (Axis 5 exceeds the upper limit of the software)",
    "01-03-7C": "工具中心超出 X 軟體下限 (Tool Center exceeds X software lower limit)",
    "01-03-7D": "工具中心超出 X 軟體上限 (Tool Center exceeds X software upper limit)",
    "01-03-7E": "工具中心超出 Y 軟體下限 (Tool center exceeds lower limit of Y software)",
    "01-03-7F": "工具中心超出 Y 軟體上限 (Tool center exceeds upper limit of Y software)",
    "01-03-80": "工具中心超出 Z 軟體下限 (Tool center exceeds the lower limit of the Z software)",
    "01-03-81": "工具中心超出 Z 軟體上限 (Tool center exceeds the upper limit of the Z software)",
    "01-03-82": "工具中心超出半徑軟體下限 (Tool center exceeds radius software lower limit)",
    "01-03-83": "工具中心超出半徑軟體上限 (The tool center exceeds the upper limit of the radius software)",
    "01-03-86": "激磁超時 (Excitation timeout)",
    "01-03-87": "軸 1 扭矩超出最大設定值 (Axis 1 torque exceeds the maximum set value)",
    "01-03-88": "軸 2 扭矩超出最大設定值 (Axis 2 torque exceeds the maximum set value)",
    "01-03-89": "軸 3 扭矩超出最大設定值 (Axis 3 torque exceeds the maximum set value)",
    "01-03-8A": "軸 4 扭矩超出最大設定值 (Axis 4 torque exceeds the maximum set value)",
    "01-03-8B": "軸 5 扭矩超出最大設定值 (Axis 5 torque exceeds the maximum set value)",
    "01-03-8D": "Servo 未就緒 (Servo not ready)",
    "01-03-8F": "運動中止 (Motion aborted)",
    "01-03-90": "取片錯誤 (Get wafer error)",
    "01-03-91": "放片錯誤 (Put wafer error)",
    "01-03-92": "中止運動超時 (Abort motion time out)",
    "01-03-93": "電夾繁忙 (Electric grip busy)",
    "01-03-94": "電夾未夾持 (Electric grip hold)", # 描述似乎與 hold 相反
    "01-03-95": "電夾釋放錯誤 (Electric grip release error)",
    "01-03-96": "電夾 Home 失敗 (Electric grip home failed)",
    "01-03-97": "電夾超出距離 (Electric grip over distance)",
    "01-03-98": "電夾位置錯誤 (Electric grip pos error)",
    "01-03-A0": "電翻緊急錯誤 (Electric flip emergency error)",
    "01-03-A1": "電翻未回 Home 錯誤 (Electric flip not back home error)",
    "01-03-A2": "電翻重置錯誤 (Electric flip reset error)",
    "01-03-A3": "電翻未到位錯誤 (Electric flip not in place error)",
    "01-03-A4": "電翻超出正極限錯誤 (Electric flip over positive limit error)",
    "01-03-A5": "電翻超出負極限錯誤 (Electric flip over negtive limit error)",
    "01-03-A6": "電翻位置錯誤 (Electric flip position error)",
    "01-03-A7": "真空狀態錯誤 (Vacuum state error)",
    "01-03-A8": "光纖狀態錯誤 (Fiber state error)",
    "01-03-A9": "正壓狀態錯誤 (Pressure state error)",
    "01-03-B0": "磁簧開關狀態錯誤 (Reed Switch state error)",
    "01-03-B1": "夾爪狀態錯誤 (Grip state error)",
    "01-03-B2": "R 軸真空 1 狀態錯誤 (R axis vacuum 1 state error)",
    "01-03-B3": "R 軸真空 2 狀態錯誤 (R axis vacuum 2 state error)",
    "01-03-B4": "R 軸真空 3 狀態錯誤 (R axis vacuum 3 state error)",
    "01-03-B5": "R 軸真空 4 狀態錯誤 (R axis vacuum 4 state error)",
    "01-03-B6": "R 軸真空 5 狀態錯誤 (R axis vacuum 5 state error)",
    "01-03-B7": "R 軸光纖 1 狀態錯誤 (R axis fiber 1 state error)",
    "01-03-B8": "R 軸光纖 2 狀態錯誤 (R axis fiber 2 state error)",
    "01-03-B9": "R 軸光纖 3 狀態錯誤 (R axis fiber 3 state error)",
    "01-03-BA": "R 軸光纖 4 狀態錯誤 (R axis fiber 4 state error)",
    "01-03-BB": "R 軸光纖 5 狀態錯誤 (R axis fiber 5 state error)",
    "01-03-BC": "R 軸正壓狀態錯誤 (R axis pressure state error)",
    "01-03-BD": "R 軸磁簧開關 1 狀態錯誤 (R axis reed switch 1 state error)",
    "01-03-BE": "R 軸磁簧開關 2 狀態錯誤 (R axis reed switch 2 state error)",
    "01-03-BF": "R 軸夾爪 1 狀態錯誤 (R axis grip 1 state error)", # 手冊原文 aixis
    "01-03-C0": "R 軸夾爪 2 狀態錯誤 (R axis grip 2 state error)", # 手冊原文 aixis
    "01-03-C1": "W 軸真空 1 狀態錯誤 (W axis vacuum 1 state error)",
    "01-03-C2": "W 軸真空 2 狀態錯誤 (W axis vacuum 2 state error)",
    "01-03-C3": "W 軸真空 3 狀態錯誤 (W axis vacuum 3 state error)",
    "01-03-C4": "W 軸真空 4 狀態錯誤 (W axis vacuum 4 state error)",
    "01-03-C5": "W 軸真空 5 狀態錯誤 (W axis vacuum 5 state error)",
    "01-03-C6": "W 軸光纖 1 狀態錯誤 (W axis fiber 1 state error)",
    "01-03-C7": "W 軸光纖 2 狀態錯誤 (W axis fiber 2 state error)",
    "01-03-C8": "W 軸光纖 3 狀態錯誤 (W axis fiber 3 state error)",
    "01-03-C9": "W 軸光纖 4 狀態錯誤 (W axis fiber 4 state error)",
    "01-03-CA": "W 軸光纖 5 狀態錯誤 (W axis fiber 5 state error)",
    "01-03-CB": "W 軸正壓狀態錯誤 (W axis pressure state error)",
    "01-03-CC": "W 軸磁簧開關 1 狀態錯誤 (W axis reed switch 1 state error)",
    "01-03-CD": "W 軸磁簧開關 2 狀態錯誤 (W axis reed switch 2 state error)",
    "01-03-CE": "W 軸夾爪 1 狀態錯誤 (W axis grip 1 state error)", # 手冊原文 R aixis
    "01-03-CF": "W 軸夾爪 2 狀態錯誤 (W axis grip 2 state error)", # 手冊原文 R aixis
    "01-03-D0": "同步輸入檢查錯誤 (Sync input check error)",
    "01-03-D1": "電夾緊急停止錯誤 (Electric variable emg Error)", # v1.40 新增
    "01-03-D2": "電夾未回 Home 錯誤 (Electric variable not back home error)", # v1.40 新增
    "01-03-D3": "電夾回 Home 錯誤 (Electric variable back home error)", # v1.40 新增
    "01-03-D4": "電夾位置錯誤 (Electric variable pos error)", # v1.40 新增
    "01-03-D5": "電夾超出正極限錯誤 (Electric variable over pos limit error)", # v1.40 新增
    "01-03-D6": "電夾超出負極限錯誤 (Electric variable over neg limit error)", # v1.40 新增
    "01-03-D7": "電夾位置偏移 (Electric variable pos offset)", # v1.40 新增
    "01-03-D8": "T 軸位置差異過大 (T-axis position difference is too large)", # v1.40 新增
    "01-03-D9": "工作臂未返回原點 (The working arm has not returned to the home point)", # v1.40 新增
    "01-03-DA": "電翻不在安全位置 (The electric flipper is not in a safe position)", # v1.40 新增
    "01-03-DB": "氣翻未翻到頂部 (The air flip does not turn to the top)", # v1.40 新增
    "01-03-DC": "氣翻未翻到底部 (The air flip does not turn to the down)", # v1.40 新增
    "01-03-DD": "回 Home 未完成 (Return to home position not completed)", # v1.40 新增
    "01-03-DE": "R 軸氣翻位置異常 (Abnormal R-axis air flip position)", # v1.40 新增
    "01-03-DF": "W 軸氣翻位置異常 (Abnormal W-axis air flip position)", # v1.40 新增
    "01-03-E0": "位置檢查錯誤 (Position check error)",
    "01-03-E1": "翻轉軸不在安全位置 (The flip axis is not in a safe position)",
    "01-03-E2": "電翻不在允許位置 (The electric flipper is not in the allowed position)",
    "01-03-E3": "Slot 不允許 (The slot not allowed)",
    # --- Operation Error (01-04-XX) ---
    "01-04-10": "讀取驅動 1 編碼器異常 (Reading drive 1 encoder is abnormal)",
    "01-04-11": "讀取驅動 2 編碼器異常 (Reading drive 2 encoder is abnormal)",
    "01-04-12": "讀取驅動 3 編碼器異常 (Read drive 3 encoder abnormal)",
    "01-04-13": "讀取驅動 4 編碼器異常 (Error reading drive 4 encoder)",
    "01-04-14": "讀取驅動 5 編碼器異常 (Read drive 5 encoder abnormal)",
    "01-04-16": "寫入驅動 1 資料異常 (The data written to drive 1 is abnormal)",
    "01-04-17": "寫入驅動 2 資料異常 (The data written to drive 2 is abnormal)",
    "01-04-18": "寫入驅動 3 資料異常 (The data written to drive 3 is abnormal)",
    "01-04-19": "寫入驅動 4 資料異常 (The data written to drive 4 is abnormal)",
    "01-04-1A": "寫入驅動 5 資料異常 (The data written to drive 5 is abnormal)",
    "01-04-1C": "清除編碼器 1 資料異常 (Clear the data abnormality of encoder 1)",
    "01-04-1D": "清除編碼器 2 資料異常 (data abnormality of encoder 2)",
    "01-04-1E": "清除編碼器 3 資料異常 (data abnormality of encoder 3)",
    "01-04-1F": "清除編碼器 4 資料異常 (Clear encoder 4 data exception)",
    "01-04-20": "清除編碼器 5 資料異常 (data abnormality of encoder 5)",
    "01-04-30": "起始位置偏差異常 (Start position deviation is abnormal)",
    "01-04-31": "軸 1 位置偏差異常 (axis 1 is abnormal)", # 描述不完整
    "01-04-32": "軸 2 位置偏差異常 (Axis 2 position deviation is abnormal)",
    "01-04-33": "軸 3 位置偏差異常 (Axis 3 position deviation is abnormal)",
    "01-04-34": "軸 4 位置偏差異常 (Axis 4 position deviation is abnormal)",
    "01-04-35": "軸 5 位置偏差異常 (axis 5 is abnormal)", # 描述不完整
    "01-04-37": "E1 軸位置偏差異常 (E1 axis position deviation is abnormal)",
    "01-04-38": "E2 軸位置偏差異常 (E2 axis position deviation is abnormal)",
    "01-04-39": "E3 軸位置偏差異常 (E3 axis position deviation is abnormal)",
    "01-04-50": "中斷計時器溢位 (Interrupt timer overflow)",
    "01-04-51": "運動指令佇列溢位 (The motion command queue overflowed)",
    "01-04-52": "寸動動作佇列溢位 (The inch action queue overflows)",
    "01-04-53": "插補暫存緩衝區溢位 (Interpolation scratch buffer overflow)",
    # --- IO & Communication Error (01-05-XX) ---
    "01-05-10": "TP 連線異常 (TP connection is abnormal)",
    "01-05-11": "無 TP 致能信號 (No TP enable singnal)",
    "01-05-20": "Robot IO 連線異常 (Robot IO connection is abnormal)",
    "01-05-21": "Robot IO 連線中斷 (The Robot IO connection is disconnected)",
    "01-05-30": "網路斷線 (Internet disconnection)",
    "01-05-31": "網路連線失敗 (Internet connection failed)",
    "01-05-32": "伺服器啟動失敗 (Server startup failed)",
    "01-05-33": "伺服器已關閉 (Server is down)",
    "01-05-34": "網路埠設定錯誤 (The network port is set incorrectly)",
    "01-05-35": "網路客戶端斷線超時 (Network client disconnection timeout)",
    "01-05-36": "現場總線通道 1 接線失敗 (Fieldbus channel 1 wiring failed)", # Fieldbus?
    "01-05-37": "現場總線通道 2 接線失敗 (Fieldbus channel 2 wiring failed)",
    "01-05-38": "現場總線通道 1 通訊錯誤 (Fieldbus channel 1 communication error)",
    "01-05-39": "現場總線通道 2 通訊錯誤 (Fieldbus channel 2 communication error)",
    "01-05-40": "現場總線通道 1 連線超時 (Fieldbus channel 1 connection timed out)",
    "01-05-41": "現場總線通道 2 連線超時 (Fieldbus channel 2 connection timed out)",
    "01-05-42": "序列 IO 斷線 (Serial IO disconnection)",
    "01-05-43": "序列 IO 讀寫錯誤 (Serial IO read/write error)",
    "01-05-51": "脈衝數超出限制 (The number of pulses exceeds the limit)", # v1.40 新增
    "01-05-55": "序列通訊開啟錯誤 (Serial communication opening error)", # v1.40 新增
    "01-05-56": "序列通訊埠錯誤 (Serial communication port error)", # v1.40 新增
    "01-05-57": "序列通訊設定參數異常 (Abnormal serial communication setting parameters)", # v1.40 新增
    # --- IO & Operator Error (01-06-XX) ---
    "01-06-10": "運動延遲指令異常 (The motion delay command is abnormal)",
    "01-06-11": "加速度設定指令異常 (The acceleration setting command is abnormal)",
    "01-06-12": "點對點運動指令異常 (The point-to-point motion command is abnormal)",
    "01-06-13": "圓弧運動指令異常 (The arc motion command is abnormal)",
    "01-06-14": "直線運動指令異常 (The linear motion command is abnormal)",
    "01-06-15": "進給率設定指令異常 (The feedrate setting command is abnormal)",
    "01-06-16": "路徑異常 (Path is abnormal)",
    "01-06-19": "平滑運動啟動錯誤 (Smooth motion start error)",
    "01-06-1A": "平滑運動關閉錯誤 (Smooth motion off error)",
    # --- External Axis Error (01-07-XX) ---
    "01-07-10": "E1 軸追隨誤差超出容許範圍 (The following error of the E1 axis is out of the allowable range)",
    "01-07-11": "E2 軸追隨誤差超出容許範圍 (The following error of the E2 axis is out of the allowable range)",
    "01-07-12": "E3 軸追隨誤差超出容許範圍 (The following error of the E3 axis is out of the allowable range)",
    "01-07-13": "E1 軸關節超出正極限 (The E1 axis joint is out of the positive limit)",
    "01-07-14": "E1 軸關節超出負極限 (The E1 axis joint exceeds the negative limit)",
    "01-07-15": "E2 軸關節超出正極限 (The E2 axis joint is out of the positive limit)",
    "01-07-16": "E2 軸關節超出負極限 (The E2 axis joint is out of the negative limit)",
    "01-07-17": "E3 軸關節超出正極限 (The E3 axis joint is out of the positive limit)",
    "01-07-18": "E3 軸關節超出負極限 (The E3 axis joint is out of the negative limit)",
    "01-07-19": "E1 軸清除編碼器資料異常 (E1 axis clearing encoder data is abnormal)",
    "01-07-1A": "E2 軸清除編碼器資料異常 (E2 axis clearing encoder data is abnormal)",
    "01-07-1B": "E3 軸清除編碼器資料異常 (E3 axis clearing encoder data is abnormal)",
    "01-07-1C": "E1 軸加速度過大 (E1 axis acceleration is too large)",
    "01-07-1D": "E2 軸加速度過大 (E2 axis acceleration is too large)",
    "01-07-1E": "E3 軸加速度過大 (E3 axis acceleration is too large)",
    "01-07-1F": "E1 扭矩超出最大設定值 (E1 torque exceeds the maximum set value)",
    "01-07-20": "E2 扭矩超出最大設定值 (E2 Torque exceeds the maximum set value)",
    "01-07-21": "E3 扭矩超出最大設定值 (E3 Torque exceeds the maximum set value)",
    "01-07-22": "H 無法執行 Homing (H cannot execute homing)", # v1.40 新增
    "01-07-23": "H Homing 編碼器規格錯誤 (H encoder specification error for homing)", # v1.40 新增
    "01-07-24": "H 驅動器不支援 Homing (H driver does not support homing)", # v1.40 新增
    "01-07-25": "H Homing 方法錯誤 (H homing method error)", # v1.40 新增
    "01-07-26": "H Homing 模式錯誤 (H homing mode error)", # v1.40 新增
    "01-07-27": "H Homing 失敗 (H homing failed)", # v1.40 新增
    # --- Database Error (01-0D-XX) ---
    "01-0D-10": "資料庫版本錯誤 (Database version error)",
    # --- Safety Input (02-01-XX) ---
    "02-01-10": "緊急停止輸入 (Emergency stop input)",
    "02-01-11": "致能開關按下 (Enable switch down)", # 描述似乎與按下相反
    "02-01-12": "功能輸入停止 (Function input stop)",
    "02-01-13": "無遠端控制輸入 (No remote control input)", # v1.40 新增
    "02-01-14": "無 Servo on 輸入 (No servo on input)", # v1.40 新增
    # --- Hardware Error (02-02-XX) ---
    "02-02-11": "無釋放煞車信號 (No release brake signal)",
    # --- Axis amplifier (03-XX-XX) ---
    # 這裡的 m 代表軸編號 (1-5), n 代表外部軸編號 (1-3)
    # 為了簡化，只列出通用格式，實際使用時需替換 m 或 En
    "03-0m(En)-21": "過電流 (Overcurrent)",
    "03-0m(En)-22": "速度回授錯誤 (Velocity feedback error)",
    "03-0m(En)-25": "STO (安全轉矩關閉) (STO)",
    "03-0m(En)-26": "安全轉矩關閉異常 (Safe Torque Off Abnormal)",
    "03-0m(En)-27": "單迴路 STO (Single circuit STO)",
    "03-0m(En)-30": "電流控制錯誤 (Current control error)",
    "03-0m(En)-32": "HFLT 不一致 (Inconsistent HFLT)",
    "03-0m(En)-34": "DC 匯流排電壓異常 (Abnormal DC bus voltage)",
    "03-0m(En)-35": "無法偵測 ECAT 介面 (ECAT interface cannot be detected)",
    "03-0m(En)-36": "CiA-402 回歸錯誤 (CiA-402 regression error)",
    "03-0m(En)-37": "風扇錯誤 (fan error)",
    "03-0m(En)-38": "絕對編碼器錯誤 (Absolute encoder error)",
    "03-0m(En)-41": "過載 (overload)",
    "03-0m(En)-43": "再生過載 (Regeneration overload)",
    "03-0m(En)-45": "過速度 (overspeed)",
    "03-0m(En)-51": "驅動器溫度異常 (Drive temperature is abnormal)",
    "03-0m(En)-52": "突波抑制電阻過熱 (Anti-surge resistor overheating)",
    "03-0m(En)-53": "動態煞車電阻過熱 (Dynamic brake resistor overheated)",
    "03-0m(En)-58": "驅動器過熱 (The drive is overheating)",
    "03-0m(En)-61": "過電壓 (Overvoltage)",
    "03-0m(En)-62": "主迴路電壓不足 (Main circuit voltage is insufficient)",
    "03-0m(En)-71": "控制電源電壓不足 (Insufficient control power supply voltage)",
    "03-0m(En)-72": "控制迴路電壓不足 (The control circuit voltage is insufficient)",
    "03-0m(En)-81": "編碼器斷線異常 (The encoder is disconnected abnormally)",
    "03-0m(En)-84": "編碼器通訊異常 (The encoder communication is abnormal)",
    "03-0m(En)-85": "編碼器初始化異常 (5V 異常) (The encoder initialization is abnormal (5V abnormal))",
    "03-0m(En)-87": "編碼器 CS 信號異常 (The encoder CS signal is abnormal)",
    "03-0m(En)-A1": "編碼器多圈資料異常 (電池異常) (The encoder multi-turn data is abnormal (battery abnormality))",
    "03-0m(En)-A3": "編碼器過速度 (Encoder overspeed)",
    "03-0m(En)-A5": "編碼器單圈計數異常 (The encoder single-turn count is abnormal)",
    "03-0m(En)-A6": "編碼器多圈計數異常 (The encoder multi-turn count is abnormal)",
    "03-0m(En)-A9": "編碼器過熱 (Encoder overheated)",
    "03-0m(En)-AB": "編碼器異常 (Encoder exception)",
    "03-0m(En)-C1": "過速度 (speeding)", # 與 45 相似
    "03-0m(En)-D1": "位置偏差過大 (The position deviation is too large)",
    "03-En-D2": "外部軸已達正極限 (external axis has reached the positive limit of the encoder)",
    "03-En-D3": "外部軸已達負極限 (The external axis has reached the negative limit of the encoder)",
    "03-0m(En)-E1": "EEPROM 異常 (EEPROM is abnormal)",
    "03-0m(En)-E2": "EEPROM 檢查異常 (EEPROM check is abnormal)",
    "03-0m(En)-EF": "馬達不匹配 (Motor does not match)",
    "03-0m(En)-F3": "驅動器警示 (Drive alert)",
    "03-0m(En)-F4": "軟體溫度極限到達 (Soft body temperature limit reached)",
    "03-0m(En)-F5": "馬達無法接線 (The motor cannot be wired)",
    "03-0m(En)-F6": "驅動器相位初始錯誤 (Drive phase initial error)",
    "03-0m(En)-F7": "霍爾感測器錯誤 (Hall sensor error)",
    "03-0m(En)-F8": "霍爾相位檢查錯誤 (Hall phase check error)",
    "03-0m(En)-F9": "過載警告 (Overload warning)", # 警告，不停機
    "03-0m(En)-FA": "放大器過熱警告 (Amplifier overheat warning)", # 警告，不停機
    "03-0m(En)-FB": "再生過載警告 (Regeneration overload warning)", # 警告，不停機
    "03-0m(En)-FC": "無法偵測電源 (Failed to detect power)", # 警告，不停機
    "03-0m(En)-FD": "主電源電壓異常 (Abnormal mains voltage)", # 警告，不停機
    "03-0m(En)-FE": "電池電量低 (The battery is low)", # 警告，不停機
    "03-0m(En)-FF": "電池已耗盡 (The battery is empty)",
    # --- DAC-S Error Code (S-XXXX) ---
    "S-3110": "電源過電壓 (Power supply overvoltage)",
    "S-3130": "主電源相位錯誤 (Mains phase error)",
    "S-3211": "過電壓 (Overvoltage)",
    "S-3212": "再生電阻過載 (Regenerative resistor overload)",
    "S-3220": "主迴路低電壓 (Main circuit low voltage)",
    "S-4110": "驅動器溫度錯誤 (drive temperature error)",
    "S-4210": "突波抑制電阻過熱 (Anti-surge resistor overheating)",
    "S-5113": "控制電源低電壓 2 (Control Power Supply Low Voltage 2)",
    "S-5114": "控制電源低電壓 (Control power supply low voltage)",
    "S-5115": "控制電源低電壓 1 (Control Power Supply Low Voltage 1)",
    "S-5210": "電流偵測異常 (Abnormal current detection)",
    "S-5220": "系統錯誤 (system error)",
    "S-5400": "主電源供應裝置錯誤 (Mains power supply device error)",
    "S-5510": "記憶體錯誤 (memory error)",
    "S-5530": "EEPROM 錯誤 (EEPROM error)",
    "S-6010": "初始化執行緒超時 (Initialization thread timed out)",
    "S-6310": "EEPROM 檢查碼錯誤 (EEPROM check code error)",
    "S-6320": "系統參數錯誤 (System parameter error)",
    "S-7120": "馬達溫度錯誤 (Motor temperature error)",
    "S-7122": "速度回授錯誤 (Speed feedback error)",
    "S-7300": "編碼器初始化失敗 (Encoder initialization failed)",
    "S-7305": "編碼器接頭 1 斷線 (Encoder connector 1 broken wire)",
    "S-7510": "通訊錯誤 (communication error)",
    "S-7520": "連結遺失 (link lost)",
    "S-8311": "過載 (overload)",
    "S-8312": "STO 安全轉矩關閉異常 (STO Safe Torque Off Abnormal)",
    "S-8400": "平均連續速度超速 (Average Continuous Speed Overspeed)",
    "S-8500": "位置指令錯誤 (location command error)",
    "S-8611": "位置偏差過大 (Position deviation is too large)",
    "S-8700": "任務執行緒錯誤 (task thread error)",
    # --- DAC-H Error Code (H-XXXX) ---
    "H-2310": "過電流 (Overcurrent)",
    "H-3110": "過電壓 (Overvoltage)",
    "H-8611": "位置錯誤過大 (Position error is too large)",
    "H-7380": "編碼器異常 (Encoder exception)",
    "H-2350": "軟體溫度極限到達 (Soft body temperature limit reached)",
    "H-7180": "馬達無法連接 (The motor cannot be connected)",
    "H-4310": "驅動器溫度異常 (Abnormal drive temperature)",
    "H-3220": "主迴路電壓不足 (Insufficient main circuit voltage)",
    "H-5280": "編碼器初始化異常 (5V 異常) (Encoder initialization abnormal (5V abnormal))",
    "H-FF06": "驅動器相位初始錯誤 (Drive phase initial error)",
    "H-7381": "編碼器通訊錯誤 (Encoder communication error)",
    "H-FF02": "電流控制錯誤 (Current control error)",
    "H-FF03": "STO 觸發 (STO trigger)",
    "H-FF04": "HFLT 不一致 (Inconsistent HFLT)",
    "H-3210": "DC 匯流排電壓異常 (Abnormal DC bus voltage)", # 與 03-0m(En)-34 相似
    "H-7580": "無法偵測 ECAT 介面 (ECAT interface cannot be detected)", # 與 03-0m(En)-35 相似
    "H-8613": "CiA-402 返回原點錯誤 (CiA-402 Return to origin error)", # 與 03-0m(En)-36 相似
    "H-5180": "風扇錯誤 (fan error)", # 與 03-0m(En)-37 相似
    "H-FF07": "絕對編碼器錯誤 (Absolute encoder error)", # 與 03-0m(En)-38 相似
}

def get_error_description(error_code):
    """
    根據錯誤代碼查找對應的描述。

    Args:
        error_code (str): 從 EFEM 收到的錯誤代碼字串。

    Returns:
        str: 對應的錯誤描述，如果找不到則返回通用提示。
    """
    # 嘗試直接匹配
    description = ERROR_CODES.get(error_code)
    if description:
        return description

    # 嘗試處理 A 系列 Robot 的通用代碼 (例如 03-0m(En)-XX)
    # 注意：這部分比較複雜，因為需要知道軸號碼 (m) 或外部軸號 (En)
    # 為了簡化，我們先查找是否存在通用格式的鍵
    if error_code.startswith("03-") and len(error_code.split('-')) == 3:
        parts = error_code.split('-')
        generic_code_m = f"03-0m(En)-{parts[2]}" # 通用軸格式
        generic_code_en = f"03-En-{parts[2]}"     # 通用外部軸格式
        description = ERROR_CODES.get(generic_code_m) or ERROR_CODES.get(generic_code_en)
        if description:
            # 可以選擇在描述中加入軸信息，但需要解析 parts[1]
            axis_info = parts[1]
            return f"{description} (軸/Axis: {axis_info})"

    # 如果都找不到，返回未知錯誤
    return f"未知的錯誤代碼 ({error_code})"

# --- 可選：測試函數 ---
if __name__ == '__main__':
    print(f"0001: {get_error_description('0001')}")
    print(f"3004: {get_error_description('3004')}")
    print(f"A001: {get_error_description('A001')}")
    print(f"9999: {get_error_description('9999')}") # 測試未知代碼
    print(f"01-01-21: {get_error_description('01-01-21')}") # 測試 A 系列代碼
    print(f"03-01-21: {get_error_description('03-01-21')}") # 測試通用格式代碼
    print(f"03-E1-D2: {get_error_description('03-E1-D2')}") # 測試通用格式代碼

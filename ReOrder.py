def redistribute_spindles(spindle_count, dice_count):
    # 生成所有dice的編號
    all_dice = [f'U{i}' for i in range(dice_count)]

    # 初始分配（假設每個spindle負責的dice數量是平均的）
    original_allocation = {}
    dice_per_spindle = dice_count // 7  # 假設原本有7個spindle
    remainder = dice_count % 7

    current_dice_index = 0
    for spindle in range(1, 8):  # 原本有7個spindle
        count = dice_per_spindle + (1 if spindle <= remainder else 0)
        original_allocation[spindle] = all_dice[current_dice_index:current_dice_index + count]
        current_dice_index += count

    # 如果spindle數量不變，直接返回原始分配
    if spindle_count == 7:
        return original_allocation, original_allocation

    # 計算新的分配
    new_allocation = {i: [] for i in range(1, spindle_count + 1)}

    # 將原有的spindle分配到新的spindle，盡量保持原有的dice列表
    for spindle, dice_list in original_allocation.items():
        # 計算新的spindle編號（將7個spindle映射到新的spindle數量）
        new_spindle = ((spindle - 1) % spindle_count) + 1
        new_allocation[new_spindle].extend(dice_list)

    # 檢查是否所有dice都被分配
    total_dice = sum(len(dice_list) for dice_list in new_allocation.values())
    if total_dice != dice_count:
        raise ValueError("分配錯誤：dice數量不符。")

    # 平衡分配（確保每個spindle的dice數量盡量平均）
    dice_per_new_spindle = dice_count // spindle_count
    remainder_new = dice_count % spindle_count

    # 計算每個spindle應該負責的dice數量
    target_counts = [dice_per_new_spindle + (1 if i <= remainder_new else 0) for i in range(1, spindle_count + 1)]

    # 調整分配，確保每個spindle的dice數量符合目標
    for spindle in new_allocation:
        current_count = len(new_allocation[spindle])
        target_count = target_counts[spindle - 1]

        if current_count < target_count:
            # 從其他spindle移動dice到當前spindle
            for other_spindle in new_allocation:
                if other_spindle != spindle and len(new_allocation[other_spindle]) > target_counts[other_spindle - 1]:
                    move_count = min(target_count - current_count, len(new_allocation[other_spindle]) - target_counts[other_spindle - 1])
                    new_allocation[spindle].extend(new_allocation[other_spindle][-move_count:])
                    new_allocation[other_spindle] = new_allocation[other_spindle][:-move_count]
                    current_count += move_count
                    if current_count == target_count:
                        break

        elif current_count > target_count:
            # 從當前spindle移動dice到其他spindle
            move_count = current_count - target_count
            for other_spindle in new_allocation:
                if other_spindle != spindle and len(new_allocation[other_spindle]) < target_counts[other_spindle - 1]:
                    move_possible = min(move_count, target_counts[other_spindle - 1] - len(new_allocation[other_spindle]))
                    new_allocation[other_spindle].extend(new_allocation[spindle][-move_possible:])
                    new_allocation[spindle] = new_allocation[spindle][:-move_possible]
                    move_count -= move_possible
                    if move_count == 0:
                        break

    return original_allocation, new_allocation

def print_allocation(title, allocation):
    print(title)
    for spindle, dice in allocation.items():
        print(f"Spindle {spindle}: {dice}")
    print()

def main():
    # 輸入spindle和dice的數量
    spindle_count = int(input("請輸入新的spindle數量: "))
    dice_count = int(input("請輸入dice的數量: "))

    # 檢查輸入是否有效
    if spindle_count <= 0 or dice_count <= 0:
        print("錯誤：spindle和dice的數量必須大於0。")
        return

    # 重新分配並顯示結果
    try:
        original_allocation, new_allocation = redistribute_spindles(spindle_count, dice_count)
        print_allocation("更改前的分配:", original_allocation)
        print_allocation(f"更改後的分配 (Spindle 數量: {spindle_count}):", new_allocation)
    except ValueError as e:
        print(f"錯誤: {e}")

# 執行主程式
if __name__ == "__main__":
    main()
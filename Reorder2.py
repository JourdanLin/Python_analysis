def redistribute_spindles(spindle_count):
    # 初始分配
    original_allocation = {
        1: ['U0', 'U1', 'U2', 'U3', 'U4'],
        2: ['U5', 'U6', 'U7', 'U8', 'U9'],
        3: ['U10', 'U11', 'U12', 'U13', 'U14'],
        4: ['U15', 'U16', 'U17', 'U18', 'U19'],
        5: ['U20', 'U21', 'U22', 'U23', 'U24'],
        6: ['U25', 'U26', 'U27', 'U28', 'U29'],
        7: ['U30', 'U31', 'U32', 'U33', 'U34']
    }

    # 將所有dice合併成一個列表
    all_dice = [dice for spindle in original_allocation.values() for dice in spindle]

    # 計算每個spindle應該負責的dice數量
    total_dice = len(all_dice)
    dice_per_spindle = total_dice // spindle_count
    remainder = total_dice % spindle_count

    # 初始化新的分配
    new_allocation = {i: [] for i in range(1, spindle_count + 1)}

    # 重新分配dice
    current_dice_index = 0
    for spindle in new_allocation:
        # 計算當前spindle應該負責的dice數量
        count = dice_per_spindle + (1 if spindle <= remainder else 0)
        # 分配dice
        new_allocation[spindle] = all_dice[current_dice_index:current_dice_index + count]
        current_dice_index += count

    return original_allocation, new_allocation

def print_allocation(title, allocation):
    print(title)
    for spindle, dice in allocation.items():
        print(f"Spindle {spindle}: {dice}")
    print()

# 測試函數
def test_redistribution(spindle_count):
    original, new = redistribute_spindles(spindle_count)
    print_allocation("更改前的分配:", original)
    print_allocation(f"更改後的分配 (Spindle 數量: {spindle_count}):", new)

# 測試不同的spindle數量
test_redistribution(4)
test_redistribution(6)
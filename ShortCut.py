import math

# SP的初始位置
sp_positions = {
    'sp1': (1, 1),
    'sp2': (1, 2),
    'sp3': (1, 3),
    'sp4': (1, 4),
    'sp5': (1, 5),
    'sp6': (1, 6),
    'sp7': (1, 7)
}

# U點的座標
u_positions = {}
u_entries = [
    {'coords': [(100,1), (100,2), (100,3), (100,4), (100,5)], 'names': ['u1','u2','u3','u4','u5']},
    {'coords': [(101,2), (101,3), (101,4), (101,5), (101,6)], 'names': ['u6','u7','u8','u9','u10']},
    {'coords': [(102,1), (102,2), (102,3), (102,4), (102,5)], 'names': ['u11','u12','u13','u14','u15']},
    {'coords': [(103,2), (103,3), (103,4), (103,5), (103,6)], 'names': ['u16','u17','u18','u19','u20']},
    {'coords': [(104,2), (104,3), (104,4), (104,5), (104,6)], 'names': ['u21','u22','u23','u24','u25']},
    {'coords': [(105,2), (105,3), (105,4), (105,5), (105,6)], 'names': ['u26','u27','u28','u29','u30']}
]

for entry in u_entries:
    for name, coord in zip(entry['names'], entry['coords']):
        u_positions[name] = coord

# 計算SP到供給中心的初始移動距離（曼哈頓）
supply_center = (0, 4)
total_initial = 0
for sp, pos in sp_positions.items():
    dx = abs(pos[0] - supply_center[0])
    dy = abs(pos[1] - supply_center[1])
    total_initial += dx + dy

# 計算每個U點的往返距離（曼哈頓）
total_u = 0
for u, coord in u_positions.items():
    dx = abs(coord[0] - supply_center[0])
    dy = abs(coord[1] - supply_center[1])
    total_u += 2 * (dx + dy)

total_distance = total_initial + total_u

# 分配U點給SP（按順序循環分配）
sp_list = list(sp_positions.keys())
u_names = list(u_positions.keys())
assignment = {sp: [] for sp in sp_list}

for i, u in enumerate(u_names):
    sp_idx = i % 7
    assignment[sp_list[sp_idx]].append(u)

print(f"最短總移動距離: {total_distance}")
print("\nSP與U點的分配關係:")
for sp, u_list in assignment.items():
    print(f"{sp}: {', '.join(u_list)}")

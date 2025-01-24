def redistribute_dice(initial_spindles, final_spindle_count):
    """
    Redistributes dice across a reduced number of spindles.

    Args:
        initial_spindles: A list of lists, representing the initial distribution of dice on spindles.
        final_spindle_count: The desired number of spindles after redistribution.

    Returns:
        A list of lists, representing the final distribution of dice on spindles.
    """

    # Flatten the initial distribution into a single list
    all_dice = [dice for spindle in initial_spindles for dice in spindle]

    # Calculate the average number of dice per spindle
    average_load = len(all_dice) // final_spindle_count

    # Create a list to store the final distribution
    final_spindles = [[] for _ in range(final_spindle_count)]

    # Distribute dice evenly across the final spindles
    for i, dice in enumerate(all_dice):
        final_spindles[i % final_spindle_count].append(dice)

    # Adjust distribution to ensure each spindle has at least the average load
    while any(len(spindle) < average_load for spindle in final_spindles):
        for i, spindle in enumerate(final_spindles):
            if len(spindle) < average_load:
                for j, other_spindle in enumerate(final_spindles):
                    if len(other_spindle) > average_load:
                        dice_to_move = other_spindle.pop()
                        spindle.append(dice_to_move)
                        break

    return final_spindles

# Example usage:
initial_spindles = [
    ['U1', 'U8', 'U15', 'U22', 'U29'],
    ['U2', 'U9', 'U16', 'U23', 'U30'],
    ['U3', 'U10', 'U17', 'U24', 'U31'],
    ['U4', 'U11', 'U18', 'U25', 'U32'],
    ['U5', 'U12', 'U19', 'U26', 'U33'],
    ['U6', 'U13', 'U20', 'U27', 'U34'],
    ['U7', 'U14', 'U21', 'U28', 'U35']
]

# Example: Reduce to 4 spindles
final_spindles_4 = redistribute_dice(initial_spindles, 4)
print("Final distribution with 4 spindles:")
for i, spindle in enumerate(final_spindles_4):
    print(f"Sp{i+1}: {spindle}")

# Example: Reduce to 3 spindles
final_spindles_3 = redistribute_dice(initial_spindles, 3)
print("Final distribution with 3 spindles:")
for i, spindle in enumerate(final_spindles_3):
    print(f"Sp{i+1}: {spindle}")

# Example: Reduce to 2 spindles
final_spindles_2 = redistribute_dice(initial_spindles, 2)
print("Final distribution with 2 spindles:")
for i, spindle in enumerate(final_spindles_2):
    print(f"Sp{i+1}: {spindle}")
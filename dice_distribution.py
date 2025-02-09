def distribute_dice(N):
    # Generate dice serial numbers
    dice = [f"U{i+1}" for i in range(N * N)]
    
    # Initialize heads and spindles
    heads = {
        "Head1": {f"Spindle{i+1}": [] for i in range(7)},
        "Head2": {f"Spindle{i+1}": [] for i in range(7)}
    }
    
    # Distribute dice evenly
    for i, die in enumerate(dice):
        head = "Head1" if i % 2 == 0 else "Head2"
        spindle_num = (i // 2) % 7 + 1
        spindle = f"Spindle{spindle_num}"
        heads[head][spindle].append(die)
    
    return heads

def print_distribution(distribution):
    for head, spindles in distribution.items():
        print(f"\n{head}:")
        for spindle, dice in spindles.items():
            print(f"  {spindle}: {', '.join(dice)}")

if __name__ == "__main__":
    try:
        N = int(input("Enter number of circuits (N): "))
        if N <= 0:
            raise ValueError("N must be positive")
            
        distribution = distribute_dice(N)
        print("\nDice Distribution:")
        print_distribution(distribution)
        
    except ValueError as e:
        print(f"Error: {e}")

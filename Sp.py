def generate_document(num_spindles):
    if num_spindles not in [4, 5, 6, 7]:
        return "Error: Number of spindles must be between 4 and 7."

    # Define the header and structure of the document
    spindles = [f"Sp{i+1}" for i in range(num_spindles)]
    units = [f"U{i+1}" for i in range(35)]
    
    # Create the grid for distribution
    grid = []
    for i in range(0, 35, num_spindles):
        grid.append(units[i:i+num_spindles])
    
    # Handle remaining units if any
    if len(units) % num_spindles != 0:
        remaining = units[len(grid) * num_spindles:]
        while len(remaining) < num_spindles:
            remaining.append("")
        grid.append(remaining)

    # Construct the output string
    output = "<DOCUMENT>\n"
    output += "\t".join(spindles) + "\n"
    for row in grid:
        output += "\t".join(row) + "\n"
    output += "</DOCUMENT>"
    
    return output

# Main program
while True:
    try:
        num_spindles = int(input("Enter the number of spindles (4-7): "))
        if 4 <= num_spindles <= 7:
            print(generate_document(num_spindles))
            break
        else:
            print("Please enter a number between 4 and 7.")
    except ValueError:
        print("Please enter a valid integer.")
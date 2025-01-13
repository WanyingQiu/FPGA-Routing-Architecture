import csv
import math
from collections import defaultdict

# Initialize a dictionary to store grouped data
grouped_data = defaultdict(list)

# Input and output file paths
input_file = "results/vpr_results_3a_2.txt"
output_file = "results/vpr_results_3a_geo_ave_3.txt"

# Function to calculate geometric mean
def geometric_mean(values):
    return math.exp(sum(math.log(v) for v in values) / len(values))

try:
    # Read and group data
    with open(input_file, 'r') as infile:
        reader = csv.DictReader(infile)
        
        # Strip whitespace from header names for easier access
        reader.fieldnames = [header.strip() for header in reader.fieldnames]
        
        # Debug: Print cleaned header names to verify correctness
        print("Cleaned Headers detected:", reader.fieldnames)

        if not reader.fieldnames:
            raise ValueError("The input file does not have headers. Please ensure the file includes a header row.")

        # Loop through rows and group data
        for row in reader:
            # Strip whitespace from each key to ensure consistency
            key = (row["sw"], row["num_wire"], row["in_val=out_val"], row["R_metal"], row["C_metal"])
            grouped_data[key].append({
                "Avg Channel Width": float(row["Avg Channel Width"]),
                "Avg Routing Area": float(row["Avg Routing Area"]),
                "Avg Per Logic Tile": float(row["Avg Per Logic Tile"]),
                "Avg Critical Path Delay": float(row["Avg Critical Path Delay"])
            })

    # List to store the rows for sorting
    sorted_rows = []

    # Calculate geometric means and store in the list
    for key, metrics in grouped_data.items():
        # Unpack the key
        sw, num_wire, in_val_out_val, r_metal, c_metal = key
        # Calculate geometric means for each metric
        geo_avgs = {
            "Geo Avg Channel Width": round(geometric_mean([m["Avg Channel Width"] for m in metrics]), 2),
            "Geo Avg Routing Area": round(geometric_mean([m["Avg Routing Area"] for m in metrics]), 2),
            "Geo Avg Per Logic Tile": round(geometric_mean([m["Avg Per Logic Tile"] for m in metrics]), 2),
            "Geo Avg Critical Path Delay": round(geometric_mean([m["Avg Critical Path Delay"] for m in metrics]), 2),
            "Area-delay": round((geometric_mean([m["Avg Routing Area"] for m in metrics]) *
                                 geometric_mean([m["Avg Critical Path Delay"] for m in metrics])), 2)
        }
        
        # Add the row to the sorted_rows list
        sorted_rows.append({
            "sw": sw, "num_wire": num_wire, "in_val=out_val": in_val_out_val,
            "R_metal": r_metal, "C_metal": c_metal,
            **geo_avgs
        })

    # Sort the rows by the "Area-delay" column in ascending order
    sorted_rows.sort(key=lambda x: x["Area-delay"])

    # Write the sorted rows to the output file
    with open(output_file, 'w', newline='') as outfile:
        fieldnames = [
            "sw", "num_wire", "in_val=out_val", "R_metal", "C_metal",
            "Geo Avg Channel Width", "Geo Avg Routing Area",
            "Geo Avg Per Logic Tile", "Geo Avg Critical Path Delay", "Area-delay"
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        # Write all sorted rows
        writer.writerows(sorted_rows)

    print(f"Geometric averages calculated, sorted by Area-delay, and saved to {output_file}.")

except KeyError as e:
    print(f"KeyError: The column '{e.args[0]}' was not found in the input file. Check the header row and ensure it matches the script.")
except ValueError as e:
    print(f"ValueError: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

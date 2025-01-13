import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import re

# Initialize a list to store the extracted data
data = []

# Regular expression pattern to capture the fields
pattern = re.compile(
    r"(?P<FileName>[\w\/\.]+),\s*(?P<in_val_out_val>[\d\.]+),\s*(?P<AvgChannelWidth>[\d\.]+),\s*"
    r"(?P<AvgRoutingArea>[\d\.]+),\s*(?P<AvgPerLogicTile>[\d\.]+),\s*(?P<AvgCriticalPathDelay>[\d\.]+)"
)

# Read the file and extract relevant data
file_path = "results/vpr_results_2a.txt"
with open(file_path, 'r') as file:
    for line in file:
        match = pattern.search(line)
        if match:
            data.append([
                match.group("FileName"),
                float(match.group("in_val_out_val")),
                float(match.group("AvgChannelWidth")),
                float(match.group("AvgRoutingArea")),
                float(match.group("AvgPerLogicTile")),
                float(match.group("AvgCriticalPathDelay")),
            ])

# Convert the data into a DataFrame for easier manipulation
columns = ["File Name", "in_val_out_val", "Avg Channel Width", "Avg Routing Area", "Avg Per Logic Tile", "Avg Critical Path Delay"]
df = pd.DataFrame(data, columns=columns)

# Calculate geometric averages grouped by Length
grouped_geo_avg = df.groupby("in_val_out_val").agg({
    "Avg Channel Width": lambda x: np.exp(np.mean(np.log(x))),
    "Avg Routing Area": lambda x: np.exp(np.mean(np.log(x))),
    "Avg Per Logic Tile": lambda x: np.exp(np.mean(np.log(x))),
    "Avg Critical Path Delay": lambda x: np.exp(np.mean(np.log(x))),
}).reset_index()

# Save the geometric averages to a text file
geo_avg_output_file = "results/vpr_results_2a_averages.txt"
with open(geo_avg_output_file, 'w') as f:
    f.write("in_val_out_val, GeoAvg_ChannelWidth, GeoAvg_RoutingArea, GeoAve_perLogicTile, GeoAvg_CriticalPathDelay\n")
    for _, row in grouped_geo_avg.iterrows():
        f.write(f"{row['in_val_out_val']}, {row['Avg Channel Width']:.6f}, {row['Avg Routing Area']:.6f}, {row['Avg Per Logic Tile']:.6f}, {row['Avg Critical Path Delay']:.6f}\n")



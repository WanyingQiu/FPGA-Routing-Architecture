import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import re

# Initialize a list to store the extracted data
data = []

# Regular expression pattern to capture the fields
pattern = re.compile(
    r"(?P<File>[\w\/\.]+),\s*(?P<Length>\d+),\s*(?P<AvgChannelWidth>[\d\.]+),\s*"
    r"(?P<AvgRoutingArea>[\d\.]+),\s*(?P<AvgPerLogicTile>[\d\.]+),\s*(?P<AvgCriticalPathDelay>[\d\.]+)"
)

# Read the file and extract relevant data
file_path = "results/vpr_results.txt"
with open(file_path, 'r') as file:
    for line in file:
        match = pattern.search(line)
        if match:
            data.append([
                match.group("File"),
                int(match.group("Length")),
                float(match.group("AvgChannelWidth")),
                float(match.group("AvgRoutingArea")),
                float(match.group("AvgPerLogicTile")),
                float(match.group("AvgCriticalPathDelay")),
            ])

# Convert the data into a DataFrame for easier manipulation
columns = ["File Name", "Length", "Avg Channel Width", "Avg Routing Area", "Avg Per Logic Tile", "Avg Critical Path Delay"]
df = pd.DataFrame(data, columns=columns)

# Calculate geometric averages grouped by Length
grouped_geo_avg = df.groupby("Length").agg({
    "Avg Channel Width": lambda x: np.exp(np.mean(np.log(x))),
    "Avg Routing Area": lambda x: np.exp(np.mean(np.log(x))),
    "Avg Per Logic Tile": lambda x: np.exp(np.mean(np.log(x))),
    "Avg Critical Path Delay": lambda x: np.exp(np.mean(np.log(x))),
}).reset_index()

# Save the geometric averages to a text file
geo_avg_output_file = "results/vpr_results_averages.txt"
with open(geo_avg_output_file, 'w') as f:
    f.write("Length, GeoAvg_ChannelWidth, GeoAvg_RoutingArea, GeoAve_perLogicTile, GeoAvg_CriticalPathDelay\n")
    for _, row in grouped_geo_avg.iterrows():
        f.write(f"{row['Length']}, {row['Avg Channel Width']:.6f}, {row['Avg Routing Area']:.6f}, {row['Avg Per Logic Tile']:.6f}, {row['Avg Critical Path Delay']:.6f}\n")

# Plot geometric averages
# (a) Geometric Average of Channel Width vs Length
plt.figure(figsize=(10, 6))
plt.plot(grouped_geo_avg["Length"], grouped_geo_avg["Avg Channel Width"], marker='o', label="Geo Avg Channel Width")
plt.title("Geometric Average Channel Width vs Length")
plt.xlabel("Length")
plt.ylabel("Channel Width")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("results/a1_channel_width2length.png")
plt.show()

# (b) Geometric Average of Routing Area vs Length
plt.figure(figsize=(10, 6))
plt.plot(grouped_geo_avg["Length"], grouped_geo_avg["Avg Routing Area"], marker='o', label="Geo Avg Routing Area")
plt.title("Geometric Average Routing Area vs Length")
plt.xlabel("Length")
plt.ylabel("Routing Area")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("results/a1_routing_area2length.png")
plt.show()

# (c) Geometric Average of Critical Path Delay vs Length
plt.figure(figsize=(10, 6))
plt.plot(grouped_geo_avg["Length"], grouped_geo_avg["Avg Per Logic Tile"], marker='o', label="GEo Avg Per Logic Tile")
plt.title("Geometric Average Per logic tile vs Length")
plt.xlabel("Length")
plt.ylabel("Area Per logic tile")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("results/1a_avePerTile2length.png")
plt.show()

# (d) Geometric Average of Area per tile vs Length
plt.figure(figsize=(10, 6))
plt.plot(grouped_geo_avg["Length"], grouped_geo_avg["Avg Critical Path Delay"], marker='o', label="Geo Avg Critical Path Delay")
plt.title("Geometric Average Critical Path Delay vs Length")
plt.xlabel("Length")
plt.ylabel("Critical Path Delay")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("results/1a_critical_path_delay2length.png")
plt.show()

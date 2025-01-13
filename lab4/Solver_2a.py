import os
import subprocess
import re
import math
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed

# Function to modify in_val and out_val in the XML file
def modify_fc_values(xml_path, val):
    # Parse the XML file
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Find the <clock> and <fc> tags and update the second <fc> tag values
    clock_tag = root.find(".//clock[@name='clk']")
    fc_tags = root.findall(".//fc")
    if clock_tag is not None and len(fc_tags) > 1:
        fc_tag = fc_tags[1]  # Second <fc> tag
        if fc_tag is not None:
            fc_tag.set('in_val', str(val))
            fc_tag.set('out_val', str(val))
            print(f"Updated {xml_path} with in_val=out_val={val}")

    # Write the modified XML back to the file
    tree.write(xml_path)

# Function to run the vpr command and capture the output
def run_vpr(seed, file_path, xml_path):
    command = f"./vpr {xml_path} {file_path} --seed {seed}"
    print(f"Running: {command}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running vpr for seed {seed} on {file_path}")
        return None
    
    match = re.search(r"Best routing used a channel width factor of (\d+)", result.stdout)
    if match:
        channel_width = int(match.group(1))
        print(f"Found channel width: {channel_width}")
        return channel_width
    else:
        print("Channel width not found in output")
        return None

# Function to run vpr with channel width and capture additional metrics
def run_vpr_with_channel_width(seed, file_path, xml_path, channel_width):
    low_stress_width = math.ceil((channel_width * 1.3) / 2) * 2
    command = f"./vpr {xml_path} {file_path} --seed {seed} --route_chan_width {low_stress_width}"
    print(f"Running: {command}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running vpr with channel width {low_stress_width} for seed {seed} on {file_path}")
        return None
    
    match = re.search(r"Total routing area: ([\d\.e\+\-]+), per logic tile: (\d+)", result.stdout)
    critical_path_match = re.search(r"Final critical path delay.*?: ([\d\.]+) ns", result.stdout)
    
    if match and critical_path_match:
        total_routing_area = match.group(1)
        per_logic_tile = match.group(2)
        critical_path_delay = critical_path_match.group(1)
        print(f"Total routing area: {total_routing_area}, per logic tile: {per_logic_tile}, Critical Path Delay: {critical_path_delay}")
        return low_stress_width, total_routing_area, per_logic_tile, critical_path_delay
    else:
        print("Routing area or critical path delay not found in output")
        return None

# Function to process a single benchmark file
def process_benchmark_file(file_path, seeds, vals):
    benchmark_results = []
    
    for val in vals:
        # Update the XML with the current in_val and out_val (both are set to val)
        xml_path = f"k6_N10_40nm.xml"
        modify_fc_values(xml_path, val)  # Modify in_val and out_val to be the same

        ave_channel_width = 0
        ave_total_routing_area = 0
        ave_per_logic_tile = 0
        ave_critical_path_delay = 0

        for seed in seeds:
            channel_width = run_vpr(seed, file_path, xml_path)
            if channel_width is not None:
                result = run_vpr_with_channel_width(seed, file_path, xml_path, channel_width)
                if result is not None:
                    low_stress_width, total_routing_area, per_logic_tile, critical_path_delay = result
                    ave_channel_width += channel_width
                    ave_total_routing_area += float(total_routing_area)
                    ave_per_logic_tile += int(per_logic_tile)
                    ave_critical_path_delay += float(critical_path_delay)

        num_seeds = len(seeds)
        benchmark_results.append((
            file_path,
            val,  # in_val = out_val = val
            round(ave_channel_width / num_seeds, 2),
            round(ave_total_routing_area / num_seeds, 2),
            round(ave_per_logic_tile / num_seeds, 2),
            round(ave_critical_path_delay / num_seeds, 2)
        ))
    
    return benchmark_results

# Main function to run benchmarks concurrently
def main():
    benchmark_dir = "a4_benchmarks"
    files = [os.path.join(benchmark_dir, f) for f in os.listdir(benchmark_dir) if os.path.isfile(os.path.join(benchmark_dir, f))]
    seeds = [2, 3, 4, 5, 6]
    vals = [0.15, 0.5, 1]  # in_val = out_val will take values in this list
    results_folder = 'results'
    os.makedirs(results_folder, exist_ok=True)
    output_file = os.path.join(results_folder, 'vpr_results_2a.txt')

    with open(output_file, 'w') as file:
        file.write("File Name, in_val=out_val, Avg Channel Width, Avg Routing Area, Avg Per Logic Tile, Avg Critical Path Delay\n")

    # Run each benchmark file in parallel
    with ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(process_benchmark_file, file_path, seeds, vals): file_path for file_path in files}
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                benchmark_results = future.result()
                with open(output_file, 'a') as file:
                    for result in benchmark_results:
                        file.write(f"{result[0]}, {result[1]}, {result[2]}, {result[3]}, {result[4]}, {result[5]}\n")
            except Exception as e:
                print(f"Exception occurred for file {file_path}: {e}")
    
    print(f"Results have been written to {output_file}")

if __name__ == "__main__":
    main()

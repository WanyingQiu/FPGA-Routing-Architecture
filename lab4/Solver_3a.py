import os
import subprocess
import re
import math
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Lock

# Global lock for synchronizing XML file writes
xml_lock = Lock()

# Function to modify in_val and out_val in the XML file
def modify_fc_values(xml_path, val):
    with xml_lock:  # Ensure exclusive access to the XML file
        tree = ET.parse(xml_path)
        root = tree.getroot()

        clock_tag = root.find(".//clock[@name='clk']")
        fc_tags = root.findall(".//fc")
        if clock_tag is not None and len(fc_tags) > 1:
            fc_tag = fc_tags[1]
            if fc_tag is not None:
                fc_tag.set('in_val', str(val))
                fc_tag.set('out_val', str(val))

        print(f"Updated {xml_path} with in_val=out_val={val}")
        tree.write(xml_path)

def modify_rc_values(xml_path, r_metal, c_metal, num):
    with xml_lock:  # Ensure exclusive access to the XML file
        tree = ET.parse(xml_path)
        root = tree.getroot()

        segment_tags = root.findall(".//segment[@freq]")
        if segment_tags:
            if 0 <= num < len(segment_tags):
                segment_tag = segment_tags[num]
                segment_tag.set('Rmetal', str(r_metal))
                segment_tag.set('Cmetal', f"{c_metal}e-15")
            else:
                print(f"Invalid wire index: {num}, total available segments: {len(segment_tags)}")
        else:
            print(f"No segments found in {xml_path}")

        print(f"Updated {xml_path} wire#{num} with R_metal={r_metal}, C_metal={c_metal}")
        tree.write(xml_path)

def modify_switch_pattern(xml_path, switch_pattern):
    with xml_lock:  # Ensure exclusive access to the XML file
        tree = ET.parse(xml_path)
        root = tree.getroot()

        sw_tags = root.findall(".//switch_block")
        if sw_tags:
            for sw_tag in sw_tags:
                sw_tag.set('type', switch_pattern)

            print(f"Updated {xml_path} with switch pattern={switch_pattern}")
            tree.write(xml_path)
        else:
            print(f"No <switch_block> tags found in {xml_path}")

# Function to run the vpr command and capture the output
def run_vpr(seed, file_path, xml_path):
    command = f"./vpr {xml_path} {file_path} --seed {seed}"
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running vpr for seed {seed} on {file_path}: {result.stderr}")
        return None

    # print(f"VPR Output: {result.stdout}")
    match = re.search(r"Best routing used a channel width factor of (\d+)", result.stdout)
    return int(match.group(1)) if match else None

def run_vpr_with_channel_width(seed, file_path, xml_path, channel_width):
    low_stress_width = math.ceil((channel_width * 1.3) / 2) * 2
    command = f"./vpr {xml_path} {file_path} --seed {seed} --route_chan_width {low_stress_width}"
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running vpr with channel width {low_stress_width} for seed {seed} on {file_path}: {result.stderr}")
        return None

    # print(f"VPR Output: {result.stdout}")
    match = re.search(r"Total routing area: ([\d\.e\+\-]+), per logic tile: (\d+)", result.stdout)
    critical_path_match = re.search(r"Final critical path delay.*?: ([\d\.]+) ns", result.stdout)

    if match and critical_path_match:
        total_routing_area = float(match.group(1))
        per_logic_tile = int(match.group(2))
        critical_path_delay = float(critical_path_match.group(1))
        return low_stress_width, total_routing_area, per_logic_tile, critical_path_delay
    else:
        print("Failed to extract routing area or critical path delay")
        return None

# Function to process a single benchmark file
def process_benchmark_file(file_path, seeds, vals, r_c_cases, lengths, switch_patterns):
    benchmark_results = []
    for length in lengths:
        xml_path = f"k6_N10_40nm_{length}_wire.xml"
        for switch_pattern in switch_patterns:
            modify_switch_pattern(xml_path, switch_pattern)
            for val in vals:
                modify_fc_values(xml_path, val)
                for r_metal, c_metal in r_c_cases:
                    for wire_i in range(length):
                        modify_rc_values(xml_path, r_metal, c_metal, wire_i)
                    ave_channel_width, ave_total_routing_area, ave_per_logic_tile, ave_critical_path_delay = 0, 0, 0, 0
                    num_valid_results = 0

                    for seed in seeds:
                        if os.path.getsize(file_path) == 0:
                            print(f"File {file_path} is empty. Skipping...")
                            continue
                        channel_width = run_vpr(seed, file_path, xml_path)
                        if channel_width is not None:
                            result = run_vpr_with_channel_width(seed, file_path, xml_path, channel_width)
                            if result is not None:
                                low_stress_width, total_routing_area, per_logic_tile, critical_path_delay = result
                                ave_channel_width += channel_width
                                ave_total_routing_area += total_routing_area
                                ave_per_logic_tile += per_logic_tile
                                ave_critical_path_delay += critical_path_delay
                                num_valid_results += 1

                    if num_valid_results > 0:
                        benchmark_results.append((file_path, switch_pattern, length, val, r_metal, c_metal,
                                                  round(ave_channel_width / num_valid_results, 2),
                                                  round(ave_total_routing_area / num_valid_results, 2),
                                                  round(ave_per_logic_tile / num_valid_results, 2),
                                                  round(ave_critical_path_delay / num_valid_results, 2)))

    return benchmark_results

# Main function to run benchmarks concurrently
def main():
    benchmark_dir = "a4_benchmarks"
    files = [os.path.join(benchmark_dir, f) for f in os.listdir(benchmark_dir) if os.path.isfile(os.path.join(benchmark_dir, f))]
    seeds = [2, 5, 6, 7, 10]
    vals = [0.15, 0.2, 0.3, 0.5]
    r_c_cases = [(101, 22.5)]
    switch_patterns = ["wilton", "subset", "universal"]
    lengths = [1, 2]
    results_folder = 'results'
    os.makedirs(results_folder, exist_ok=True)
    output_file = os.path.join(results_folder, 'vpr_results_3a_3.txt')

    with open(output_file, 'w') as file:
        file.write("File Name, sw, num_wire, in_val=out_val, R_metal, C_metal, Avg Channel Width, Avg Routing Area, Avg Per Logic Tile, Avg Critical Path Delay\n")

    with ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(process_benchmark_file, file_path, seeds, vals, r_c_cases, lengths, switch_patterns): file_path for file_path in files}
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                benchmark_results = future.result()
                if isinstance(benchmark_results, list):
                    with open(output_file, 'a') as file:
                        for result in benchmark_results:
                            print(f"Writing result: {result}")
                            file.write(f"{result[0]}, {result[1]}, {result[2]}, {result[3]}, {result[4]}, {result[5]}, {result[6]}, {result[7]}, {result[8]}, {result[9]}\n")
            except Exception as e:
                print(f"Exception occurred for file {file_path}: {e}")

    print(f"Results have been written to {output_file}")

if __name__ == "__main__":
    main()

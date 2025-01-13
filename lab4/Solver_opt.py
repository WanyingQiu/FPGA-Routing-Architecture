import os
import subprocess
import re
import math
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Lock

# Global lock for synchronizing XML file writes
xml_lock = Lock()

# Function to run the vpr command and capture the output
def run_vpr(seed, file_path, xml_path):
    command = f"./vpr {xml_path} {file_path} --seed {seed}"
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running vpr for seed {seed} on {file_path}")
        # Check for the specific routing error in stderr
        if "Traceback no RR edge between RR nodes" in result.stderr:
            print("Routing error detected: Returning invalid minimum channel width (-1).")
            return -1  # Return invalid minimum channel width
        return None  # Return None for other errors

    # Search for the channel width in the output
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

# Function to compute the geometric mean
def geometric_mean(values):
    product = 1
    count = 0
    for value in values:
        if value > 0:  # Ignore zero or negative values for geometric mean
            product *= value
            count += 1
    return math.pow(product, 1 / count) if count > 0 else 0

# Function to process a single benchmark file
def process_benchmark_file(file_path, seeds):
    benchmark_results = []
    xml_path = f"k6_N10_40nm_2_wire.xml"
    ave_channel_width, ave_total_routing_area, ave_per_logic_tile, ave_critical_path_delay = 0, 0, 0, 0
    num_valid_results = 0
    used_seeds = set()
    additional_seed = 100  # Starting point for additional seeds

    while num_valid_results < 5:  # Ensure 5 successful runs
        for seed in seeds:
            if seed in used_seeds:  # Skip already used seeds
                continue
            used_seeds.add(seed)

            if os.path.getsize(file_path) == 0:
                print(f"File {file_path} is empty. Skipping...")
                break

            channel_width = run_vpr(seed, file_path, xml_path)
            if channel_width is not None:
                if channel_width == -1:
                    print(f"Invalid channel width (-1) for seed {seed}. Skipping this seed.")
                    continue  # Skip this seed and move to the next one
                result = run_vpr_with_channel_width(seed, file_path, xml_path, channel_width)
                if result is not None:
                    low_stress_width, total_routing_area, per_logic_tile, critical_path_delay = result
                    ave_channel_width += channel_width
                    ave_total_routing_area += total_routing_area
                    ave_per_logic_tile += per_logic_tile
                    ave_critical_path_delay += critical_path_delay
                    num_valid_results += 1

            if num_valid_results >= 5:
                break

        # If not enough valid results, add new seeds
        if num_valid_results < 5:
            seeds.append(additional_seed)
            additional_seed += 1

    if num_valid_results > 0:
        benchmark_results.append((
            file_path,
            round(ave_channel_width / num_valid_results, 2),
            round(ave_total_routing_area / num_valid_results, 2),
            round(ave_per_logic_tile / num_valid_results, 2),
            round(ave_critical_path_delay / num_valid_results, 2)
        ))

    return benchmark_results


# Main function to run benchmarks concurrently
def main():
    benchmark_dir = "a4_benchmarks"
    files = [os.path.join(benchmark_dir, f) for f in os.listdir(benchmark_dir) if os.path.isfile(os.path.join(benchmark_dir, f))]
    seeds = [1, 10, 20, 30, 40]
    results_folder = 'results'
    os.makedirs(results_folder, exist_ok=True)
    output_file = os.path.join(results_folder, 'vpr_opt.txt')

    # Prepare results storage
    all_channel_widths = []
    all_routing_areas = []
    all_per_logic_tiles = []
    all_critical_path_delays = []
    results = []  # Collect all results here

    # Write header
    # with open(output_file, 'w') as file:
        # file.write("File Name, Geo_Channel Width, Geo_Routing Area, Geo_Per Logic Tile, Geo_Critical Path Delay, area_delay\n")

    # Process files with multithreading
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(process_benchmark_file, file_path, seeds): file_path for file_path in files}

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:  # Append results for individual files
                    results.extend(result)  # Store results for later writing
                    for res in result:
                        # Collect values for geometric mean calculation
                        all_channel_widths.append(res[1])
                        all_routing_areas.append(res[2])
                        all_per_logic_tiles.append(res[3])
                        all_critical_path_delays.append(res[4])
            except Exception as e:
                print(f"Exception processing file: {e}")

    # Write all results to the file
    # with open(output_file, 'a') as file:
    #     for res in results:
    #         file.write(
    #             f"{res[0]}, {res[1]:.2f}, {res[2]:.2f}, {res[3]:.2f}, {res[4]:.2f}\n"
    #         )

    # Compute overall geometric averages
    if all_channel_widths:
        overall_geo_channel_width = geometric_mean(all_channel_widths)
        overall_geo_routing_area = geometric_mean(all_routing_areas)
        overall_geo_per_logic_tile = geometric_mean(all_per_logic_tiles)
        overall_geo_critical_path_delay = geometric_mean(all_critical_path_delays)
        overall_geo_area_delay = overall_geo_critical_path_delay * overall_geo_routing_area

        # Write overall geometric averages
        with open(output_file, 'a') as file:
            file.write("\nOverall Geometric Averages:\n")
            file.write(
                f"{overall_geo_channel_width:.2f}, "
                f"{overall_geo_routing_area:.2f}, "
                f"{overall_geo_per_logic_tile:.2f}, "
                f"{overall_geo_critical_path_delay:.2f}, "
                f"{overall_geo_area_delay:.2f}\n"
            )
            file.write("\n")

        print(f"Geometric averages have been written to {output_file}")
        print("\n")
if __name__ == "__main__":
    main()

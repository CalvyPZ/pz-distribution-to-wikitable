import os
import re
import csv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ThreadPoolExecutor

def process_lua_file(input_file_name, output_file_path):
    print("Starting to clean the Lua file...")
    with open(input_file_name, 'r') as file:
        content = file.read()
    cleaned_content = re.sub(r',\s*junk\s*=\s*{\s*rolls\s*=\s*\d+,\s*items\s*=\s*\{\s*\}\s*}', '', content, flags=re.DOTALL)
    with open(output_file_path, 'w') as output_file:
        output_file.write(cleaned_content)
    print("Cleaned file created successfully.")

def split_containers_and_output_files(input_file_path, output_dir):
    print("Starting to split containers into individual files and generate unique items list...")
    unique_items = []
    with open(input_file_path, 'r') as file:
        content = file.read()
    container_pattern = re.compile(r'(\w+)\s*=\s*{[^}]*}', re.DOTALL)
    item_name_pattern = re.compile(r'"([^"]+)"')
    for container in container_pattern.finditer(content):
        container_name, container_data = container.group(1), container.group(0)
        item_names = item_name_pattern.findall(container_data)
        for item_name in set(item_names):  # Use set to ensure uniqueness
            if item_name not in unique_items:
                unique_items.append(item_name)
        container_file_path = os.path.join(output_dir, f"{container_name}.lua")
        with open(container_file_path, 'w') as container_file:
            container_file.write(container_data)
    with open(unique_items_file_path, 'w') as items_file:
        for item in unique_items:
            items_file.write(f"{item}\n")
    print("Unique items list generated and container files split successfully.")

def check_file_for_item(pattern, split_dir, filename):
    try:
        with open(os.path.join(split_dir, filename), 'r') as file:
            if pattern.search(file.read()):
                return filename[:-4]  # Remove '.lua' extension
    except Exception as e:
        print(f"Error processing file {filename}: {e}")
    return None

def generate_locations(input_file_path, unique_items_file_path, output_dir, split_dir, locations_file_name):
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(unique_items_file_path, 'r') as file:
        unique_items = [line.strip() for line in file.readlines()]

    total_items = len(unique_items)  # Total number of unique items

    with open(os.path.join(output_dir, locations_file_name), 'w') as locations_file:
        for idx, item in enumerate(unique_items, start=1):  # Start counting from 1
            pattern = re.compile(rf'"{item}"')
            containers = []

            # Create a list to hold the futures
            futures = []
            with ThreadPoolExecutor() as executor:
                for filename in os.listdir(split_dir):
                    futures.append(executor.submit(check_file_for_item, pattern, split_dir, filename))

                # Wait for all futures to complete
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        containers.append(result)

            locations_file.write(f"{item}, {', '.join(containers)}\n")

            # Print the progress after processing each item
            print(f"Finished locations for {item} ({idx}/{total_items})")

    print("Locations file created successfully.")


def generate_csv_files(locations_file_path, split_dir, csv_dir):
    print("Starting to generate CSV files for each item...")
    with open(locations_file_path, 'r') as locations_file:
        locations = locations_file.readlines()

    for index, line in enumerate(locations, start=1):
        item, *containers = line.strip().split(', ')
        valid_containers = []  # List to keep track of valid containers

        # Check for valid containers before creating the CSV
        for container_name in containers:
            container_file_path = os.path.join(split_dir, f"{container_name}.lua")
            if os.path.exists(container_file_path):
                with open(container_file_path, 'r') as container_file:
                    container_content = container_file.read()
                # Check for rolls and chance in the container
                if re.search(r'rolls\s*=\s*(\d+(?:\.\d+)?)', container_content) and \
                        re.search(rf'"{item}", (\d+(?:\.\d+)?)', container_content):
                    valid_containers.append(container_name)

        # Skip CSV creation if no valid containers found
        if not valid_containers:
            print(f"No valid containers found for {item}, skipping CSV creation.")
            continue

        # Proceed with CSV creation since valid containers exist
        print(f"Creating CSV for {item}...")
        csv_file_path = os.path.join(csv_dir, f"{item}.csv")

        with open(csv_file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # Removed the line that writes the header row

            for container_name in valid_containers:
                container_file_path = os.path.join(split_dir, f"{container_name}.lua")
                with open(container_file_path, 'r') as container_file:
                    container_content = container_file.read()
                rolls_match = re.search(r'rolls\s*=\s*(\d+(?:\.\d+)?)', container_content)
                rolls = float(rolls_match.group(1)) if rolls_match else "Unknown"
                chance_matches = re.findall(rf'"{item}", (\d+(?:\.\d+)?)', container_content)
                for chance in chance_matches:
                    chance_float = float(chance)
                    csv_writer.writerow([container_name, rolls, chance_float])

        print(f"CSV for {item} created successfully. ({index}/{len(locations)})")


def clean_distributions_file(input_file_path, output_file_path):
    # Open the original Lua file, read its lines, and then write the cleaned content to a new file
    with open(input_file_path, 'r') as original_file:
        lines = original_file.readlines()

    # Remove the first 8 and last 5 lines
    cleaned_lines = lines[8:-5]

    # Write the cleaned lines to the new file
    with open(output_file_path, 'w') as cleaned_file:
        cleaned_file.writelines(cleaned_lines)

def find_room_container_and_room(lua_file_path, loottable_name):
    container_stack = []  # Stack to keep track of container hierarchy

    with open(lua_file_path, 'r') as lua_file:
        for line in lua_file:
            # Check for container start
            if '{' in line:
                container_match = re.search(r'(\w+)\s*=\s*\{', line)
                if container_match:
                    container_name = container_match.group(1)
                    # Push the container name to the stack
                    container_stack.append(container_name)

            # Check for container end
            elif '}' in line:
                if container_stack:
                    # Pop the last container as we are leaving its scope
                    popped_container = container_stack.pop()

            if loottable_name in line and container_stack:
                # If the loottable is found and we have a container stack,
                # Edit the stack to only contain the first two entries (if they exist)
                room_container_info = container_stack[:2]
                return room_container_info

    # Return None if the loottable is not found within any container
    return None



def process_csv_files(input_dir, lua_file_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Ensure the export directory exists
    export_dir = os.path.join(output_dir)
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    failed_file_path = os.path.join("failed.txt")

    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    total_files = len(csv_files)

    for index, csv_file_name in enumerate(csv_files, start=1):
        csv_file_path = os.path.join(input_dir, csv_file_name)
        output_csv_path = os.path.join(export_dir, csv_file_name)  # Adjusted to write to export_dir

        print(f"Processing {csv_file_name} ({index}/{total_files})")

        with open(csv_file_path, mode='r', newline='') as csv_file, \
             open(output_csv_path, mode='w', newline='') as output_file, \
             open(failed_file_path, mode='a', newline='') as failed_file:

            csv_reader = csv.reader(csv_file)
            csv_writer = csv.writer(output_file)

            for row in csv_reader:
                try:
                    # Assuming each row follows a specific format, e.g., loottable, rolls, chance
                    loottable, rolls_str, chance_str = row
                    rolls = float(rolls_str)  # Convert rolls to float
                    chance = float(chance_str)  # Convert chance to float
                except ValueError:
                    print(f"Skipping row due to incorrect format: {row}")
                    failed_file.write(",".join(row) + "\n")  # Write the failed row to failed.txt
                    continue

                # Assuming `find_room_container_and_room` returns a tuple (room_name, container_name)
                room_container_info = find_room_container_and_room(lua_file_path, loottable)

                if room_container_info:
                    room_name, container_name = room_container_info
                    csv_writer.writerow([room_name, container_name, loottable, rolls, chance])
                else:
                    print(f"Failed to output {loottable}, loottable not found")
                    failed_file.write(",".join([loottable, str(rolls), str(chance)]) + "\n")  # Adjusted to keep consistency

        print(f"Completed processing {csv_file_name} ({index}/{total_files})")


def adjust_decimal(row):
    # This function checks and modifies the fourth and fifth entries if they end with '.0'
    for i in [3, 4]:  # Indexes for the fourth and fifth entries
        if i < len(row) and row[i].endswith('.0'):
            row[i] = row[i].rstrip('.0')
            if row[i] == '':  # If the entry was just '.0', convert it to '0'
                row[i] = '0'
    return row


def sort_csv_file(file_path, current_file_number, total_files):
    print(f"Processing file {current_file_number} of {total_files}: {os.path.basename(file_path)}")
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            # Read all rows, adjust decimals, and then modify the second column
            rows = []
            for row in reader:
                adjusted_row = adjust_decimal(row)
                # Add double square brackets around the second column (index 1)
                if len(adjusted_row) > 1:  # Ensure there is at least a second item
                    adjusted_row[1] = f"[[{adjusted_row[1]}]]"
                rows.append(adjusted_row)

            # Sort rows
            sorted_rows = sorted(rows, key=lambda row: tuple(row))

        # Write the sorted and modified rows back to the file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(sorted_rows)

        print(f"Successfully processed and sorted {os.path.basename(file_path)}")
    except Exception as e:
        print(f"Error processing {os.path.basename(file_path)}: {e}")


def sort_all_csv_files_in_folder(folder_path):
    if not os.path.isdir(folder_path):
        print(f"The folder {folder_path} does not exist or is not accessible.")
        return

    # Get all CSV files in the folder
    csv_files = [f for f in os.listdir(folder_path) if
                 os.path.isfile(os.path.join(folder_path, f)) and f.endswith('.csv')]
    if not csv_files:
        print("No CSV files found in the folder.")
        return

    total_files = len(csv_files)
    print(f"Found {total_files} CSV files in the folder.")

    # Iterate over all CSV files and sort each one
    for index, file_name in enumerate(csv_files, start=1):
        full_path = os.path.join(folder_path, file_name)
        sort_csv_file(full_path, index, total_files)

def convert_csv_to_wiki_table(csv_folder, output_folder):
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Iterate over each CSV file in the folder
    for filename in os.listdir(csv_folder):
        if filename.endswith(".csv"):
            base_filename_without_extension = os.path.splitext(filename)[0]
            filepath = os.path.join(csv_folder, filename)
            output_filepath = os.path.join(output_folder, f"{base_filename_without_extension}.txt")

            with open(filepath, 'r', newline='', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file)
                rows = list(reader)

                processed_rows = process_rows_for_wiki_format(rows)

                # Convert to new wiki table format with the header text
                wiki_table = convert_rows_to_wiki_table(processed_rows, base_filename_without_extension)

                with open(output_filepath, 'w', newline='', encoding='utf-8') as output_file:
                    output_file.write(wiki_table)
            print(f"Processed {filename}")


def process_rows_for_wiki_format(rows):
    """
    Processes rows from CSV to fit the new wiki table format, excluding an unused column and correctly applying rowspan for the 'Building/Room' column.
    This version assumes there is no header row and only data rows are present.
    """
    processed_rows = []
    rowspan = defaultdict(int)  # Initialize a dict to keep track of rowspan counts
    current_building = None

    # First pass to calculate rowspan
    for row in rows:
        building = row[0]
        if building == current_building:
            rowspan[building] += 1
        else:
            if current_building is not None:  # Adjust rowspan count for the previous building
                rowspan[current_building] += 1
            current_building = building

    # Adjust rowspan count for the last building in the list
    rowspan[current_building] += 1

    # Second pass to prepare rows with relevant columns and rowspan handling
    used_buildings = set()  # Keep track of buildings already processed for rowspan
    for row in rows:
        building, container = row[0], row[1]
        rolls, chance = row[3], row[4]  # Skip the unused third column

        if building not in used_buildings and rowspan[building] > 1:
            processed_row = [f'rowspan="{rowspan[building]}"|{building}', container, rolls, chance]
            used_buildings.add(building)
        elif building not in used_buildings and rowspan[building] == 1:
            processed_row = [building, container, rolls, chance]
        else:
            # For additional rows of the same building with rowspan applied, omit the building column
            processed_row = ['', container, rolls, chance]

        processed_rows.append(processed_row)

    return processed_rows


def convert_rows_to_wiki_table(rows, file_name_without_extension):
    """
    Converts processed rows into a wiki table string with the new specified format, ensuring consistent spacing.
    """
    # Standard header text
    header_text = "==Distribution==\nThe loot distributions can be found in the table(s) below.\n\n"

    # Start of the collapsible wiki table with custom attributes and consistent spacing
    wiki_table = ('{| class="mw-collapsible mw-collapsed wikitable theme-red" data-expandtext="{{int:show}}" '
                  'data-collapsetext="{{int:hide}}" style="text-align:center; min-width:24em;"\n'
                  '! colspan="4" | Containers\n|-\n'
                  '! Building/Room\n! Container\n! style="width: 3.2em;" | Rolls\n! style="width: 3.2em;" | Chance')

    for row in rows:
        filtered_row = [item for item in row if item.strip()]  # Remove any empty strings from row
        if not filtered_row:  # If the row is empty after filtering, skip it
            continue
        wiki_table += '\n|-'
        if len(filtered_row) == 4:
            wiki_table += f'\n|{filtered_row[0]} \n|{filtered_row[1]} \n|{filtered_row[2]} \n|{filtered_row[3]}'
        else:
            wiki_table += '\n|' + ' \n|'.join(filtered_row)

    # Closing table tag
    wiki_table += '\n|}'

    return header_text + wiki_table



if __name__ == "__main__":
    # Initialization of paths and directory structures
    lua_file_name = 'ProceduralDistributions.lua'
    export_dir = 'export'
    unique_items_file_path = os.path.join(export_dir, 'UniqueItems.txt')
    split_dir = os.path.join(export_dir, 'split')
    csv_dir = os.path.join(export_dir, 'csv')
    export_file_name = os.path.join(export_dir, 'ProceduralDistributions_Cleaned.lua')
    locations_file_name = 'locations.txt'

    # Ensure necessary directories exist
    os.makedirs(split_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)

    process_lua_file(lua_file_name, export_file_name)
    split_containers_and_output_files(export_file_name, split_dir)

    current_dir = os.path.dirname(__file__)
    input_dir = os.path.join(current_dir, 'export', 'csv')

    export_dir = os.path.join(current_dir, 'export')
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    original_lua_file_path = os.path.join(current_dir, 'Distributions.lua')
    cleaned_lua_file_path = os.path.join(export_dir, 'Distributions_cleaned.lua')
    output_dir = os.path.join(export_dir, 'csv', 'processed')
    folder_path = "export\csv\processed"
    csv_folder = 'export/csv/processed'
    output_folder = 'export/completed'


    # Processes
    generate_locations(export_file_name, unique_items_file_path, export_dir, split_dir, locations_file_name)
    generate_csv_files(os.path.join(export_dir, locations_file_name), split_dir, csv_dir)
    clean_distributions_file(original_lua_file_path, cleaned_lua_file_path)
    process_csv_files(input_dir, cleaned_lua_file_path, output_dir)
    sort_all_csv_files_in_folder(folder_path)
    convert_csv_to_wiki_table(csv_folder, output_folder)
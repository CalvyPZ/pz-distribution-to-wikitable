import re
import os
import csv
import shutil
from tqdm import tqdm


def main():
    root_path = os.getcwd()
    resources_path = os.path.join(root_path, 'resources')
    output_path = os.path.join(root_path, 'output')  # Base output path
    csv_output_path = os.path.join(output_path, 'csv')  # Specific path for CSVs
    file_names = ['distributions.lua', 'proceduraldistributions.lua', 'VehicleDistributions.lua']
    forage_file_name = 'foragedefinitions.lua'

    # Extract unique items
    unique_items = unique_items_extract(resources_path, file_names, forage_file_name)
    write_unique_names(unique_items, output_path)
    item_processing(unique_items, resources_path, csv_output_path, file_names)

    # Formatting CSVs into specific structured output
    formatting(unique_items, output_path)


def unique_items_extract(resources_path, file_names, forage_file_name):
    unique_items = set()
    # Regex to look for 'items = {' or 'junk = {'
    item_regex = re.compile(r'\b(items|junk)\s*=\s*\{')
    # Regex for matching 'type' entries in foragedefinitions.lua
    type_regex = re.compile(r'^\s*type\s*=\s*"([^"]+)",\s*$')

    # Process distribution and vehicle files
    for file_name in file_names:
        with open(os.path.join(resources_path, file_name), 'r') as file:
            recording = False
            for line in file:
                if line.strip().startswith('--'):
                    continue
                if recording:
                    if '}' in line:
                        recording = False
                    else:
                        items = re.findall(r'"([^"]+)"', line)
                        cleaned_items = [re.sub(r'.*\.', '', item) for item in items]
                        unique_items.update(cleaned_items)
                elif item_regex.search(line):
                    recording = True

    # Process foragedefinitions.lua for 'type' entries and items blocks
    path = os.path.join(resources_path, forage_file_name)
    with open(path, 'r') as file:
        recording = False
        for line in file:
            if line.strip().startswith('--'):
                continue
            if recording:
                if '}' in line:
                    recording = False
                else:
                    if type_regex.match(line):
                        match = type_regex.match(line)
                        full_item = match.group(1)
                        item_name = full_item.split('.')[-1]
                        unique_items.add(item_name)
                    else:
                        items = re.findall(r'"([^"]+)"', line)
                        cleaned_items = [re.sub(r'.*\.', '', item) for item in items]
                        unique_items.update(cleaned_items)
            elif item_regex.search(line):
                recording = True

    return unique_items


def write_unique_names(unique_items, output_path):
    # Create the full path for the unique names file
    file_path = os.path.join(output_path, 'unique_names.txt')
    os.makedirs(output_path, exist_ok=True)
    with open(file_path, 'w') as file:
        for item in sorted(unique_items):
            file.write(item + '\n')


def item_processing(unique_items, resources_path, output_path, file_names):
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path, exist_ok=True)

    for item in tqdm(unique_items, desc="Processing items"):
        processed_entries = item_processing_container(item, resources_path)
        processed_entries = process_distribution_items(item, resources_path, processed_entries)
        write_container_csv(item, output_path, processed_entries)
        item_processing_vehicle(item, resources_path, output_path)
        item_processing_foraging(item, resources_path, output_path)


def item_processing_container(item, resources_path):
    procedural_data = os.path.join(resources_path, 'proceduraldistributions.lua')
    distribution_data = os.path.join(resources_path, 'distributions.lua')

    processed_entries = set()

    with open(procedural_data, 'r') as file:
        proc_lines = file.readlines()
    with open(distribution_data, 'r') as file:
        dist_lines = file.readlines()

    item_pattern = re.compile(r'"{}"'.format(re.escape(item)), re.IGNORECASE)
    id_pattern = re.compile(r'^\s{4}(\w+)\s')

    for i, line in enumerate(proc_lines):
        if item_pattern.search(line):
            proc_id = None
            for j in range(i-1, -1, -1):
                id_match = id_pattern.match(proc_lines[j])
                if id_match:
                    proc_id = id_match.group(1)
                    break
            if not proc_id:
                continue  # Skip if no ID is found

            rolls_value = None
            for j in range(i-1, -1, -1):  # Scan above for 'rolls'
                if 'rolls' in proc_lines[j]:
                    rolls_match = re.search(r'rolls\s*=\s*(\d+)', proc_lines[j])
                    if rolls_match:
                        rolls_value = rolls_match.group(1)
                        break

            search_id_pattern = re.compile(r'"{}"'.format(re.escape(proc_id)), re.IGNORECASE)
            room_pattern = re.compile(r'^\s{4}(\w+)\s')
            container_pattern = re.compile(r'^\s{8}(\w+)\s')

            for k, dist_line in enumerate(dist_lines):
                if search_id_pattern.search(dist_line):
                    room, container = None, None
                    for m in range(k-1, -1, -1):
                        if not room and room_pattern.match(dist_lines[m]):
                            room = room_pattern.match(dist_lines[m]).group(1).strip()
                        if not container and container_pattern.match(dist_lines[m]):
                            container = container_pattern.match(dist_lines[m]).group(1).strip()
                        if room and container:
                            break

                    quantity_match = re.search(r'"{}",\s*(\d+)'.format(re.escape(item)), line)
                    if quantity_match:
                        quantity = quantity_match.group(1)
                        processed_entries.add((room, container, rolls_value, quantity))

    return processed_entries


def process_distribution_items(item, resources_path, processed_entries):
    distribution_data = os.path.join(resources_path, 'distributions.lua')

    with open(distribution_data, 'r') as file:
        lines = file.readlines()

    item_pattern = re.compile(r'"{}"\s*,\s*(\d+(?:\.\d+)?)'.format(re.escape(item)), re.IGNORECASE)

    for i, line in enumerate(lines):
        if item_pattern.search(line):
            chance_match = item_pattern.search(line)
            if chance_match and chance_match.group(1):
                chance = chance_match.group(1)
                # Process upward search for 'rolls' and 'container name'
                room, container, rolls_value = None, None, None
                for j in range(i - 1, -1, -1):
                    if not container and 'rolls' in lines[j]:
                        rolls_match = re.search(r'rolls\s*=\s*(\d+)', lines[j])
                        if rolls_match:
                            rolls_value = rolls_match.group(1)
                            container_match = re.match(r'^\s*(\w+)\s*=\s*\{', lines[j-1])
                            if container_match:
                                container = container_match.group(1).strip()
                                bracket_count = 0
                                # Count from the matched line starting at '{' on the same line
                                # to see if the brackets close before reaching the container line
                                for k in range(j-1, -1, -1):
                                    bracket_count += lines[k].count('{') - lines[k].count('}')
                                    if bracket_count == 0:
                                        break
                                else:
                                    room = "all"
                                if bracket_count == 0:
                                    # If brackets close before reaching the container line, set room to "all"
                                    room = "all"
                                else:
                                    for k in range(j-2, -1, -1):
                                        room_match = re.match(r'^\s{4}(\w+)\s', lines[k])
                                        if room_match:
                                            room = room_match.group(1).strip()
                                            break
                                processed_entries.add((room, container, rolls_value, chance))
                            break

    return processed_entries


def write_container_csv(item, output_path, processed_entries):
    # Only proceed if there are entries to write
    if processed_entries:
        csv_file_path = os.path.join(output_path, f'{item}_container.csv')
        os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
        sorted_entries = sorted(processed_entries, key=lambda x: (x[0], x[1]))

        with open(csv_file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for entry in sorted_entries:
                writer.writerow(entry)


def item_processing_vehicle(item, resources_path, output_path):
    vehicle_data_path = os.path.join(resources_path, 'VehicleDistributions.lua')
    vehicle_entries = set()
    item_pattern = re.compile(r'"{}"\s*,\s*(\d+(?:\.\d+)?)'.format(re.escape(item)), re.IGNORECASE)

    with open(vehicle_data_path, 'r') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if item_pattern.search(line):
            # Find the first word of the line that defines vehicle type
            for j in range(i, -1, -1):
                if re.match(r'VehicleDistributions\.[^\s]+ = \{', lines[j]):
                    vehicle_type = re.match(r'VehicleDistributions\.([^\s]+) = \{', lines[j]).group(1)
                    break
            # Find the 'rolls' value
            rolls_value = None
            for k in range(i, -1, -1):
                if 'rolls' in lines[k]:
                    rolls_value = re.search(r'rolls\s*=\s*(\d+)', lines[k]).group(1)
                    break
            # Extract the quantity
            quantity = item_pattern.search(line).group(1)

            vehicle_entries.add((vehicle_type, rolls_value, quantity))

    # Write results to CSV only if there are entries
    if vehicle_entries:
        csv_file_path = os.path.join(output_path, f'{item}_vehicle.csv')
        os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
        with open(csv_file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for entry in sorted(vehicle_entries):
                writer.writerow(entry)


def clean_foraging_file(resources_path):
    forage_file_path = os.path.join(resources_path, 'forageDefinitions.lua')
    output_path = os.path.join(resources_path, 'foraging_clean.lua')

    with open(forage_file_path, 'r') as file:
        content = file.readlines()

    start_index = next((i for i, line in enumerate(content) if "======== forageDefs ========" in line), None)
    if start_index is not None:
        content = content[start_index + 1:]

    clean_content = []
    in_comment_block = False
    for line in content:
        original_line = line
        line = line.strip()
        if line.startswith('--[[') or ('--[[ ' in line):
            in_comment_block = True
        elif line.endswith(']]') or (' ]]--' in line):
            in_comment_block = False
            continue
        if not in_comment_block and not line.startswith('--'):
            clean_content.append(original_line)

    with open(output_path, 'w') as file:
        file.writelines(clean_content)

    return output_path


def item_processing_foraging(item, resources_path, output_path):
    clean_file_path = clean_foraging_file(resources_path)
    with open(clean_file_path, 'r') as file:
        content = file.readlines()

    details_type1 = process_type1_foraging(item, content)
    details_type2 = process_type2_foraging(item, content)

    if details_type1:
        save_to_csv(details_type1, output_path, item, 1)
    if details_type2:
        save_to_csv(details_type2, output_path, item, 2)


def process_type1_foraging(item, content):
    details_type1 = {}
    type1_regex = re.compile(r'type\s*=\s*"[\w\.]*' + re.escape(item) + r'"', re.IGNORECASE)
    record_type1 = False
    block_content = []
    brace_count = 0  # To manage nested braces

    for i, line in enumerate(content):
        line = line.strip()
        if type1_regex.search(line):
            if not record_type1:
                record_type1 = True
                brace_count = 1  # Start counting braces from this line
                block_content = [line]
        elif record_type1:
            block_content.append(line)
            if '{' in line:
                brace_count += line.count('{')
            if '}' in line:
                brace_count -= line.count('}')
            if brace_count == 0:  # Only end recording when all opened braces are closed
                record_type1 = False
                block_data = extract_data_from_block(block_content)
                details_type1[item] = block_data

    return details_type1


def process_type2_foraging(item, content):
    details_type2 = {}
    item_pattern = re.compile(r'{} = "Base\.{}"'.format(item, item), re.IGNORECASE)
    context_start_pattern = re.compile(r'^\t\t\w+ = \{')  # To identify the start of a block
    blacklist = set()

    for index, line in enumerate(content):
        line = line.strip()
        if item_pattern.search(line) and line not in blacklist:
            blacklist.add(line)
            context_index = index
            block_data = {'chance': None, 'months': None}

            # First independent search for 'months'
            months_index = context_index
            while months_index > 0 and not block_data['months']:
                months_index -= 1
                current_line = content[months_index].strip()
                if 'months =' in current_line:
                    months = re.findall(r'\{([\s\d,]+)\}', current_line)
                    if months:
                        month_numbers = months[0].replace(' ', '').split(',')
                        block_data['months'] = '|'.join(month_numbers)
                if context_start_pattern.match(current_line):
                    break  # Stop this search upon hitting another block start

            # Second independent search for 'chance'
            chance_index = context_index
            while chance_index > 0 and not block_data['chance']:
                chance_index -= 1
                current_line = content[chance_index].strip()
                if 'chance =' in current_line:
                    chance_match = re.search(r'chance\s*=\s*(\d+)', current_line)
                    if chance_match:
                        block_data['chance'] = chance_match.group(1)
                if context_start_pattern.match(current_line):
                    break  # Stop this search upon hitting another block start

            if block_data['months'] or block_data['chance']:
                details_type2[item] = block_data

    return details_type2


def save_to_csv(details, output_path, item, type_number):
    headers = {
        1: ['minCount', 'maxCount', 'skill', 'snowChance', 'rainChance', 'dayChance', 'nightChance', 'months', 'bonusMonths', 'malusMonths', 'zones'],
        2: ['chance', 'months']
    }

    csv_file_path = os.path.join(output_path, f'{item}_foraging{type_number}.csv')
    with open(csv_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers[type_number])
        for key, data in details.items():
            row = [data.get(header) for header in headers[type_number]]
            writer.writerow(row)


def extract_data_from_block(block_content):
    block_data = {
        'minCount': None, 'maxCount': None, 'skill': None,
        'xp': None, 'snowChance': None, 'rainChance': None, 'dayChance': None, 'nightChance': None,
        'months': '', 'bonusMonths': '', 'malusMonths': '', 'zones': ''
    }
    for line in block_content:
        line = line.strip()
        if 'minCount' in line:
            block_data['minCount'] = re.findall(r'minCount\s*=\s*(\d+)', line)[0]
        if 'maxCount' in line:
            block_data['maxCount'] = re.findall(r'maxCount\s*=\s*(\d+)', line)[0]
        if 'skill' in line:
            block_data['skill'] = re.findall(r'skill\s*=\s*(\d+)', line)[0]
        if 'xp' in line:
            block_data['xp'] = re.findall(r'xp\s*=\s*(\d+)', line)[0]
        if 'snowChance' in line:
            block_data['snowChance'] = re.findall(r'snowChance\s*=\s*(-?\d+)', line)[0]
        # Include patterns for other fields similarly

        # Handling lists within blocks for zones, months, etc.
        if 'zones' in line and '{' in line:
            zone_data = []
            zone_start_index = block_content.index(line)  # Find the starting index of zones
            for zone_line in block_content[zone_start_index:]:
                if '}' in zone_line:
                    break
                zone_match = re.findall(r'(\w+)\s*=\s*(\d+)', zone_line)
                if zone_match:
                    zone_data.extend(zone_match)
            block_data['zones'] = dict(zone_data)

        # Parsing months, ensuring to capture lists correctly
        if 'bonusMonths' in line:
            bonus_months = re.findall(r'(\d+)', line)
            block_data['bonusMonths'] = '|'.join(bonus_months)
        if 'malusMonths' in line:
            malus_months = re.findall(r'(\d+)', line)
            block_data['malusMonths'] = '|'.join(malus_months)

    return block_data


def month_lookup(month_number):
    month_dict = {
        '1': 'January', '2': 'February', '3': 'March',
        '4': 'April', '5': 'May', '6': 'June',
        '7': 'July', '8': 'August', '9': 'September',
        '10': 'October', '11': 'November', '12': 'December'
    }
    return month_dict.get(month_number, '-')


def formatting(unique_items, base_output_path):
    version = "41.78.16"  # Set the version variable at the top of the function
    complete_output_path = os.path.join(base_output_path, 'complete')
    csv_output_path = os.path.join(base_output_path, 'csv')

    # Clear existing files in the complete directory
    if os.path.exists(complete_output_path):
        shutil.rmtree(complete_output_path)
    os.makedirs(complete_output_path)

    # Process each unique item with a progress bar
    for item in tqdm(unique_items, desc="Formatting items"):
        output_data = f"<!--BOT FLAG|{item}|{version}-->\n"
        output_data += "<div class=\"togglebox theme-red\">\n"
        output_data += f"    <div>{item} distribution\n"
        output_data += f"        <span class=\"mw-customtoggle-togglebox-{item}\" title=\"{{{{int:show}}}} / {{{{int:hide}}}}\" style=\"float:right; padding-right:30px; padding-top:4px; font-size:0.7em; font-weight:normal;\">{{{{int:show}}}} / {{{{int:hide}}}}</span></div>\n"
        output_data += f"    <div class=\"mw-collapsible mw-collapsed\" id=\"mw-customcollapsible-togglebox-{item}\">\n"
        output_data += "    <div class=\"toggle-content\"><div style=\"display: flex;\">"

        item_files = {file_type: None for file_type in ['container', 'vehicle', 'foraging1', 'foraging2']}
        # Search for files that include the item name
        for filename in os.listdir(csv_output_path):
            for file_type in item_files.keys():
                if filename.startswith(item + '_') and filename.endswith(f'{file_type}.csv'):
                    item_files[file_type] = os.path.join(csv_output_path, filename)

        # Process container and vehicle files
        for file_type in ['container', 'vehicle']:
            if item_files[file_type]:
                rows_to_add = []
                with open(item_files[file_type], mode='r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    header = next(reader)  # Skip the header row

                    for row in reader:
                        if file_type == 'container':
                            formatted_row = f"""    |-
    | {row[0]}
    | {{{{ll|{row[1]}}}}}
    | {row[2]}
    | {row[3]}
"""
                        elif file_type == 'vehicle':
                            formatted_row = f"""    |-
    | {row[0]}
    | {row[1]}
    | {row[2]}
"""
                        rows_to_add.append(formatted_row)

                if rows_to_add:
                    table_caption = "{{ll|Containers}}" if file_type == 'container' else "{{ll|Vehicles}}"
                    table_div = "<div style=\"float:left;\">\n"
                    table_div += f"    {{| class=\"wikitable theme-red\" style=\"margin-right:15px; width:95%;\"\n"
                    table_div += f"    |+ {table_caption}\n"
                    table_div += "    ! " + (
                        "Building / Room\n    ! Container\n    ! Rolls\n    ! Chance\n" if file_type == 'container' else "Vehicle Type/Location\n    ! Rolls\n    ! Chance\n")
                    table_div += ''.join(rows_to_add) + "    |}\n</div>\n"
                    output_data += table_div

        # Append closing div for the flex container
        output_data += "    </div><div style=\"clear:both;\"></div>\n"

        # Process foraging files
        for file_type in ['foraging1', 'foraging2']:
            if item_files[file_type]:
                rows_to_add = []
                with open(item_files[file_type], mode='r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    header = next(reader)  # Skip the header row

                    for row in reader:
                        row = [x.strip() if x else '-' for x in row]
                        if file_type == 'foraging1':
                            zones = re.sub(r"[{}']", "", row[10]).replace(":", " ").replace(",", "<br>")
                            months = "<br>".join([month_lookup(x) for x in row[7].split('|') if x])
                            bonus_months = "<br>".join([month_lookup(x) for x in row[8].split('|') if x])
                            malus_months = "<br>".join([month_lookup(x) for x in row[9].split('|') if x])
                            formatted_row = f"""    |-
    | {row[0]}-{row[1]}
    | {row[2]}
    | {zones}
    | {row[3]}
    | {row[4]}
    | {row[5]}
    | {row[6]}
    | {months}
    | {bonus_months}
    | {malus_months}
"""
                        elif file_type == 'foraging2':
                            chance_info = f"all with {row[0]} chance"
                            formatted_row = f"""    |-
    | 1
    | 0
    | {chance_info}
    | -
    | -
    | -
    | -
    | all
    | -
    | -
"""
                        rows_to_add.append(formatted_row)

                if rows_to_add:
                    foraging_table = f"    {{| class=\"wikitable theme-red\" style=\"width:98%;\"\n"
                    foraging_table += "    |+ {{ll|Foraging}}\n"
                    foraging_table += "    ! rowspan=\"2\" | Amount\n    ! rowspan=\"2\" | Skill level\n    ! rowspan=\"2\" | Biomes\n    ! colspan=\"4\" style=\"text-align:center;\" | Weather modifiers\n    ! colspan=\"3\" style=\"text-align:center;\" | Month modifiers\n    |-\n"
                    foraging_table += "    ! Snow\n    ! Rain\n    ! Day\n    ! Night\n    ! Months available\n    ! Bonus months\n    ! Malus months\n"
                    foraging_table += ''.join(rows_to_add) + "    |}\n"
                    output_data += foraging_table

        # Append closing divs for the toggle content and box
        output_data += f"    </div></div><div class=\"toggle large mw-customtoggle-togglebox-{item}\" title=\"{{{{int:show}}}}/{{{{int:hide}}}}\"></div></div>\n"

        # Add the closing bot flag
        output_data += f"<!--END BOT FLAG|{item}|{version}-->"

        # Write the formatted data to a file if there's any data to write
        if output_data:
            with open(os.path.join(complete_output_path, f'{item}.txt'), 'w') as output_file:
                output_file.write(output_data)


if __name__ == '__main__':
    main()

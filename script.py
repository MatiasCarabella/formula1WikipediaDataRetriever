# Import required libraries
import requests
import json
import re
import unicodedata
from bs4 import BeautifulSoup

def clean_driver_name(driver):
    # Remove text between square brackets
    driver = re.sub(r'\[.*?\]', '', driver)
    driver = re.sub(r"\(.*\)", "", driver)

    # Replace certain Unicode characters with their ASCII equivalents
    driver = unicodedata.normalize('NFKD', driver).encode('ASCII', 'ignore').decode('ASCII')

    return driver

def split_names(string):
    # Define a regular expression pattern using a lookbehind assertion (?<=)
    # and a lookahead assertion (?=). This will match any position between
    # a lowercase letter and an uppercase letter.
    pattern = r"(?<=[a-z.])(?=[A-Z])"
    
    # Use the re.split() function to split the string using the regular
    # expression pattern as the delimiter.
    split_string = re.split(pattern, string)
    
    # Use a list comprehension to iterate over the split string and remove
    # any leading or trailing whitespace from each name. Also remove any
    # empty strings from the list.
    return [name.strip() for name in split_string if name.strip()]

def clean_constructor_name(constructor):
    # Get FIRST WORD and reemove text between square brackets
    constructor = re.sub(r'\[.*?\]', '', constructor.get_text(strip=True).split('-')[0])

    return constructor

### CONSTANTS ### 
# You'll probably have to modify some of these depending on the YEAR you are querying

YEAR = 1965 # Year from which to retrieve data

ENTRIES_TABLE_INDEX = 1 # USUALLY '0' OR '1'
RESULTS_TABLE_INDEX = 2 # USUALLY '4', '5', OR '6'
# When running the script, a 'tables.html' file is generated. If one of them (or both) are not the right ones, then modify these.

ENTRIES_START_FROM_INDEX = 1 # USUALLY '1' OR '2'
RESULTS_START_FROM_INDEX = 1 # USUALLY '1' OR '2'
# These are for ignoring the header rows, the number should match the first row with actual data.

SPECIAL_FORMAT = YEAR in [2015, 2017, 2018, 2019, 2020, 2021, 2022, 2023]
# Sometimes there's NO headers in the Entries table, this boolean takes that into account.

ENTRIES_DRIVER_MAIN_INDEX = 4 # USUALLY EITHER '4' OR '5'
ENTRIES_DRIVER_SECONDARY_INDEX = 0 # USUALLY EITHER '0' OR '1'
# The column index in which the Driver name is present. Given that the Constructor spans multiple Drivers (but only counts as a column in its first row),
# the first driver from a given team is always a higher index than the rest.

ARTICLE_NAME ='Formula_One_World_Championship' if  YEAR >= 1981 else 'Formula_One_season' 

# Define the URL of the Wikipedia page to retrieve data from
url = 'https://en.wikipedia.org/wiki/' + str(YEAR) + '_' + ARTICLE_NAME

# Send an HTTP request to the webpage and retrieve the HTML content
response = requests.get(url)
html_content = response.content

# Parse the HTML content using BeautifulSoup and locate the tables you want to extract data from
soup = BeautifulSoup(html_content, 'html.parser')
tables = soup.find_all('table')

# Extract the tables for entries and final standings
table_entries = tables[ENTRIES_TABLE_INDEX] # USUALLY '0' OR '1'
table_results = tables[RESULTS_TABLE_INDEX] # USUALLY '4', '5', OR '6'

### DEBUG ###

# Define the filename of the HTML file to save
filename = 'tables.html'

# Open the file for writing
with open(filename, 'w') as f:
    # Write the HTML code for the entries table
    f.write(str(table_entries))

    # Write the HTML code for the final standings table
    f.write(str(table_results))

### ENTRIES TABLE ###

# Extract the rows from the entries table (skipping the first row which contains the headers)
rows = table_entries.find_all('tr')[ENTRIES_START_FROM_INDEX:]

# Initialize the most recent value of the Constructor column to an empty string
latest_constructor = ''

# Extract the values of the Constructor and Driver columns from each row and store them in a list of dictionaries
data = []

for row in rows:
    # Extract the th and td columns from each row
    cols_th = row.find_all('th')
    cols_td = row.find_all('td')
    # If the Constructor column is not empty, update the latest_constructor value
    if (cols_th):
        constructor = clean_constructor_name(cols_th[0])
        if (constructor.startswith("Source")):
            break
        latest_constructor = constructor
        if (cols_td):
            if (len(cols_td) < 6): # This takes an edge case (combined cells) into account
                continue
            drivers = cols_td[ENTRIES_DRIVER_MAIN_INDEX] # USUALLY EITHER '4' OR '5'
    else:
        if SPECIAL_FORMAT:
            if (clean_constructor_name(cols_td[0]).startswith("Source")):
                break
            constructor = clean_constructor_name(cols_td[1])
            drivers = cols_td[5]
        else:
            latest_constructor = constructor
            # If the Driver column does not contain letters, then it's not really the Driver column, so we look for it at a different index
            if re.search(r'[A-Za-z]', cols_td[ENTRIES_DRIVER_SECONDARY_INDEX].get_text(strip=True)): # USUALLY EITHER '0' OR '1'
                drivers = cols_td[ENTRIES_DRIVER_SECONDARY_INDEX] # USUALLY EITHER '0' OR '1'
            else:
                drivers = cols_td[ENTRIES_DRIVER_SECONDARY_INDEX + 1] # USUALLY EITHER '0' OR '1'
    for driver in split_names(clean_driver_name(drivers.get_text(strip=True))):
        # Append the extracted data to the list of dictionaries
        data.append({
            'year': YEAR, 
            'name': driver, 
            'team': constructor})

# Save the data to a JSON file
with open('entry_output.json', 'w') as f:
    json.dump(data, f, indent=4)

### RESULTS TABLE ###

# Extract the rows from the final standings table (skipping the first two rows which contain the headers)
rows = table_results.find_all('tr')[RESULTS_START_FROM_INDEX:] # USUALLY '1' OR '2'

# Extract the values of the Driver, Championship Position, Points, Wins, and Podiums columns from each row and store them in a list of dictionaries
data = []

for row in rows:
    # Initialize variables for the number of wins and podiums
    wins = 0
    podiums = 0

    # Extract the th and td columns from each row
    cols_th = row.find_all('th')
    cols_td = row.find_all('td')

    if (len(cols_th) == 0):
        break

    # Extract the Championship Position, Points and Driver columns. If Championship Position equals 'Pos.' then that's the end of the table so we end the loop
    championship_position = cols_th[0].get_text(strip=True)
    if championship_position.startswith("Pos") or championship_position.startswith("Driver"):
        continue
    if championship_position == "Key":
        break

    # SOMETIMES INDEX '1' DOESN'T EXIST, AND POINTS ARE PRESENT IN THE FINAL <td>
    if (len(cols_th)) > 1: 
        points = cols_th[1].get_text(strip=True) 
        points_header = True
    else:
        points = cols_td[len(cols_td) - 1].get_text(strip=True)
        points_header = False

    driver = clean_driver_name(cols_td[0].get_text(strip=True))

    # Extract the Wins and Podiums columns
    for i, cols in enumerate(cols_td[1:]):
        if (not(points_header) and i == len(cols_td) - 2):
            break
        race_position = cols.text.strip()
        match = re.search(r'\d+', race_position)
        if match:
            race_position = int(match.group())
            if race_position == 1:
                wins += 1
            if race_position <= 3 and race_position != 0: # Beware drivers with exactly '1' point, it might count as a Win/Podium
                podiums += 1
    
    # Append the extracted data to the list of dictionaries
    data.append({'name': driver, 'position': championship_position, 'points': points, 'wins': wins, 'podiums': podiums})

# Save the data to a JSON file
with open('results_output.json', 'w') as f:
    json.dump(data, f, indent=4)

### MERGING THE JSON files

# Load the JSON data from the files
with open('entry_output.json') as f:
    file1 = json.load(f)

with open('results_output.json') as f:
    file2 = json.load(f)

# Combine dictionaries based on "name" field
combined = []
for f2 in file2:
    for f1 in file1:
        if f1["name"] == f2["name"]:
            # merge dictionaries
            f2.update(f1)
            combined.append(f2)
            break

# Reorder fields
reordered_data = []
for item in combined:
    reordered_item = {}
    reordered_item["year"] = item.pop("year")
    reordered_item["name"] = item.pop("name")
    reordered_item["team"] = item.pop("team")
    reordered_item.update(item)
    reordered_data.append(reordered_item)

# Write the reordered data to a file
with open('final_output.json', 'w') as f:
    json.dump(reordered_data, f, indent=4)
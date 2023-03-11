# Import required libraries
import requests
import json
import re
import unicodedata
from bs4 import BeautifulSoup

def clean_driver_name(driver):
    # Remove text between square brackets
    driver = re.sub(r'\[.*?\]', '', driver)

    # Replace certain Unicode characters with their ASCII equivalents
    driver = unicodedata.normalize('NFKD', driver).encode('ASCII', 'ignore').decode('ASCII')

    return driver

def split_names(string):
    # Define a regular expression pattern using a lookbehind assertion (?<=)
    # and a lookahead assertion (?=). This will match any position between
    # a lowercase letter and an uppercase letter.
    pattern = r"(?<=[a-z])(?=[A-Z])"
    
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

# Set the year to retrieve data for
year = 2014

# Define the URL of the Wikipedia page to retrieve data from
url = 'https://en.wikipedia.org/wiki/' + str(year) + '_Formula_One_World_Championship'

# Send an HTTP request to the webpage and retrieve the HTML content
response = requests.get(url)
html_content = response.content

# Parse the HTML content using BeautifulSoup and locate the tables you want to extract data from
soup = BeautifulSoup(html_content, 'html.parser')
tables = soup.find_all('table')

# Extract the tables for entries and final standings
table_entries = tables[0] # USUALLY '0' OR '1'
table_results = tables[6] # USUALLY '4', '5', OR '6'

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
rows = table_entries.find_all('tr')[1:]

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
        if (constructor == 'Sources:'):
            break
        latest_constructor = constructor
        if (cols_td):
            drivers = cols_td[4] # USUALLY EITHER '4' OR '5'
    else:
        latest_constructor = constructor
        # If the Driver column does not contain letters, then it's not really the Driver column, so we look for it at a different index
        if re.search(r'[A-Za-z]', cols_td[0].get_text(strip=True)): # USUALLY EITHER '0' OR '1'
            drivers = cols_td[0] # USUALLY EITHER '0' OR '1'
        else:
            drivers = cols_td[1] # USUALLY EITHER '0' OR '1'

    for driver in split_names(clean_driver_name(drivers.get_text(strip=True))):
        # Append the extracted data to the list of dictionaries
        data.append({
            'year': year, 
            'name': driver, 
            'team': constructor})

# Save the data to a JSON file
with open('entry_output.json', 'w') as f:
    json.dump(data, f, indent=4)

### FINAL STANDINGS TABLE ###

# Extract the rows from the final standings table (skipping the first two rows which contain the headers)
rows = table_results.find_all('tr')[1:] # USUALLY '1' OR '2'

# Extract the values of the Driver, Championship Position, Points, Wins, and Podiums columns from each row and store them in a list of dictionaries
data = []

for row in rows:
    # Initialize variables for the number of wins and podiums
    wins = 0
    podiums = 0

    # Extract the th and td columns from each row
    cols_th = row.find_all('th')
    cols_td = row.find_all('td')

    # Extract the Championship Position, Points and Driver columns. If Championship Position equals 'Pos.' then that's the end of the table so we end the loop
    championship_position = cols_th[0].get_text(strip=True)
    if championship_position == 'Pos.':
        break
    points = cols_th[1].get_text(strip=True)
    driver = clean_driver_name(cols_td[0].get_text(strip=True))

    # Extract the Wins and Podiums columns
    for cols in cols_td[1:]:
        race_position = cols.text.strip()
        match = re.search(r'\d+', race_position)
        if match:
            race_position = int(match.group())
            if race_position == 1:
                wins += 1
            if race_position <= 3:
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
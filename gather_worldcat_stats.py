## Script for Gathering Library Records from WorldCat
## gather_worldcat_stats.py

## Refer to read_me.txt in the worldcat_analysis directory for an explanation of the script and its dependencies.
## Main Program starts on line 486

import string
import csv
import requests
import json
from bs4 import BeautifulSoup

import codecs
import sys
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# Importing file that contains WorldCat Search API key
import secrets

# Setting up cache
CACHE_FNAME = "worldcat_search_cache.json"

try:
    cache_file = open(CACHE_FNAME, 'r', encoding="utf-8")
    cache_contents = cache_file.read()
    CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    CACHE_DICTION = {}

### Functions

## Functions for making API requests and scraping web pages, and managing the returned data

# Makes unique request string for WorldCat Search API caching
def make_unique_request_string(base_url, params_diction, private_keys=["wskey"]):
    sorted_parameters = sorted(params_diction.keys())
    fields = []
    for parameter in sorted_parameters:
        if parameter not in private_keys:
            fields.append("{}-{}".format(parameter, params_diction[parameter]))
    return base_url + "&".join(fields)

# Makes the request and caches the new data, or retrieves the cached data; handles both API interaction and gathering HTML from the Web
def make_request_using_cache(url, params=None):
    global problematic_json_snippets
    if params != None:
        cache_url = make_unique_request_string(url, params)
    else:
        cache_url = url
    if cache_url in CACHE_DICTION.keys():
        # print("Retrieving cached data...")
        return CACHE_DICTION[cache_url]
    else:
        # For requests to WorldCat Search API
        if params != None:
            # print("Making a request for new data...")
            response = requests.get(url, params)
            if response.status_code == 403:
                message = "Reached API limit"
                print(message)
                return message
            else:
                if "json" in params.values():
                    json_string = response.text
                    for snippet in problematic_json_snippets:
                        if snippet in json_string:
                            corrected_snippet = snippet.replace('"', '')
                            json_string = json_string.replace(snippet, corrected_snippet)
                    data = json.loads(json_string)
                else:
                    data = response.text
        else:
            # For gathering HTML from Wikimedia site
            response = requests.get(url)
            data = response.text
        CACHE_DICTION[cache_url] = data
        dumped_json_cache = json.dumps(CACHE_DICTION, indent=4)
        file_open = open(CACHE_FNAME, "w", encoding="utf-8")
        file_open.write(dumped_json_cache)
        file_open.close()
        return CACHE_DICTION[cache_url]

# Creates a dictionary containing the work-specific metadata provided in WorldCat Library Locations responses
def create_metadata_dictionary(data):
    metadata_dict = {"Title": data["title"],
                     "Author": data["author"],
                     "Publisher": data["publisher"],
                     "Date": data["date"],
                     "OCLC Number": data["OCLCnumber"]}
    if "ISBN" not in data.keys():
        metadata_dict["ISBN"] = "No ISBNs provided"
    else:
        metadata_dict["ISBN"] = data["ISBN"]
    return metadata_dict

# Constructs a URL and dictionary of parameters, passes those to the make_request_using_cache function, and, when records are found
# corresponding to an identifier (ISBN or OCLC number), combines the library results from multiple requests and returns the data in
# a neat format.
def collect_data_for_title(identifier, isbn_or_oclc, frbr_grouping=True):
    global worldcat_search_api_key
    global not_found_uri

    base_url = "http://www.worldcat.org/webservices/catalog/content/libraries/"
    if isbn_or_oclc == "isbn":
        base_url += "isbn/{}?".format(identifier)
    elif isbn_or_oclc == "oclc":
        base_url += "{}?".format(identifier)
    library_index = 1
    message = None
    params = {"wskey": worldcat_search_api_key,
              "format":"json",
              "servicelevel": "default",
              "maximumLibraries": "100",
              "startLibrary": int(library_index)}
    if frbr_grouping == False:
        params["frbrGrouping"] = "off"

    library_dictionaries = []
    more_records = True
    first_successful_request = True

    while more_records:
        params["startLibrary"] = library_index
        data = make_request_using_cache(base_url, params)
        if type(data) == type("string") and data == "Reached API limit":
            return data
        else:
            if "diagnostic" in data.keys():
                message = data["diagnostic"]["message"]
                uri = data["diagnostic"]["uri"]
                if uri != not_found_uri:
                    print("Unexpected result; check cache.")
                return uri
            elif "diagnostics" in data.keys():
                if "diagnostic" in data["diagnostics"].keys():
                    uri = data["diagnostics"]["diagnostic"]["uri"]
                    if uri != not_found_uri:
                        print("Unexpected result; check cache")
                    return uri
            else:
                if "diagnostic" in data["library"][0].keys():
                    message = data["library"][0]["diagnostic"]["message"]
                    uri = data["library"][0]["diagnostic"]["uri"]
                    if uri == not_found_uri:
                        metadata = create_metadata_dictionary(data)
                        metadata["Number of Libraries"] = 0
                        library_dictionaries = []
                        return (metadata, library_dictionaries)
                    elif message == "First position out of range":
                        more_records = False
                    else:
                        print("Unexpected result; check cache.")
                        return message
                else:
                    if first_successful_request:
                        metadata = create_metadata_dictionary(data)
                        first_successful_request = False
                    new_libraries = data["library"]
                    library_dictionaries += new_libraries
        library_index += 100
    metadata["Number of Libraries"] = len(library_dictionaries)
    return (metadata, library_dictionaries)

# Coordinates requests for each identifier, handles normal and problematic results, and then combines data associated with all identifiers
def collect_libraries_for_identifiers(identifiers, isbn_or_oclc, frbr_grouping=True):
    at_api_limit = False
    identifiers_searched = []
    metadata_dictionaries = {}
    all_libraries_for_title = []
    for identifier in identifiers:
        result = collect_data_for_title(identifier, isbn_or_oclc, frbr_grouping)
        identifiers_searched.append(identifier)
        if type(result) == type("string"):
            if result == "Reached API limit":
                at_api_limit = True
                break
            elif result == not_found_uri:
                print("No records found for {} ({})".format(identifier, isbn_or_oclc))
        else:
            metadata = result[0]
            metadata_dictionaries[identifier] = metadata
            libraries = result[1]
            all_libraries_for_title += libraries
    return (identifiers_searched, metadata_dictionaries, all_libraries_for_title, at_api_limit)

# Uses the Bibliographic Resource tool to search for records, parses the returned MARC XML, and then returns a list of matching OCLC numbers and
# additional metadata for validation purposes
def look_up_record_for_oclc_numbers(title_dictionary, title_key, frbr_grouping=True):
    global worldcat_search_api_key
    base_url = 'http://www.worldcat.org/webservices/catalog/search/sru?'

    if title_dictionary["Subtitle"] not in ["N/A", ""]:
        full_title = "{} {}".format(title_dictionary["Title"], title_dictionary["Subtitle"])
    else:
        full_title = title_dictionary["Title"]
    title_to_search = full_title.replace(":", "").replace(",", "").replace('"', '').replace("&", "and").replace("#", "")

    params = {"wskey": worldcat_search_api_key,
              "query": 'srw.ti all "{}"'.format(title_to_search),
              "maximumRecords": 100}
    if frbr_grouping == False:
        params["frbrGrouping"] = "off"
    result = make_request_using_cache(base_url, params)
    if result == "Reached API limit":
        return result
    result_xml = BeautifulSoup(result, 'xml')
    number_of_records = result_xml.find("numberOfRecords").text
    records = result_xml.find_all("recordData")

    oclc_matches = {}
    oclc_matches["Number of Records"] = number_of_records
    oclc_matches["Query"] = params["query"]
    oclc_matches["FRBR Grouping"] = frbr_grouping
    oclc_matches["OCLC Numbers"] = {}
    for record in records:
        marc_title = record.find("datafield", tag="245").find("subfield", code="a")
        if marc_title != None:
            marc_title = marc_title.text
        else:
            marc_title = "[No title included]"

        marc_fields_dict = {"Imprint": ["260", "b"],
                            "Author": ["100", "a"],
                            "Series": ["490", "a"]}

        marc_values_dict = {"Title": marc_title}
        for key in marc_fields_dict:
            statement = record.find("datafield", tag=marc_fields_dict[key][0])
            if statement == None:
                value = "[No {} included]".format(key)
            else:
                value = statement.find("subfield", code=marc_fields_dict[key][1])
                if value == None:
                    value = "[No {} included]".format(key)
                else:
                    value = value.text
            marc_values_dict[key] = value

        if marc_title != "[No title included]":
            title_comparison_result = compare_titles(title_dictionary["Title"], marc_title)
        else:
            title_comparison_result = False
        if marc_values_dict["Imprint"] != "[No imprint included]":
            imprint_comparison_result = compare_imprints(title_dictionary["Imprint"], marc_values_dict["Imprint"])
        else:
            imprint_comparison_result = False

        if title_comparison_result == True and imprint_comparison_result == True:
            oclc_number = record.find("controlfield", tag="001").text
            oclc_matches["OCLC Numbers"][oclc_number] = {"MARC Title": marc_values_dict["Title"],
                                                         "MARC Imprint": marc_values_dict["Imprint"],
                                                         "MARC Author": marc_values_dict["Author"],
                                                         "MARC Series": marc_values_dict["Series"]}
    return oclc_matches

# Takes a CSV string and converts it to a Python Boolean value; for processing FRBR instructions in tricky_titles.csv
def convert_frbr_string_to_boolean(string):
    if string == "TRUE":
        frbr_value = True
    elif string == "FALSE":
        frbr_value = False
    else:
        frbr_value = ""
        print("FRBR value not valid")
    return frbr_value

## Functions for comparing text in WorldCat response to text in records from neh_title_records.json

# Normalizes WorldCat and record titles, checks whether one is contained within the other, and then, if necessary, compares individual terms
def compare_titles(record_title, other_title):
    lower_record_title = record_title.lower().replace('"', '').replace(",", "").replace(".", "").replace(":", "").replace("-", " ").strip()
    lower_record_title_split = lower_record_title.split()
    normalized_record_title_split = []
    for word in lower_record_title_split:
        if word not in string.punctuation:
            normalized_record_title_split.append(word)
    normalized_record_title = " ".join(normalized_record_title_split)

    lower_other_title = other_title.lower().replace('"', '').replace(",", "").replace(".", "").replace(":", "").replace("&quot;", "").replace("-", " ").strip()
    lower_other_title_split = lower_other_title.split()
    if lower_other_title_split[0].lower() in ["the", "a", "an"]:
        lower_other_title_split.pop(0)
    normalized_other_title_split = []
    for word in lower_other_title_split:
        if word not in string.punctuation:
            normalized_other_title_split.append(word)
    normalized_other_title = " ".join(normalized_other_title_split)

    if normalized_record_title in normalized_other_title or normalized_other_title in normalized_record_title:
        match = True
    else:
        list_comp = [(a, b) for a in normalized_record_title_split for b in normalized_other_title_split if a == b]
        list_comp_without_dups = []
        for pair in list_comp:
            occurences = normalized_record_title_split.count(pair[0])
            if list_comp_without_dups.count(pair) < occurences:
                list_comp_without_dups.append(pair)

        ratio = len(list_comp_without_dups) / len(normalized_record_title_split)
        if ratio >= 0.75:
            match = True
        else:
            match = False
    return match

# Normalizes WorldCat and record imprint values, and then checks whether the center name, the university, or whether the city and state
# is in the WorldCat value
def compare_imprints(record_imprint, other_imprint):
    normalized_record_imprint = record_imprint.lower().replace("um ", "").replace("u of m", "")
    normalized_other_imprint = other_imprint.lower().replace("univ.", "university").replace("univ ", "university ").replace("mich.", "michigan").replace("centre", "center").replace(",", "")

    if normalized_record_imprint in normalized_other_imprint or "university of michigan" in normalized_other_imprint:
        match = True
    else:
        if "ann arbor" in normalized_other_imprint and "michigan" in normalized_other_imprint:
            match = True
        else:
            match = False
    return match

# Compares title, author, and publisher information from an API response to our metadata records, determining whether they are acceptably similar;
# this function reports results which are then assigned to the "Match Check" key in the worldcat_stats dictionary
def check_for_metadata_match(title_dictionary, metadata_dictionaries):
    check_dictionaries = {}
    for isbn in metadata_dictionaries:
        metadata_dictionary = metadata_dictionaries[isbn]
        checks = {}

        # Comparing titles
        record_title = title_dictionary["Title"]
        found_title = metadata_dictionary["Title"]
        if ":" in metadata_dictionary["Title"]:
            if title_dictionary["Subtitle"] not in ["N/A", ""]:
                record_title += ": {}".format(title_dictionary["Subtitle"])
            else:
                found_title = found_title.split(":")[0]
        checks["Title"] = compare_titles(record_title, found_title)

        # Comparing imprint/publisher
        checks["Publisher"] = compare_imprints(title_dictionary["Imprint"], metadata_dictionary["Publisher"])

        # Comparing authors
        normalized_record_author = title_dictionary["Author 1 - Last"].lower()
        normalized_oclc_author = metadata_dictionary["Author"].lower()
        if normalized_record_author in normalized_oclc_author:
            checks["Author"] = True
        else:
            checks["Author"] = False

        check_dictionaries[isbn] = checks

    conversion_dict = {"Title": "Title", "Author": "Author 1 - Last", "Publisher": "Imprint"}
    all_results = []
    match_failures = {}
    for isbn_key in check_dictionaries:
        checks_for_isbn = check_dictionaries[isbn_key]
        match_failures[isbn_key] = {}
        all_results += list(checks_for_isbn.values())
        for check_key in checks_for_isbn:
            if checks_for_isbn[check_key] == False:
                match_failures[isbn_key][check_key] = "{} did not match {}".format(metadata_dictionaries[isbn_key][check_key], title_dictionary[conversion_dict[check_key]])

    if False in all_results:
        return (False, match_failures)
    else:
        return (True, match_failures)

## Functions for analyzing library data for each title

# Iterates through a list of libraries and creates a new list of libraries with any duplicates removed
def find_libraries_without_duplicates(library_list):
    library_symbols = []
    libraries_without_duplicates = []
    for library in library_list:
        symbol = library["oclcSymbol"]
        if symbol not in library_symbols:
            library_symbols.append(symbol)
            libraries_without_duplicates.append(library)
    return libraries_without_duplicates

# Gathers HTML from Wikimedia page (https://meta.wikimedia.org/wiki/List_of_countries_by_regional_classification) and creates a dictionary for simple lookup
def create_country_to_region_dictionary():
    url = "https://meta.wikimedia.org/wiki/List_of_countries_by_regional_classification"
    data = make_request_using_cache(url)
    wikimedia_html = BeautifulSoup(data, "html.parser")
    table_html = wikimedia_html.find("tbody")
    trs = table_html.find_all("tr")
    country_to_region_dictionary = {}
    for tr in trs[1:]:
        tds = tr.find_all("td")
        country = tds[0].text.strip()
        region = tds[1].text.strip()
        if country not in ["Anonymous Proxy", "Invalid IP", "Satellite Provider", "Europe"]:
            country_to_region_dictionary[country] = region
    return country_to_region_dictionary

# Creates a dictionary for each title record that counts the number of libraries found and determines their distribution by country and region
def perform_basic_analysis(libraries):
    global country_to_region_dictionary
    data_summary_dict = {}

    data_summary_dict["Number of Libraries"] = len(libraries)

    countries_represented = {}
    for library in libraries:
        if library["country"] not in countries_represented:
            countries_represented[library["country"]] = 0
        countries_represented[library["country"]] += 1
    data_summary_dict["Country Distribution"] = countries_represented

    region_counts = {}
    weird_case_conversion_dict = {"Viet Nam": "Vietnam", "Macao": "Macau"}
    for library in libraries:
        if library["country"] in weird_case_conversion_dict.keys():
            country = weird_case_conversion_dict[library["country"]]
        else:
            country = library["country"]
        if country in country_to_region_dictionary.keys():
            region = country_to_region_dictionary[country]
            if region not in region_counts:
                region_counts[region] = 0
            region_counts[region] += 1
        else:
            if country == "":
                if "Unknown" not in region_counts.keys():
                    region_counts["Unknown"] = 0
                region_counts["Unknown"] += 1
            else:
                print("*** {} not found in country to region conversion dictionary ***".format(library["country"]))
    data_summary_dict["Region Distribution"] = region_counts

    return data_summary_dict

### Initializing Variables

global worldcat_search_api_key
worldcat_search_api_key = secrets.production_wskey

# The problematic_json_snippets variable lists phrases returned in various API responses that resulted in errors, specifically because
# extra quotation marks made incorrectly formatted JSON strings. The make_request_using_cache function includes a few lines of code that
# remove these extra quotation marks. Problematic snippets were identified by printing the full json_string in the command line interface,
# copying it, and then pasting it into the JSON Editor Online tool (https://jsoneditoronline.org/).
global problematic_json_snippets
problematic_json_snippets = ['"Mario Gattullo"', '"Lucian Blaga"', '"Antonio Pigliaru"', '"Walter Bigiavi"', '"Roberto Ruffilli"']

global not_found_uri
not_found_uri = "info:srw/diagnostic/1/65"

global country_to_region_dictionary
country_to_region_dictionary = create_country_to_region_dictionary()

# Creating a dictionary (from data contained in tricky_titles.csv) that contains titles that I identified as having small or erroneous
# library counts or other issues when using the ISBN search method. Instructions are included in the nested dictionaries on how to use
# the Bibliographic Resource tools to identify OCLC numbers and whether to use the FRBR grouping setting. See read_me.txt for additional
# explanation.
tricky_open = open("inputs/tricky_titles.csv", newline='', encoding="utf-8-sig")
csvreader = csv.reader(tricky_open)
rows = []
for line in csvreader:
    rows.append(line)
tricky_open.close()

tricky_titles = {}
headers = rows[0]
for row in rows[1:]:
    tricky_title = {}
    for field in headers[1:]:
        field_value = row[headers.index(field)]
        if field == "OCLC Numbers":
            field_value = field_value.split("; ")
        tricky_title[field.strip()] = field_value
    tricky_titles[row[0]] = tricky_title

# Unique identifiers for titles temporarily or permanently excluded from analysis
problematic_record_keys = ["191", "241", "245", "259", "265", "266", "308", "365"]

# Opening title records file to enable access to title info and ISBNs
records_file = open("inputs/neh_title_records.json", "r", encoding="utf-8")
neh_title_records = json.loads(records_file.read())["Title Records"]
records_file.close()

# Variable that allows the script's user to control up to what record to gather data for
last_record_number = 372

### Main Program

if __name__ == "__main__":

    print("*** WorldCat Analysis Script for NEH/Mellon HOB Asian Studies Project ***")

    worldcat_stats = {}
    at_api_limit = False
    no_records_found = []
    match_issues = []
    title_keys = list(neh_title_records.keys())

    for title_key in title_keys[:last_record_number]:
        print("*** #{} ***".format(title_key))
        if at_api_limit == True:
            print("Stopping program...")
            break
        else:
            if title_key in problematic_record_keys:
                worldcat_stats[title_key] = {}
            else:
                title_record = neh_title_records[title_key]
                if title_key in tricky_titles.keys():
                    skip_isbn = True
                else:
                    skip_isbn = False
                    isbns = []
                    for isbn_field in ["HC ISBN", "PB ISBN", "EB ISBN", "EB (OA) ISBN"]:
                        if title_record[isbn_field] not in ["", "PB Only", "Paper Only", "See rights column", "N/A", "Not Available"]:
                            isbns.append(title_record[isbn_field])
                    result = collect_libraries_for_identifiers(isbns, "isbn")
                    at_api_limit = result[3]
                    if at_api_limit == True:
                        break
                    else:
                        isbns_searched = result[0]
                        metadata_dictionaries = result[1]
                        all_libraries = result[2]
                if skip_isbn == False and len(all_libraries) != 0:
                    match_check = check_for_metadata_match(title_record, metadata_dictionaries)
                    if match_check[0] == False:
                        match_issues.append(title_key)
                    libraries_without_duplicates = find_libraries_without_duplicates(all_libraries)
                    worldcat_stats[title_key] = {"Identifier Type Used for Data Collection": "ISBN",
                                                 "ISBNs Searched": isbns_searched,
                                                 "OCLC Lookup Matches": "N/A",
                                                 "OCLC Numbers Searched": "N/A",
                                                 "Library Locations - FRBR Grouping": True,
                                                 "Response Metadata": metadata_dictionaries,
                                                 "Match Check": match_check,
                                                 "Complete Library Data": libraries_without_duplicates}
                else:
                    if skip_isbn == True:
                        isbns_searched = ["Problems with the ISBN results were identified."]
                    if title_key in tricky_titles:
                        if tricky_titles[title_key]["Bibliographic/Manual"] == "Bibliographic":
                            frbr_grouping_bib = convert_frbr_string_to_boolean(tricky_titles[title_key]["Bibliographic Resource - FRBR Grouping"])
                            oclc_matches = look_up_record_for_oclc_numbers(neh_title_records[title_key], title_key, frbr_grouping=frbr_grouping_bib)
                            if oclc_matches == "Reached API limit":
                                print("Stopping program...")
                                break
                            oclc_numbers = oclc_matches["OCLC Numbers"].keys()
                        elif tricky_titles[title_key]["Bibliographic/Manual"] == "Manual":
                            oclc_matches = "N/A; Tricky Title; OCLC numbers gathered manually."
                            oclc_numbers = tricky_titles[title_key]["OCLC Numbers"]
                        else:
                            print("Nonvalid entry!")
                    else:
                        oclc_matches = look_up_record_for_oclc_numbers(neh_title_records[title_key], title_key)
                        if oclc_matches == "Reached API limit":
                            print("Stopping program...")
                            break
                        else:
                            oclc_numbers = oclc_matches["OCLC Numbers"].keys()
                    if len(oclc_numbers) == 0:
                        worldcat_stats[title_key] = {"Identifier Type Used for Data Collection": "N/A",
                                                     "ISBNs Searched": isbns_searched,
                                                     "OCLC Lookup Matches": oclc_matches,
                                                     "OCLC Numbers Searched": [],
                                                     "Library Locations - FRBR Grouping": "N/A",
                                                     "Response Metadata": "No results found using ISBNs or OCLC numbers",
                                                     "Match Check": "N/A",
                                                     "Complete Library Data": []}
                        no_records_found.append(title_key)
                    else:
                        if title_key in tricky_titles:
                            frbr_grouping_library = convert_frbr_string_to_boolean(tricky_titles[title_key]["Library Locations - FRBR Grouping"])
                        else:
                            frbr_grouping_library = True
                        result = collect_libraries_for_identifiers(oclc_numbers, "oclc", frbr_grouping=frbr_grouping_library)
                        at_api_limit = result[3]
                        if at_api_limit == True:
                            break
                        else:
                            oclc_numbers_searched = result[0]
                            metadata_dictionaries = result[1]
                            all_libraries = result[2]
                            libraries_without_duplicates = find_libraries_without_duplicates(all_libraries)
                            worldcat_stats[title_key] = {"Identifier Type Used for Data Collection": "OCLC",
                                                         "ISBNs Searched": isbns_searched,
                                                         "OCLC Lookup Matches": oclc_matches,
                                                         "OCLC Numbers Searched": oclc_numbers_searched,
                                                         "Library Locations - FRBR Grouping": frbr_grouping_library,
                                                         "Response Metadata": metadata_dictionaries,
                                                         "Match Check": "N/A",
                                                         "Complete Library Data": libraries_without_duplicates}
                            if len(all_libraries) == 0:
                                no_records_found.append(title_key)

    # Adding dictionary with basic analysis to each worldcat_stats record with library dictionaries
    for key in worldcat_stats:
        if key not in problematic_record_keys:
            libraries_found_for_title = worldcat_stats[key]["Complete Library Data"]
            if len(libraries_found_for_title) != 0:
                worldcat_stats[key]["Data Summary"] = perform_basic_analysis(libraries_found_for_title)
            else:
                worldcat_stats[key]["Data Summary"] = "N/A"

    # Storing data gathered from WorldCat in a JSON file
    worldcat_stats_file = open("outputs/worldcat_stats.json", "w", encoding="utf-8")
    worldcat_stats_file.write(json.dumps(worldcat_stats, indent=4))
    worldcat_stats_file.close()

    print("\n")

    ## Data testing
    print("*** Data testing ***")
    print("Records with match issues: " + str(len(match_issues)))
    print("Records with no results: " + str(len(no_records_found)))

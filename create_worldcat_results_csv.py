## Script for Creating Results Summary of WorldCat Library Holdings
## create_worldcat_results_csv.py

## Refer to read_me.txt in the worldcat_analysis directory for an explanation of the script and its dependencies.
## Main Program starts on line 33

import json
import csv
import gather_worldcat_stats

## Functions

# Creates a string version of a Python dictionary to include in some CSV columns
def make_dictionary_string(dictionary):
    list_of_pairs = []
    keys_sorted = sorted(dictionary.keys(), key=lambda x: dictionary[x], reverse=True)
    for key in keys_sorted:
        key_value_string = "{}: {}".format(key, dictionary[key])
        list_of_pairs.append(key_value_string)
    dictionary_string = "; ".join(list_of_pairs)
    return dictionary_string

## Initializing Variables

records_file = open("inputs/neh_title_records.json", "r", encoding="utf-8")
neh_title_records = json.loads(records_file.read())["Title Records"]
records_file.close()

worldcat_stats_file = open("outputs/worldcat_stats.json", "r", encoding="utf-8")
worldcat_stats_dictionary = json.loads(worldcat_stats_file.read())
worldcat_stats_file.close()

## Main Program

results_open = open("outputs/worldcat_analysis_results.csv", "w", encoding="utf-8-sig", newline='')
csvwriter = csv.writer(results_open, delimiter=",", quoting=csv.QUOTE_MINIMAL)

csvwriter.writerow(["Unique Identifier", "Prefix", "Title", "Subtitle", "ISBN/OCLC", "Identifiers Searched", "OCLC Collection Method",
                    "Bibliographic Resource - FRBR Grouping", "Library Locations - FRBR Grouping", "Records Found",  "Number of Libraries",
                    "Country Distribution", "Libraries in Africa", "Libraries in Asia & Pacific", "Libraries in Arab States", "Libraries in Europe",
                    "Libraries in North America", "Libraries in South/Latin America", "Libraries' Location Unknown"])

record_keys = list(neh_title_records.keys())[:(gather_worldcat_stats.last_record_number)]
tricky_titles = gather_worldcat_stats.tricky_titles

for record_key in record_keys:
    title_record = neh_title_records[record_key]
    worldcat_stats_for_record = worldcat_stats_dictionary[record_key]

    unique_identifier = record_key
    prefix = title_record["Prefix"]
    title = title_record["Title"]
    subtitle = title_record["Subtitle"]

    if len(worldcat_stats_for_record.keys()) == 0:
        isbn_or_oclc = "Record excluded from analysis"
        identifiers_searched = "N/A"
        oclc_collection_method = "N/A"
        bibliographic_frbr_grouping = "N/A"
        library_frbr_grouping = "N/A"
        records_found = "N/A"
        number_of_libraries = ""
        country_distribution = ""
        region_csv_values = []
    else:
        isbn_or_oclc = worldcat_stats_for_record["Identifier Type Used for Data Collection"]
        if isbn_or_oclc == "ISBN":
            identifiers_searched = "; ".join(worldcat_stats_for_record["ISBNs Searched"])
        elif isbn_or_oclc == "OCLC":
            identifiers_searched = "; ".join(worldcat_stats_for_record["OCLC Numbers Searched"])
        else:
            identifiers_searched = ""

        if record_key in tricky_titles:
            oclc_collection_method = tricky_titles[record_key]["Bibliographic/Manual"]
            bibliographic_frbr_grouping = tricky_titles[record_key]["Bibliographic Resource - FRBR Grouping"]
            library_frbr_grouping = tricky_titles[record_key]["Library Locations - FRBR Grouping"]
        else:
            if isbn_or_oclc == "OCLC":
                oclc_collection_method = "Bibliographic"
                bibliographic_frbr_grouping = "TRUE"
            else:
                oclc_collection_method = "N/A"
                bibliographic_frbr_grouping = "N/A"
            library_frbr_grouping = "TRUE"

        if worldcat_stats_for_record["Data Summary"] != "N/A":
            records_found = "True"
            data_summary_dictionary = worldcat_stats_for_record["Data Summary"]
            number_of_libraries = data_summary_dictionary["Number of Libraries"]
            country_distribution = make_dictionary_string(data_summary_dictionary["Country Distribution"])
            region_counts = data_summary_dictionary["Region Distribution"]
            regions = ["Africa", "Asia & Pacific", "Arab States", "Europe", "North America", "South/Latin America", "Unknown"]
            region_csv_values = []
            for region in regions:
                if region in region_counts:
                    region_csv_values.append(region_counts[region])
                else:
                    region_csv_values.append(0)
        else:
            records_found = "False"
            number_of_libraries = ""
            country_distribution = ""
            region_csv_values = []
    csvwriter.writerow([unique_identifier, prefix, title, subtitle, isbn_or_oclc, identifiers_searched, oclc_collection_method, bibliographic_frbr_grouping,
                        library_frbr_grouping, records_found, number_of_libraries, country_distribution] + region_csv_values)
results_open.close()

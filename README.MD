# READ ME for gather_worldcat_stats.py and create_worldcat_results_csv.py scripts
### Creator(s): Sam Sciolla (ssciolla@umich.edu)
### Last Updated: 3/4/2019

These Python 3 scripts use the WorldCat Search API, provided by OCLC, to gather data about libraries that have in their holdings Asian Studies titles under consideration for open access publication as part of the NEH/Mellon Humanities Open Book Program grant awarded to the University of Michigan Press.

## Note on script structure and comments

The two scripts within the worldcat_analysis directory are both structured in the same way, proceeding as follows: module imports, function definitions, initialization of important variables, and then the main program. In the gather_worldcat_stats.py script, functions have been grouped together by general purpose and demarcated with comments. Functions and significant variables are described briefly in a comment directly above the relevant code. Some portions of the script have additional comments to explain choices or enhance readability.

## Summary of gather_worldcat_stats.py

The gather_worldcat_stats.py script seeks to take a set of title metadata records from neh_title_records.json, search for library holdings information available through the WorldCat Search API for each of those titles, and then store and analyze the metadata for accuracy and presentation purposes.

There are three main ways that data gathering occurs: using ISBNs, using OCLC numbers, and using tricky_titles.csv (which is, in effect, a variation on using OCLC numbers). In all cases, interaction with the API is handled using the requests Python module and a caching pattern (see functions make_request_using_cache and make_unique_request_string). Currently, print statements that indicate whether new data is being collected or old data is being retrieved from the cache have been commented out.

Once library location data is collected, the program iterates through the results and stores only unique listings (see find_libraries_without_duplicates function) before storing them in a separate dictionary under the same unique identifier key as that of the title's metadata record (see the Inputs and Outputs section).

### ISBNs

For the majority of titles, library location data is collected using ISBN 13 numbers included in the in-progress metadata records, which are made accessible here through the neh_title_records.json file (see Inputs and Outputs section below). For an individual title, the program first identifies all ISBNs associated with a title (including potentially hardcover, paperback, and e-book ISBNs) and then, for each of them, calls out to the API's Library Locations service. The API responds to each successful request with some essential metadata identifying the main record associated with the library holdings and then a list of libraries, with details about their geographic location. As the API can only return a maximum number of 100 libraries in each response, repeated requests were often necessary to collect all library locations associated with an ISBN.

To help ensure the library data returned was for the correct title, a function called check_for_metadata_match was implemented that compares the title, publisher, and author information contained within the metadata returned from the API. The results of the comparison are stored under the key "Match Check" under the record's unique identifier in worldcat_stats (see Inputs and Outputs section below). If the metadata from the API failed to match the record metadata, the record is added to a match_issues variable that is printed out at the end of the script. Inclusion in match_issues is only meant to flag possible issues with data collected, not to indicate a definitive failure.

* Key functions and/or code blocks
  * collect_libraries_for_identifiers
  * collect_data_for_title
  * check_for_metadata_match
  * Lines 511-536 under Main Program

## OCLC Numbers

In cases where a record does not include ISBNs or a search using ISBNs yielded no results, the program initiates an alternative method for identifying records that uses the API's Bibliographic Resource tool. The service allows users to query the WorldCat catalog for records, returning them in a MARC XML format. Using primarily the look_up_record_for_oclc_numbers function, the program is set up to ask the API to return records whose title includes all terms in a string that combines the title and subtitle, with colons and a few other punctuation marks removed. Once the matching records are returned, the program uses the bs4 (BeautifulSoup) Python module to parse the XML records to identify the OCLC Number (OCLC's unique identifiers), the title, and publisher. The title and publisher values are then compared to the corresponding values in the in-house metadata records in a process that repurposes functionality from the previously mentioned "Match Check" algorithm (see compare_titles and compare_imprints functions). Once a set of records that are deemed to acceptably match the internal record are determined, the program then uses the Library Locations service to make requests for library holdings data based on the records' OCLC numbers.

Because a match is required in this case to determine whether an OCLC Number should be searched for, the compare_titles and compare_imprints functions are probably the least reliable part of this program. WorldCat records related to a specific title can be plentiful and inconsistent. To address that, the compare_titles function is written to be relatively forgiving, checking to see whether either of the titles are included within each other after normalizing the title strings (i.e. making them lowercase and removing punctuation marks). If that fails, it checks again to see if the majority (75 percent) of terms in the title in our records appear in the title in the MARC XML. This leads to some false positives; however, the compare_imprints function helps to remove many of those cases, as the function looks for more controlled terms such as the one of the publisher's names (e.g. Center for Chinese Studies), the name of the university, or the city and state (i.e. Ann Arbor and Michigan). Still, these functions could include erroneous records or exclude legitimate one -- possibilities which supported the rationale for ample human inspection and the final data gathering method, described next.

* Key functions and/or code blocks
  * look_up_record_for_oclc_numbers function
  * compare_titles function
  * compare_imprints function
  * Lines 554-591 under Main Program

### Tricky Titles

While many of the cases are dealt with using the two previous methods, other odd situations emerged during testing, which required still another approach to gathering the library holdings data. The "Match Check" process for ISBN data gathering had revealed some instances where records with significantly different titles were being included. There were also numerous cases in which searches for ISBNs produced results, but the library counts was low enough to induce suspicion as to whether the all key records were being included. In other cases, it was clear that a record grouped together multiple volumes or publishers that needed to be considered separately.

To manage these anomalies and special cases, the tricky_titles.csv file was produced to track issues, indicate solutions, and turn on or off FRBR settings (explained below). The document is designed to handle only cases in which OCLC Numbers are being used for data gathering. The following bulleted list is a data dictionary defining the column headers (except for Prefix, Title, and Subtitle) included in the CSV. Using the values in these fields, the program determines how to generate a list of OCLC numbers and how to go about requesting library holdings data for them. Most significantly, this arrangement allows a user to manually enter a list of OCLC Numbers, providing an alternative solution when the script fails to include all the appropriate records.

* Unique Identifier: The sequential number that serves as the key for the dictionary containing the internal metadata record for a particular title, as found in neh_title_records.json.

* Bibliographic/Manual: A column with two modes indicating whether OCLC Numbers were gathered using the API's Bibliographic Resource service as described above or gathered manually. In most cases, the Bibliographic Resource method was used first as a starting point, and then the results were checked by searching the WorldCat website, leading to either a validation of the list of OCLC Numbers or a manually entered list of numbers.

* Bibliographic Resource - FRBR Grouping: A column with two allowed values (TRUE or FALSE) indicating whether a setting called FRBR Grouping should be turned on or off. When FRBR Grouping is turned on (which is the default setting) for the Bibliographic Resource service, similar bibliographic records are grouped together into overarching records. While this setting can simplify results, turning the setting off can help to locate records on a more granular level. This is especially useful when it appears multiple versions from different publishers or multiple volumes in a set are grouped under a single record. For more information about FRBR Grouping, refer to the FAQs for the WorldCAt Search API
(https://www.oclc.org/developer/develop/web-services/worldcat-search-api/faqs.en.html).

* OCLC Numbers: A list of OCLC numbers separated by semicolons. This column should only be used when "Manual" was entered under the "Bibliographic/Manual" column.

* Library Locations - FRBR Setting: A column with two allowed values (TRUE or FALSE) indicating whether the FRBR Grouping setting should be turned on or off when searching for library holdings information. Functionally, this setting has a similar purpose to the FRBR Grouping setting for the Bibliographic Resource tool. When this setting is turned on (also the default), the API will pull library holdings data for all versions of a work nested under a main record. While sometimes useful, this can prevent differentiation between specific versions of work. In most cases where FRBR Grouping has been set to FALSE for the Bibliographic Resource, it will also make sense to set the Library Locations value to FALSE, to ensure only the holdings data associated with those more specific records are gathered.

* Key functions and/or code blocks
  * Lines 457-73 under Initializing Variables
  * Lines 540-91 under Main Program

### Data Analysis

After gathering library holdings data for each of the titles, the script performs some basic analysis on the results. For each title, the script iterates through all the libraries that contain that title in their holdings, counting how many time a particular country appears in the results. In addition, the libraries are sorted by geographic region, using a list of country classifications published by Wikimedia (see Notes on Resources Used). The script stores this information, along with the total number of unique libraries for each title, in the worldcat_stats dictionary under the title's unique identifier and the key "Data Summary" (see Inputs and Outputs section).

* Key functions and/or code blocks
  * create_country_to_region_dictionary function
  * perform_basic_analysis function

### Problematic Records

Over the course of the data gathering and analysis, some records were identified that proved problematic because of uncertainty about what entity published the work, the existence of multiple versions, or whether the work was ever released as a stand-alone publication. To exclude these titles from the data gathering and analysis, a variable called problematic_record_keys was created that contains a list of unique identifiers. When the program encountered these records while iterating through the keys of the title records dictionary (from neh_title_records.json), it is instructed to create and store an empty dictionary for that record in worldcat_stats and then move on.

* Key functions and/or code blocks
  * Line 476 under Initializing Variables
  * Lines 504-5 under Main Program

### Last Record Number

This script includes a variable called last_record_number to help control the data gathering process. While making new requests for data to the API, executing the program can take a significant amount of time. Thus, the last_record_number variable can be tweaked to instruct the script to only gather data up to a certain number of records. Then, the results can be checked to ensure that all aspects of the script are working as expected before continuing to gather data for remaining records.

* Key functions and/or code blocks
  * Line 484 under Initializing Variables
  * Line 498 under Main Program

## Summary of create_worldcat_results_csv.py

The create_worldcat_results_csv.py script makes use of information from neh_title_records.json, worldcat_stats.json, and tricky_titles.csv to create a CSV that contains identifying information for titles under consideration for the project, details on how library holdings data were gathered for that title, and the results of some analysis done on the data to capture the total number of libraries with the title and those libraries' geographic distribution.

The script makes use of the csv Python module and follows a common pattern, writing a row of headers and then a row of data for each title. Data associated with an individual title across the files listed above is linked together using the unique identifiers that serve as keys for each record in neh_title_records.json. The script is also designed to handle records excluded from data gathering and analysis (see the Problematic Records section above) and cases in which no library holdings are found.

The script imports gather_worldcat_stats.py as a module in order to access data from tricky_titles.csv (which the other script already loads) and the last_record_number variable, which this script makes use of to know when to stop creating new spreadsheet rows.

## Inputs and Outputs

Sample inputs and outputs are not provided, but each is described in detail below. 'inputs' and 'outputs' subdirectories will also need to be created before attempting to run the script.

### Inputs

Aside from the Web Services key needed to access the WorldCat Search API (see the Notes on Resources Used below), the following two documents are needed to successfully use the script. Users will need to place them within the inputs subdirectory and ensure they conform to the script's expectations and are saved in the correct file format.

#### neh_title_records.json

The neh_title_records.json used for this project contains 372 metadata records that represent the in-progress work of the grant team on enriching the bibliographic and descriptive metadata for titles under consideration for the project. The JSON file was created using another script that transformed spreadsheet rows into Python dictionaries (with column header names serving as keys, and field contents serving as values).

The keys from the records used by these scripts include "Title", "Subtitle", "Author 1 - Last", "Imprint", "HC ISBN", "PB ISBN", "EB ISBN", and "EB (OA) ISBN". Each dictionary that represents the data from a spreadsheet row about a particular title is matched with a key, a sequential number that serves as a unique identifier for that record. In the JSON document, the records are embedded within a larger dictionary that has one other key, "Last Updated", indicating when the document was created. The document is encoded in UTF-8, so special characters may be included in values used by the program.

#### tricky_titles.csv

The contents of the tricky_titles.csv file is discussed in detail above under Summary for gather_worldcat_stats.py. For the sake of simplicity and avoiding file format issues, this file should be saved as a plain .csv file without a specific encoding. Special characters typically handled by UTF-8 should be removed from this document.

### Outputs

These scripts produce two main output files, both of which will be saved to the outputs subdirectory.

#### worldcat_stats.json

This JSON document contains all of the data and metadata gathered for each title over the course of the execution of the gather_worldcat_stats.py script. For all titles except for eight records excluded as problematic, there is a key-value pair, with the key being identical to the key for that title in neh_title_records.json and the value being a dictionary containing all of the information gathered about that title. The document is encoded in UTF-8 to enable the representation of special characters taken from neh_title_records.json and returned from the WorldCat Search API.

Each dictionary will have the following structure and keys:

* "Identifier Type Used for Data Collection": This key will have a value of "ISBN", "OCLC", or "N/A", depending on whether and how library location data are gathered from the API.

* "ISBNs Searched": This will be a list of all ISBNs included in calls to the API; even if the "Identifier Type Used for Data Collection" is "OCLC", there may be ISBNs listed here, as calls for ISBNs might have been made to the API that returned no results.

* "OCLC Lookup Matches": The value for this key will contain another dictionary, with information about the query used to look up records using the Bibliographic Resource service, whether FRBR Grouping was on or off, the number of records returned, and identifying metadata about records deemed to match, including OCLC numbers and title, publisher, author, and series information.

* "Library Locations - FRBR Grouping": The value for this key will either be true, false, or "N/A", with the latter occurring when no identifiers were found for a record.

* "Response Metadata": The value for this key will include a list of dictionaries that contain the title-related metadata returned from each successful call to the API's Library Locations service. The basic metadata typically includes title, author, publisher, date, OCLC number, and ISBNs. In addition, the number of libraries associated with that particular record is included in each dictionary.

* "Match Check": When the ISBN method is used to gather data, the "Match Check" key will have further nested data as its value, stating the results of comparisons between the title, author, and publisher information contained in the neh_title_records.json record and the metadata listed under the "Response Metadata" key. The data will be in the form of a list, with the first element signaling whether the metadata from the API matches the record or not (true or false) and the second element being a dictionary that identifies where and what values failed to match. If the script did not use the ISBN method to gather data, the value for "Match Check" will simply be "N/A".

* "Complete Library Data": Nested underneath this key will be a list of dictionaries carrying information about the libraries that WorldCat identified as having the title in question in their holdings. Dictionaries for individual libraries will only appear once, as duplicates have been removed by the script before the list is assigned to this key.

* "Data Summary": If library holdings were found, this key will include a dictionary containing the results of the analysis detailed under the Data Analysis section above. Keys of the dictionary will include "Number of Libraries", "Country Distribution", and "Region Distribution". If no results were found, the value for "Data Summary" will be simply "N/A".

* worldcat_analysis_results.csv

The second output created by these scripts, the worldcat_analysis_results.csv summarizes how the library holdings data was collected for each title in neh_title_records.json and presents the results of the analysis done on the data collected. The script creates the CSV file with UTF-8 text encoding. A data dictionary is not presented here, as all of the file contents originate either from neh_title_records.json, worldcat_stats.json, or tricky_titles.csv, which have all been previously described. For more information, refer to the script summaries and the neh_title_records.json and worldcat_stats.json subsections above and the Wikimedia subsection of the Notes on Resources Used section below.

Refer to the Summary of create_worldcat_results_csv.py section above for additional explanation.

## Notes on Resources Used

### WorldCat Search API

The WorldCat Search API allows users to gather data programmatically about bibliographic records and library holdings worldwide. These scripts use the Library Locations service to request library holdings data associated with identifiers (either ISBNs or OCLC numbers) and the Bibliographic Resource service to determine OCLC numbers associated with title and publisher information. Data returned using the Bibliographic Resource service is in the MARC XML format, parsed using the Beautiful Soup and the lxml parser (see Computing Environment Configuration below), and data returned from the Library Locations tool was in JSON format.

OCLC requires a Web Services Key to use the WorldCat Search API. The gather_worldcat_stats.py script accesses the key by importing secrets.py as a module. Developers from institutions can obtain a Production level key which allows for less limitations and enhanced feature access. Alternatively, users can request a Sandbox level key by creating an account and completing a simple application on the site. However, Sandbox API use is subject to some limitations, including a maximum of 100 calls per day. This project was created and tested using both Sandbox and Production keys.

The following links provide more information on the API and the specific services used in these scripts:
* Main documentation page for WorldCat Search API: https://www.oclc.org/developer/develop/web-services/worldcat-search-api.en.html
* Documentation for Library Locations service: https://www.oclc.org/developer/develop/web-services/worldcat-search-api/library-locations.en.html
* Documentation for Bibliographic Resource service: https://www.oclc.org/developer/develop/web-services/worldcat-search-api/bibliographic-resource.en.html

### Wikimedia, "List of Countries by Regional Classification"

The Data Analysis portion of the gather_worldcat_stats.py script uses regional classifications of countries provided online by Wikimedia (https://meta.wikimedia.org/wiki/List_of_countries_by_regional_classification). The script pulls the classifications from the webpage as HTML and parses them (using the Beautiful Soup module) to create a lookup table that is used to sort libraries geographically into one of six regions: Africa, Arab States, Asia & Pacific, Europe, North America, and South/Latin America. In the worldcat_analysis_results.csv file, the number of libraries holding a title in each of these regions is listed in separate columns, with an additional column listing the number of libraries whose geographic location is unknown.

## Computing Environment Configuration

Both scripts can be run using a command line utility, such as Git Bash, Terminal, or Windows Command Prompt. Neither script requires inputs from the command line, and provided that a version of Python 3 has been correctly installed, they can be executed with these commands: "python gather_worldcat_stats.py" or "python create_worldcat_results_csv.py". These scripts were written and tested using the 3.6.3 version of Python.

The bs4 (Beautiful Soup) Python module needs to be installed for the program to run successfully. The other modules used (requests, json, string, csv, codecs, and sys) should be included as part of the Python Standard Library.

In addition, to use Beautiful Soup to parse XML, you may need to pip install the lxml package. The documentation for BeautifulSoup may be useful for understanding portions of the gather_worldcat_stats.py script and for tips on installing the lxml parser (https://www.crummy.com/software/BeautifulSoup/bs4/doc/).

## Additional Questions?

Questions, comments, advice for improvements, or inquiries about reusing this code can be directed to Sam Sciolla (samgsciolla@gmail.com).

# dbnl-scraper

This scraper script allows one to scrape text from [dbnl](http://dbnl.org/), the Dutch digital library for the Arts.

## Requirements 

The scraper is written in Python, heavily depending upon the 
[BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/) package.
[Requests: HTTP for Humans](http://docs.python-requests.org/) package handles the requests for us.
You can install the requirements with [pip](https://pip.pypa.io/en/stable/quickstart/), 
if necessary in a [virtualenv](http://virtualenv.readthedocs.org/).  

    pip install -r requirements.txt

## Running the script

Running the script is as easy as: 

    python scrape.py 

In the first lines of the file you can set the base URL, 
the number of pages to be scraped (set to 0 to scrape all pages), and
the output folder (normally to a directory "data" in the folder you ran `scrape.py`).

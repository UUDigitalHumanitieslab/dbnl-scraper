import codecs
import re
import os

import requests
from bs4 import BeautifulSoup, element

BASE_URL = 'http://www.dbnl.org/tekst/mand001schi01_01/'
PAGE_NUMBER = re.compile(r"""
    \[          # matches the opening bracket
    (.*?)       # matches anything (lazily)
    \]          # matches the closing bracket
""", re.X)
OUT_FOLDER = 'data'


def scrape_page(page, folder, current_file=None):
    """
    Scrapes a single page. Loops over all contentholder elements to find pages.
    Returns the filename of the last page worked with.
    """
    soup = BeautifulSoup(page, 'html.parser')
    for ch in soup.find_all('div', class_='contentholder'):
        if ch.contents:
            first_child = ch.contents[0]
            if first_child.name == 'div':
                if 'pb' in first_child['class']:
                    current_file = PAGE_NUMBER.match(first_child.text).group(1).replace('*', 'x').replace('.', '')
                    continue

            if current_file:
                lines = []
                # Retrieve the text elements from the page
                for child in ch.children:
                    if child.name in ['h1', 'h2', 'h3', 'h4', 'p']:
                        lines.append(child)
                    # Special handlers for poems
                    if child.name == 'div' and child['class'][0] in ['poem', 'poem-small-margins']:
                        lines.extend(get_poem(child))

                # Write the lines to an output file
                if lines:
                    with codecs.open(os.path.join(folder, current_file + '.txt'), 'ab') as out_file:
                        for line in lines:
                            write_line(line, out_file)

    return current_file


def strip_encode(line):
    """
    Strips a line and encodes it as UTF-8.
    """
    return line.strip().encode('utf-8')


def write_line(line, out_file):
    """
    Writes a line to the given out_file, and ends it with a new line.
    """
    line = strip_encode(line.text)
    if line:
        out_file.write(line)
        out_file.write('\n')


def get_poem(poem):
    """
    Retrieves all the lines of a complete poem to the given out_file.
    """
    lines = []
    for line in poem.children:
        if line.name == 'div' and line['class'][0] in ['poem-head', 'line']:
            lines.append(line)
    return lines

if __name__ == "__main__":
    # Retrieve the table of contents
    soup = BeautifulSoup(requests.get(BASE_URL).content, 'html.parser')
    toc = soup.find('h2', {'class': 'inhoud'})

    # Loop over all URLs and scrape the pages
    processed = 0
    chapter_nr = 0
    section_nr = 0
    current_folder = None
    previous_file = None
    for p in toc.parent.next_siblings:
        if type(p) == element.Tag:
            for a in p.find_all('a'):
                url = BASE_URL + a['href']

                if 'head2' in a['class']:
                    chapter_nr += 1
                    section_nr = 0
                    current_folder = os.path.join(OUT_FOLDER, 'h{0:02d}'.format(chapter_nr))
                    previous_file = None
                elif 'head3' in a['class']:
                    section_nr += 1
                    current_folder = os.path.join(OUT_FOLDER, 'h{0:02d}'.format(chapter_nr), 'c{0:02d}'.format(section_nr))

                if not os.path.exists(current_folder):
                    os.makedirs(current_folder)

                print 'Now processing {}'.format(url)
                previous_file = scrape_page(requests.get(url).content, current_folder, previous_file)
                processed += 1
        if processed == 5:  # prevent scraping the whole database on the first try :-)
            break

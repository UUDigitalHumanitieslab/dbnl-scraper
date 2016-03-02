import codecs
import re

import requests
from bs4 import BeautifulSoup

BASE_URL = 'http://www.dbnl.org/tekst/mand001schi01_01/'
PAGE_NUMBER = re.compile(r"""
    \[          # matches the opening bracket
    (.*?)       # matches anything (lazily)
    \]          # matches the closing bracket
""", re.X)


def scrape_page(page):
    """
    Scrapes a single page. Loops over all contentholder elements to find pages.
    """
    soup = BeautifulSoup(page, 'html.parser')
    current_file = None
    for ch in soup.find_all(class_='contentholder'):
        if ch.contents:

            first_child = ch.contents[0]
            if first_child.name == 'div' and first_child['class'][0] == 'pb':
                filename = PAGE_NUMBER.match(first_child.text).group(1).replace('*', 'x').replace('.', '')
                if current_file:
                    current_file.close()
                current_file = codecs.open('data/' + filename + '.txt', 'wb')

                next_row = first_child.find_parent('tr').next_sibling.find(class_='contentholder')
                for child in next_row.children:
                    if child.name in ['h1', 'h2', 'h3', 'p']:
                        write_line(child, current_file)
                    # Special handlers for poems
                    if child.name == 'div' and child['class'][0] in ['poem', 'poem-small-margins']:
                        write_poem(child, current_file)

    if current_file:
        current_file.close()


def strip_encode(line):
    """
    Strips a line and encodes it as UTF-8.
    """
    return line.strip().encode('utf-8')


def write_line(line, out_file):
    """
    Writes a line to the given out_file, and ends it with an enter.
    """
    out_file.write(strip_encode(line.text))
    out_file.write('\n')


def write_poem(poem, out_file):
    """
    Writes a complete poem to the given out_file.
    """
    for line in poem.children:
        if line.name == 'div' and line['class'][0] in ['poem-head', 'line']:
            out_file.write(strip_encode(line.text))
        out_file.write('\n')

if __name__ == "__main__":
    # Retrieve the table of contents
    soup = BeautifulSoup(requests.get(BASE_URL).content, 'html.parser')
    toc = soup.find('h2', {'class': 'inhoud'})

    # Loop over all URLs and scrape the pages
    processed = 0
    for p in toc.parent.next_siblings:
        if p.find('a') != -1:
            url = p.find('a')['href']
            print 'Now processing {}'.format(BASE_URL + url)
            scrape_page(requests.get(BASE_URL + url).content)
            processed += 1
            if processed == 20:
                break

import codecs
from collections import defaultdict
import re
import os

import requests
from bs4 import BeautifulSoup, element

from utils import UnicodeWriter, write_line

# Change below settings to your specific settings.
BASE_URL = 'http://www.dbnl.org/tekst/mand001schi01_01/'
MAX_PAGES = 5
OUT_FOLDER = 'data'

PAGE_NUMBER = re.compile(r"""
    \[          # matches the opening bracket
    (.*?)       # matches anything (lazily)
    \]          # matches the closing bracket
""", re.X)


def scrape_page(page, folder, current_page_nr=None):
    """
    Scrapes a single page. Loops over all contentholder elements to find pages.
    Returns the filename of the last page worked with.
    """
    pages = defaultdict(list)
    soup = BeautifulSoup(page, 'html.parser')
    for ch in soup.find_all('div', class_='contentholder'):
        if ch.contents:
            first_child = ch.contents[0]
            if first_child.name == 'div':
                if 'pb' in first_child['class']:
                    current_page_nr = PAGE_NUMBER.match(first_child.text).group(1).replace('*', 'x').replace('.', '')
                    continue

            if current_page_nr:
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
                    pages[current_page_nr].extend(lines)

                    with codecs.open(os.path.join(folder, current_page_nr + '.txt'), 'ab') as out_file:
                        for line in lines:
                            write_line(line, out_file)

    return pages, current_page_nr


def get_poem(poem):
    """
    Retrieves all the lines of a complete poem to the given out_file.
    """
    lines = []
    for line in poem.children:
        if line.name == 'div' and line['class'][0] in ['poem-head', 'line']:
            lines.append(line)
    return lines


def parts_to_csv(parts):
    with open('data/parts.csv', 'wb') as f:
        f.write(u'\uFEFF'.encode('utf-8'))  # the UTF-8 BOM to hint Excel we are using that...
        csv_writer = UnicodeWriter(f, delimiter=';')
        csv_writer.writerow(['book', 'nr', 'title'])
        for n, part in enumerate(parts, start=1):
            csv_writer.writerow(['Het schilder-boeck', str(n), part])


def chapters_to_csv(chapters):
    with open('data/chapters.csv', 'wb') as f:
        f.write(u'\uFEFF'.encode('utf-8'))  # the UTF-8 BOM to hint Excel we are using that...
        csv_writer = UnicodeWriter(f, delimiter=';')
        csv_writer.writerow(['part', 'nr', 'title'])
        for part, c in chapters.items():
            for n, chapter in enumerate(c, start=1):
                csv_writer.writerow([part, str(n), chapter])


def pages_to_csv(pages):
    with open('data/pages.csv', 'wb') as f:
        f.write(u'\uFEFF'.encode('utf-8'))  # the UTF-8 BOM to hint Excel we are using that...
        csv_writer = UnicodeWriter(f, delimiter=';')
        csv_writer.writerow(['chapter', 'nr', 'title'])
        for page_nr, lines in pages.items():
            lines_stripped = [line.text.strip().replace('\n', '<br><br>') for line in lines]
            csv_writer.writerow(['', page_nr, '<br>'.join(lines_stripped)])


def scrape_pages(toc):
    parts = []
    chapters = defaultdict(list)
    pages = defaultdict(list)
    current_folder = None
    processed = 0
    for p in toc.parent.next_siblings:
        if type(p) == element.Tag:
            for a in p.find_all('a'):
                url = BASE_URL + a['href']

                if 'head2' in a['class']:
                    if a.string in parts:
                        raise ValueError('Part titles not unique!')
                    parts.append(a.string)
                    current_folder = os.path.join(OUT_FOLDER, 'h{0:02d}'.format(len(parts)))
                    previous_page_nr = None
                elif 'head3' in a['class']:
                    chapters[parts[-1]].append(a.string)
                    current_folder = os.path.join(OUT_FOLDER, 'h{0:02d}'.format(len(chapters)),
                                                  'c{0:02d}'.format(len(parts)))

                if not os.path.exists(current_folder):
                    os.makedirs(current_folder)

                print 'Now processing {}'.format(url)
                scraped_pages, previous_page_nr = scrape_page(requests.get(url).content, current_folder,
                                                              previous_page_nr)
                pages.update(scraped_pages)
                processed += 1
        if MAX_PAGES and processed == MAX_PAGES:  # prevent scraping the whole database on the first try :-)
            break

    return parts, chapters, pages


if __name__ == "__main__":
    # Retrieve the table of contents
    soup = BeautifulSoup(requests.get(BASE_URL).content, 'html.parser')
    toc = soup.find('h2', {'class': 'inhoud'})

    # Loop over all URLs and scrape the pages
    parts, chapters, pages = scrape_pages(toc)

    parts_to_csv(parts)
    chapters_to_csv(chapters)
    pages_to_csv(pages)

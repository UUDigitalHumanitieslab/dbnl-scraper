import codecs
from collections import defaultdict
import re
import os

import requests
from bs4 import BeautifulSoup, element

from models import Page
from utils import UnicodeWriter, write_line

# Change below settings to your specific settings.
DBNL_URL = 'http://www.dbnl.org'
BASE_URL = DBNL_URL + '/tekst/mand001schi01_01/'
MAX_PAGES = 10
OUT_FOLDER = 'data'

PAGE_NUMBER = re.compile(r"""
    \[          # matches the opening bracket
    (.*?)       # matches anything (lazily)
    \]          # matches the closing bracket
""", re.X)


def scrape_page(scraped_pages, page, folder, current_chapter, current_page_nr=None):
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
                    current_page_nr = PAGE_NUMBER.match(first_child.text).group(1).replace('*', 'x').replace('.', '')
                    current_original = first_child.a['href']
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
                    if not current_page_nr in scraped_pages:
                        p = Page(current_page_nr, current_original, current_chapter)
                        scraped_pages[current_page_nr] = p
                    scraped_pages[current_page_nr].add_lines(lines)

                    with codecs.open(os.path.join(folder, current_page_nr + '.txt'), 'ab') as out_file:
                        for line in lines:
                            write_line(line, out_file)

    return scraped_pages, current_page_nr


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
            # For each part, write an introduction chapter
            csv_writer.writerow([part, str(0), part])
            for n, chapter in enumerate(c, start=1):
                csv_writer.writerow([part, str(n), chapter])


def pages_to_csv(pages):
    with open('data/pages.csv', 'wb') as f:
        f.write(u'\uFEFF'.encode('utf-8'))  # the UTF-8 BOM to hint Excel we are using that...
        csv_writer = UnicodeWriter(f, delimiter=';')
        csv_writer.writerow(['chapter', 'title', 'pagenumber', 'original', 'body'])
        n = 0
        for page_nr, page in sorted(pages.items(), key=lambda x: x[1].link_to_original):
            n += 1
            # Strip all lines and replace new lines by <br> tags
            lines_stripped = [line.text.strip().replace('\n', '<br>') for line in page.lines]
            csv_writer.writerow([page.chapter,
                                 str(n) + '|' + page_nr,
                                 page_nr,
                                 DBNL_URL + page.link_to_original,
                                 '<br>'.join(lines_stripped)])


def scrape_pages(toc):
    parts = []
    chapters = defaultdict(list)
    scraped_pages = defaultdict(Page)
    current_folder = None
    processed = 0
    for p in toc.parent.next_siblings:
        if type(p) == element.Tag:
            for a in p.find_all('a'):
                url = BASE_URL + a['href']

                if 'head2' in a['class']:
                    current_chapter = a.string
                    if current_chapter in parts:
                        raise ValueError('Part titles not unique!')
                    parts.append(current_chapter)
                    current_folder = os.path.join(OUT_FOLDER, 'h{0:02d}'.format(len(parts)))
                    previous_page_nr = None
                elif 'head3' in a['class']:
                    current_chapter = a.string
                    chapters[parts[-1]].append(current_chapter)
                    current_folder = os.path.join(OUT_FOLDER, 'h{0:02d}'.format(len(parts)),
                                                  'c{0:02d}'.format(len(chapters[parts[-1]])))

                if not os.path.exists(current_folder):
                    os.makedirs(current_folder)

                print 'Now processing {}'.format(url)
                scraped_pages, previous_page_nr = scrape_page(scraped_pages,
                                                              requests.get(url).content,
                                                              current_folder,
                                                              current_chapter,
                                                              previous_page_nr)
                processed += 1
        if MAX_PAGES and processed == MAX_PAGES:  # prevent scraping the whole database on the first try :-)
            break

    return parts, chapters, scraped_pages


if __name__ == "__main__":
    # Retrieve the table of contents
    soup = BeautifulSoup(requests.get(BASE_URL).content, 'html.parser')
    toc = soup.find('h2', {'class': 'inhoud'})

    # Loop over all URLs and scrape the pages
    parts, chapters, pages = scrape_pages(toc)

    parts_to_csv(parts)
    chapters_to_csv(chapters)
    pages_to_csv(pages)

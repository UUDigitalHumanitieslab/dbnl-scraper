class Page:
    def __init__(self, page_number, link_to_original, part, chapter):
        self.page_number = page_number
        self.link_to_original = link_to_original
        self.part = part
        self.chapter = chapter
        self.lines = []

    def add_lines(self, lines):
        self.lines.extend(lines)

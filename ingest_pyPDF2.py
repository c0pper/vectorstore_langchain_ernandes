from pypdf import PdfReader
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTImage
from typing import Iterable
import logging


def get_most_used_font_size(pdf_file_path, pages_to_analyze=20):
    # Extract text from the PDF

    # Initialize a dictionary to store font sizes and their frequencies
    font_size_counts = {}

    # Analyze the layout to get font sizes
    for idx, page_layout in enumerate(extract_pages(pdf_file_path)):
        if idx < pages_to_analyze:
            print(f"idx {idx}")
            print(font_size_counts)
            for element in page_layout:
                if isinstance(element, Iterable):
                    for text_line in element:
                        font_size = get_font_size(text_line)
                        # print(char.get_text(), font_size)
                        if font_size:
                            font_size_counts[font_size] = font_size_counts.get(font_size, 0) + 1
        else:
            break

    # Find the most used font size
    most_used_font_size = max(font_size_counts, key=font_size_counts.get)
    smallest_font_size = min(font_size_counts.keys())
    print(font_size_counts)
    print(most_used_font_size)

    return most_used_font_size, smallest_font_size


def is_header(textline, most_used_font_size, next_textline):
    header_status = False
    if isinstance(textline, Iterable):
        font_size = get_font_size(textline)
        if font_size and font_size > most_used_font_size:
            # Check if the font size of the next text line is equal to the most used font size
            next_textline_font_size = get_font_size(next_textline)
            next_line_lenght = len(next_textline.get_text())
            if next_textline_font_size and next_textline_font_size == most_used_font_size and next_line_lenght > 5:
                header_status = True
            if next_textline_font_size > most_used_font_size and next_textline_font_size <= font_size:
                header_status = True
    return header_status


def get_font_size(textline):
    if hasattr(textline, "get_text") and isinstance(textline, Iterable):
        font_size = None
        for idx, char in enumerate(textline):
            if idx == 0:
                if isinstance(char, LTChar):
                    font_size = round(char.size, 2)
        return font_size
    else:
        return None


def extract_text_with_headers(pdf_file_path):
    # Get the most used font size in the PDF
    most_used_font_size, smallest_font_size = get_most_used_font_size(pdf_file_path)  # Smallest for footnotes

    # Iterate through each page in the PDF
    paragraphs = []
    text_lines = []
    #  Collecting all text lines in doc
    for page_layout in extract_pages(pdf_file_path):
        for element in page_layout:
            if isinstance(element, Iterable):
                for text_line in element:
                    if hasattr(text_line, "get_text") and len(text_line.get_text()) > 3:  # Not an image
                        text_lines.append(text_line)

    #  For each text line check if it's a header, if it is collect its paragraph in the paragraphs array
    header_hierarchy = []
    current_complete_header = ""
    for i in range(len(text_lines) - 1):
        current_textline = text_lines[i]
        current_font_size = get_font_size(text_lines[i])
        header_status = is_header(text_lines[i], most_used_font_size, text_lines[i + 1])
        if header_status:
            header = current_textline.get_text().replace("\n", " ")
            if header not in current_complete_header:
                for h in text_lines[i + 1:]:
                    l_font_size = get_font_size(h)
                    if l_font_size == current_font_size:  # If header is on more than one line
                        header += h.get_text().replace("\n", " ")
                    else:
                        break
                current_complete_header = header

            previous_header_font_size = header_hierarchy[-1][1] if header_hierarchy else 0

            #  Current header smaller than last in hierarchy: append
            if current_font_size < previous_header_font_size:
                header_hierarchy.append((current_complete_header, current_font_size))

            #  Current header equal to last in hierarchy: pop last and append
            if current_font_size == previous_header_font_size:
                header_hierarchy.pop()
                header_hierarchy.append((current_complete_header, current_font_size))

            #  Current header bigger than last in hierarchy: pop last element while current font size >= prev font size and append
            if header_hierarchy and current_font_size > previous_header_font_size:
                while header_hierarchy and current_font_size >= previous_header_font_size:
                    header_hierarchy.pop()
                    previous_header_font_size = header_hierarchy[-1][1] if header_hierarchy else 999
                # header_hierarchy = header_hierarchy[:-2]
                header_hierarchy.append((current_complete_header, current_font_size))

            # First iteration, empty header hierarchy
            if not header_hierarchy:
                header_hierarchy.append((current_complete_header, current_font_size))

            current_paragraph_lines = []
            for line in text_lines[i + 1:]:
                print(line.get_text(), get_font_size(line))
                if current_font_size > get_font_size(line) == most_used_font_size:
                    current_paragraph_lines.append(line.get_text())
                elif get_font_size(line) <= smallest_font_size:
                    continue
                else:
                    break
            paragraph = " ".join(current_paragraph_lines)
            if paragraph:
                schema = {
                    "hierarchy": " -> ".join([f"{x[0].strip()} ({x[1]})" for x in header_hierarchy]),
                    "paragraph": paragraph
                }
                paragraphs.append(schema)

    [print(f"{p['hierarchy']}\n---\n{p['paragraph']}\n\n\n\n") for p in paragraphs]
    [logging.info(f"{p['hierarchy']}\n---\n{p['paragraph']}\n\n\n\n") for p in paragraphs]


if __name__ == "__main__":

    pdf_file_path = 'D3.1.pdf'
    logging.basicConfig(filename=f'{pdf_file_path}.log', filemode='a', format='%(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    extract_text_with_headers(pdf_file_path)

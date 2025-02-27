import os
import time
import datetime
import fnmatch
import json

# import csv
import re

import cv2
import matplotlib.pyplot as plt
from pdf2image import convert_from_path
import pytesseract
import pypdf
import spacy
from spacy.matcher import Matcher
from langchain.text_splitter import CharacterTextSplitter
import pytextrank
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def replace_with_underscores(input_string):
    cleaned_string = re.sub(r"[\s,]+", "_", input_string)
    return cleaned_string


def pdf_to_images(filepath, title):
    """
    This function converts the PDF page by page into
    JPEG files that will be used to scrape text.
    """
    pages = convert_from_path(filepath, 400)

    i = 1
    for page in pages:
        print(os.path.dirname(os.path.abspath(__file__)))
        image_name = f"{title}_page_{i}.jpg"
        page.save(f"./image_store/{image_name}", "JPEG")
        i += 1


def show_image(image):
    """
    This administrative function can show any of the images
    during transformation or plotting areas to scrape
    """
    plt.figure(figsize=(10, 10))
    plt.imshow(image)
    plt.show()
    time.sleep(0.25)
    plt.close("all")


def mark_region(image_path):
    """
    This section performs a transform against the image provided,
    and then it finds each section of text to be scanned and
    returns the coordinates.
    """
    im = cv2.imread(image_path)

    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 30
    )

    # Dilate to combine adjacent text contours
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    dilate = cv2.dilate(thresh, kernel, iterations=6)

    # Find contours, highlight text areas, and extract ROIs
    cnts = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    line_items_coordinates = []
    count = 0
    # Select sections of text
    for c in cnts:
        count += 1
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)

        image = cv2.rectangle(
            im, (x, y), (2800, y + h), color=(255, 0, 255), thickness=3
        )
        image = cv2.putText(
            im,
            f"{count}",
            (x + 5, y + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (36, 255, 12),
            2,
        )
        line_items_coordinates.append([(x, y), (2800, y + h)])

    return line_items_coordinates


def get_text(coordinates, filepath):
    """
    Recieves coordinates grabbed with OpenCV, and then scrapes text off
    of these areas using tesseract
    """
    # load the original image
    image = cv2.imread(filepath)

    # get co-ordinates to crop the image
    c = coordinates

    # cropping image img = image[y0:y1, x0:x1]
    img = image[c[0][1] : c[1][1], c[0][0] : c[1][0]]

    # convert the image to black and white for better OCR
    ret, thresh1 = cv2.threshold(img, 120, 255, cv2.THRESH_BINARY)

    # pytesseract image to string to get results
    text = str(pytesseract.image_to_string(thresh1, config="--psm 6"))

    return text


def scrape_page(page_number, title):
    """
    Once images are generated from the pdf, this function first uses
    OpenCV to mark the regions for scraping ( mark_region() )
    and then uses tesseract to get each section of text ( get_text() )
    """
    filepath = os.path.abspath(f"image_store/{title}_page_{page_number}.jpg")
    print(f"Scanning Page {page_number}\n")
    coordinates = mark_region(filepath)

    page_text = []
    count = 0
    for coordinate_set in coordinates:
        count += 1
        section_text = get_text(coordinate_set, filepath)
        page_text.append(section_text)

    page_text.reverse()
    page_text = "\n".join(page_text)

    return page_text


def unstructured_scrape(filepath):
    """
    Main application, the function will scrape one entire document
    based on the filepath provided
    """
    print(f"Beginning Unstructured Scrape of '{filepath}'\n")
    pdf_to_images(filepath)

    dir_path = "image_store"

    number_of_files = len(fnmatch.filter(os.listdir(dir_path), "*.*"))

    text_list = []

    for i in range(number_of_files):
        page_text = scrape_page(i)
        text_list.append(page_text)

    full_text = "\n".join(text_list)

    print(f"Finished Unstructured Scrape of '{filepath}'\n")

    print("Clearing Storage Directory of Images\n")

    for f in os.listdir(dir_path):
        os.remove(os.path.join(dir_path, f))

    return full_text


def structured_scrape(filepath):
    """
    This is to execute a scrape of a structured pdf.
    """
    text_list = []
    print(f"Beginning Structured Scrape of '{filepath}'\n")
    mypdf = open(filepath, mode="rb")
    pdf_document = pypdf.PdfReader(mypdf)
    num_pages = len(pdf_document.pages)

    for i in range(num_pages):
        page = pdf_document.pages[i]
        page_text = page.extract_text()
        text_list.append(page_text)

    print(f"Finished Structured Scrape of '{filepath}'\n")
    full_text = "\n".join(text_list)

    return full_text


def search_document(nlp, document, matcher):
    doc = nlp(document)
    matches = matcher(doc)

    if matches is not None:
        print(f"{len(matches)} Matches Found\n")
        # for match_id, start, end in matches:
        #     print(f"Match ID: {match_id}, Matched Text: {doc[start:end].text}\n")

    return matches


def create_timestamp():
    x = datetime.datetime.now()
    x = str(x)
    x = x.replace(" ", "_time_")
    x = x.replace(":", "_")
    x = x.replace(".", "ms")

    return x


def load_pattern(filename):
    f = open(f"match_patterns/{filename}")
    pattern = json.load(f)

    return pattern


def add_matcher_pattern(matcher, pattern_name, pattern_config):
    pattern = load_pattern(pattern_config)

    matcher.add(pattern_name, [pattern], greedy="LONGEST")

    return matcher


def text_split(raw_text):
    # We need to split the text using Character Text Split such that it sshould not increse token size
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=800,
        chunk_overlap=200,
        length_function=len,
    )
    texts = text_splitter.split_text(raw_text)
    return texts


def remove_filetype(string, symbol):
    return re.sub(f"{re.escape(symbol)}.*", "", string)


def get_text_matches(raw_text, title):
    nlp = spacy.load("en_core_web_lg")

    matcher = Matcher(nlp.vocab)

    for pattern in os.listdir(MATCHPATH):
        pattern_title = remove_filetype(pattern, ".")
        print(
            f"Constructing the following match pattern: title={pattern_title}, file={pattern}\n"
        )
        matcher = add_matcher_pattern(matcher, f"{pattern_title}", pattern)

    # TODO: fix the scraper to get proper nouns - current matches are noise and often just single characters
    matches = search_document(nlp, raw_text, matcher)

    matched_words = []

    for match_id, start, end in matches:
        matched_words.append(f"{raw_text[start:end]}")

    ## Created Matches report (inactive)
    # fieldnames = ["title", "contents"]

    # with open(
    #    f"reports/document_report_{create_timestamp()}.csv",
    #    "w",
    #    encoding="UTF8",
    #    newline="",
    # ) as f:
    #    writer = csv.DictWriter(f, fieldnames=fieldnames)
    #    writer.writeheader()
    #    writer.writerows(matched_document_list)
    # print(document_texts[0])

    for doc in document_texts:
        f = open(f"data/{doc['title']}.txt", "a")
        f.write(doc["contents"])
        f.close()

    if len(matched_words) > 0:
        print(f"Found the following matches in {title}: {matched_words}\n")
        matched_string = ", ".join(matched_words)
        return matched_string
    else:
        return None


def get_keywords(text):
    nlp = spacy.load("en_core_web_lg")

    nlp.add_pipe("textrank")
    doc = nlp(text)

    keywords = []

    for phrase in doc._.phrases[:10]:
        keywords.append(phrase.text)

    return keywords

import os
import fnmatch

import pypdf

from utils.utils import pdf_to_images, scrape_page, replace_with_underscores


class FileReader:
    def __init__(self, filepath):
        self.filepath = filepath
        self.readable = self.is_readable()
        self.title = None
        self.authors = None
        self.publisher = None
        self.date_published = None

    def input_metadata(self, title, authors, publisher, date_published):
        """
        Update the metadata associated with the document before
        writing to the database.
        """
        self.title = title
        self.authors = authors
        self.publisher = publisher
        self.date_published = date_published
        return

    def details(self):
        print(self.filepath, self.readable, self.title, self.authors)

    def generate_filename(self):
        title = replace_with_underscores(self.title)
        authors = replace_with_underscores(self.authors)
        timestamp = replace_with_underscores(self.date_published)
        filename = f"{title}_{authors}_{timestamp}"
        return filename

    def is_readable(self):
        """
        Determine whether or not the document is readable or not
        """
        try:
            with open(self.filepath, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                # Attempt to read the first page (or any)
                _ = pdf_reader.get_page(0)
            return True
        except Exception:
            return False

    def scrape_text(self):
        """
        This is to execute a scrape of a document
        """
        folder_path = "image_store"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder_path}' created.")
        else:
            print(f"Folder '{folder_path}' already exists.")

        if self.readable:
            text_list = self.structured_scrape()
            return text_list

        else:
            text_list = self.unstructured_scrape()
            return text_list

    def structured_scrape(self):
        text_list = []
        print(f"Beginning Structured Scrape of {self.title}")
        pdf_to_images(self.filepath, self.title)

        pdf = open(self.filepath, mode="rb")
        pdf_document = pypdf.PdfReader(pdf)
        num_pages = len(pdf_document.pages)

        for i in range(num_pages):
            page = pdf_document.pages[i]
            contents = page.extract_text()
            text_list.append({"page_number": str(i + 1), "contents": contents})

        print(f"Finished Structured Scrape of {self.title}")

        return text_list

    def unstructured_scrape(self):
        """
        Main application, the function will scrape one entire document
        based on the filepath provided
        """
        print(f"Beginning Unstructured Scrape of '{self.filepath}'\n")
        pdf_to_images(self.filepath, self.title)

        dir_path = "image_store"

        number_of_files = len(fnmatch.filter(os.listdir(dir_path), f"{self.title}_*"))

        text_list = []

        for i in range(number_of_files):
            contents = scrape_page((i + 1), self.title)
            text_list.append({"page_number": str(i + 1), "contents": contents})

        print(f"Finished Unstructured Scrape of '{self.filepath}'\n")

        return text_list

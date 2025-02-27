import os
import shutil
import sys
import builtins

from rich.console import Console
from tqdm import tqdm
import ollama
import uuid
from PIL import Image
from pdf2image import convert_from_path
import pdb

from file_reader import FileReader
from chroma_db import ChromaClient

console = Console()
_client = ChromaClient()
Image.MAX_IMAGE_PIXELS = None


def rich_print(*args, **kwargs):
    console.print(*args, **kwargs)


builtins.print = rich_print


def pdf_page_to_image(pdf_path, page_num=1, dpi=200):
    """Converts a specific page of a PDF to a PIL Image object."""
    images = convert_from_path(
        pdf_path, dpi=dpi, first_page=page_num, last_page=page_num
    )
    return images[0] if images else None


def scan_documents():
    folderpath = "./uploaded"
    _client.client_info

    for f in os.listdir(folderpath):
        filepath = os.path.join(folderpath, f)

        file = FileReader(filepath)

        while True:
            print(f"Name of the file is {f}")

            image = pdf_page_to_image(filepath)
            image.show()

            file.input_metadata()
            print("File Details: ", file.details())
            try:
                correct = input("Are these details correct? (Y/N): ").lower()
                if correct in ["yes", "y"]:
                    print("Continuing process...")
                    break
                elif correct in ["no", "n"]:
                    print("Re-enter information")
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")
            except Exception as e:
                print(f"An error occurred: {e}. Please try again.")

        new_filename = file.generate_filename()
        text_list = file.scrape_text()

        collection = _client.create_collection("library")

        print("Collection: ", collection)

        for i, text in enumerate(tqdm(text_list)):
            print(i, text)
            try:
                response = ollama.embeddings(
                    model="nomic-embed-text", prompt=text["contents"]
                )

                embedding = response["embedding"]
                random_id = str(uuid.uuid4())

                collection.add(
                    ids=[random_id],
                    embeddings=[embedding],
                    documents=[text["contents"]],
                    metadatas=[
                        {
                            "unique_id": random_id,
                            "source": file.title,
                            "authors": file.authors,
                            "publisher": file.publisher,
                            "date_published": file.date_published,
                            "page": text["page_number"],
                        }
                    ],
                )
            except Exception as e:
                print("Error: ", e)

        source = filepath
        destination = os.path.join("./processed", new_filename)
        try:
            shutil.move(source, destination)
        except Exception as e:
            print("Error: ", e)


def query_documents():
    """
    Tool to get data from chronmadb and inject it into the history
    """
    _collection = _client.create_collection("library")

    prompt = input("Please enter a query: ")

    try:
        # generate an embedding for the prompt and retrieve the most relevant doc
        response = ollama.embeddings(prompt=prompt, model="nomic-embed-text")

        results = _collection.query(
            query_embeddings=[response["embedding"]],
            n_results=10,
        )

        data = results["documents"][0]
        metadata = results["metadatas"][0]

        data_list = []

        for i, x in enumerate(data):
            data_list.append(
                {
                    # "unique_id": metadata[i]["unique_id"],
                    "source": metadata[i]["source"],
                    "authors": metadata[i]["authors"],
                    "date_published": metadata[i]["date_published"],
                    # "publisher": metadata[i]["publisher"],
                    "page": metadata[i]["page"],
                    "contents": data[i],
                }
            )

        return data_list

    except Exception as e:
        print(e)


def query():
    data = query_documents()
    for i, datum in enumerate(data):
        print("\n\n\n----------------------", i, "----------------------------")
        print(datum["contents"])
        print("\n\nCitation:\n\n")
        print(
            f"{datum['authors']}({datum['date_published']}) {datum['source']}. pgs. {datum['page']}"
        )


def main():
    # scan_documents()
    query()


if __name__ == "__main__":
    main()

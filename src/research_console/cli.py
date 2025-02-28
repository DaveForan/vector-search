from __future__ import annotations
import os
import shutil
import builtins
from typing_extensions import Doc
import time

from rich.console import Console
from tqdm import tqdm
import ollama
import uuid
from PIL import Image
from pdf2image import convert_from_path
from textual import work, on
from textual.reactive import reactive
from textual.screen import Screen
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Input, Markdown, Static, Button, Header

from file_reader import FileReader
from chroma_db import ChromaClient

console = Console()
_client = ChromaClient()
Image.MAX_IMAGE_PIXELS = None


def rich_print(*args, **kwargs):
    console.print(*args, **kwargs)


# builtins.print = rich_print

SETTINGS_TEXT = """

VectorSearch Application

Press "a" to go to the search page. As you type, answers will appear from the database.

Press "s" to return to this page, the settings page. If you are in an input box these controls dont work.

Press "d" to go to the processing page. There you can view files pending for processing and execute ingestion.

"Thanks for using my application, I hope you find it worthwhile."

"""

DOCUMENT_METADATA = {
    "title": "",
    "authors": "",
    "publisher": "",
    "date_published": "",
    "run_scrape": False,
}


class Name(Widget):
    """Generates a greeting."""

    status = reactive("Status will be updated here")

    def render(self) -> str:
        return f"Current Status: {self.status}"


class Settings(Screen):
    """This is just a settings page"""

    TITLE = "Settings"
    SUB_TITLE = "Basic Application Information"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(SETTINGS_TEXT)


class Processing(Screen):
    """This is the screen used to ingest documents into the database"""

    TITLE = "Processing"
    SUB_TITLE = """Ingest documents loaded in the "uploaded" folder"""

    title = reactive("")
    authors = reactive("")
    publisher = reactive("")
    date_published = reactive("")
    run_scrape = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Put Title of document here...", id="title")
        yield Input(placeholder="Put 'Authors' of document here...", id="authors")
        yield Input(placeholder="Put 'Publisher' of document here...", id="publisher")
        yield Input(
            placeholder="Put 'Date Published' of document here...", id="date_published"
        )
        yield Button("Submit", id="submit_form", variant="success")
        yield Button("Scan New", id="scan_new", variant="primary")
        yield Name()

    async def scan_documents(self):
        folderpath = "./uploaded"
        _client.client_info

        for f in os.listdir(folderpath):
            filepath = os.path.join(folderpath, f)

            self.query_one(Name).status = f"Beginning scrape of {filepath}"
            time.sleep(2)
            file = FileReader(filepath)

            images = convert_from_path(filepath, dpi=200, first_page=1, last_page=1)
            image = images[0]
            image.show()

            self.query_one(
                Name
            ).status = (
                f"Enter metadata for {filepath} in the form above and click 'Submit'"
            )

            while True:
                try:
                    if self.run_scrape:
                        file.input_metadata(
                            self.title,
                            self.authors,
                            self.publisher,
                            self.date_published,
                        )
                        break
                    else:
                        time.sleep(5)
                        pass
                except Exception as e:
                    print(f"An error occurred: {e}. Please try again.")

            new_filename = file.generate_filename()
            text_list = file.scrape_text()

            self.run_scrape = False

            collection = _client.create_collection("library")

            print("Collection: ", collection)

            list_length = len(text_list)

            for i, text in enumerate(tqdm(text_list)):
                print(i, text)
                self.query_one(
                    Name
                ).status = (
                    f"{self.title} is being scanned {i // list_length}% complete..."
                )
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
                self.query_one(Name).status = f"{self.title} scanning complete!"
                time.sleep(3)
                self.title = ""
                self.authors = ""
                self.publisher = ""
                self.date_published = ""
            except Exception as e:
                print("Error: ", e)

    @on(Input.Changed, "#title")
    async def title_changed(self, message: Input.Changed) -> None:
        """A coroutine to handle a text changed message."""
        if message.value:
            self.title = message.value

    @on(Input.Changed, "#authors")
    def author_changed(self, message: Input.Changed) -> None:
        """A coroutine to handle a text changed message."""
        if message.value:
            self.authors = message.value

    @on(Input.Changed, "#publisher")
    def publisher_changed(self, message: Input.Changed) -> None:
        """A coroutine to handle a text changed message."""
        if message.value:
            self.publisher = message.value

    @on(Input.Changed, "#date_published")
    def date_changed(self, message: Input.Changed) -> None:
        """A coroutine to handle a text changed message."""
        if message.value:
            self.date_published = message.value

    @on(Button.Pressed, "#submit_form")
    def submit_button_pressed(self) -> None:
        self.run_scrape = True

    @on(Button.Pressed, "#scan_new")
    def scan_button_pressed(self) -> None:
        self.run_worker(self.scan_documents(), thread=True)


class VectorSearch(Screen):
    """Searches a vector database as you type"""

    CSS_PATH = "vectorsearchapp.tcss"
    TITLE = "Vector Search"
    SUB_TITLE = "Search all your documents"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Create search entry", id="vector-search")
        with VerticalScroll(id="results-container"):
            yield Markdown(id="results")

    async def on_input_changed(self, message: Input.Changed) -> None:
        """A coroutine to handle a text changed message."""
        if message.value:
            self.lookup_word(message.value)
        else:
            # Clear the existing results
            await self.query_one("#results", Markdown).update("")

    @work(exclusive=True)
    async def lookup_word(self, prompt: str) -> None:
        """Looks up a source"""
        results = await query_documents(prompt)

        if prompt == self.query_one(Input).value:
            markdown = self.make_word_markdown(results)
            self.query_one("#results", Markdown).update(markdown)

    def make_word_markdown(self, results) -> str:
        """Convert the results into markdown"""
        lines = []
        for i, result in enumerate(results):
            lines.append(f"# {i+1}. {result['citation']}")
            lines.append(f"{result['contents']}")

        return "\n".join(lines)


async def query_documents(prompt: str):
    """
    Tool to get data from chronmadb and inject it into the history
    """
    _collection = _client.create_collection("library")

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
                    "unique_id": metadata[i]["unique_id"],
                    "source": metadata[i]["source"],
                    "authors": metadata[i]["authors"],
                    "date_published": metadata[i]["date_published"],
                    "publisher": metadata[i]["publisher"],
                    "page": metadata[i]["page"],
                    "citation": f"{metadata[i]["authors"]}({metadata[i]["date_published"]}) {metadata[i]["source"]}. Pgs. {metadata[i]["page"]}",
                    "contents": data[i],
                }
            )

        return data_list

    except Exception as e:
        print(e)


class VectorSearchApp(App):
    CSS_PATH = "vectorsearchapp.tcss"

    SCREENS = {"vectorsearch": VectorSearch}
    BINDINGS = [
        ("d", "switch_mode('processing')", "Processing"),
        ("s", "switch_mode('settings')", "Settings"),
        ("a", "switch_mode('vectorsearch')", "VectorSearch"),
    ]
    MODES = {
        "processing": Processing,
        "vectorsearch": VectorSearch,
        "settings": Settings,
    }

    def on_mount(self) -> None:
        self.switch_mode("settings")


def main():
    if not os.path.exists("processed"):
        os.makedirs("processed")
        print("Folder 'processed' created.")
    else:
        print("Folder 'processed' already exists.")

    if not os.path.exists("uploaded"):
        os.makedirs("uploaded")
        print("Folder 'uploaded' created.")
    else:
        print("Folder 'uploaded' already exists.")

    app = VectorSearchApp()
    app.run()


if __name__ == "__main__":
    main()

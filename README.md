# Vector Search

### This is a terminal based application that allows the user to ingest files

To get this application running on a Macbook, you'll need to do the following

1. Install [Brew](https://brew.sh) for mac by running the following in your terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Install [Git](https://git-scm.com/downloads/mac) by running the following in your terminal

```bash
brew install git
```

3. Install [UV](https://docs.astral.sh/uv/getting-started/installation/) by running the following in your terminal

```bash
brew install uv
```

4. Once those things are installed, create a Project folder from your root directory and navigate into it. After moving into the folder, clone this [repo](https://github.com/RedSunDave/vector-search)

Change to root folder

```bash
cd ~
```

Make a directory called Projects

```bash
mkdir Projects
```

Change into the directory

```bash
cd Projects
```

Clone this github repo / codebase

```bash
git clone https://github.com/RedSunDave/vector-search.git
```

Add the appropriate environmental variable to run UV to your .bashrc file

```bash
echo "export UV_PREVIEW=1" >> ~/.bashrc
```

Reload your .bashrc file

```bash
source ~/.bashrc
```

5. You've downloaded the application. Now change into that folder and run the following commands to start it up.

Change into the vector-search folder

```bash
cd vector-search
```

Run the application

```bash
uv run src/vector_search/main.py
```

The application should take some time to download resources and build the virtual environment, please be patient. After this point, the application should start up and you will be on the main screen.

The main screen will give you the basic instructions to get started. Try exiting the application by pressing 'Ctrl-q'

Now you are ready to load PDFs. Look in your filesystem window for the folder "uploaded". Copy whatever PDFs you want to make searchable into that folder.

1. Place PDFs for ingestion into the "uploaded" folder located in the root folder.
2. Run the application, press 'd', then on the scan page click 'scan now'.
3. When prompted, the application will show you the first page of the PDF. Enter metadata and click "submit".
4. Repeat this process until all PDFs are ingested.
5. Press 'a' and enter your queries to search all of your PDFs Vector Style.

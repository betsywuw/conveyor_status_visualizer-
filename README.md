# Set up process

* Clone this repo or download from GitHub and unzip it
* Open the folder in VSCode and create a new terminal session (press **Ctrl + `**)
* Run the following command in the terminal: `python -m venv .venv` if not `python3 -m venv .venv`. This will create a Python virtual environment specifically for this project.
* Then, run `.venv\Scripts\activate` which tells it to use a virtual environment that we just created.
* Run `pip install -r requirements.txt` if not `pip3 install -r requirements.txt`. This will install all the packages we need in this project.
* To start the web app, run `python app.py` if not `python3 app.py`. The terminal should tells you something about the URL for the app (probably http://127.0.0.1:5000/).


# How it works?

* Once the app starts, it tries to fetch the latest .xlsx file from the URL that Amazon should give to you (maybe with some authentication needed).
* It saves the .xlsx file to the [data](./data/) directory, sort of a database. Moreover, it also processes the .xlsx file to be ready to render as chart and graph.
* If you leave the app running, it will try to get a new .xlsx automatically everyday at midnight and do the same things as above.


# What to change?

* I added **TODO** comment in the [app.py](./app.py) for actually set up the fetching. Everything else should be working the same.
* More specifically, the `EXTERNAL_EXCEL_URL` and `fetch_store_and_process_excel()` (the first 2 lines) are needed to be changed. It needs you to tell it where + how to get .xlsx file.


# Note on making it production ready

* Now the app only run on a particular machine that has this project set up. The URL http://127.0.0.1:5000/ is only local.
* Anyone to be able to access it, there will need a server that connects to the internet and it takes some configuration in there.

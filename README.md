# LeccapDL

A utility for downloading lecture recordings from the [University of Michigan's CAEN Lecture Recording Service](https://caen.engin.umich.edu/lecrecording/).

Uses Python and Selenium for interactive authentication using the University's login system.

## Instructions

### Setup

1. Clone the repo and `cd` into it
1. Run `python3 -m venv env`
1. Activate the environment
   1. On Linux: `source env/bin/activate`
   1. On Windows: idk, use WSL
1. Install dependencies with `pip install -r requirements.txt`

### Running

1. Simply run `python3 main.py` and enter your desired course name

A Selenium-controlled browser window will appear. You will need to log into your University of Michigan account in order to access the lecture capture site.

All the source code is plainly visible in [main.py](./main.py). Please feel free to read through it closely if you are wary of entering your login info.

Your cookies and other data will be stored in the `./chrome-data/` directory for subsequent runs. If you are done with the program for a while, consider deleting this directory when you are done, so that your credentials aren't stored.

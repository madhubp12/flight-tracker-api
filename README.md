#Flight Tracker API

A FastAPI-based web application that scrapes flight data from [FlightStats](https://www.flightstats.com) using Selenium, stores it in a SQLite database, and provides a REST API to query flight status.

---

##  Features

- Scrapes flight details from FlightStats using Selenium
- Stores flight data in a local SQLite database
- FastAPI backend with a single `/track-flight/` endpoint
- Returns structured JSON response

---
## Tech-installation
  # Install fastAPI
  use the command 
  pip install fastapi uvicorn requests beautifulsoup4 sqlalchemy sqlite3
#fastapi - Web framework
#uvicorn - ASGI server
#requests - For HTTP requests to scrape FlightStats
#beautifulsoup4 - For parsing HTML response
#sqlalchemy - ORM for database interactions
#sqlite3 - database for storage

## Installation

### 1. Clone the repo

git clone https://github.com/your-username/flight-tracker-api.git
cd flight-tracker-api

## Run the code
  #Run main.py
    uvicorn main:app --reload
  #Run test_main.py
    pytest test_main.py


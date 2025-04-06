from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Initialize FastAPI
app = FastAPI()

# Database setup
DATABASE_URL = "sqlite:///./flights.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Flight model
class Flight(Base):
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    airline_code = Column(String, index=True)
    flight_number = Column(String, index=True)
    departure_date = Column(String)
    status = Column(String)
    departure_airport = Column(String)
    arrival_airport = Column(String)
    departure_time = Column(String)
    arrival_time = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

# Create the database tables
if not os.path.exists("flights.db"):
    Base.metadata.create_all(bind=engine)

# Pydantic model for response
class FlightResponse(BaseModel):
    airline_code: str
    flight_number: str
    departure_date: str
    status: str
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str

def scrape_flight_data(airline_code: str, flight_number: str, departure_date: str):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Format date
        year, month, day = departure_date.split("-")
        month, day = str(int(month)), str(int(day))

        flight_url = f"https://www.flightstats.com/v2/flight-tracker/{airline_code}/{flight_number}?year={year}&month={month}&date={day}"
        driver.get(flight_url)
        driver.implicitly_wait(10)  # Wait for JavaScript to load elements

        # Flight Status
        try:
            status_elem = driver.find_element(By.CSS_SELECTOR, ".text-success, .text-warning, .text-danger")
            status = status_elem.text.strip()
        except:
            status = "Unknown"

        # Flight Details
        try:
            flight_number_elem = driver.find_element(By.CSS_SELECTOR, ".flight-number")
            flight_number = flight_number_elem.text.strip()
        except:
            flight_number = "Unknown"

        try:
            departure_airport_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'New York')]")
            departure_airport = departure_airport_elem.text.strip()
        except:
            departure_airport = "Unknown"

        try:
            arrival_airport_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'London')]")
            arrival_airport = arrival_airport_elem.text.strip()
        except:
            arrival_airport = "Unknown"

        try:
            departure_time_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Scheduled')]/following-sibling::div")
            departure_time = departure_time_elem.text.strip()
        except:
            departure_time = "Unknown"

        try:
            arrival_time_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Scheduled')]/following-sibling::div")
            arrival_time = arrival_time_elem.text.strip()
        except:
            arrival_time = "Unknown"

        return {
            "airline_code": airline_code,
            "flight_number": flight_number,
            "departure_date": departure_date,
            "status": status,
            "departure_airport": departure_airport,
            "arrival_airport": arrival_airport,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        driver.quit()


@app.get("/track-flight/", response_model=FlightResponse)
def track_flight(
    airline_code: str = Query(..., min_length=2, max_length=2),
    flight_number: str = Query(..., min_length=1),
    departure_date: str = Query(...)
):
    # Validate date format
    try:
        datetime.strptime(departure_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    db = SessionLocal()
    
    # Check if flight data exists
    existing_flight = db.query(Flight).filter(
        Flight.airline_code == airline_code,
        Flight.flight_number == flight_number,
        Flight.departure_date == departure_date
    ).first()

    if existing_flight:
        return existing_flight

    # Scrape and save new data
    flight_data = scrape_flight_data(airline_code, flight_number, departure_date)
    new_flight = Flight(**flight_data)

    db.add(new_flight)
    db.commit()
    db.refresh(new_flight)
    
    return new_flight

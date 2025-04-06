from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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

if not os.path.exists("flights.db"):
    Base.metadata.create_all(bind=engine)

# Pydantic model
class FlightResponse(BaseModel):
    airline_code: str
    flight_number: str
    departure_date: str
    status: str
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str

    class Config:
        from_attributes = True

def scrape_flight_data(airline_code: str, flight_number: str, departure_date: str):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        year, month, day = departure_date.split("-")
        month, day = str(int(month)), str(int(day))

        flight_url = f"https://www.flightstats.com/v2/flight-tracker/{airline_code}/{flight_number}?year={year}&month={month}&date={day}"
        driver.get(flight_url)
        driver.implicitly_wait(10)

        # Accept cookies if present
        try:
            accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]"))
            )
            accept_button.click()
        except Exception as e:
            print("No cookie popup or error:", e)

        driver.save_screenshot("debug.png")

        try:
            status_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ticket__StatusBadge-sc-1rrbl5o-12"))
            )
            status = status_elem.text.strip()
        except Exception as e:
            print("Error extracting status:", e)
            status = "Unknown"

        try:
            flight_number_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "div.ticket__FlightNumberContainer-sc-1rrbl5o-4.exbpMf > div.text-helper__TextHelper-sc-8bko4a-0.OvgJa"
                ))
            )
            flight_number = flight_number_elem.text.strip()
        except Exception as e:
            print("Flight number error:", e)
            flight_number = "Unknown"

        try:
            departure_airport = driver.find_element(By.XPATH, "//div[contains(text(), 'New York')]").text.strip()
        except:
            departure_airport = "Unknown"

        try:
            arrival_airport = driver.find_element(By.XPATH, "//div[contains(text(), 'London')]").text.strip()
        except:
            arrival_airport = "Unknown"

        try:
            departure_time = driver.find_element(By.XPATH, "//div[contains(text(), 'Scheduled')]/following-sibling::div").text.strip()
        except:
            departure_time = "Unknown"

        try:
            arrival_time = driver.find_element(By.XPATH, "//div[contains(text(), 'Scheduled')]/following-sibling::div").text.strip()
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
        print("Scraping error:", e)
        raise HTTPException(status_code=500, detail=f"Scraping failed: {e}")
    finally:
        driver.quit()

@app.get("/track-flight/", response_model=FlightResponse)
def track_flight(
    airline_code: str = Query(..., min_length=2, max_length=2),
    flight_number: str = Query(..., min_length=1),
    departure_date: str = Query(...)
):
    try:
        datetime.strptime(departure_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    db = SessionLocal()
    try:
        flight = db.query(Flight).filter(
            Flight.airline_code == airline_code,
            Flight.flight_number == flight_number,
            Flight.departure_date == departure_date
        ).first()

        if flight:
            return flight

        data = scrape_flight_data(airline_code, flight_number, departure_date)
        new_flight = Flight(**data)
        db.add(new_flight)
        db.commit()
        db.refresh(new_flight)
        return new_flight
    finally:
        db.close()

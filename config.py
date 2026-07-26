import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://yourusername.github.io/trieste_business_tycoon/webapp/")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
DATABASE_PATH = os.getenv("DATABASE_PATH", "trieste_tycoon.db")
STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "5000"))
SEASONAL_MULTIPLIERS = {
    "estate": 1.50,
    "inverno": 0.70,
    "primavera": 1.10,
    "autunno": 0.90
}

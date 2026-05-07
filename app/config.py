import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "mco")
MYSQL_USER = os.getenv("MYSQL_USER", "mco")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "mco")

PERCENTUAL_MINIMO = float(os.getenv("PERCENTUAL_MINIMO", "90.0"))

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
)

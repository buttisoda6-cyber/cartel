import sys
sys.path.append('backend')
from database import SessionLocal
from app_db import SessionLocal as AppSessionLocal
from routes.insights import get_interventions
db=SessionLocal()
app_db=AppSessionLocal()
import traceback
try:
    get_interventions(db, app_db)
except Exception as e:
    traceback.print_exc()

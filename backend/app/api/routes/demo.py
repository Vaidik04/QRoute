from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.services.demo_service import demo_service

router = APIRouter()

@router.post("/demo/reset")
def reset_demo_environment(db: Session = Depends(get_db)):
    return demo_service.reset_demo(db)

@router.get("/demo/scenarios")
def get_demo_scenarios():
    return demo_service.get_scenarios()

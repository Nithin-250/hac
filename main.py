# main.py
from fastapi import FastAPI, Request
from fraud_detection_service import detect_fraud
from pydantic import BaseModel

app = FastAPI()

# Define input schema
class Transaction(BaseModel):
    amount: float
    location: str
    card_type: str
    ip_address: str
    to_account: str

@app.post("/detect")
def detect(transaction: Transaction):
    result = detect_fraud(transaction.dict())
    return {"fraud": result}

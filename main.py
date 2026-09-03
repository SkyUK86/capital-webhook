import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

CAPITAL_API_URL = "https://demo-api-capital.backend-capital.com/api/v1"

API_KEY = os.getenv("CAPITAL_API_KEY", "54mYfOiT9tKlFjld")
IDENTIFIER = os.getenv("CAPITAL_IDENTIFIER", "switchgameconsolebg@gmail.com")
PASSWORD = os.getenv("CAPITAL_PASSWORD", "632189pP!")

class SignalPayload(BaseModel):
    action: str
    epic: str
    size: float
    stop_level: float = None

def get_capital_session():
    url = f"{CAPITAL_API_URL}/session"
    headers = {
        "X-CAP-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "identifier": IDENTIFIER,
        "password": PASSWORD
    }
    res = requests.post(url, json=body, headers=headers)
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail=f"Грешка при автентикация: {res.text}")

    cst = res.headers.get("CST")
    x_token = res.headers.get("X-SECURITY-TOKEN")
    return cst, x_token

@app.get("/")
def read_root():
    return {"status": "Webhook сървърът е онлайн и готов за сигнали!"}

@app.post("/webhook")
async def execute_trade(payload: SignalPayload):
    cst, x_token = get_capital_session()
    headers = {
        "X-CAP-API-KEY": API_KEY,
        "CST": cst,
        "X-SECURITY-TOKEN": x_token,
        "Content-Type": "application/json"
    }

    if payload.action in ["BUY", "SELL"]:
        order_body = {
            "epic": payload.epic,
            "direction": payload.action,
            "size": payload.size
        }
        if payload.stop_level:
            order_body["stopLevel"] = payload.stop_level

        order_res = requests.post(f"{CAPITAL_API_URL}/positions", json=order_body, headers=headers)
        return {"status": "Order Placed", "response": order_res.json()}

    elif payload.action == "CLOSE":
        pos_res = requests.get(f"{CAPITAL_API_URL}/positions", headers=headers)
        positions = pos_res.json().get("positions", [])

        closed_trades = []
        for p in positions:
            if p["market"]["epic"] == payload.epic:
                deal_id = p["position"]["dealId"]
                del_res = requests.delete(f"{CAPITAL_API_URL}/positions/{deal_id}", headers=headers)
                closed_trades.append(del_res.json())

        return {"status": "Positions Closed", "results": closed_trades}

    raise HTTPException(status_code=400, detail="Невалидно действие")

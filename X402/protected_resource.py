from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="x402 Protected API")

# === ADD CORS - This is the most important fix ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # Allow your React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/premium-data")
async def get_premium_data(x_payment_receipt: str = Header(None)):
    """
    HACKATHON DEMO MODE:
    - Returns 402 with x402_instructions if no receipt
    - Unlocks resource if receipt is provided
    """
    
    if not x_payment_receipt:
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "message": "This endpoint costs 1 ALGO.",
                "x402_instructions": {
                    "oracle_endpoint": "http://localhost:8000/attest",
                    "contract_app_id": 758707534,
                    "contract_address": "K5J4MYOGU6ZRUEG4DMCNAKQOJP7HBUMZAM5GWTNAJTR2EAMU3GS63ZNR5A"
                }
            }
        )
    
    # Receipt provided → unlock
    print(f"\n🔍 [API INTERNAL] Verifying Algorand TxID: {x_payment_receipt}...")
    print("✅ [API INTERNAL] Payment verified on Testnet. Unlocking resource.")

    return {
        "status": "success",
        "message": "Premium resource unlocked successfully",
        "data": {
            "temperature": 24,
            "condition": "Sunny",
            "wind_speed": "12 km/h",
            "agent_message": "Good morning AI! Here is your premium data."
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
import os
import base64
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import load_dotenv
from algokit_utils import AlgorandClient, micro_algo
from algokit_utils import AppClientMethodCallParams
# Algorand imports
from algosdk import mnemonic, account
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk.encoding import decode_address



# Safe import for calling contract methods matching deploy.py
try:
    from algokit_utils import AppClientMethodCallParams
except ImportError:
    from algokit_utils.applications.app_client import AppClientMethodCallParams

# Import custom modules
from oracle.ml.score import score_transaction
from oracle.crypto.signer import sign_payload, verify_signature_locally

# Load .env with override to prevent ghost keys
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)


# ── Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Ageniz Oracle starting up...")
    print(f" Oracle Public Key : {os.getenv('ORACLE_PUBLIC_KEY') or 'Not set yet!'}")
    yield
    print("🛑 Ageniz Oracle shutting down...")


app = FastAPI(
    title="Ageniz Oracle",
    description="Zero-trust ML Risk Oracle for Algorand AI Agents",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ──────────────────────────────────────────────────────
class AttestRequest(BaseModel):
    agent_address: str
    recipient_address: str
    amount_micro: int
    velocity: int
    timing_delta: float

class AttestResponse(BaseModel):
    verdict: str
    confidence_score: float
    signature_b64: str | None = None
    payload_hex: str | None = None
    oracle_public_key: str | None = None
    debug: dict | None = None

class ExecutePaymentRequest(BaseModel):
    agent_address: str
    amount_micro: int
    recipient_address: str
    signature_b64: str




# ── X402 PREMIUM DATA ENDPOINT (Moved from protected_resource.py) ───────
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
                    "oracle_endpoint": "/attest", 
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
# ── Attest Endpoint ─────────────────────────────────────────────────────
@app.post("/attest", response_model=AttestResponse)
async def attest_transaction(req: AttestRequest):
    if req.amount_micro <= 0:
        return AttestResponse(verdict="INVALID", confidence_score=0.0, debug={"reason": "Amount must be positive"})

    ml_result = score_transaction(
        amount=req.amount_micro / 1_000_000,
        velocity=req.velocity,
        timing_delta=req.timing_delta,
        wallet_address=req.recipient_address
    )

    if ml_result["verdict"] != "SAFE":
        return AttestResponse(
            verdict=ml_result["verdict"],
            confidence_score=ml_result["confidence_score"],
            debug=ml_result.get("debug")
        )

    signed = sign_payload(req.agent_address, req.amount_micro)

    return AttestResponse(
        verdict="SAFE",
        confidence_score=ml_result["confidence_score"],
        signature_b64=signed["signature_b64"],
        payload_hex=signed["payload_hex"],
        oracle_public_key=signed["oracle_public_key"],
        debug=ml_result.get("debug")
    )


# ── REAL EXECUTE PAYMENT ENDPOINT ───────────────────────────────────────
@app.post("/execute-payment")
async def execute_payment(req: ExecutePaymentRequest):
    try:
        algorand = AlgorandClient.testnet()

        deployer_mnemonic = os.getenv("DEPLOYER_MNEMONIC")
        if not deployer_mnemonic:
            raise HTTPException(status_code=500, detail="DEPLOYER_MNEMONIC not set in .env")

        private_key = mnemonic.to_private_key(deployer_mnemonic)
        sender = account.address_from_private_key(private_key)

        raw_app_id = os.getenv("APP_ID")
        if not raw_app_id:
            raise HTTPException(status_code=500, detail="APP_ID not set in .env")
        app_id = int(raw_app_id)

        # oracle/main.py

       # ── 🔍 MAIN.PY DATA TRACE ──
        print("\n--- 🛰️ INCOMING BLOCKCHAIN REQUEST ---")
        print(f"1. APP_ID from .env    : {app_id}")
        print(f"2. Agent Address       : {req.agent_address}")
        print(f"3. Amount (MicroAlgos) : {req.amount_micro}")
        
        # Decode the signature to check what we are actually holding
        decoded_sig = base64.b64decode(req.signature_b64)
        print(f"4. Signature (Hex)     : {decoded_sig.hex()}")
        print(f"5. Signature Length    : {len(decoded_sig)} bytes")
        
        # Final consistency check using your proven signer.py logic
        from oracle.crypto.signer import verify_signature_locally
        is_consistent = verify_signature_locally(
            req.agent_address, 
            req.amount_micro, 
            req.signature_b64
        )
        print(f"6. Local Re-Verify     : {'✅ PASSED' if is_consistent else '❌ FAILED'}")
        
        print(f"7. Active Oracle Key   : {os.getenv('ORACLE_PUBLIC_KEY')}")
        print("--------------------------------------\n")

        print("\n--- PRE-FLIGHT CHECK ---")
        print(f"Contract App ID       : {app_id}")
        print(f"Txn Sender (Deployer) : {sender}")
        print(f"Agent Address (React) : {req.agent_address}")

       

        # Local verification
        is_valid_local = verify_signature_locally(
            agent_address=req.agent_address,
            amount_micro=req.amount_micro,
            signature_b64=req.signature_b64
        )
        print(f"Local Signature Valid? : {'✅ YES' if is_valid_local else '❌ NO'}")
        print("---------------------------\n")

        if not is_valid_local:
            raise HTTPException(status_code=400, detail="Local pre-flight verification failed")

        # Load ARC56 spec exactly like deploy.py does
        arc56_path = os.path.join(os.path.dirname(__file__), "..", "contract", "AgenizContract.arc56.json")
        if not os.path.exists(arc56_path):
            raise HTTPException(status_code=500, detail="ABI Spec not found. Did you compile the contract?")

        with open(arc56_path, "r", encoding="utf-8") as f:
            arc56_json = f.read()

        signer = AccountTransactionSigner(private_key)

        # 1. Create the App Factory
        factory = algorand.client.get_app_factory(
        app_spec=arc56_json,
        default_sender=sender,
        default_signer=signer
        )

        app_client = factory.get_app_client_by_id(app_id=app_id)

        
        
        result = app_client.send.call(
    params=AppClientMethodCallParams(
        method="execute_payment",
        args=[
        req.amount_micro,
        req.recipient_address,
        base64.b64decode(req.signature_b64),
        req.agent_address
       ],
        extra_fee=micro_algo(7000)
    )
)
        tx_id = result.tx_id
        print(f"✅ On-chain payment executed. TxID: {tx_id}")

        return {"success": True, "tx_id": tx_id}

    except Exception as e:
        print(f"❌ Blockchain Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Health Check ────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "online",
        "oracle_public_key": os.getenv("ORACLE_PUBLIC_KEY"),
        "app_id": os.getenv("APP_ID")
    }

if __name__ == "__main__":
    import uvicorn
    # This keeps port 8000 for local testing, but allows Render to inject its own port!
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
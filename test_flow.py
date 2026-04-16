import os
import base64
import requests
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk.encoding import decode_address
import algokit_utils

try:
    from algokit_utils import AppClientMethodCallParams
except ImportError:
    from algokit_utils.applications.app_client import AppClientMethodCallParams

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────
ORACLE_URL   = "http://127.0.0.1:8000/attest"
APP_ID       = int(os.getenv("APP_ID", 0))

TEST_AGENT_ADDRESS      = "GARDLGBGOJIUSROUU4FGFRXFSGW4IDAKGTCNHYBRODTFL236IY2QMXWRQE"
TARGET_RECEIVER_ADDRESS = "EUKRBWJBKMYRCRQOHFGEUMXGK2JDXESZ5A2W5SJVJVTF7BW5CWBSUG422Q"
TEST_AMOUNT_MICRO       = 1_000_000  # 1 ALGO

def opt_in_if_needed(app_client):
    """Opt the wallet into the contract to initialize local state."""
    try:
        app_client.send.opt_in(
            params=AppClientMethodCallParams(
                method="opt_in",
                args=[]
            )
        )
        print("✅ Opted into contract successfully")
    except Exception as e:
        if "already opted in" in str(e).lower() or "has already opted" in str(e).lower():
            print("✅ Already opted in — skipping")
        else:
            print(f"⚠️  Opt-in error: {e}")

def test_flow():
    print("🔍 Starting Ageniz End-to-End Test...\n")
    print(f"   APP_ID         : {APP_ID}")
    print(f"   Agent Address  : {TEST_AGENT_ADDRESS}")
    print(f"   Recipient      : {TARGET_RECEIVER_ADDRESS}")
    print(f"   Amount         : {TEST_AMOUNT_MICRO / 1_000_000} ALGO\n")

    # ── Setup App Client early (needed for opt-in) ─────────────────────────
    algorand         = algokit_utils.AlgorandClient.testnet()
    private_key      = mnemonic.to_private_key(os.getenv("DEPLOYER_MNEMONIC"))
    deployer_address = account.address_from_private_key(private_key)
    signer           = AccountTransactionSigner(private_key)

    arc56_path = os.path.join(os.path.dirname(__file__), "contract", "AgenizContract.arc56.json")
    with open(arc56_path, "r", encoding="utf-8") as f:
        arc56_json = f.read()

    app_client = algorand.client.get_app_client_by_id(
        app_id=APP_ID,
        app_spec=arc56_json,
        default_sender=deployer_address,
        default_signer=signer
    )

    # ── Step 1: Opt-In ─────────────────────────────────────────────────────
    print("🔑 Checking opt-in status...")
    opt_in_if_needed(app_client)

    # ── Step 2: Call Oracle ────────────────────────────────────────────────
    payload = {
        "agent_address": TEST_AGENT_ADDRESS,
        "recipient_address": "weather_api_1",
        "amount_micro": TEST_AMOUNT_MICRO,
        "velocity": 5,
        "timing_delta": 720
    }

    print("\n📡 Calling FastAPI Oracle...")
    try:
        resp = requests.post(ORACLE_URL, json=payload, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"❌ Failed to reach Oracle. Is FastAPI running?")
        print(f"   cd oracle && uvicorn main:app --reload")
        return

    print(f"   Verdict          : {data.get('verdict')}")
    print(f"   Confidence Score : {data.get('confidence_score')}")
    print(f"   Debug            : {data.get('debug')}")

    if data.get('verdict') != "SAFE":
        print("\n❌ Transaction blocked by ML Oracle")
        return

    if not data.get('signature_b64'):
        print("\n❌ Oracle returned SAFE but no signature — check signer.py")
        return

    print("\n✅ Oracle approved + signature received")

    # ── Step 3: Submit to Smart Contract ───────────────────────────────────
    print("⛓️  Submitting to Algorand Smart Contract...")

    try:
        result = app_client.send.call(
            params=AppClientMethodCallParams(
                method="execute_payment",
                args=[
                    TEST_AMOUNT_MICRO,
                    decode_address(TARGET_RECEIVER_ADDRESS),
                    base64.b64decode(data["signature_b64"]),
                    
                ],
                extra_fee=algokit_utils.AlgoAmount(micro_algo=4000)
            )
        )

        print(f"\n🎉 Transaction Successful! Firewall passed the funds.")
        print(f"   Transaction ID : {result.tx_id}")
        print(f"   Explorer       : https://testnet.explorer.perawallet.app/tx/{result.tx_id}")

    except Exception as e:
        print(f"\n❌ Smart Contract Rejected: {e}")

if __name__ == "__main__":
    test_flow()
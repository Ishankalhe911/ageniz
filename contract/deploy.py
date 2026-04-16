import os
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk.transaction import PaymentTxn, wait_for_confirmation
import algokit_utils

# 🔥 THE ACTUAL FIX: Importing the Factory params, not the Client params!
try:
    from algokit_utils import AppFactoryCreateMethodCallParams
except ImportError:
    from algokit_utils.applications.app_factory import AppFactoryCreateMethodCallParams

# Load .env from root folder
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Config ─────────────────────────────────────────────────────────────────
ALGOD_URL         = os.getenv("ALGORAND_NODE_URL", "https://testnet-api.algonode.cloud")
DEPLOYER_MNEMONIC = os.getenv("DEPLOYER_MNEMONIC")
ORACLE_PUBLIC_KEY = os.getenv("ORACLE_PUBLIC_KEY")

if not DEPLOYER_MNEMONIC or not ORACLE_PUBLIC_KEY:
    raise EnvironmentError("Missing DEPLOYER_MNEMONIC or ORACLE_PUBLIC_KEY in .env")

def deploy():
    print("🚀 Deploying Ageniz Contract to Testnet...")

    # ── Setup ──────────────────────────────────────────────────────────────
    algorand = algokit_utils.AlgorandClient.testnet()

    private_key      = mnemonic.to_private_key(DEPLOYER_MNEMONIC)
    deployer_address = account.address_from_private_key(private_key)
    signer           = AccountTransactionSigner(private_key)

    algorand.set_signer(deployer_address, signer)
    print(f"📬 Deployer Address: {deployer_address}")

    # ── Load ARC56 spec ────────────────────────────────────────────────────
    arc56_path = os.path.join(os.path.dirname(__file__), "AgenizContract.arc56.json")
    if not os.path.exists(arc56_path):
        raise FileNotFoundError("ARC56 JSON not found. Run: algokit compile python contract/ageniz_contract.py")

    with open(arc56_path, "r", encoding="utf-8") as f:
        arc56_json = f.read()

    # ── Create Factory ─────────────────────────────────────────────────────
    factory = algorand.client.get_app_factory(
        app_spec=arc56_json,
        default_sender=deployer_address,
        default_signer=signer
    )

    # ── Deploy ─────────────────────────────────────────────────────────────
    print(f"📡 Using Oracle Public Key: {ORACLE_PUBLIC_KEY}")
    print("⏳ Sending create transaction...")

    # 🔥 Passing the string directly. The SDK handles the 32-byte encoding because the contract uses arc4.Address!
    result, app_client = factory.send.create(
        params=AppFactoryCreateMethodCallParams(
            method="init",
            args=[ORACLE_PUBLIC_KEY] 
        )
    )

    app_id      = app_client.app_id
    app_address = app_client.app_address

    print(f"\n🎉 Contract Deployed Successfully!")
    print(f"   App ID      : {app_id}")
    print(f"   App Address : {app_address}")
    print(f"\n🔗 View on Explorer:")
    print(f"   https://testnet.explorer.perawallet.app/application/{app_id}")

    # 🔥 We removed the automatic .env writing to prevent the ghost APP_ID bug.
    print("\n⚠️  MANUAL STEP REQUIRED:")
    print(f"Update your .env file and React UI with EXACTLY these values:")
    print(f"APP_ID={app_id}")
    print(f"APP_ADDRESS={app_address}\n")

    return app_id, app_address


def fund_contract(app_address: str, amount_algo: float = 0.5): # Keep funding at 0.5 to save dispenser limits
    print(f"💰 Funding contract with {amount_algo} ALGO...")

    algorand     = algokit_utils.AlgorandClient.testnet()
    algod_client = algorand.client.algod
    private_key  = mnemonic.to_private_key(DEPLOYER_MNEMONIC)
    deployer_address = account.address_from_private_key(private_key)

    params       = algod_client.suggested_params()
    amount_micro = int(amount_algo * 1_000_000)

    txn = PaymentTxn(
        sender=deployer_address,
        sp=params,
        receiver=app_address,
        amt=amount_micro
    )
    signed_txn = txn.sign(private_key)
    tx_id      = algod_client.send_transaction(signed_txn)
    wait_for_confirmation(algod_client, tx_id)

    print(f"✅ Funded successfully.")
    print(f"   Txn ID: {tx_id}")

if __name__ == "__main__":
    try:
        app_id, app_address = deploy()
        fund_contract(app_address, amount_algo=0.5)
        print("\n🔥 Ageniz Contract is LIVE on Testnet and funded. Ready for demo!")
      
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        raise
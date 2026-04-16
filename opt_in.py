from algosdk import transaction, mnemonic
from algosdk.v2client import algod
from algosdk.atomic_transaction_composer import AtomicTransactionComposer, AccountTransactionSigner
from algosdk.abi import Method
from algosdk import transaction, mnemonic, account
# --- CONFIGURATION ---
ALGOD_ADDR = "https://testnet-api.algonode.cloud"
APP_ID = 758871176 

# 🔥 PASTE YOUR 25-WORD PASSPHRASE HERE (Inside the quotes)
# Example: "apple banana cherry dog elephant..."
MNEMONIC = "view record come belt leaf hazard dune clerk like brisk upper expire small link forum category jungle engine flash wrong welcome wreck wasp able happy"

# Convert the 25 words into the raw Private Key and Public Address
raw_key = mnemonic.to_private_key(MNEMONIC)
AGENT_ADDRESS = account.address_from_private_key(raw_key)

def opt_in_to_contract():
    client = algod.AlgodClient("", ALGOD_ADDR, headers={"User-Agent": "algosdk"})
    
    # Signer now uses the perfectly derived Base64 key
    signer = AccountTransactionSigner(raw_key) 
    sp = client.suggested_params()
    
    atc = AtomicTransactionComposer()
    
    # We call the opt_in method specifically with the OptIn OnComplete flag
    atc.add_method_call(
        app_id=APP_ID,
        method=Method.from_signature("opt_in()void"),
        sender=AGENT_ADDRESS,
        sp=sp,
        signer=signer,
        on_complete=transaction.OnComplete.OptInOC
    )
    
    print(f"🚀 Sending Opt-In transaction for {AGENT_ADDRESS} to App {APP_ID}...")
    try:
        result = atc.execute(client, 4)
        print(f"✅ OPT-IN SUCCESSFUL! TxID: {result.tx_ids[0]}")
        print("🎉 You can now run the execute_payment demo!")
    except Exception as e:
        print(f"❌ Opt-In Failed: {e}")

if __name__ == "__main__":
    opt_in_to_contract()
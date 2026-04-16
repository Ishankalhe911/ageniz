import os

import httpx

import base64

from dotenv import load_dotenv

from algosdk.v2client import algod

from algosdk import mnemonic, account

from algosdk.atomic_transaction_composer import AtomicTransactionComposer, AccountTransactionSigner

from algosdk.abi import Method



load_dotenv()



# ── Config ─────────────────────────────────────────────────────────────────

ALGOD_URL  = "https://testnet-api.algonode.cloud"

ALGOD_TOKEN = ""

APP_ID     = int(os.getenv("APP_ID", 758707417))

ORACLE_URL = "http://127.0.0.1:8000/attest"



# ── Agent Wallet ───────────────────────────────────────────────────────────

AGENT_MNEMONIC   = os.getenv("DEPLOYER_MNEMONIC")

agent_private_key = mnemonic.to_private_key(AGENT_MNEMONIC)

agent_address     = account.address_from_private_key(agent_private_key)

agent_signer      = AccountTransactionSigner(agent_private_key)



# ── Algorand Client ────────────────────────────────────────────────────────

algod_client = algod.AlgodClient(

    ALGOD_TOKEN, ALGOD_URL,

    headers={"User-Agent": "algosdk"}

)



class X402AgentMiddleware:

    def __init__(self, agent_wallet_address: str):

        self.agent_wallet    = agent_wallet_address

        self.current_velocity = 1

        self.timing_delta     = 720.0



    def fetch_resource(

        self,

        target_url: str,

        amount_micro_algo: int,

        recipient_address: str,

        ml_wallet: str = "weather_api_1"  # known safe wallet for ML scoring

    ):

        print(f"\n🤖 [AGENT] Requesting resource: {target_url}")



        # ── Step 1: Initial Request → expect 402 ──────────────────────────

        response = httpx.get(target_url)



        if response.status_code != 402:

            print(f"✅ [API] No payment needed. Status: {response.status_code}")

            return response.json()



        print("🛑 [API] 402 Payment Required intercepted.")

        instructions = response.json().get("x402_instructions", {})

        oracle_url   = instructions.get("oracle_endpoint", ORACLE_URL)



        # ── Step 2: Call Ageniz Oracle ─────────────────────────────────────

        print(f"🛡️  [AGENIZ] Requesting ML attestation...")



        attest_payload = {

            "agent_address":     self.agent_wallet,

            "recipient_address": ml_wallet,          # ML scoring wallet

            "amount_micro":      amount_micro_algo,

            "velocity":          self.current_velocity,

            "timing_delta":      self.timing_delta

        }



        try:

            oracle_res  = httpx.post(oracle_url, json=attest_payload, timeout=10)

            attest_data = oracle_res.json()

        except Exception as e:

            print(f"❌ [AGENIZ] Oracle unreachable: {e}")

            return None



        verdict = attest_data.get("verdict")

        print(f"   Verdict          : {verdict}")

        print(f"   Confidence Score : {attest_data.get('confidence_score')}")



        if verdict != "SAFE":

            print("❌ [AGENIZ] Transaction BLOCKED — anomaly detected.")

            print(f"   Reason: {attest_data.get('debug')}")

            return None



        signature_b64  = attest_data.get("signature_b64")  # ← correct key

        signature_bytes = base64.b64decode(signature_b64)

        print(f"✅ [AGENIZ] Approved. Signature: {signature_b64[:20]}...")



        # ── Step 3: Execute On-Chain Payment ──────────────────────────────

        print(f"🔗 [ALGORAND] Executing payment via App ID: {APP_ID}...")



        method = Method.from_signature(
            "execute_payment(uint64,address,byte[])bool"
        )



        sp          = algod_client.suggested_params()

        sp.fee      = 2000  # extra fee for inner transaction

        sp.flat_fee = True



        atc = AtomicTransactionComposer()

        atc.add_method_call(

            app_id=APP_ID,

            method=method,

            sender=agent_address,

            sp=sp,

            signer=agent_signer,

            method_args=[

                amount_micro_algo,

                recipient_address,

                signature_bytes

            ]

        )



        try:

            result = atc.execute(algod_client, 4)

            tx_id  = result.tx_ids[0]

            print(f"💸 [ALGORAND] Payment successful!")

            print(f"   TxID     : {tx_id}")

            print(f"   Explorer : https://testnet.explorer.perawallet.app/tx/{tx_id}")

        except Exception as e:

            print(f"❌ [ALGORAND] Smart Contract rejected: {e}")

            return None



        # ── Step 4: Retry API with payment receipt ────────────────────────

        print("🤖 [AGENT] Retrying API with payment receipt...")

        headers  = {"x-payment-receipt": tx_id}

        final_res = httpx.get(target_url, headers=headers)



        if final_res.status_code == 200:

            print("🎉 [API] Success! Premium resource acquired.")

            return final_res.json()

        else:

            print(f"⚠️  [API] Failed after payment. Status: {final_res.status_code}")

            return None





if __name__ == "__main__":

    API_RECIPIENT_WALLET = os.getenv(

        "APP_ADDRESS",

        "K5J4MYOGU6ZRUEG4DMCNAKQOJP7HBUMZAM5GWTNAJTR2EAMU3GS63ZNR5A"

    )



    agent = X402AgentMiddleware(agent_wallet_address=agent_address)



    data = agent.fetch_resource(

        target_url="http://localhost:8001/api/v1/premium-data",

        amount_micro_algo=1_000_000,  # 1 ALGO

        recipient_address=API_RECIPIENT_WALLET

    )



    print("\n📦 Final Resource Output:", data)
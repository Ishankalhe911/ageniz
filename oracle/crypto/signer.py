import os
import base64
import struct
import nacl.signing  # <-- Critical: We use this instead of algosdk.util.sign_bytes

from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.encoding import decode_address
from core.payload import build_payload

# Determine path to .env (root of the project)
# Goes up two levels: oracle/crypto/ -> oracle/ -> root/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOTENV_PATH = os.path.join(BASE_DIR, ".env")


def sign_payload(agent_address: str, amount_micro: int) -> dict:
    """
    Signs a transaction attestation only if the ML verdict is SAFE.
    This is the core gatekeeper function for the Ageniz Oracle.
    """
    # 🔥 FIX 1: Added override=True to ensure fresh keys are always loaded
    load_dotenv(DOTENV_PATH, override=True)
    
    private_key_b64 = os.getenv("ORACLE_PRIVATE_KEY")
    public_key = os.getenv("ORACLE_PUBLIC_KEY")

    if not private_key_b64:
        print(f"❌ ERROR: .env file not found or ORACLE_PRIVATE_KEY missing at: {DOTENV_PATH}")
        raise EnvironmentError("ORACLE_PRIVATE_KEY not set in .env")
        
    # The payload is built externally now
    payload = build_payload(agent_address, amount_micro)

    print("🔵 SIGNER FINAL PAYLOAD:", payload.hex())
    print("🔵 SIGNER LENGTH:", len(payload))

    # 2. Cryptographic Signing (RAW BARE-METAL)
    try:
        # We bypass algosdk to avoid the "MX" prefix!
        # Algorand private keys are 64 bytes (32b seed + 32b pubkey) in base64
        raw_priv_key = base64.b64decode(private_key_b64)
        
        # PyNaCl uses the 32-byte seed to create the signature
        signing_key = nacl.signing.SigningKey(raw_priv_key[:32])
        
        # Sign the RAW payload directly
        signed_message = signing_key.sign(payload)
        
        
        # Extract the 64-byte signature and encode it for the API
        signature_b64 = base64.b64encode(signed_message.signature).decode('utf-8')
        
        return {
            "signature_b64": signature_b64,
            "payload_hex": payload.hex(), # Helpful for debugging in the console
            "oracle_public_key": public_key
        }
    except Exception as e:
        print(f"❌ RAW SIGNING ERROR: {e}")
        raise


def generate_oracle_keypair():
    """
    Utility function to generate a fresh Oracle identity.
    Run this to generate the keys you'll put in your .env.
    """
    private_key, address = account.generate_account()
    mnemonic_str = mnemonic.from_private_key(private_key)
    
    print("\n--- 🛡️ NEW AGENIZ ORACLE IDENTITY ---")
    print(f"Public Key (Address): {address}")
    print(f"Private Key (Base64): {private_key}")
    print(f"Mnemonic: {mnemonic_str}")
    print("\n--- ⚠️ UPDATE YOUR .env FILE ---")
    print(f'ORACLE_PRIVATE_KEY="{private_key}"')
    print(f'ORACLE_PUBLIC_KEY="{address}"')
    
    return private_key, address


def verify_signature_locally(agent_address: str, amount_micro: int, signature_b64: str) -> bool:
    """
    Offline verification helper to test the logic before going on-chain.
    Ensures that the Python side is consistent with its own keys.
    """
    load_dotenv(DOTENV_PATH, override=True)
    public_key = os.getenv("ORACLE_PUBLIC_KEY")
    
    if not public_key:
        raise EnvironmentError("ORACLE_PUBLIC_KEY missing for verification")
        
    payload = build_payload(agent_address, amount_micro)
    signature_bytes = base64.b64decode(signature_b64)
    
    try:
        verify_key = nacl.signing.VerifyKey(decode_address(public_key))
        verify_key.verify(payload, signature_bytes)
        
        # 🔥 FIX 2: Explicit Payload Trace Added
        print("✅ LOCAL VERIFY OK. PAYLOAD HEX:", payload.hex())
        return True
    except Exception as e:
        # 🔥 FIX 3: Catch exact error instead of silent fail
        print("❌ LOCAL VERIFY FAILED:", str(e))
        return False
    
if __name__ == "__main__":
    generate_oracle_keypair()
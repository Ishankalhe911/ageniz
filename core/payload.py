# core/payload.py
from algosdk.encoding import decode_address
import struct

PREFIX = b"MX"
SUFFIX = b"SAFE"

def build_payload(agent_address: str, amount_micro: int) -> bytes:
    """
    Canonical 46-byte payload. 
    Matches: [MX (2)] + [Agent (32)] + [Amount (8)] + [SAFE (4)]
    """
    agent_bytes = decode_address(agent_address)
    # Ensure 8-byte big-endian alignment
    amount_bytes = struct.pack(">Q", int(amount_micro)) 

    payload = PREFIX + agent_bytes + amount_bytes + SUFFIX
    
    # --- DEBUG LOG ---
    print(f"DEBUG: Payload Parts:")
    print(f"  - Prefix: {PREFIX.hex()}")
    print(f"  - Agent : {agent_bytes.hex()}")
    print(f"  - Amount: {amount_bytes.hex()} (microAlgos: {amount_micro})")
    print(f"  - Suffix: {SUFFIX.hex()}")
    print(f"  - FULL PAYLOAD HEX: {payload.hex()}")
    print(f"  - TOTAL LENGTH: {len(payload)} bytes")
    # ------------------
    # 
    # ... your existing build_payload code ...
    return payload

    
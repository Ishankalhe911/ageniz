# Create a tiny script: check_key.py
import base64
from algosdk import encoding
addr = "ZVFEJHPZVTOCHPNOYYUWQL7GDX5EBTRMX2ADK3FPL7MSQMF6AHFVO4RSSQ"
print(base64.b64encode(encoding.decode_address(addr)).decode())
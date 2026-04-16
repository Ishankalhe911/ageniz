from algopy import (
    ARC4Contract,
    Bytes,
    GlobalState,
    LocalState,
    Txn,
    UInt64,
    arc4,
    Global,
    op,
    itxn,
    Account,
    ensure_budget,
    log  # 🔥 ADD THIS
)
import typing

class AgenizContract(ARC4Contract):
    def __init__(self) -> None:
        # Global State: Trusted Python ML Oracle's public key
        self.oracle_pubkey = GlobalState(Bytes)

        # Local State: Per-agent daily spending tracker
        self.daily_spent = LocalState(UInt64)
        self.last_reset  = LocalState(UInt64)

    # ── Deploy (called ONCE) ───────────────────────────────────────────────
    @arc4.abimethod(create="require")
    def init(self, oracle_pubkey: arc4.Address) -> None: 
        """Called once at deployment. Stores the Oracle's exactly 32-byte public key."""
        self.oracle_pubkey.value = oracle_pubkey.bytes # ✅ CORRECT AND CLEAN

    @arc4.abimethod
    def noop(self) -> None:
     pass
    @arc4.abimethod(allow_actions=["OptIn"])
    def opt_in(self) -> None:
        """Agent calls this to initialize its local state (daily cap tracking)."""
        self.daily_spent[Txn.sender] = UInt64(0)
        self.last_reset[Txn.sender]  = Global.latest_timestamp

    @arc4.abimethod
    def execute_payment(
        self, 
        amount: UInt64, 
        recipient: Account, 
        signature: arc4.StaticArray[arc4.Byte, typing.Literal[64]],
        agent: arc4.Address
    ) -> None:
        
        # 🟢 3000 budget is plenty now
        ensure_budget(3000) 
        
        # 1. Payload Reconstruction
        payload = (
            Bytes(b"MX") +
            agent.bytes +
            op.itob(amount) +
            Bytes(b"SAFE")
        )

        # ── 🔍 THE GATES OF TRUTH ──
        assert payload.length == 46, "ERR: Payload Length Not 46"
        assert signature.bytes.length == 64, "ERR: Signature Length Not 64"

        # ── 🔥 THE ACTUAL FIX: BARE VERIFICATION 🔥 ──
        # op.ed25519verify_bare verifies EXACT raw bytes without adding "ProgData"
        is_valid = op.ed25519verify_bare(
            payload, 
            op.extract(signature.bytes, 0, 64),  
            op.extract(self.oracle_pubkey.value, 0, 32) # Using actual Global State Key
        )
        
        assert is_valid, "REJECTED: Oracle signature invalid or forged!"

        # 3. Check Daily Cap (Local State)
        current_time = Global.latest_timestamp
        one_day      = UInt64(86400)
        limit        = UInt64(5_000_000) # 5 ALGO limit

        if current_time - self.last_reset[Txn.sender] >= one_day:
            self.daily_spent[Txn.sender] = UInt64(0)
            self.last_reset[Txn.sender]  = current_time

        assert self.daily_spent[Txn.sender] + amount <= limit, \
            "REJECTED: Daily 5 ALGO spending limit exceeded!"

        # 4. Check Contract Balance
        assert Global.current_application_address.balance >= amount, \
            "REJECTED: Insufficient contract balance!"

        # 5. Final Execution
        itxn.Payment(
            receiver=recipient,
            amount=amount,
            fee=0 
        ).submit()

        # 6. Update State
        self.daily_spent[Txn.sender] += amount
        
    # ── Read-only Helpers ──────────────────────────────────────────────────
    @arc4.abimethod(readonly=True)
    def get_daily_spent(self) -> UInt64:
        """Returns how much the calling agent has spent today."""
        return self.daily_spent[Txn.sender]

    @arc4.abimethod(readonly=True)
    def get_remaining_limit(self) -> UInt64:
        """Returns remaining daily limit for the calling agent."""
        limit = UInt64(5_000_000)
        spent = self.daily_spent[Txn.sender]
        
        # Explicit return paths so Puya compiler doesn't panic
        if spent >= limit:
            return UInt64(0)
        else:
            return limit - spent
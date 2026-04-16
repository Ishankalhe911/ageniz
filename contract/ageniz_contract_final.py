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
)

class AgenizContract(ARC4Contract):
    def __init__(self) -> None:
        # Global State: Trusted Python ML Oracle's public key
        self.oracle_pubkey = GlobalState(Bytes)

        # Local State: Per-agent daily spending tracker
        self.daily_spent = LocalState(UInt64)
        self.last_reset  = LocalState(UInt64)

    # ── Deploy (called ONCE) ───────────────────────────────────────────────
    @arc4.abimethod(create="require")
    def init(self, oracle_pubkey: Bytes) -> None:
        """Called once at deployment. Locks the Oracle public key permanently."""
        self.oracle_pubkey.value = oracle_pubkey

    # ── Opt-In (Agent must call this first) ────────────────────────────────
    @arc4.abimethod(allow_actions=["OptIn"])
    def opt_in(self) -> None:
        """Agent calls this to initialize its local state (daily cap tracking)."""
        self.daily_spent[Txn.sender] = UInt64(0)
        self.last_reset[Txn.sender]  = Global.latest_timestamp

    # ── Main Payment Gatekeeper (FINAL VERSION) ────────────────────────────
    @arc4.abimethod
    def execute_payment(
        self,
        amount: UInt64,
        recipient: Account,
        signature: Bytes
    ) -> bool:
        """
        FINAL VERSION — full dual-layer security.
        Check 1: Oracle ML signature verification
        Check 2: Daily 5 ALGO spending cap
        Check 3: Contract balance
        """
        # ── Check 1: Oracle Signature ──────────────────────────────────────
        # Reconstructs exact 44-byte payload that signer.py built:
        # Txn.sender.bytes = decode_address(agent_address) → 32 bytes
        # op.itob(amount)  = struct.pack(">Q", amount_micro) → 8 bytes
        # Bytes(b"SAFE")                                    → 4 bytes
        payload = Txn.sender.bytes + op.itob(amount) + Bytes(b"SAFE")

        is_valid = op.ed25519verify(
            payload,
            signature,
            self.oracle_pubkey.value
        )
        assert is_valid, "REJECTED: Oracle signature invalid or forged!"

        # ── Check 2: Daily Cap ─────────────────────────────────────────────
        current_time = Global.latest_timestamp
        one_day      = UInt64(86400)
        limit        = UInt64(5_000_000)

        if current_time - self.last_reset[Txn.sender] >= one_day:
            self.daily_spent[Txn.sender] = UInt64(0)
            self.last_reset[Txn.sender]  = current_time

        assert self.daily_spent[Txn.sender] + amount <= limit, \
            "REJECTED: Daily 5 ALGO spending limit exceeded!"

        # ── Check 3: Balance ───────────────────────────────────────────────
        assert Global.current_application_address.balance >= amount + Global.min_txn_fee, \
            "REJECTED: Insufficient contract balance!"

        # ── Execute Payment ────────────────────────────────────────────────
        itxn.Payment(
            receiver=recipient,
            amount=amount,
            fee=Global.min_txn_fee
        ).submit()

        self.daily_spent[Txn.sender] += amount
        return True

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
        if spent >= limit:
            return UInt64(0)
        return limit - spent
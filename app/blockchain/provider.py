from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.blockchain.payload import MEMO_PROGRAM_ID
from app.blockchain.wallet import load_issuer
from app.config import settings


@dataclass
class AnchorResult:
    provider: str
    cluster: str
    memo: str
    tx_signature: str
    slot: int | None = None
    block_time: datetime | None = None
    explorer_url: str | None = None
    logs: list[str] = field(default_factory=list)


class AnchorProvider(Protocol):
    name: str
    cluster: str

    def anchor(self, memo: str) -> AnchorResult: ...

    def fetch_memo(self, tx_signature: str) -> str | None: ...


class LocalAnchorProvider:
    """In-process Solana (LiteSVM). Real Memo Program execution, no network or SOL.

    State lives only for the lifetime of the process, so verification falls back to the
    memo stored off-chain. Used as the default for development and the demo.
    """

    name = "local"
    cluster = "local"

    def __init__(self, program_id: str = MEMO_PROGRAM_ID) -> None:
        from solders.keypair import Keypair
        from solders.litesvm import LiteSVM

        self._program_id = program_id
        self._issuer = Keypair()
        self._svm = LiteSVM()
        self._svm.airdrop(self._issuer.pubkey(), 100_000_000_000)
        self._memos: dict[str, str] = {}

    def anchor(self, memo: str) -> AnchorResult:
        from solders.instruction import Instruction
        from solders.pubkey import Pubkey
        from solders.transaction import Transaction

        program = Pubkey.from_string(self._program_id)
        instruction = Instruction(program, memo.encode("utf-8"), [])
        blockhash = self._svm.latest_blockhash()
        transaction = Transaction.new_signed_with_payer(
            [instruction], self._issuer.pubkey(), [self._issuer], blockhash
        )
        meta = self._svm.send_transaction(transaction)
        signature = str(meta.signature())
        self._memos[signature] = memo
        return AnchorResult(
            provider=self.name,
            cluster=self.cluster,
            memo=memo,
            tx_signature=signature,
            logs=list(meta.logs()),
        )

    def fetch_memo(self, tx_signature: str) -> str | None:
        return self._memos.get(tx_signature)


class DevnetAnchorProvider:
    """Anchors the memo on a real Solana cluster through an RPC node."""

    name = "solana"

    def __init__(
        self,
        *,
        rpc_url: str | None = None,
        cluster: str | None = None,
        program_id: str | None = None,
        issuer_secret_key: str | None = None,
    ) -> None:
        self.cluster = cluster or settings.solana_cluster
        self._rpc_url = rpc_url or settings.solana_rpc_url
        self._program_id = program_id or settings.solana_memo_program_id
        secret = (
            issuer_secret_key
            if issuer_secret_key is not None
            else settings.solana_issuer_secret_key
        )
        self._issuer = load_issuer(secret)

    def _client(self):  # noqa: ANN202 - solana Client only imported when needed
        from solana.rpc.api import Client

        return Client(self._rpc_url)

    def anchor(self, memo: str) -> AnchorResult:
        from solana.rpc.commitment import Confirmed
        from solana.rpc.models import TxOpts
        from solders.instruction import Instruction
        from solders.pubkey import Pubkey
        from solders.transaction import Transaction

        client = self._client()
        program = Pubkey.from_string(self._program_id)
        instruction = Instruction(program, memo.encode("utf-8"), [])

        response = None
        last_error: Exception | None = None
        for _ in range(3):
            blockhash = client.get_latest_blockhash(commitment=Confirmed).value.blockhash
            transaction = Transaction.new_signed_with_payer(
                [instruction], self._issuer.pubkey(), [self._issuer], blockhash
            )
            try:
                response = client.send_transaction(
                    transaction,
                    opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed),
                )
                break
            except Exception as exc:  # noqa: BLE001 - public RPCs drop stale blockhashes
                last_error = exc
        if response is None:
            raise last_error or RuntimeError("could not send the anchor transaction")
        try:
            client.confirm_transaction(response.value, commitment=Confirmed)
        except Exception:  # noqa: BLE001 - already submitted; verify resolves confirmation later
            pass

        slot: int | None = None
        block_time: datetime | None = None
        try:
            info = client.get_transaction(
                response.value, max_supported_transaction_version=0
            ).value
            if info is not None:
                slot = info.slot
                if info.block_time:
                    block_time = datetime.fromtimestamp(info.block_time, tz=timezone.utc)
        except Exception:  # noqa: BLE001 - confirmation metadata is best-effort
            pass

        signature = str(response.value)
        return AnchorResult(
            provider=self.name,
            cluster=self.cluster,
            memo=memo,
            tx_signature=signature,
            slot=slot,
            block_time=block_time,
            explorer_url=explorer_url(self.cluster, signature),
        )

    def fetch_memo(self, tx_signature: str) -> str | None:
        from solders.signature import Signature

        client = self._client()
        info = client.get_transaction(
            Signature.from_string(tx_signature),
            encoding="base64",
            max_supported_transaction_version=0,
        ).value
        if info is None:
            return None
        return extract_memo(info.transaction.transaction, self._program_id)


def extract_memo(transaction, program_id: str) -> str | None:  # noqa: ANN001 - solders VersionedTransaction
    message = transaction.message
    account_keys = [str(key) for key in message.account_keys]
    for instruction in message.instructions:
        if account_keys[instruction.program_id_index] == program_id:
            try:
                return bytes(instruction.data).decode("utf-8")
            except UnicodeDecodeError:
                return None
    return None


def explorer_url(cluster: str, signature: str | None) -> str | None:
    if not signature or cluster in ("", "local"):
        return None
    suffix = "" if cluster == "mainnet-beta" else f"?cluster={cluster}"
    return f"https://explorer.solana.com/tx/{signature}{suffix}"


def get_anchor_provider() -> AnchorProvider:
    if settings.solana_anchor_provider == "devnet":
        return DevnetAnchorProvider()
    return LocalAnchorProvider()

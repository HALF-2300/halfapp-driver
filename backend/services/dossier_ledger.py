"""Double-entry ledger for the dossier marketplace slice."""
from __future__ import annotations

import json
import uuid
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from schemas.dossier_marketplace import LedgerEntryDraft
from services.datetime_utils import utc_now_naive

SYSTEM_CORPORATE_CASH = "acct_corporate_cash"
SYSTEM_PROCESSING_EXPENSE = "acct_processing_expense"
SYSTEM_PROCESSOR_PAYABLE = "acct_processor_payable"
SYSTEM_PLATFORM_REVENUE = "acct_platform_revenue"


class LedgerBalanceError(ValueError):
    pass


class LedgerSplitError(ValueError):
    pass


def driver_wallet_account_id(driver_id: str) -> str:
    return f"acct_driver_wallet_{driver_id}"


def ensure_driver_wallet_account(db: Session, driver_id: str) -> str:
    account_id = driver_wallet_account_id(driver_id)
    existing = db.execute(
        text("SELECT id FROM ledger_accounts WHERE id = :account_id"),
        {"account_id": account_id},
    ).fetchone()
    if existing:
        return account_id

    db.execute(
        text(
            """
            INSERT INTO ledger_accounts (id, user_id, account_type, normality, label)
            VALUES (:id, :user_id, 'liability', 'CREDIT', :label)
            """
        ),
        {
            "id": account_id,
            "user_id": driver_id,
            "label": f"Driver Wallet ({driver_id})",
        },
    )
    return account_id


def validate_balanced_entries(entries: Iterable[LedgerEntryDraft]) -> tuple[int, int]:
    debits = sum(entry.amount_cents for entry in entries if entry.direction == "DEBIT")
    credits = sum(entry.amount_cents for entry in entries if entry.direction == "CREDIT")
    if debits != credits:
        raise LedgerBalanceError(
            f"Ledger entries do not balance. debits={debits} credits={credits}"
        )
    return debits, credits


def build_trip_payment_entries(
    *,
    driver_id: str,
    fare_cents: int,
    driver_share_cents: int,
    processing_fee_cents: int,
    platform_share_cents: int,
) -> list[LedgerEntryDraft]:
    allocated = driver_share_cents + platform_share_cents + processing_fee_cents
    if allocated != fare_cents:
        raise LedgerSplitError(
            f"Fare split must equal fare_cents. fare={fare_cents} allocated={allocated}"
        )

    entries: list[LedgerEntryDraft] = [
        LedgerEntryDraft(
            account_id=SYSTEM_CORPORATE_CASH,
            amount_cents=fare_cents - processing_fee_cents,
            direction="DEBIT",
        ),
        LedgerEntryDraft(
            account_id=driver_wallet_account_id(driver_id),
            amount_cents=driver_share_cents,
            direction="CREDIT",
        ),
        LedgerEntryDraft(
            account_id=SYSTEM_PLATFORM_REVENUE,
            amount_cents=platform_share_cents,
            direction="CREDIT",
        ),
    ]
    if processing_fee_cents:
        entries.extend(
            [
                LedgerEntryDraft(
                    account_id=SYSTEM_PROCESSING_EXPENSE,
                    amount_cents=processing_fee_cents,
                    direction="DEBIT",
                ),
                LedgerEntryDraft(
                    account_id=SYSTEM_PROCESSOR_PAYABLE,
                    amount_cents=processing_fee_cents,
                    direction="CREDIT",
                ),
            ]
        )
    return entries


def execute_ledger_transaction(
    db: Session,
    *,
    transaction_id: str,
    reference_key: str,
    description: str,
    trip_id: str | None,
    entries: list[LedgerEntryDraft],
) -> str:
    validate_balanced_entries(entries)

    existing = db.execute(
        text("SELECT id FROM ledger_transactions WHERE reference_key = :reference_key"),
        {"reference_key": reference_key},
    ).fetchone()
    if existing:
        return existing[0]

    db.execute(
        text(
            """
            INSERT INTO ledger_transactions (id, reference_key, description, trip_id, created_at)
            VALUES (:id, :reference_key, :description, :trip_id, :created_at)
            """
        ),
        {
            "id": transaction_id,
            "reference_key": reference_key,
            "description": description,
            "trip_id": trip_id,
            "created_at": utc_now_naive(),
        },
    )

    for entry in entries:
        db.execute(
            text(
                """
                INSERT INTO ledger_entries (transaction_id, account_id, amount_cents, direction, created_at)
                VALUES (:transaction_id, :account_id, :amount_cents, :direction, :created_at)
                """
            ),
            {
                "transaction_id": transaction_id,
                "account_id": entry.account_id,
                "amount_cents": entry.amount_cents,
                "direction": entry.direction,
                "created_at": utc_now_naive(),
            },
        )

    return transaction_id


def new_transaction_id() -> str:
    return str(uuid.uuid4())

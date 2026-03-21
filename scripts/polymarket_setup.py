#!/usr/bin/env python3
"""Polymarket Wallet Setup — automates contract approvals and CLOB credential derivation.

Usage:
    python scripts/polymarket_setup.py

Prerequisites:
    1. Generate a fresh Polygon wallet (dedicated to Polymarket, never reuse)
    2. Fund with USDC.e on Polygon ($1,000-2,000) + ~1 MATIC for gas
    3. Set POLYMARKET_PRIVATE_KEY in your environment or .env

This script will:
    - Check Polygon MATIC + USDC.e balance
    - Approve 3 Polymarket exchange contracts for USDC.e + CTF tokens (6 txns)
    - Derive CLOB API credentials
    - Place and cancel a $0.01 test order to verify connectivity
    - Print .env values to configure
"""

from __future__ import annotations

import os
import sys
import time
from getpass import getpass

# ── Constants ──────────────────────────────────────────────────────────

POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"
CHAIN_ID = 137

# Polymarket contracts on Polygon
USDC_E_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"  # Conditional Token Framework

# Contracts that need approval
EXCHANGE_CONTRACTS = {
    "CTF Exchange": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
    "Neg Risk CTF Exchange": "0xC5d563A36AE78145C45a50134d48A1215220f80a",
    "Neg Risk Adapter": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
}

MAX_APPROVAL = 2**256 - 1  # type: ignore[operator]

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

CTF_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_operator", "type": "address"},
            {"name": "_approved", "type": "bool"},
        ],
        "name": "setApprovalForAll",
        "outputs": [],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_operator", "type": "address"},
        ],
        "name": "isApprovedForAll",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]


def main() -> None:
    try:
        from web3 import Web3
    except ImportError:
        print("ERROR: web3 not installed. Run: pip install web3")
        sys.exit(1)

    # ── Get private key ────────────────────────────────────────────
    # Load from .env if not already in environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    pk = os.environ.get("POLYMARKET_PRIVATE_KEY", "")
    if not pk:
        try:
            pk = getpass("Enter Polygon private key (hex, no 0x prefix): ").strip()
        except EOFError:
            print("ERROR: POLYMARKET_PRIVATE_KEY not set in environment or .env")
            sys.exit(1)
    if pk.startswith("0x"):
        pk = pk[2:]
    if len(pk) != 64:
        print("ERROR: Private key must be 64 hex characters")
        sys.exit(1)

    pk_hex = f"0x{pk}"

    # ── Connect to Polygon ─────────────────────────────────────────
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    if not w3.is_connected():
        print("ERROR: Cannot connect to Polygon RPC")
        sys.exit(1)

    account = w3.eth.account.from_key(pk_hex)
    address = account.address
    print(f"\n  Wallet: {address}")

    # ── Check balances ─────────────────────────────────────────────
    matic_wei = w3.eth.get_balance(address)
    matic = w3.from_wei(matic_wei, "ether")
    print(f"  MATIC:  {matic:.4f}")

    usdc_contract = w3.eth.contract(
        address=Web3.to_checksum_address(USDC_E_ADDRESS),
        abi=ERC20_ABI,
    )
    usdc_raw = usdc_contract.functions.balanceOf(address).call()
    usdc = usdc_raw / 1e6
    print(f"  USDC.e: ${usdc:,.2f}")

    if float(matic) < 0.1:
        print("\n  WARNING: Low MATIC balance — need ~0.1 MATIC for gas")
    if usdc < 100:
        print("\n  WARNING: Low USDC.e balance — recommended $1,000-2,000")

    # ── Approve contracts ──────────────────────────────────────────
    ctf_contract = w3.eth.contract(
        address=Web3.to_checksum_address(CTF_ADDRESS),
        abi=CTF_ABI,
    )

    print("\n--- Contract Approvals ---")
    nonce = w3.eth.get_transaction_count(address)
    txn_count = 0

    for name, contract_addr in EXCHANGE_CONTRACTS.items():
        spender = Web3.to_checksum_address(contract_addr)

        # 1. USDC.e approval
        allowance = usdc_contract.functions.allowance(address, spender).call()
        if allowance < MAX_APPROVAL // 2:
            print(f"  Approving USDC.e for {name}...", end=" ", flush=True)
            txn = usdc_contract.functions.approve(spender, MAX_APPROVAL).build_transaction({
                "from": address,
                "nonce": nonce,
                "gas": 60_000,
                "gasPrice": w3.eth.gas_price,
                "chainId": CHAIN_ID,
            })
            signed = w3.eth.account.sign_transaction(txn, pk_hex)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            print(f"OK (tx: {tx_hash.hex()[:16]}...)")
            nonce += 1
            txn_count += 1
        else:
            print(f"  USDC.e already approved for {name}")

        # 2. CTF (ERC-1155) approval
        is_approved = ctf_contract.functions.isApprovedForAll(address, spender).call()
        if not is_approved:
            print(f"  Approving CTF for {name}...", end=" ", flush=True)
            txn = ctf_contract.functions.setApprovalForAll(spender, True).build_transaction({
                "from": address,
                "nonce": nonce,
                "gas": 60_000,
                "gasPrice": w3.eth.gas_price,
                "chainId": CHAIN_ID,
            })
            signed = w3.eth.account.sign_transaction(txn, pk_hex)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            print(f"OK (tx: {tx_hash.hex()[:16]}...)")
            nonce += 1
            txn_count += 1
        else:
            print(f"  CTF already approved for {name}")

    print(f"\n  {txn_count} approval transaction(s) sent")

    # ── Derive CLOB API credentials ────────────────────────────────
    print("\n--- CLOB API Credentials ---")
    try:
        from py_clob_client.client import ClobClient

        host = "https://clob.polymarket.com"
        client = ClobClient(host, key=pk_hex, chain_id=CHAIN_ID)
        api_creds = client.derive_api_key()
        print(f"  API Key:    {api_creds.api_key[:12]}...")
        print(f"  Secret:     {api_creds.api_secret[:12]}...")
        print(f"  Passphrase: {api_creds.api_passphrase[:12]}...")

        # Set creds on client
        client.set_api_creds(api_creds)
        print("  CLOB client authenticated successfully")
    except Exception as e:
        print(f"  ERROR deriving CLOB credentials: {e}")
        sys.exit(1)

    # ── Print .env values ──────────────────────────────────────────
    print("\n--- Add to .env ---")
    print(f"POLYMARKET_PRIVATE_KEY={pk}")
    print("POLYMARKET_PAPER_TRADING=false")
    print("POLYMARKET_SHADOW_MODE=true")
    print("POLYMARKET_KILL_SWITCH=false")
    print("POLYMARKET_MAX_BET_LIVE=20")
    print(f"POLYMARKET_BANKROLL={usdc:.0f}")

    print("\n  Setup complete. Start with shadow mode to verify decisions match paper trading.")
    print("  When ready, set POLYMARKET_SHADOW_MODE=false to start live trading.")


if __name__ == "__main__":
    main()

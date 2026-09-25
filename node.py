import argparse
import threading

import requests
from flask import Flask, jsonify, request

from block import Block
from chain import Blockchain
from transaction import Transaction
from wallet import Wallet

app = Flask(__name__)
blockchain = Blockchain(difficulty=4)
wallet = Wallet()
peers = set()
lock = threading.Lock()

# Converts dictionary to JSON for HTTP compatibility and broadcasts to all peers, times out unresponsive peers
def broadcast(path, payload):
    for peer in list(peers):
        try:
            requests.post(f"{peer}{path}", json=payload, timeout=5)
        except requests.RequestException:
            print(f"Could not reach {peer}")

# Receives chain from all peers and replaces local chain with longest valid chain in network
def resolve_conflicts():
    replaced = False
    for peer in list(peers):
        try:
            response = requests.get(f"{peer}/chain", timeout=5)
            new_chain = [Block.from_dict(peerblock) for peerblock in response.json()["chain"]]
            with lock:
                if blockchain.replace_chain(new_chain):
                    print(f"Switched to the chain from {peer} (more proof of work)")
                    replaced = True
        except (requests.RequestException, KeyError, TypeError, ValueError):
            print(f"Could not get a usable chain from {peer}")
    return replaced

# Accepts transactions from peers
def accept_transaction(tx):
    try:
        with lock:
            blockchain.add_transaction(tx)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    broadcast("/transactions", tx.to_dict())
    return jsonify({"message": "Transaction added to the mempool", "transaction": tx.to_dict()}), 201


# ---------- Transaction Commands ----------

# Accepts transactions from peers and adds them to the memory pool
@app.post("/transactions")
def receive_transaction():
    try:
        tx = Transaction.from_dict(request.get_json())
    except TypeError:
        return jsonify({"error": "Badly formed transaction"}), 400
    return accept_transaction(tx)

# Sends transactions to peers
@app.post("/send")
def send():
    try:
        body = request.get_json()
        tx = Transaction(wallet.address, body["recipient"], body["amount"])
    except (KeyError, TypeError):
        return jsonify({"error": "Send needs a recipient and an amount"}), 400
    tx.sign(wallet)
    return accept_transaction(tx)

# Gets node's local memory pool
@app.get("/transactions/pending")
def pending_transactions():
    with lock:
        return jsonify([tx.to_dict() for tx in blockchain.pending_transactions])


# ---------- Blockchain Commands ----------

# Mines a block
@app.post("/mine")
def mine():
    with lock:
        block = blockchain.mine_pending_transactions(wallet.address)
    broadcast("/blocks", block.to_dict())
    return jsonify({"message": "New block mined", "block": block.to_dict()}), 201

# Receives, checks and adds peer blocks
@app.post("/blocks")
def receive_block():
    try:
        block = Block.from_dict(request.get_json())
        with lock:
            added = blockchain.add_block(block)
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Badly formed block"}), 400

    if added:
        return jsonify({"message": f"Block {block.index} added"}), 201

    replaced = resolve_conflicts()
    return jsonify({"message": "Block did not fit our chain, checked peers", "replaced": replaced})

# Gets node's local chain
@app.get("/chain")
def get_chain():
    with lock:
        return jsonify({
            "length": len(blockchain.chain),
            "work": blockchain.total_work(blockchain.chain),
            "chain": [block.to_dict() for block in blockchain.chain],
        })

# Manually trigger consensus with peers
@app.post("/resolve")
def resolve():
    replaced = resolve_conflicts()
    return jsonify({"replaced": replaced, "length": len(blockchain.chain)})


# ---------- Wallet and Peer Commands ----------

# Gets node's local wallet
@app.get("/wallet")
def my_wallet():
    with lock:
        return jsonify({"address": wallet.address, "balance": blockchain.get_balance(wallet.address)})

# Gets local record of balances for each address in chain
@app.get("/balance/<address>")
def balance(address):
    with lock:
        return jsonify({"address": address, "balance": blockchain.get_balance(address)})

# Adds a peer to the list of peer nodes
@app.post("/peers/register")
def register_peer():
    peers.add(request.get_json()["url"].rstrip("/"))
    return jsonify({"peers": sorted(peers)})

# Gets node's local list of peers
@app.get("/peers")
def list_peers():
    return jsonify(sorted(peers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--peers", nargs="*", default=[])
    args = parser.parse_args()

    my_url = f"http://localhost:{args.port}"
    for peer in args.peers:
        peer = peer.rstrip("/")
        peers.add(peer)
        try:
            requests.post(f"{peer}/peers/register", json={"url": my_url}, timeout=5)
        except requests.RequestException:
            print(f"Could not reach {peer}")

    resolve_conflicts()

    print(f"Node running at {my_url}")
    print(f"Wallet address: {wallet.address}")
    app.run(port=args.port)

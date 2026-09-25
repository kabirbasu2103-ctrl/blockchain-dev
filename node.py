import argparse
import copy
import os
import threading

import requests
from flask import Flask, jsonify, render_template, request

from block import Block
from chain import Blockchain
from transaction import Transaction
from wallet import Wallet

app = Flask(__name__)
blockchain = Blockchain(difficulty=4)
wallet = Wallet()
peers = set()
lock = threading.Lock()


@app.get("/")
def home():
    return render_template("index.html")

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


@app.post("/demo/tamper/<int:block_index>")
def simulate_tampering(block_index):
    with lock:
        test_chain = copy.deepcopy(blockchain.chain)
        difficulty = blockchain.difficulty

    if block_index <= 0 or block_index >= len(test_chain):
        return jsonify({"error": "Choose a mined block after the genesis block."}), 400

    test_chain[block_index].timestamp += 1
    target = "0" * difficulty
    statuses = []
    valid_prefix = True

    for index, block in enumerate(test_chain):
        hash_matches = block.hash == block.calculate_hash()
        link_matches = index == 0 or block.previous_hash == test_chain[index - 1].hash
        proof_of_work_matches = block.hash.startswith(target)
        valid = valid_prefix and hash_matches and link_matches and proof_of_work_matches

        statuses.append({
            "index": block.index,
            "valid": valid,
            "hash_matches": hash_matches,
            "link_matches": link_matches,
            "proof_of_work_matches": proof_of_work_matches,
        })
        valid_prefix = valid

    return jsonify({
        "tampered_block": block_index,
        "simulation_only": True,
        "live_chain_changed": False,
        "blocks": statuses,
    })


@app.post("/demo/overspend")
def simulate_overspending():
    with lock:
        test_blockchain = copy.deepcopy(blockchain)
        address = wallet.address
        confirmed_balance = test_blockchain.get_balance(address)
        pending_outgoing = test_blockchain.get_pending_spending(address)
        available_balance = confirmed_balance - pending_outgoing
        attempted_amount = max(1, available_balance + 1)

        transaction = Transaction(address, "0" * 40, attempted_amount)
        transaction.sign(wallet)

        try:
            test_blockchain.add_transaction(transaction)
        except ValueError as error:
            result = "REJECTED"
            reason = str(error)
        else:
            result = "ACCEPTED"
            reason = "The copied node state accepted an overspending transaction."

    return jsonify({
        "test": "overspend",
        "result": result,
        "confirmed_balance": confirmed_balance,
        "pending_outgoing": pending_outgoing,
        "available_balance": available_balance,
        "attempted_amount": attempted_amount,
        "reason": reason,
        "live_state_changed": False,
    })


@app.post("/demo/tamper-signature")
def simulate_signature_tampering():
    with lock:
        test_blockchain = copy.deepcopy(blockchain)
        address = wallet.address
        signed_amount = 1
        transaction = Transaction(address, "1" * 40, signed_amount)
        transaction.sign(wallet)
        transaction.amount += 1
        attempted_amount = transaction.amount

        try:
            test_blockchain.add_transaction(transaction)
        except ValueError as error:
            result = "REJECTED"
            reason = str(error)
        else:
            result = "ACCEPTED"
            reason = "The copied node state accepted a transaction with a changed amount."

    return jsonify({
        "test": "signature_tampering",
        "result": result,
        "signed_amount": signed_amount,
        "attempted_amount": attempted_amount,
        "reason": reason,
        "live_state_changed": False,
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
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5001")))
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

    print(f"Node listening at http://{args.host}:{args.port}")
    print(f"Wallet address: {wallet.address}")
    app.run(host=args.host, port=args.port, debug=False)

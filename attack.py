import argparse
import logging
import threading

import requests
from flask import Flask, jsonify
from werkzeug.serving import make_server

from block import Block
from transaction import REWARD_SENDER, Transaction
from wallet import Wallet

DIFFICULTY = 4
FAKE_PEER_PORT = 5099

attacker = Wallet()
node = "http://localhost:5001"
fake_chain = []
results = []


# ---------- Helpers ----------

def get_chain():
    response = requests.get(f"{node}/chain", timeout=10)
    return [Block.from_dict(b) for b in response.json()["chain"]]


def balance(address):
    return requests.get(f"{node}/balance/{address}", timeout=10).json()["balance"]


def signed(wallet, recipient, amount):
    tx = Transaction(wallet.address, recipient, amount)
    tx.sign(wallet)
    return tx


def reward(amount=50):
    return Transaction(REWARD_SENDER, attacker.address, amount)


def make_block(transactions, previous=None, mine=True):
    previous = previous or get_chain()[-1]
    block = Block(previous.index + 1, [tx.to_dict() for tx in transactions], previous.hash)
    if mine:
        block.mine(DIFFICULTY)
    return block


def record(name, blocked, response):
    outcome = "BLOCKED" if blocked else "GOT THROUGH"
    results.append((name, outcome))
    print(f"\n{name}\n  -> {outcome} | node replied: {response}")


def attempt_transaction(name, payload):
    if isinstance(payload, Transaction):
        payload = payload.to_dict()
    response = requests.post(f"{node}/transactions", json=payload, timeout=10)
    record(name, response.status_code == 400, response.json())


def attempt_block(name, block):
    length_before = len(get_chain())
    response = requests.post(f"{node}/blocks", json=block.to_dict(), timeout=60)
    record(name, len(get_chain()) == length_before, response.json())


def start_fake_peer():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = Flask("fake_peer")

    @app.get("/chain")
    def chain():
        return jsonify({"chain": [block.to_dict() for block in fake_chain]})

    server = make_server("localhost", FAKE_PEER_PORT, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    requests.post(f"{node}/peers/register", json={"url": f"http://localhost:{FAKE_PEER_PORT}"}, timeout=10)
    return server


# ---------- Setup: give the attacker some real coins ----------

def setup():
    victim = requests.get(f"{node}/wallet", timeout=10).json()["address"]
    requests.post(f"{node}/mine", timeout=60)
    requests.post(f"{node}/send", json={"recipient": attacker.address, "amount": 20}, timeout=10)
    requests.post(f"{node}/mine", timeout=60)
    print(f"Victim (the node's wallet): {victim[:12]}... balance {balance(victim)}")
    print(f"Attacker:                   {attacker.address[:12]}... balance {balance(attacker.address)}")
    return victim


# ---------- Transaction attacks (POST /transactions) ----------

def transaction_attacks(victim):
    print("\n========== TRANSACTION ATTACKS ==========")

    forged = Transaction(victim, attacker.address, 30)
    forged.sender_public_key = attacker.public_key_hex
    forged.signature = attacker.sign(forged.signing_message())
    attempt_transaction("1. Steal: spend the victim's coins, signed with the attacker's key", forged)

    requests.post(f"{node}/send", json={"recipient": Wallet().address, "amount": 5}, timeout=10)
    intercepted = requests.get(f"{node}/transactions/pending", timeout=10).json()[-1]
    intercepted["recipient"] = attacker.address
    attempt_transaction("2. Intercept: redirect the victim's genuine payment to the attacker", intercepted)

    attempt_transaction("3. Overspend: attacker sends 1000 (has 20)", signed(attacker, victim, 1000))

    requests.post(f"{node}/transactions", json=signed(attacker, Wallet().address, 15).to_dict(), timeout=10)
    attempt_transaction(
        "4. Double-spend: attacker sends 15 twice (the first was accepted)",
        signed(attacker, Wallet().address, 15),
    )

    old_payment = next(
        tx for block in get_chain() for tx in block.data
        if tx["sender"] == victim and tx["recipient"] == attacker.address
    )
    attempt_transaction("5. Replay: resubmit the victim's old payment to the attacker", old_payment)

    attempt_transaction("6. Fake reward: submit a 1000-coin mining reward", reward(1000))

    attempt_transaction("7. Negative amount: attacker 'sends' -100 to take coins", signed(attacker, victim, -100))

    attempt_transaction("8. Garbage: a transaction with missing fields", {"sender": "nobody"})

    return forged, old_payment


# ---------- Block attacks (POST /blocks) ----------

def block_attacks(victim, forged, old_payment):
    print("\n========== BLOCK ATTACKS (each takes a moment to mine) ==========")

    attempt_block("9. Skip proof-of-work: send an unmined block", make_block([reward()], mine=False))

    block = make_block([reward()])
    block.data[0]["amount"] = 1000
    attempt_block("10. Edit after mining: raise the reward to 1000, keep the old hash", block)

    attempt_block("11. Greedy miner: properly mine a block with a 1000 reward", make_block([reward(1000)]))

    attempt_block("12. No reward: a block with no transactions at all", make_block([]))

    attempt_block("13. Two rewards: sneak a second reward into the block", make_block([reward(), reward()]))

    attempt_block("14. Theft inside a block: include the forged transaction", make_block([reward(), forged]))

    attempt_block(
        "15. Overspend inside a block: attacker pays 1000",
        make_block([reward(), signed(attacker, victim, 1000)]),
    )

    attempt_block(
        "16. Replay inside a block: include an already-mined payment",
        make_block([reward(), Transaction.from_dict(old_payment)]),
    )

    fake_parent = Block(0, [], "0")
    fake_parent.hash = "0" * 64
    attempt_block("17. Broken link: a block that points to a block that doesn't exist",
                  make_block([reward()], previous=fake_parent))


# ---------- Chain attacks (a fake peer offers a longer chain) ----------

def rewrite_history_attack(victim):
    print("\n========== CHAIN ATTACK: REWRITE HISTORY ==========")
    chain = get_chain()

    position = None
    for i, block in enumerate(chain):
        for tx in block.data:
            if tx["sender"] == victim and tx["recipient"] == attacker.address:
                tx["amount"] = 2000
                position = i

    for i in range(position, len(chain)):
        chain[i].previous_hash = chain[i - 1].hash
        chain[i].mine(DIFFICULTY)

    for _ in range(2):
        chain.append(make_block([reward()], previous=chain[-1]))

    fake_chain[:] = chain
    response = requests.post(f"{node}/resolve", timeout=120).json()
    record("18. Rewrite history: change 20 to 2000, re-mine everything after, make it longer",
           not response["replaced"], response)


def majority_attack(victim):
    print("\n========== CHAIN ATTACK: 51% (out-mine the network) ==========")
    print(f"Before: victim {balance(victim)}, attacker {balance(attacker.address)}")

    honest_length = len(get_chain())
    chain = get_chain()[:1]
    while len(chain) <= honest_length:
        chain.append(make_block([reward()], previous=chain[-1]))

    fake_chain[:] = chain
    response = requests.post(f"{node}/resolve", timeout=120).json()
    record("19. 51% attack: a valid chain from genesis with more proof of work",
           not response["replaced"], response)
    print(f"After:  victim {balance(victim)}, attacker {balance(attacker.address)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate attacks against a running node")
    parser.add_argument("--node", default="http://localhost:5001")
    parser.add_argument("--majority", action="store_true",
                        help="also run a 51%% attack (this WILL rewrite the node's chain)")
    args = parser.parse_args()
    node = args.node.rstrip("/")

    victim = setup()
    forged, old_payment = transaction_attacks(victim)
    block_attacks(victim, forged, old_payment)

    server = start_fake_peer()
    rewrite_history_attack(victim)
    if args.majority:
        majority_attack(victim)
    server.shutdown()

    print("\n========== SUMMARY ==========")
    for name, outcome in results:
        print(f"{outcome:12} {name}")

# Week 1 Blockchain Mechanics Demo

[Open the live demo](https://blockchain-dev.onrender.com/) · [View the GitHub repository](https://github.com/kabirbasu2103-ctrl/blockchain-dev)

This project is a small Python blockchain built to explore the mechanics behind blocks, proof of work, signed transactions, and chain validation. It includes a browser dashboard so the main ideas can be demonstrated without installing anything.

The project is a toy model of blockchain mechanics.

## What the demo shows

- Blocks store transactions and link to the previous block by hash.
- Proof of work uses a configurable difficulty.
- Wallets sign transactions with ECDSA on the secp256k1 curve.
- A transaction pool checks signatures, duplicate transactions, and available balances before accepting transactions.
- Mining puts pending transactions into a block and awards the node's wallet a fixed learning reward.
- Chain validation detects changes to mined blocks and invalid links to later blocks.
- A browser dashboard lets visitors inspect the chain, submit transactions, mine blocks, and try isolated validation and tampering demonstrations.
- Two locally running nodes can register as peers and exchange transactions and chain data.

## Try the live demo

Open the [deployed website](https://blockchain-dev.onrender.com/) and use the dashboard to inspect the wallet, submit a transaction, mine a block, and review the chain. The page also includes demonstrations for overspending, changing a signed transaction, and tampering with a mined block.

The hosted demo uses one server-side wallet shared by visitors. It does not create a separate wallet for each visitor. Its chain, wallet, and pending transactions are held in memory, so the state may be reset when the service restarts. Treat the live site as a shared, disposable learning demo.

## Run locally

From the project folder, create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start a node:

```bash
python node.py --port 5001
```

Open [http://localhost:5001/](http://localhost:5001/) in a browser.

## Run two local nodes

Open two terminals in the project folder. Activate the virtual environment in each terminal.

Terminal 1:

```bash
python node.py --port 5001
```

Terminal 2:

```bash
python node.py --port 5002 --peers http://localhost:5001
```

Open [http://localhost:5001/](http://localhost:5001/) and [http://localhost:5002/](http://localhost:5002/) in separate browser tabs. The second node registers with the first node when it starts.

## Suggested demo walkthrough

1. On node 1, mine a block to give its wallet the 50-coin mining reward.
2. On node 2, open **Open wallet data** and copy its wallet address.
3. On node 1, send 10 coins to node 2. The signed transaction should appear in the pending transaction lists.
4. Mine a block on node 1. Refresh both dashboards and inspect the updated balances.
5. Try an overspending transaction and observe that it is rejected.
6. Change the amount of a signed transaction in the tampering demonstration and observe that signature validation rejects it.
7. Simulate changing a mined block and observe that the displayed chain copy becomes invalid. The demonstration uses a copy, so it does not damage the live chain.

## API quick reference

Replace `5001` with the port used by the node.

| Action | Request |
| --- | --- |
| Mine a block | `POST /mine` |
| Send a transaction | `POST /send` with JSON `{"recipient":"ADDRESS","amount":10}` |
| View pending transactions | `GET /transactions/pending` |
| View wallet and confirmed balance | `GET /wallet` |
| View the chain | `GET /chain` |
| Simulate an overspending transaction | `POST /demo/overspend` |
| Simulate changing a signed transaction | `POST /demo/tamper-signature` |
| Simulate editing a mined block | `POST /demo/tamper/1` |
| Check configured peers | `GET /peers` |
| Try chain conflict resolution | `POST /resolve` |

For example, the local mining endpoint is `http://localhost:5001/mine`.

## Deployment

The public demo is hosted on Render. The Flask application object is named `app` in `node.py`, and the included `Procfile` starts it with Gunicorn. The equivalent start command is:

```bash
gunicorn --workers 1 --bind "0.0.0.0:${PORT:-8000}" node:app
```

Use one worker because the chain, wallet, and transaction pool are stored in process memory. Multiple worker processes would each have separate in-memory state.


## Learning takeaway

The demo helps explain how a transaction is signed, how proof of work adds a block, and why changing an older block causes its hash links to stop matching. It is a first step toward understanding blockchain systems; later work can compare these mechanics with Ethereum accounts, gas, and smart-contract execution.

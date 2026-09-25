# Week 1 Blockchain Mechanics Demo

[Open the live demo](https://blockchain-dev.onrender.com/) · [View the GitHub repository](https://github.com/kabirbasu2103-ctrl/blockchain-dev)

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

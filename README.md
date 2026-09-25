DESC:
This is a simple layer 1 blockchain demo allowing users to locally run multiple nodes with their own wallets.
Nothing is saved, a node currently loses its wallet when it is shut down.
Data is transferred between nodes as JSON through HTTP.
Networking across multiple devices is not yet supported (can add that later, maybe using a private network, but will have to change much of node.py). Mainly Mac-compatible right now.

Run node.py to launch node at port 5001

Run in new terminal. For each NUM, use 5001...5099 for Mac

CREATE NODE: python3 node.py --port NUM --peers http://localhost:NUM

MINE BLOCK: curl -X POST http://localhost:NUM/mine

ADD TRANSACTION: curl -X POST http://localhost:NUM/send -H "Content-Type: application/json" -d '{"recipient": "ADDRESS", "amount": <NUM>}'

VIEW BALANCE: curl http://localhost:NUM/wallet

VIEW CHAIN: curl http://localhost:NUM/chain

MANUALLY RESOLVE CONFLICT: curl http://localhost:NUM/resolve

VIEW PEERS: curl http://localhost:NUM/peers

REGISTER PEERS: curl http://localhost:NUM/peers/register/<peeraddress>

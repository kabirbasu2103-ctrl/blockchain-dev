from block import Block
from transaction import REWARD_SENDER, Transaction

# Too much? But fractions are unsupported because of truncation errors with floating point values
MINING_REWARD = 50

# Blockchain class is defined as a list of block objects
class Blockchain:
    def __init__(self, difficulty=4):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []

# First block in chain - index 0, no data, previous hash 0, timestamp 0
    def create_genesis_block(self):
        genesis = Block(0, [], "0", timestamp=0)
        genesis.mine(self.difficulty)
        return genesis

    def get_latest_block(self):
        return self.chain[-1]

# Balance of each node's wallet is calculated dynamically by iterating through the chain instead of storing in a centralised database
    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block.data:
                if tx["recipient"] == address:
                    balance += tx["amount"]
                if tx["sender"] == address:
                    balance -= tx["amount"]
        return balance

# Pending transactions in memory pool are summed to prevent double spending before blocks containing those transactions are mined
    def get_pending_spending(self, address):
        return sum(tx.amount for tx in self.pending_transactions if tx.sender == address)

# Prevents duplicate transactions being added to memory pool since valid signatures can be duplicated for transactions with the same timestamp, amount, sender and recipient
    def contains_transaction(self, transaction):
        message = transaction.signing_message()

        for tx in self.pending_transactions:
            if tx.signing_message() == message:
                return True

        for block in self.chain:
            for tx_data in block.data:
                if Transaction.from_dict(tx_data).signing_message() == message:
                    return True

        return False

# Transaction validation process prevents miners adding reward transactions from the network, unsigned transactions, negative values, duplicate transactions, or transactions with amounts greater than funds in wallet
    def add_transaction(self, transaction):
        if transaction.sender == REWARD_SENDER:
            raise ValueError("Mining rewards can only be created by mining a block")

        if not transaction.is_valid():
            raise ValueError("Transaction is invalid (bad signature or amount)")

        if self.contains_transaction(transaction):
            raise ValueError("Transaction has already been submitted")

        available = self.get_balance(transaction.sender) - self.get_pending_spending(transaction.sender)
        if transaction.amount > available:
            raise ValueError(f"Insufficient funds: {available} available, tried to send {transaction.amount}")

        self.pending_transactions.append(transaction)

# Mining function – collects transactions from memory pool and starts the mining process for a new block containing them
    def mine_pending_transactions(self, miner_address):
        reward = Transaction(REWARD_SENDER, miner_address, MINING_REWARD)
        transactions = [reward] + self.pending_transactions

        previous_block = self.get_latest_block()
        new_block = Block(
            previous_block.index + 1,
            [tx.to_dict() for tx in transactions],
            previous_block.hash,
        )
        new_block.mine(self.difficulty)

    # The new block mined is only appended to the user's local copy of the chain and needs to be broadcasted to other nodes
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

# Add block method allows nodes to add blocks mined by other nodes to their local copy of the chain. Verification is in-built.
    def add_block(self, block):
        if block.previous_hash != self.get_latest_block().hash:
            print(f"Block {block.index}: previous hash does not match latest block")
            return False

        if not self.is_valid_chain(self.chain + [block]):
            print(f"Block {block.index}: is not valid")
            return False

        self.chain.append(block)
        self.refresh_pending_transactions()
        return True

# Allows nodes to calculate the proof of work for different chains and switch to the one with the most work
    def total_work(self, chain):
        return len(chain) * 16 ** self.difficulty

# Allows nodes to replace local chain copy with the longest valid chain in the network
    def replace_chain(self, new_chain):
        if self.total_work(new_chain) <= self.total_work(self.chain):
            print("New chain is not longer than the current chain")
            return False

        if not self.is_valid_chain(new_chain):
            print("New chain is not valid")
            return False

    # Creates list of transactions that are no longer in the longest valid chain, and adds them back to the memory pool
        orphaned = []
        for block in self.chain[1:]:
            for tx_data in block.data[1:]:
                orphaned.append(Transaction.from_dict(tx_data))

        self.chain = new_chain
        self.refresh_pending_transactions(orphaned)
        return True

# Refreshes memory pool of pending transactions
    def refresh_pending_transactions(self, extra=()):
        candidates = list(extra) + self.pending_transactions
        self.pending_transactions = []
        for tx in candidates:
            try:
                self.add_transaction(tx)
            except ValueError:
                pass

# Shortcut to check if the local chain is valid (I defined and used this everywhere before adding network functionality XD)
    def is_valid(self):
        return self.is_valid_chain(self.chain)

# Chain validity checker
    def is_valid_chain(self, chain):
        target = "0" * self.difficulty
        balances = {}
        seen = set()

    # 0th block is the genesis block, should be same for all nodes to ensure consensus
        if chain[0].to_dict() != self.chain[0].to_dict():
            print("Chain starts from a different genesis block")
            return False

        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

        # Check if block hash is valid for all blocks in chain
            if current.hash != current.calculate_hash():
                print(f"Block {current.index}: contents were changed after mining")
                return False

        # Check if the hash chain is valid for all blocks in chain
            if current.previous_hash != previous.hash or current.index != previous.index + 1:
                print(f"Block {current.index}: link to block {previous.index} is broken")
                return False

        # Check if the hash matches the difficulty test for all blocks in chain
            if not current.hash.startswith(target):
                print(f"Block {current.index}: was never properly mined")
                return False

        # Check if transactions within block are valid for all blocks in chain
            if not self.has_valid_transactions(current, balances, seen):
                return False

        return True

# Transaction validity checker - checks whether transactions are present, valid signatures, duplicate transactions, and overspending. Balances are updated as transactions are verified to prevent double spending.
    def has_valid_transactions(self, block, balances, seen):
        transactions = [Transaction.from_dict(tx) for tx in block.data]

    # No transactions in block - no reward :(
        if not transactions:
            print(f"Block {block.index}: has no mining reward")
            return False

        reward = transactions[0]
        payments = transactions[1:]

    # Validates reward transaction and updates miner balance
        if reward.sender != REWARD_SENDER or reward.amount != MINING_REWARD or not reward.is_valid():
            print(f"Block {block.index}: mining reward is missing or wrong")
            return False
        balances[reward.recipient] = balances.get(reward.recipient, 0) + reward.amount

    # Checks validity of all transactions in a block and updates wallet balances
        for tx in payments:
            if tx.sender == REWARD_SENDER or not tx.is_valid():
                print(f"Block {block.index}: contains an invalid transaction")
                return False

            message = tx.signing_message()
            if message in seen:
                print(f"Block {block.index}: contains a duplicate transaction")
                return False
            seen.add(message)

            if balances.get(tx.sender, 0) < tx.amount:
                print(f"Block {block.index}: {tx.sender[:8]}... spent more than they had")
                return False
            balances[tx.sender] -= tx.amount
            balances[tx.recipient] = balances.get(tx.recipient, 0) + tx.amount

        return True

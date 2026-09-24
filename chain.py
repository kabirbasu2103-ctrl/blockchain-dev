from block import Block
from transaction import REWARD_SENDER, Transaction

MINING_REWARD = 50


class Blockchain:
    def __init__(self, difficulty=4):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []

    def create_genesis_block(self):
        genesis = Block(0, [], "0")
        genesis.mine(self.difficulty)
        return genesis

    def get_latest_block(self):
        return self.chain[-1]

    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block.data:
                if tx["recipient"] == address:
                    balance += tx["amount"]
                if tx["sender"] == address:
                    balance -= tx["amount"]
        return balance

    def get_pending_spending(self, address):
        return sum(tx.amount for tx in self.pending_transactions if tx.sender == address)

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

        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def is_valid(self):
        target = "0" * self.difficulty
        balances = {}
        seen = set()

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                print(f"Block {current.index}: contents were changed after mining")
                return False

            if current.previous_hash != previous.hash:
                print(f"Block {current.index}: link to block {previous.index} is broken")
                return False

            if not current.hash.startswith(target):
                print(f"Block {current.index}: was never properly mined")
                return False

            if not self.has_valid_transactions(current, balances, seen):
                return False

        return True

    def has_valid_transactions(self, block, balances, seen):
        transactions = [Transaction.from_dict(tx) for tx in block.data]

        if not transactions:
            print(f"Block {block.index}: has no mining reward")
            return False

        reward = transactions[0]
        payments = transactions[1:]

        if reward.sender != REWARD_SENDER or reward.amount != MINING_REWARD or not reward.is_valid():
            print(f"Block {block.index}: mining reward is missing or wrong")
            return False
        balances[reward.recipient] = balances.get(reward.recipient, 0) + reward.amount

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

import hashlib
import json
import time

# Block class represents a single block in the blockchain with attributes for index within the chain, transaction data, previous hash, timestamp and nonce for miner to generate a valid hash.
class Block:
    def __init__(self, index, data, previous_hash, timestamp=None, nonce=0):
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

# Hash calculation method is defined to generate a SHA-256 hash of the block's contents
    def calculate_hash(self):
        block_contents = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        block_string = json.dumps(block_contents, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

# Mine method allows nodes within the system to run through nonce values and bruteforce a hash satisfying the difficulty specification
    def mine(self, difficulty):
        target = "0" * difficulty
        self.hash = self.calculate_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

# This method converts the block object attributes into a dictionary for compatibility with JSON serialization to transmit data between nodes
    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

# This method lets nodes recreate blocks from dictionaries, so that data received as JSON can be converted back into blocks for verificaiton in the chain
    @classmethod
    def from_dict(cls, data):
        block = cls(data["index"], data["data"], data["previous_hash"], data["timestamp"], data["nonce"])
        block.hash = data["hash"]
        return block

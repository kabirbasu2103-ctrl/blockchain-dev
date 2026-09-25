import json
import time

from wallet import public_key_to_address, verify_signature

# Rewards for mining are awarded by a sender called "NETWORK" - prevents miners from creating their own rewards
REWARD_SENDER = "NETWORK"

# Transaction class is strictly defined with sender, recipient, amount, timestamp, public-private key pair and timestamp)
class Transaction:
    def __init__(self, sender, recipient, amount, timestamp=None, sender_public_key=None, signature=None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.sender_public_key = sender_public_key
        self.signature = signature

# Signing message method converts transaction attributes into JSON compatible dictionary to transmit data between nodes
    def signing_message(self):
        contents = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "sender_public_key": self.sender_public_key,
        }
        return json.dumps(contents, sort_keys=True)

# Sign function allows nodes to sign transactions with their wallet's private key
    def sign(self, wallet):
        if wallet.address != self.sender:
            raise ValueError("You can only sign transactions sent from your own wallet")
        self.sender_public_key = wallet.public_key_hex
        self.signature = wallet.sign(self.signing_message())

# Transaction validation checks for +ve integer amounts, skips over reward transactions, prevents wallets from adding transactions without their own public keys/signatures
    def is_valid(self):
        if not isinstance(self.amount, int) or self.amount <= 0:
            return False

        if self.sender == REWARD_SENDER:
            return True

        if not self.signature or not self.sender_public_key:
            return False

        if public_key_to_address(self.sender_public_key) != self.sender:
            return False

        return verify_signature(self.sender_public_key, self.signing_message(), self.signature)

# Converts transaction object attributes into a dictionary for compatibility with JSON serialization to transmit data between nodes
    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "sender_public_key": self.sender_public_key,
            "signature": self.signature,
        }

# Lets nodes recreate transactions from dictionaries to verify transactions received and update balances
    @classmethod
    def from_dict(cls, data):
        return cls(**data)

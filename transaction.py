import json
import time

from wallet import public_key_to_address, verify_signature

REWARD_SENDER = "NETWORK"


class Transaction:
    def __init__(self, sender, recipient, amount, timestamp=None, sender_public_key=None, signature=None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.sender_public_key = sender_public_key
        self.signature = signature

    def signing_message(self):
        contents = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "sender_public_key": self.sender_public_key,
        }
        return json.dumps(contents, sort_keys=True)

    def sign(self, wallet):
        if wallet.address != self.sender:
            raise ValueError("You can only sign transactions sent from your own wallet")
        self.sender_public_key = wallet.public_key_hex
        self.signature = wallet.sign(self.signing_message())

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

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "sender_public_key": self.sender_public_key,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

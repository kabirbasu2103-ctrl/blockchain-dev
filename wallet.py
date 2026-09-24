import hashlib

from ecdsa import SECP256k1, BadSignatureError, SigningKey, VerifyingKey
from ecdsa.errors import MalformedPointError


def public_key_to_address(public_key_hex):
    public_key_bytes = bytes.fromhex(public_key_hex)
    return hashlib.sha256(public_key_bytes).hexdigest()[:40]


def verify_signature(public_key_hex, message, signature_hex):
    try:
        verifying_key = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
        return verifying_key.verify(
            bytes.fromhex(signature_hex), message.encode(), hashfunc=hashlib.sha256
        )
    except (BadSignatureError, MalformedPointError, ValueError):
        return False


class Wallet:
    def __init__(self, private_key_hex=None):
        if private_key_hex:
            self.private_key = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
        else:
            self.private_key = SigningKey.generate(curve=SECP256k1)

        self.public_key_hex = self.private_key.get_verifying_key().to_string().hex()
        self.address = public_key_to_address(self.public_key_hex)

    def sign(self, message):
        signature = self.private_key.sign(message.encode(), hashfunc=hashlib.sha256)
        return signature.hex()

    def export_private_key(self):
        return self.private_key.to_string().hex()

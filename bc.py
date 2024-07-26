from nacl.signing import VerifyKey
from base64 import b64decode
from hashlib import sha512, sha1
from json import dumps

sha  = lambda d: sha512(d.encode()).hexdigest()
dsha = lambda d:   sha1(d.encode()).hexdigest()

import time

class ValidationError(Exception):
    pass

class Block:
    def __init__(self, timestamp: int, signature: str, **kw):
        self.ts = timestamp
        self.data = kw
        self.signature = signature # Signature of block
        self.prev = "0"
        self.nonce = -1
        self.difficulty = 0
        self.generator_verify_key = ""
        self.hash = self.get_hash()

    def get_hash(self):
        return sha(self.get_data_hash() + str(self.nonce) + self.signature)
    
    def get_data_hash(self):
        return dsha(self.prev + str(self.ts) + dumps(self.data) + str(self.difficulty))
    
    def mine(self, difficulty):
        self.nonce = 0
        target = '0' * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.get_hash()
        self.difficulty = difficulty

    def validate(self) -> bool:
        # just validate block

        verify = VerifyKey(b64decode(self.generator_verify_key))

        # Validate PoW
        if self.hash != self.get_hash():
            return False

        if not self.hash.startswith("0" * self.difficulty):
            return False

        # Lets check the signature!
        try:
            verify.verify(self.get_data_hash().encode(), b64decode(self.signature))
        except:
            return False # Looks signature of block is not valid.
        
        # TODO: Check signature of transaction (info in data)

        return True
    
    def encode(self) -> dict:
        return {
            "ts": self.ts,
            "data": self.data,
            "signature": self.signature,
            "prev": self.prev,
            "nonce": self.nonce,
            "hash": self.hash,
            "diff": self.difficulty
        }
    
    @staticmethod
    def fromdict(dictionary: dict):
        b = Block()
        b.ts = dictionary['ts']
        b.data = dictionary['data']
        b.signature = dictionary['signature']
        b.prev = dictionary['prev']
        b.nonce = dictionary['nonce']
        b.hash = dictionary['hash']
        b.difficulty = dictionary['diff']
        return b

class Blockchain:
    def __init__(self, create_genesis = True) -> None:
        self.diff = 1
        self.block_time = 30
        self.chain = []
        self.static = False
        if create_genesis:
            self.chain.append(Block(int(time.time()), ""))

    def get_last(self) -> Block:
        return self.chain[-1]
    
    def add_block(self, block: Block):
        block.prev = self.get_last().hash

        block.hash = block.get_hash()

        if block.nonce == -1:
            block.mine(self.diff)

        if not block.validate():
            raise ValidationError("Block is not really valid")

        self.chain.append(block)

        if not self.static: self.diff += 0 if self.diff == 0 else ( 1 if int(time.time()) - block.ts < self.block_time else -1 ) 
    
    def encode(self):
        return {
            "diff": self.diff,
            "block_time": self.block_time,
            "chain": map(lambda a: a.encode(), self.chain)
        }
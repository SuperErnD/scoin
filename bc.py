from hashlib import sha512, sha1
from json import dumps

sha  = lambda d: sha512(d.encode()).hexdigest()
dsha = lambda d:   sha1(d.encode()).hexdigest()

import time

class Block:
    def __init__(self, timestamp: int, **kw):
        self.ts = timestamp
        self.data = kw
        self.prev = "0"
        self.nonce = -1
        self.hash = self.get_hash()
        

    def get_hash(self):
        return sha(self.get_data_hash() + str(self.nonce))
    
    def get_data_hash(self):
        return dsha(self.prev + str(self.ts) + dumps(self.data))
    
    def mine(self, difficulty):
        self.nonce = 0
        target = '0' * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.get_hash()
            time.sleep(0.01)

    
class Blockchain:
    def __init__(self, create_genesis = True) -> None:
        self.diff = 1
        self.block_time = 30
        self.chain = []
        self.static = False
        if create_genesis:
            self.chain.append(Block(int(time.time())))

    def get_last(self) -> Block:
        return self.chain[-1]
    
    def add_block(self, block: Block):
        block.prev = self.get_last().hash

        block.hash = block.get_hash()

        if block.nonce == -1:
            block.mine(self.diff)

        self.chain.append(block)

        if not self.static: self.diff += 0 if self.diff == 0 else ( 1 if int(time.time()) - block.ts < self.block_time else -1 ) 
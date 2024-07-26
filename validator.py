import json
import base64
import asyncio
from websockets.server import serve
from nacl.signing import SigningKey, VerifyKey
import struct
from nacl.public import PrivateKey, PublicKey, Box
from jsonrpcserver import method, Success, Error, Result, async_dispatch
from saver_pickle import Saver
from bc import Block, Blockchain
import time
import enum
import hashlib
import socket
import threading
import random

class Packets(enum.Enum):
    HELLO = 0x00
    NEW_BLOCK = 0x01
    APPROVE_BLOCK = 0x02
    DENY_BLOCK = 0x03
    ADD_BLOCKCHAIN = 0x04

class State(enum.Enum):
    CONNECTING = 1
    INIT_CONNECT = 2 # Like HELLO packets, etc.
    CONNECTED = 3 # A valid validator! He can verify our blocks too!
    DISCONNECTED = 4

class Node:
    async def send(self, data):
        await self.loop.sock_sendall(self.sock, self._box.encrypt(data))
    loop: asyncio.AbstractEventLoop = None
    sock: socket.socket = None
    address: str = None
    verify_key: VerifyKey = None # key lol
    state: State = State.INIT_CONNECT
    _box: Box = None

# Try to load keys.. (without them we are никто and we cant sign anything)
def load_file(file: str) -> str:
    with open(file, "r") as f:
        return f.read()
    
_keys = json.loads(load_file("wallet.json"))
_sign_key = _keys['a']
_verify_key = _keys['b']

# Ok, we have keys, create constructors
sign_key = SigningKey(base64.b64decode(_sign_key))
verify_key = VerifyKey(base64.b64decode(_verify_key))
private_key = PrivateKey.generate()
public_key = private_key.public_key
addr = _keys['c']

# load blockchain

s = Saver()
s.init()
bc = None
try:
    bc = s.load()
except Exception as e:
    print(e)
    bc = Blockchain()

validators: dict[str, Node] = {}
pk_cache = {}

# Methods

@method
async def new_transaction(context, to="0x0", amount=0, signature=""):
    data = {"sender":context['address'], "receiver":to, "amount":amount}
    # first of all check signature
    if context['verify'] == None or context['address'] == None:
        return Error("not loggined")

    try: context['verify'].verify(json.dumps(data),base64.b64decode(signature))
    except: return Error("Signature is not valid")

    if not len(validators):
        # seems im alone :c, well i'll generate block and verify it
        block = Block(int(time.time()), signature, type="transaction", data=data, signature=signature)

        bc.add_block(block) # Blockchain class will automatically mine it if not already mined and verify it
    else:
        block = Block(int(time.time()), signature, type="transaction", data=data, signature=signature)
        for addr, node in validators:
            await node.send(encode_new_block(block))
        pass # TODO
    return Success("ok") # maybe, in progress it'll be

@method 
async def request_blockchain(context):
    return Success(blockchain=json.dumps(bc.encode()), hash=hashlib.sha1(json.dumps(bc.encode())).hexdigest())

@method
async def validator_connect(context, ip, port, pk):
    # Maybe after that it should dis~~~~ connect
    pk_cache[(ip,port)] = PublicKey(base64.b64decode(pk))
    return Success(
        pk = base64.b64encode(public_key.encode()).decode(),
        ip = socket.gethostbyname(socket.gethostname()),
        port = 10248
    )
    
@method
async def me(context, verify_key="", addr=""):
    if '0x' + hashlib.sha256(base64.b64decode(verify_key)).hexdigest() != addr:
        return Error("Looks like your address is not valid!")
    
    context['verify'] = VerifyKey(base64.b64decode(verify_key))
    context['address'] = addr

    return Success("ok")

# Now start the server

async def handler(websocket):
    print("Oh hello, new client!")
    state = {
        "verify": None,
        "address": None
    }
    while True:
        if response := await async_dispatch(await websocket.recv(), context=state):
            await websocket.send(response)

def encode_hello(addr, verify):
    verify_encoded = base64.b64encode(verify.encode()).decode()
    prepared_data = json.dumps({
        "wallet_address": addr,
        "verify_key": verify_encoded
    })
    # 3 + len(prepared_data) is length (type + prepared_data_len + prepared_data)
    length = 3 + len(prepared_data)
    base = struct.pack("!HBH", length, Packets.HELLO.value, len(prepared_data))
    base += prepared_data.encode("ascii")

    return base

def encode_new_block(block: Block):
    prepared_data = json.dumps({
        "block": block.encode()
    })
    # 3 + len(prepared_data) is length (type + prepared_data_len + prepared_data)
    length = 3 + len(prepared_data)
    base = struct.pack("!HBH", length, Packets.NEW_BLOCK.value, len(prepared_data))
    base += prepared_data.encode("ascii")

    return base

def encode_deny(block: Block):
    ts = int(time.time())
    prepared_data = json.dumps({
        "signature": base64.b64encode(sign_key.sign(json.dumps(['deny', block.hash, ts]).encode())),
        "of": block.hash,
        "timestamp": ts
    })
    # 3 + len(prepared_data) is length (type + prepared_data_len + prepared_data)
    length = 3 + len(prepared_data)
    base = struct.pack("!HBH", length, Packets.DENY_BLOCK.value, len(prepared_data))
    base += prepared_data.encode("ascii")

    return base

def encode_approve(block: Block):
    ts = int(time.time())
    prepared_data = json.dumps({
        "signature": base64.b64encode(sign_key.sign(json.dumps(['approve', block.hash, ts]).encode())),
        "of": block.hash,
        "timestamp": ts
    })
    # 3 + len(prepared_data) is length (type + prepared_data_len + prepared_data)
    length = 3 + len(prepared_data)
    base = struct.pack("!HBH", length, Packets.APPROVE_BLOCK.value, len(prepared_data))
    base += prepared_data.encode("ascii")

    return base

async def validate_block(node: Node, block: Block):
    if block.validate():
        # Block validated.
        await node.send(encode_approve(block))
    else:
        # Block **is not** validated! (incorrect)
        await node.send(encode_deny(block))

async def handle_client(client: socket.socket, addr):
    loop = asyncio.get_event_loop()
    client.setblocking(False)
    pk = pk_cache[addr]
    box = Box(private_key, pk)
    addr = node_info['wallet_address']
    await loop.sock_sendall(client, box.encrypt(encode_hello(addr, verify_key)))
    while True:
        try:
            msg_enc, msg_from = await loop.sock_recv(client, 4096)
            print(msg_enc, msg_from)
            msg = box.decrypt(msg_enc)
            length = struct.unpack("!H", msg[:2]) # length
            data = msg[2:2+length]
            type = struct.unpack("!B", data[0])
            if type == Packets.HELLO.value:
                # Hello! we should add now this peer with details
                len = struct.unpack("!H", data[1:3])
                node_info = json.loads(data[5:5+len])

                node = Node()
                node.address = node_info['wallet_address']
                node.sock = client
                node.verify_key = VerifyKey(base64.b64decode(node_info['verify_key']))
                node._box = box
                node.state = State.CONNECTED
                validators[node.address] = node
            elif type == Packets.NEW_BLOCK.value:
                # New block to validate! 
                len = struct.unpack("!H", data[1:3])
                block = json.loads(data[5:5+len])['block']
                # Spawn a thread to validate thread
                threading.Thread(target=lambda: asyncio.run(validate_block(validators[addr], Block.fromdict(block)))).start()

        except TimeoutError:
            pass

    client.close()

async def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 10248))
    server.listen(10)
    server.setblocking(False)

    loop = asyncio.get_event_loop()

    while True:
        client, addr = await loop.sock_accept(server)
        loop.create_task(handle_client(client, addr))

async def main():
    loop = asyncio.get_event_loop()
    async with serve(handler, "localhost", 10247):
        loop.create_task(run_server())
        print("Now validator is running!")
        await asyncio.Future()

asyncio.run(main())
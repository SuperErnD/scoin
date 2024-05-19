from jsonrpcserver import method, Success, Error, Result, async_dispatch
from websockets.server import serve
import asyncio
from time import time
from tortoise import Tortoise
from bc import *
from models import Wallet
from saver_pickle import Saver
from uuid import uuid4
from tomllib import load
from math import log
from argon2 import PasswordHasher
from threading import Thread

ph = PasswordHasher()

conf = None

with open("config.toml", 'rb') as f:
    conf = load(f)

difficulty_data = {
    "low": 1,
    "med": 2,
    "hig": 3
}

bc = Blockchain()

calculate_diff = lambda d: bc.diff * difficulty_data[d]

@method
async def ping(context):
    return Success("pong")

saver = Saver()

try:
    bc = saver.load()
except Exception as e:
    print(e)
    bc = Blockchain()

bc.static = conf['blockchain']['static_diff']
bc.diff = conf['blockchain']['static_val']

print("Current difficulty is", bc.diff)

@method
async def test_login(context, token: str) -> Result:
    username = token.split(":")[0]
    private = token.split(":")[1]

    wallet = await Wallet.filter( nick = username )

    if not ph.verify(wallet[0].private, private):
        return Error(0, "Invalid username/private")

    if not len(wallet):
        return Error(0, "Invalid username/private")

    return Success("ok")

@method 
async def register(context, username: str) -> Result:
    wallet = await Wallet.filter( nick = username )

    if len(wallet):
        return Error(0, "already exists account with that username")
    
    priv = uuid4().hex
    
    wallet = await Wallet.create(private=str(ph.hash(priv)), nick=username, balance=0)

    return Success(priv)

@method
async def blockinfo(context, block: str):
    blk = next(filter(lambda obj: obj.hash.startswith(block), bc.chain), None)
    if not blk:
        return Error(0, "Block not found.")
    
    res = {"type": blk.data['type'], "ts": blk.ts, "hash": blk.hash}

    if blk.data['type'] == "mining":
        res['miner'] = blk.data['miner']
    elif blk.data['type'] == "transaction":
        res['from'] = blk.data['from']
        res['to'] = blk.data['to']

    return Success(dumps(res))

@method
async def balance(context, token: str):
    username = token.split(":")[0]
    private = token.split(":")[1]

    wallet = await Wallet.filter( nick = username )

    if not ph.verify(wallet[0].private, private):
        return Error(0, "Invalid username/private")
    
    if not len(wallet):
        return Error(0, "Invalid username/private")

    return Success(str(wallet[0].balance))

@method
async def send(context, token: str, to: str, amount: float):
    username = token.split(":")[0]
    private = token.split(":")[1]

    if username == to:
        return Error(0, "Cant send to self")
    
    if amount <= 0:
        return Error(0, "Amount cant be 0/negative number")

    wallet = await Wallet.filter( nick = username )

    if not ph.verify(wallet[0].private, private):
        return Error(0, "Invalid username/private")

    if not len(wallet):
        return Error(0, "Invalid username/private")
    
    target_wallet = await Wallet.filter(nick=to)

    if wallet[0].balance < amount:
        return Error(0, "still mine")
    
    if not len(target_wallet):
        return Error(0, "Receiver is not exists!")

    Thread(target=lambda: bc.add_block(Block(int(time.time()), type="transaction", sender=username, receiver=to, amount=amount))).start()

    wallet[0].balance -= amount
    target_wallet[0].balance += amount

    await wallet[0].save()
    await target_wallet[0].save()

@method
async def job(context, username: str, difficulty: str) -> Result:
    block = Block(int(time.time()), type="mining", miner=username)

    context['block'] = block
    context['difficulty'] = calculate_diff(difficulty)
    context['diff_multp'] = difficulty_data[difficulty]
    context['is_mining'] = True
    context['username'] = username

    return Success(dumps({ "data": block.get_data_hash(), "difficulty": calculate_diff(difficulty)} ))

@method
async def job_done(context, result_hash: str, nonce: int, hs: int) -> Result:
    # Checking

    # Step 0 (Check base & does we mining?)
    if not context['is_mining'] == True:
        context['is_mining'] = False
        return Error(-1, "Not mining.")
    
    if not result_hash.startswith("0" * context['difficulty']):
        context['is_mining'] = False
        return Error(0, "Invalid hash!")
    
    # Step 1 (Just check hash, if valid process)
    
    if sha(context['block'].get_data_hash() + str(nonce)) != result_hash:
        context['is_mining'] = False
        return Error(1, "Invalid hash (hash is not equal to a calculated)")
    
    # Step 2 (Final check of hash, if valid we can give a reward and add a block into blockchain) (its mostly dont needed because we check the result hash is == a calculated one and does result hash is matches but i write it code because i think 1 extra check wont harm)

    if not sha(context['block'].get_data_hash() + str(nonce)).startswith("0" * context['difficulty']):
        context['is_mining'] = False
        return Error(2, "Invalid hash!")
    
    context['is_mining'] = False

    # yay its correct
    context['block'].nonce = nonce
    bc.add_block(context['block'])

    saver.save(bc)

    # try find the awesome wallet
    wallet = await Wallet.filter( nick = context['username'] )


    # calculate reward

    reward = log((int(time.time()) - context['block'].ts + 0.0000001) * (hs / (1000 * 1000)) * context['diff_multp']) / 1000

    if len(wallet) == 0:
        # idk say to client or no
        pass
        #wallet = await Wallet.create(private=uuid4().hex, nick=context['username'], balance=reward)
    else:
        wallet = wallet[0]
        wallet.balance += reward
        await wallet.save()

    return Success("ok")


async def handler(websocket):
    print("new connection")
    ctx = { "ws": websocket, "block": None, "difficulty": None, "is_mining": False, "username": "" }
    while True:
        if response := await async_dispatch(await websocket.recv(), context=ctx):
            await websocket.send(response)

async def main():
    # db init
    await Tortoise.init(
        db_url="sqlite://db.sqlite3",
        modules={'models': ['models']}
    )

    await Tortoise.generate_schemas()

    async with serve(handler, "localhost", 10800, ping_timeout=60 * 30): # timeout is 30 minutes, should be ok for *ONE* block 
        print("Server is now running!")
        await asyncio.Future()

asyncio.run(main())
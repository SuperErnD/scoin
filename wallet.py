import asyncio

from jsonrpcclient import Ok, parse_json, request_json
import websockets
import sys
from json import loads

async def main():
    tok = ""

    async with websockets.connect("ws://localhost:10800") as ws:
        while True:
            command = input("> ")
            if command.startswith("help"):
                print("this is wallet, we have a register, send, get balance, login, blockinfo")
                print("login <username> <private>")
                print("register")
                print("send <receiver> <amount>")
                print("blockinfo <hash>")
                print("balance")
                continue
            elif command.startswith("balance"):
                if not tok:
                    print("not loggined")
                    continue

                await ws.send(request_json("balance", params={"token": tok}))
                res = parse_json(await ws.recv())

                if isinstance(res, Ok):
                    print("ok")
                    print("your balance is " + res.result)
                    continue
                else:
                    print("fail")
                    print(res.message)
                    continue

            elif command.startswith("blockinfo"):
                hsh = command.split(" ")[1]
                await ws.send(request_json("blockinfo", params={"block": hsh}))
                res = parse_json(await ws.recv())
                
                if isinstance(res, Ok):
                    blk = loads(res.result)
                    print("Block:")
                    print(f"Type: {blk['type']}")
                    print(f"Timestamp: {blk['ts'] * 1000}")
                    print(f"Full hash: {blk['hash']}")
                    if blk['type'] == "transaction":
                        print(f"{blk['from']} ~> {blk['to']}")
                    elif blk['type'] == "mining":
                        print(f"miner ~> {blk['miner']}")
                else:
                    print("fail")
                    print(res.message)

            elif command.startswith("send"):
                receiver = command.split(" ")[1]
                amount = command.split(" ")[2]

                if not tok:
                    print("not loggined")
                    continue
                
                await ws.send(request_json("send", params={"token": tok, "to": receiver, "amount": float(amount)}))
                res = parse_json(await ws.recv())

                if isinstance(res, Ok):
                    print("done")
                else:
                    print("fail")
                    print(res.message)
                    continue
            
            elif command.startswith("register"):
                if tok:
                    print("already loggined")
                    continue

                username = input("input username > ")

                await ws.send(request_json("register", params={"username": username}))
                res = parse_json(await ws.recv())
            
                if isinstance(res, Ok):
                    tok = f"{username}:{res.result}"

                    print("registered and automatically logined")
                    print(f"here your private (DO NOT SHARE IT, SAVE IT OTHERWISE YOU CANT ACCESS THE WALLET): {res.result}")
                else:
                    print("fail")
                    print(res.message)
                    tok = ""
                    continue

            elif command.startswith("login"):
                if tok:
                    print("already loggined")
                    continue

                cmd = command.split(" ")
                tok = f"{cmd[1]}:{cmd[2]}"

                await ws.send(request_json("test_login", params={"token": tok}))
                res = parse_json(await ws.recv())

                if isinstance(res, Ok):
                    print("ok")
                    continue
                else:
                    print("fail")
                    print(res.message)
                    tok = ""
                    continue
            elif command.startswith("exit"):
                await ws.close()
                        
                break # exited
            else:
                print('unk command')




asyncio.get_event_loop().run_until_complete(main())

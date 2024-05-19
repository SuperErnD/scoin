import asyncio
import logging

from jsonrpcclient import Ok, parse_json, request_json
import websockets

from hashlib import sha512
from json import loads
import time

sha  = lambda d: sha512(d.encode()).hexdigest()

async def main():
    while True:
        try:
            async with websockets.connect("ws://localhost:10800") as ws:
                while True:
                    await ws.send(request_json("job", params={"username":"Mords", "difficulty":"low"}))
                    response = parse_json(await ws.recv())

                    if isinstance(response, Ok):
                        job = loads(response.result)
                        nonce = 0
                        diff = job['difficulty']
                        data = job['data']
                        target = "0" * diff
                        h = ""
                        st = time.time()
                        hr = 0
                        hc = 0

                        while not h.startswith(target): # fix here please, nonce = 0 could be too 
                            # we could receive something while mining..
                            #a = await ws.recv()
                            #print(a)

                            nonce += 1
                            h = sha(data + str(nonce))
                            hc += 1

                            #print("Mining.. - " + h)
                            if nonce % 100000 == 0:
                                elapsed = time.time() - st
                                hr = hc / elapsed
                                print(f"Current hashrate: {hr:.2f} H/s")

                        print("seems good block")
                        
                        await ws.send(request_json("job_done", params={"result_hash": sha(data + str(nonce)), "nonce": nonce, "hs": int(hr)}))
                        await ws.recv()
                    else:
                        logging.error(response.message)
        except:
            pass




asyncio.get_event_loop().run_until_complete(main())

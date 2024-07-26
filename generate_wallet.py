import nacl.signing
import base64
import hashlib 
import json

private = nacl.signing.SigningKey.generate()
public = private.verify_key
addr = hashlib.sha256(public.encode()).hexdigest()

# All done! Write it
print(json.dumps({
    "a": base64.b64encode(private.encode()).decode(),
    "b": base64.b64encode(public.encode()).decode(),
    "c": '0x'+addr
}))
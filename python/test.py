import lockdown

import RSACipher
from AESCipher import *

import json
import Search
import base64

sym = "wassup"
sym2 = "wassup2"
aes = AESCipher(sym)
aes2 = AESCipher(sym2)

from Crypto.PublicKey import RSA

private_key = RSA.generate(2048)
public_key = private_key.publickey()

t = RSACipher.encrypt(public_key, sym)

private_key2 = RSA.generate(2048)
public_key2 = private_key2.publickey()

t2 = RSACipher.encrypt(public_key2, sym2)
t3 = RSACipher.encrypt(public_key, sym2)

# https://github.com/diafygi/webcrypto-examples

plain = "what, a lame entry!"
json_str = f'''
{{
  "content": "{aes.encrypt(plain).decode()}",
  "key_list": [["{RSACipher.export_key(public_key)}", "{t.decode()}"]],
  "search_blob": {json.dumps([base64.b64encode(x).decode() for x in Search.generate_blob(plain, hashlib.sha256(sym.encode()).digest())])}
}}
'''

#print(list(hashlib.sha256(sym.encode()).digest()))
print(json_str)

content = lockdown.Cell.from_json(json_str)

ssn = lockdown.Cell.from_json(f'''
{{
  "content": "{aes2.encrypt("a ssn").decode()}",
  "key_list": [["{RSACipher.export_key(public_key)}", "{t3.decode()}"], ["{RSACipher.export_key(public_key2)}", "{t2.decode()}"]]
}}
''')

ssn2 = lockdown.Cell.from_json(f'''
{{
  "content": "{aes2.encrypt("a ssn").decode()}",
  "key_list": [["{RSACipher.export_key(public_key)}", "{t3.decode()}"]]
}}
''')

#print(content.to_json())

conn = lockdown.LockdownConnection("demodb.sqlite")

cur = conn.cursor()
cur.execute("INSERT INTO Tweets (Content, Owner, SSN) VALUES (?, ?, ?)", (content, 0, ssn))
#cur.execute("INSERT INTO Tweets (Content, Owner, SSN) VALUES (?, ?, ?)", (content, 0, ssn2))

#cur.execute("SELECT * FROM Tweets WHERE Owner=0", pub_key=RSACipher.export_key(public_key))

cur.execute("SELECT id, Content FROM Tweets WHERE Owner == 0 AND Content LIKE '%im_useless%' AND 1=1", pub_key=RSACipher.export_key(public_key))
meta_fetch = cur.fetchall(metadata=True)
search_keys = {}
for row_id, cell_json in meta_fetch:
  search_keys[str(row_id)] = [base64.b64encode(x).decode() for x in Search.gen_search_key("lame", hashlib.sha256(sym.encode()).digest())]

cur.execute("SELECT id, Content FROM Tweets WHERE Owner == 0 AND Content LIKE '%im_useless%' AND 1=1", 
  pub_key=RSACipher.export_key(public_key), 
  search_keys=search_keys)
print([x for x in cur.fetchall(pub_key=RSACipher.export_key(public_key))])


#cur.execute("SELECT * FROM Tweets", pub_key=RSACipher.export_key(public_key2))
#print([x[0] for x in cur.fetchall()])

#print(get_query_columns("SELECT name, poo FROM Tweets"))
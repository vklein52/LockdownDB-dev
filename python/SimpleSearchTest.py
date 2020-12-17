# Referenced https://github.com/atulmahind/song-wagner-perrig/blob/master/scheme.py
from Crypto.Cipher import AES
from Crypto.Util import Counter
import struct
import re

# Should be used as a PRG, S_k(i)
class StreamCipher:
  garbage = b'This is garbage!'

  def __init__(self, key):
    self.key = key
    self.ctr = Counter.new(128, initial_value=0, little_endian=True)
    self.aes = AES.new(self.key, mode=AES.MODE_CTR, counter=self.ctr)
  
  def next(self):
    return self.aes.encrypt(self.garbage)

class AESCipher:
  garbage = b'This is garbage!'

  def __init__(self, key):
    self.key = key

  def encrypt(self, raw):
    cipher = AES.new(self.key, AES.MODE_CBC, self.garbage)
    return cipher.encrypt(raw)

xor_word = lambda ss,cc: b''.join(bytes([s ^ c]) for s,c in zip(ss,cc))

def generate_blob(myplain, key):
  results = []
  # Can we use same key?
  s_k = StreamCipher(key)

  # Generate key from cell
  word_encryptor = AESCipher(key)

  # Need a different key or no?
  word_key_generator = AESCipher(key)

  for word in re.findall(r"[\w']+", myplain):
    if len(word) > 32:
      continue
    
    padded = word.ljust(32, ' ').encode()
    enc_word = word_encryptor.encrypt(padded)
    ki = word_key_generator.encrypt(enc_word)

    f_ki = AESCipher(ki)
    s = s_k.next()

    f_ki_s = f_ki.encrypt(s)

    results.append(xor_word(enc_word, (s + f_ki_s)))
  
  return results

def search(blob, enc_word, ki):
  f_ki = AESCipher(ki)

  for cipher_word in blob:
    stream = xor_word(cipher_word, enc_word)
    f_ki_s = f_ki.encrypt(stream[:16])

    if stream[16:] == f_ki_s:
      return True

  return False

myplain = "this is a sad sentence, written on a sad day by a few sad boys!"
ENCRYPTION_KEY = bytes([197, 232, 10, 200, 209, 232, 141, 185, 136, 164, 90, 246, 61, 16, 252, 24, 85, 25, 55, 148, 243, 153, 239, 212, 160, 229, 146, 227, 94, 217, 226, 28])
blob = generate_blob(myplain, ENCRYPTION_KEY)

target = "written"
padded = target.ljust(32, ' ').encode()
word_encryptor = AESCipher(ENCRYPTION_KEY)
word_key_generator = AESCipher(ENCRYPTION_KEY)
enc_word = word_encryptor.encrypt(padded)
ki = word_key_generator.encrypt(enc_word)

print(search(blob, enc_word, ki))
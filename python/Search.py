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

def gen_search_key(word, key):
  padded = word.ljust(32, ' ').encode()
  word_encryptor = AESCipher(key)
  word_key_generator = AESCipher(key)
  enc_word = word_encryptor.encrypt(padded)
  ki = word_key_generator.encrypt(enc_word)
  return [enc_word, ki]
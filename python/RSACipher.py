import base64

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

def encrypt(key, data):
  cipher_rsa = PKCS1_OAEP.new(key)
  return base64.b64encode(cipher_rsa.encrypt(data.encode()))

def decrypt(key, data):
  cipher_rsa = PKCS1_OAEP.new(key)
  return cipher_rsa.decrypt(base64.b64decode(data)).decode()

def export_key(key):
  s = key.exportKey().decode()
  s = s.replace("-----BEGIN RSA PUBLIC KEY-----", "")
  s = s.replace("-----END RSA PUBLIC KEY-----", "")
  s = s.replace("\n", "")
  return s

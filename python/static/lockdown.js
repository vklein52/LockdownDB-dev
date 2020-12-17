/*
  Convert a string into an ArrayBuffer
  from https://developers.google.com/web/updates/2012/06/How-to-convert-ArrayBuffer-to-and-from-String
  */
  function str2ab(str) {
  const buf = new ArrayBuffer(str.length);
  const bufView = new Uint8Array(buf);
  for (let i = 0, strLen = str.length; i < strLen; i++) {
    bufView[i] = str.charCodeAt(i);
  }
  return buf;
}
/*
Convert  an ArrayBuffer into a string
from https://developers.google.com/web/updates/2012/06/How-to-convert-ArrayBuffer-to-and-from-String
*/
function ab2str(buf) {
  return String.fromCharCode.apply(null, new Uint8Array(buf));
}

function getMessageEncoding(message) {
  let enc = new TextEncoder();
  return enc.encode(message);
}

function encryptMessage(key) {
  let encoded = getMessageEncoding();
  // counter will be needed for decryption
  counter = window.crypto.getRandomValues(new Uint8Array(16));
  return window.crypto.subtle.encrypt(
    {
      name: "AES-CTR",
      counter,
      length: 64
    },
    key,
    encoded
  );
}

function _base64ToArrayBuffer(base64) {
    var binary_string = window.atob(base64);
    var len = binary_string.length;
    var bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt(i);
    }
    return bytes.buffer;
}

async function aes_cbc_demo() {
  let iv = new Uint8Array([44, 79, 251, 142, 199, 122, 45, 2, 127, 231, 118, 192, 90, 172, 101, 188]);
  let data = getMessageEncoding("what, a lame entry!");
  
  
  //let key = importPrivateKey(pemEncodedKey)
  //crypto functions are wrapped in promises so we have to use await and make sure the function that
  //contains this code is an async function
  //encrypt function wants a cryptokey object
  const key_encoded = await crypto.subtle.importKey(  "raw",    new Uint8Array([197, 232, 10, 200, 209, 232, 141, 185, 136, 164, 90, 246, 61, 16, 252, 24, 85, 25, 55, 148, 243, 153, 239, 212, 160, 229, 146, 227, 94, 217, 226, 28]),   'AES-CBC' ,  false,   ["encrypt", "decrypt"]);
  const encrypted_content = await window.crypto.subtle.encrypt(
      {
        name: "AES-CBC",
        iv:  iv
      },
      key_encoded,
      data
    );

  //Uint8Array
  console.log(new Uint8Array(encrypted_content));
  console.log(new Uint8Array(_base64ToArrayBuffer("LE/7jsd6LQJ/53bAWqxlvPZxuTKxX9qcC/yAbnmLY7K6Rid1NuwF2MwIZdIqgjwX")));
}

function bnToBuf(bn) {
  var hex = BigInt(bn).toString(16);
  if (hex.length % 2) { hex = '0' + hex; }

  var len = hex.length / 2;
  var u8 = new Uint8Array(len);

  var i = 0;
  var j = 0;
  while (i < len) {
    u8[i] = parseInt(hex.slice(j, j+2), 16);
    i += 1;
    j += 2;
  }

  return u8;
}

async function aes_ctr_demo() {
  counter = new Uint8Array(16);
  garbage = new Uint8Array([84, 104, 105, 115, 32, 105, 115, 32, 103, 97, 114, 98, 97, 103, 101, 33])
  const key_encoded = await crypto.subtle.importKey(  "raw",    new Uint8Array([197, 232, 10, 200, 209, 232, 141, 185, 136, 164, 90, 246, 61, 16, 252, 24, 85, 25, 55, 148, 243, 153, 239, 212, 160, 229, 146, 227, 94, 217, 226, 28]),   'AES-CTR' ,  false,   ["encrypt", "decrypt"]);
  a = await window.crypto.subtle.encrypt(
    {
      name: "AES-CTR",
      counter,
      length: 128
    },
    key_encoded,
    garbage
  );

  console.log(new Uint8Array(a))
  console.log(new Uint8Array([79, 9, 54, 247, 60, 150, 181, 16, 120, 120, 117, 135, 116, 116, 111, 216]))

  // TODO: make this work past 4 billion
  ctrnew = new Uint32Array(counter.buffer);
  ctrnew[0] += 1;
  ctrnew = new Uint8Array(ctrnew.buffer);

  a = await window.crypto.subtle.encrypt(
    {
      name: "AES-CTR",
      counter: ctrnew,
      length: 128
    },
    key_encoded,
    garbage
  );

  console.log(new Uint8Array(a))
  console.log(new Uint8Array([60, 129, 197, 57, 235, 167, 40, 105, 24, 8, 63, 212, 174, 164, 91, 130]))
}

class StreamCipher {
  constructor(key) {
    this.key = key;
    this.counter = new Uint8Array(16);
    this.garbage = new Uint8Array([84, 104, 105, 115, 32, 105, 115, 32, 103, 97, 114, 98, 97, 103, 101, 33]);
  }

  async next() {
    let res = await window.crypto.subtle.encrypt(
      {
        name: "AES-CTR",
        counter: this.counter,
        length: 128
      },
      this.key,
      this.garbage
    );

    // TODO: make this work past 4 billion
    let ctrnew = new Uint32Array(this.counter.buffer);
    ctrnew[0] += 1;
    this.counter = new Uint8Array(ctrnew.buffer);

    return res;
  }
}

class AESCipher {
  constructor(key) {
    this.key = key;
    this.garbage = new Uint8Array([84, 104, 105, 115, 32, 105, 115, 32, 103, 97, 114, 98, 97, 103, 101, 33]);
  }

  async encrypt(data) {
    const encrypted_content = await window.crypto.subtle.encrypt(
        {
          name: "AES-CBC",
          iv:  this.garbage
        },
        this.key,
        data
      );
    return new Uint8Array(encrypted_content.slice(0, encrypted_content.byteLength-16));
  }
}

function xor_word(a, b) {
  let out = new Uint8Array(a.byteLength);
  for (let i = 0; i < a.length; ++i) {
    out[i] = a[i] ^ b[i];
  }
  return out;
}

function concat_buffers(buffer1, buffer2) {
  var tmp = new Uint8Array(buffer1.byteLength + buffer2.byteLength);
  tmp.set(new Uint8Array(buffer1), 0);
  tmp.set(new Uint8Array(buffer2), buffer1.byteLength);
  return tmp;
};

async function generate_blob(key_bytes, plain) {
  let plain_bytes = getMessageEncoding(plain);
  let results = [];

  let s_k = new StreamCipher(await crypto.subtle.importKey(  "raw",    key_bytes,   'AES-CTR' ,  false,   ["encrypt", "decrypt"]));
  let word_encryptor = new AESCipher(await crypto.subtle.importKey(  "raw",    key_bytes,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));
  let word_key_generator = new AESCipher(await crypto.subtle.importKey(  "raw",    key_bytes,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));

  for (let word of plain.match(/[\w']+/g)) {
    let padded = getMessageEncoding(word.padEnd(32, " "));
    let enc_word = (await word_encryptor.encrypt(padded));
    let ki = (await word_key_generator.encrypt(enc_word));
    
    let f_ki = new AESCipher(await crypto.subtle.importKey(  "raw",    ki,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));
    let s = await s_k.next();

    let f_ki_s = await f_ki.encrypt(s);

    results.push(btoa(ab2str(xor_word(enc_word, concat_buffers(s, f_ki_s)))));
  }
  
  return results
}

async function gen_search_key(word, key_bytes) {
  let padded = getMessageEncoding(word.padEnd(32, " "));
  let word_encryptor = new AESCipher(await crypto.subtle.importKey(  "raw",    key_bytes,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));
  let word_key_generator = new AESCipher(await crypto.subtle.importKey(  "raw",    key_bytes,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));
  let enc_word = (await word_encryptor.encrypt(padded));
  let ki = (await word_key_generator.encrypt(enc_word));
  return [btoa(ab2str(enc_word)), btoa(ab2str(ki))]
}

async function search_demo() {
  plain = "this is a sad sentence, written on a sad day by a few sad boys!";
  const key = new Uint8Array([197, 232, 10, 200, 209, 232, 141, 185, 136, 164, 90, 246, 61, 16, 252, 24, 85, 25, 55, 148, 243, 153, 239, 212, 160, 229, 146, 227, 94, 217, 226, 28]);
  await generate_blob(key, plain)
  console.log(await gen_search_key("this", key))
}

class RSACipher {
  constructor(key) {
    if (key != null) {
      this.private_key = key.privateKey;
      this.public_key = key.publicKey;
    }
  }

  async importKeys(private_key, public_key) {
    const binaryDerString = atob(public_key);
    // convert from a binary string to an ArrayBuffer
    const binaryDer = str2ab(binaryDerString);

    this.public_key = await window.crypto.subtle.importKey(
      "spki",
      binaryDer,
      {
        name: "RSA-OAEP",
        hash: "SHA-256"
      },
      true,
      ["encrypt"]
    );

    if (private_key != null) {
      const binaryDerString2 = atob(private_key);
      // convert from a binary string to an ArrayBuffer
      const binaryDer2 = str2ab(binaryDerString2);

      this.private_key = await window.crypto.subtle.importKey(
        "pkcs8",
        binaryDer2,
        {
          name: "RSA-OAEP",
          hash: "SHA-256"
        },
        true,
        ["decrypt"]
      );
    }

  }

  async encrypt(plain, is_bytes=false) {
    let encoded = plain;
    if (!is_bytes) {
      encoded = getMessageEncoding(plain);
    }
    let ciphertext = await window.crypto.subtle.encrypt(
      {
        name: "RSA-OAEP"
      },
      this.public_key,
      encoded
    );

    return btoa(ab2str(ciphertext));
  }

  async decrypt(cipher, is_bytes=false) {
    let bytes = str2ab(atob(cipher));
    let decrypted = await window.crypto.subtle.decrypt(
      {
        name: "RSA-OAEP",
      },
      this.private_key,
      bytes
    );

    if (is_bytes) {
      return new Uint8Array(decrypted);
    }

    let dec = new TextDecoder();
    return dec.decode(decrypted);
  }

  async export_key_public() {
    return btoa(ab2str(await window.crypto.subtle.exportKey(
      "spki",
      this.public_key
    )));
  }

  async export_key_private() {
    return btoa(ab2str(await window.crypto.subtle.exportKey(
      "pkcs8",
      this.private_key
    )));
  }
}

class AES {
  constructor(key) {
    this.key = key;
  }

  async encrypt(plain) {
    let encoded = getMessageEncoding(plain);
    // The iv must never be reused with a given key.
    let iv = window.crypto.getRandomValues(new Uint8Array(16));
    let ciphertext = await window.crypto.subtle.encrypt(
      {
        name: "AES-CBC",
        iv
      },
      this.key,
      encoded
    );

    return btoa(ab2str(concat_buffers(iv, ciphertext)));
  }

  async decrypt(cipher) {
    let bytes = str2ab(atob(cipher));
    let decrypted = await window.crypto.subtle.decrypt(
      {
        name: "AES-CBC",
        iv: bytes.slice(0, 16)
      },
      this.key,
      bytes.slice(16, bytes.byteLength)
    );

    let dec = new TextDecoder();
    return dec.decode(decrypted);
  }
}

class Lockdown {
  constructor(private_key, public_key) {
    this.private_key = private_key;
    this.public_key = public_key;
    this.rsa = new RSACipher(null);
  }

  async init() {
    await this.rsa.importKeys(this.private_key, this.public_key);
  }

  async gen_search_query(query, metadata) {
    let search_keys = {};

    for (let row of metadata) {
      let id = row[0];
      let cell = new Cell(row[1]);

      search_keys[id] = await cell.search_query(query)
    }

    return {
      pub_key: await lockdown.rsa.export_key_public(),
      search_keys: search_keys
    }
  }
}

class Cell {
  constructor(json_data) {
    let parsed = JSON.parse(json_data);
    this.content = parsed.content;
    this.key_list = parsed.key_list;
    this.search_blob = parsed.search_blob;
  }

  async get_sym() {
    let my_pub = await lockdown.rsa.export_key_public();
    for (let k of this.key_list) {
      if (k[0] == my_pub) {
        let sym_key = await lockdown.rsa.decrypt(k[1], true);
        return sym_key
      }
    }
  }

  async read() {
    let sym_key = await this.get_sym();
    let a = new AES(await crypto.subtle.importKey(  "raw",    sym_key,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));
    return a.decrypt(this.content);
  }

  async write(plain) {
    let sym_key = await this.get_sym();
    let a = new AES(await crypto.subtle.importKey(  "raw",    sym_key,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));
    this.content = await a.encrypt(plain);
  }

  async search_query(query) {
    return await gen_search_key(query, await this.get_sym());
  }

  static async new_container(plain, extra_pub_keys=[], searchable=false) {
    let key = window.crypto.getRandomValues(new Uint8Array(32));
    let a = new AES(await crypto.subtle.importKey(  "raw",    key,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));
    
    let d = {};
    d.content = await a.encrypt(plain);
    d.key_list = [[await lockdown.rsa.export_key_public(), await lockdown.rsa.encrypt(key, true)]];

    for (let extra_key of extra_pub_keys) {
      let cur_entry = [extra_key];

      let r = new RSACipher(null);
      await r.importKeys(null, extra_key);

      cur_entry.push(await r.encrypt(key, true));
      d.key_list.push(cur_entry);
    }

    if (searchable) {
      d.search_blob = await generate_blob(key, plain);
    }
    
    return new Cell(JSON.stringify(d))
  }

  to_json() {
    let d = {
      content: this.content,
      key_list: this.key_list,
      search_blob: this.search_blob
    };
    Object.keys(d).forEach(key => {
      if (d[key] === undefined) {
        delete d[key];
      }
    });
    return JSON.stringify(d);
  }
}

async function test() {
  //search_demo()
  /*
  let key = await window.crypto.subtle.generateKey(
      {
          name: "RSA-OAEP",
          modulusLength: 2048, //can be 1024, 2048, or 4096
          publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
          hash: {name: "SHA-256"}, //can be "SHA-1", "SHA-256", "SHA-384", or "SHA-512"
      },
      true, //whether the key is extractable (i.e. can be used in exportKey)
      ["encrypt", "decrypt"] //can be any combination of "sign" and "verify"
  );*/

  window.lockdown = new Lockdown(localStorage.getItem("private_key"), localStorage.getItem("public_key"));
  await window.lockdown.init();

  //console.log(key.publicKey)
  //localStorage.setItem("private_key", await r.export_key_private());
  //localStorage.setItem("public_key", await r.export_key_public());

  //console.log(await r.export_key_public());
  //console.log(await r.export_key_private());

  const key = new Uint8Array([197, 232, 10, 200, 209, 232, 141, 185, 136, 164, 90, 246, 61, 16, 252, 24, 85, 25, 55, 148, 243, 153, 239, 212, 160, 229, 146, 227, 94, 217, 226, 28]);
  
  let a = new AES(await crypto.subtle.importKey(  "raw",    key,   'AES-CBC' ,  false,   ["encrypt", "decrypt"]));

  let plain = "this is a sad sentence, written by a few sad boys on a sad day!";

  //console.log(await r.decrypt(await r.encrypt(plain)));
  //console.log(await r.decrypt(await r.encrypt(key, true), true))
  /*console.log({
content: await a.encrypt(plain),
key_list: [[await r.export_key_public(), await r.encrypt(key, true)]],
search_blob: await generate_blob(key, plain)
})*/
  
  /*fetch('/insert_test', {
    method: 'post',
    body: JSON.stringify(
    {
      content: await a.encrypt(plain),
      key_list: [[await r.export_key_public(), await r.encrypt(key, true)]],
      search_blob: await generate_blob(key, plain)
    })
  }).then(function(response) {
    console.log(response.text())
  })*/

  /*
  let resp = await fetch('/search_test', {
    method: 'post',
    body: JSON.stringify({
      pub_key: await r.export_key_public()
    })
  });

  console.log(await resp.text())*/
  /*
  let resp = await fetch('/search_test', {
    method: 'post',
    body: JSON.stringify({
      pub_key: await lockdown.rsa.export_key_public(),
      search_keys: {
        169: await gen_search_key("sad", key)
      }
    })
  });
  j = await resp.json()
  c = new Cell(j[0][1]);
  console.log(await c.read());
  await c.write("yo")
  console.log(await c.read());*/
  //console.log(await resp.text())

  //let e = await a.encrypt("hi sweetie");
  //console.log(await a.decrypt(e))
  
  /*let r2 = new RSACipher(null);
  await r2.importKeys(await r.export_key_private(), await r.export_key_public());

  console.log(await r2.export_key_public());
  console.log(await r2.export_key_private());*/
}
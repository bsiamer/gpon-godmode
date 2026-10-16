"""Stanford Javascript Crypto Library (SJCL) compatible routines for Nokia/Alcatel GPON Gateway."""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as symmetric_padding


def base64url_escape(b64_str: str) -> str:
    """Escapes standard base64 string to match the router's SJCL base64url encoding."""
    return b64_str.replace("+", "-").replace("/", "_").replace("=", ".")


def base64url_encode(data: bytes) -> str:
    """Encodes raw bytes to URL-safe base64 string without trailing padding."""
    b64 = base64.b64encode(data).decode("utf-8")
    return b64.replace("+", "-").replace("/", "_").replace("=", "")


def sha256_sjcl(val1: str, val2: str) -> str:
    """Computes SJCL SHA-256 hash for val1:val2."""
    msg = f"{val1}:{val2}".encode("utf-8")
    digest = hashlib.sha256(msg).digest()
    return base64.b64encode(digest).decode("utf-8")


def sha256url_sjcl(val1: str, val2: str) -> str:
    """Computes SJCL SHA-256 and converts to URL-safe base64."""
    return base64url_escape(sha256_sjcl(val1, val2))


def encrypt_login_payload(username: str, password: str, nonce: str, pubkey_pem: str) -> str:
    """Encrypts credentials matching the Nokia GPON login.cgi protocol.
    
    Uses AES-128-CBC for the form parameters, and RSA PKCS1v15 for the session key.
    """
    a1 = sha256_sjcl(username, password)
    response = sha256url_sjcl(a1, nonce)
    userhash = sha256url_sjcl(username, nonce)

    postdata = f"userhash={userhash}&response={response}&nonce={base64url_escape(nonce)}"

    dec_key_bytes = os.urandom(16)
    dec_iv_bytes = os.urandom(16)
    dec_key = base64.b64encode(dec_key_bytes).decode("utf-8")
    dec_iv = base64.b64encode(dec_iv_bytes).decode("utf-8")

    postdata += f"&enckey={base64url_escape(dec_key)}&enciv={base64url_escape(dec_iv)}"

    aeskey_bytes = os.urandom(16)
    iv_bytes = os.urandom(16)

    padder = symmetric_padding.PKCS7(128).padder()
    padded_data = padder.update(postdata.encode("utf-8")) + padder.finalize()

    cipher = Cipher(algorithms.AES(aeskey_bytes), modes.CBC(iv_bytes))
    encryptor = cipher.encryptor()
    ct_bytes = encryptor.update(padded_data) + encryptor.finalize()

    ct = base64url_encode(ct_bytes)

    public_key = serialization.load_pem_public_key(pubkey_pem.encode("utf-8"))
    aesinfo = (
        base64.b64encode(aeskey_bytes).decode("utf-8")
        + " "
        + base64.b64encode(iv_bytes).decode("utf-8")
    )

    rsa_ciphertext = public_key.encrypt(aesinfo.encode("utf-8"), padding.PKCS1v15())
    ck = base64url_escape(base64.b64encode(rsa_ciphertext).decode("utf-8"))

    return f"encrypted=1&ct={ct}&ck={ck}"

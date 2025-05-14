import secrets
from web3 import Web3
from eth_account import Account

def generate_ethereum_account():
    """Yangi Ethereum akkauntini generatsiya qilish"""
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    
    return {
        'address': account.address,
        'private_key': private_key
    }

def format_address(address):
    """Ethereum manzilini qisqartirib ko'rsatish"""
    if not address:
        return ""
    return address[:6] + "..." + address[-4:]

def validate_ethereum_address(address):
    """Ethereum manzilini tekshirish"""
    if not address:
        return False
    
    if not address.startswith('0x'):
        return False
        
    try:
        int(address, 16)
        
        return len(address) == 42
    except:
        return False
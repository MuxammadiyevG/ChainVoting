import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from flask import current_app

class BlockchainClient:
    def __init__(self, provider_url=None, contract_address=None):
        if provider_url is None:
            provider_url = current_app.config['BLOCKCHAIN_PROVIDER']
        
        if contract_address is None:
            contract_address = current_app.config.get('CONTRACT_ADDRESS')
        
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract = None
        
        # Admin akkountni sozlash
        self.admin_address = current_app.config.get('ADMIN_ADDRESS')
        self.admin_private_key = current_app.config.get('ADMIN_PRIVATE_KEY')
        
        # Kontraktni yaratish (agar manzil berilgan bo'lsa)
        if contract_address:
            try:
                # ABI ni o'qish
                with open('contracts/abi.json', 'r') as file:
                    contract_abi = json.load(file)
                
                # Kontraktni yaratish
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address), 
                    abi=contract_abi
                )
            except Exception as e:
                print(f"Kontraktni yaratishda xatolik: {str(e)}")
    
    def is_connected(self):
        return self.w3.is_connected()
    
    def is_contract_deployed(self):
        return self.contract is not None and self.w3.eth.get_code(self.contract.address) != b''
    
    def get_candidates_count(self):
        if not self.is_contract_deployed():
            return 0
        try:
            return self.contract.functions.candidatesCount().call()
        except Exception as e:
            print(f"Kandidatlarni sanashda xatolik: {str(e)}")
            return 0
    
    def get_candidate(self, candidate_id):
        if not self.is_contract_deployed():
            return (0, "", 0)
        try:
            return self.contract.functions.getCandidate(candidate_id).call()
        except Exception as e:
            print(f"Nomzod ma'lumotlarini olishda xatolik: {str(e)}")
            return (0, "", 0)
    
    def has_voted(self, voter_address):
        if not self.is_contract_deployed():
            return False
        try:
            return self.contract.functions.hasVoted(voter_address).call()
        except Exception as e:
            print(f"Ovoz berganligini tekshirishda xatolik: {str(e)}")
            return False
    
    def is_election_active(self):
        if not self.is_contract_deployed():
            return False
        try:
            started = self.contract.functions.electionStarted().call()
            ended = self.contract.functions.electionEnded().call()
            return started and not ended
        except Exception as e:
            print(f"Saylov holatini tekshirishda xatolik: {str(e)}")
            return False
    """  
    def add_candidate(self, name):
        if not self.is_contract_deployed() or not self.admin_address or not self.admin_private_key:
            raise Exception("Kontrakt o'rnatilmagan yoki admin kredentsiallari yo'q")
            
        nonce = self.w3.eth.get_transaction_count(self.admin_address)
        
        txn = self.contract.functions.addCandidate(name).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': self.admin_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    """
    def add_candidate(self, name):
        if not self.is_contract_deployed() or not self.admin_address or not self.admin_private_key:
            raise Exception("Kontrakt o'rnatilmagan yoki admin kredentsiallari yo'q")
            
        nonce = self.w3.eth.get_transaction_count(self.admin_address)
    
        txn = self.contract.functions.addCandidate(name).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': self.admin_address
        })
    
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
    
        logs = self.contract.events.CandidateAdded().process_receipt(receipt)
        candidate_id = logs[0]['args']['candidateId'] if logs else self.get_candidates_count()
    
        return candidate_id

    def start_election(self):
        if not self.is_contract_deployed() or not self.admin_address or not self.admin_private_key:
            raise Exception("Kontrakt o'rnatilmagan yoki admin kredentsiallari yo'q")
            
        nonce = self.w3.eth.get_transaction_count(self.admin_address)
        
        txn = self.contract.functions.startElection().build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': self.admin_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    
    def end_election(self):
        if not self.is_contract_deployed() or not self.admin_address or not self.admin_private_key:
            raise Exception("Kontrakt o'rnatilmagan yoki admin kredentsiallari yo'q")
            
        nonce = self.w3.eth.get_transaction_count(self.admin_address)
        
        txn = self.contract.functions.endElection().build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': self.admin_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    
    def vote(self, voter_private_key, voter_address, candidate_id):
        if not self.is_contract_deployed():
            raise Exception("Kontrakt o'rnatilmagan")
            
        nonce = self.w3.eth.get_transaction_count(voter_address)
        
        txn = self.contract.functions.vote(candidate_id).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': voter_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=voter_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    
    def get_all_candidates(self):
        candidates = []
        count = self.get_candidates_count()
        
        for i in range(1, count + 1):
            candidate_data = self.get_candidate(i)
            candidates.append({
                'id': candidate_data[0],
                'name': candidate_data[1],
                'votes': candidate_data[2]
            })
            
        return candidates
    
    
    
    #1 ETH yuborish
    def send_eth(self, recipient_address, amount_eth):
        amount_wei = self.w3.to_wei(amount_eth, 'ether')
        nonce = self.w3.eth.get_transaction_count(self.admin_address)

        txn = {
            'to': recipient_address,
            'value': amount_wei,
            'gas': 21000,  # ETH transferi uchun standart gaz limiti
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'chainId': self.w3.eth.chain_id
        }

        signed_txn = self.w3.eth.account.sign_transaction(txn, self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
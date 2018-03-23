import json
from bitcoinrpc.authproxy import AuthServiceProxy
from django.conf import settings

def biblepay_client_factory(network):
    """ creates and returns the biblepay client for rpc commands """
    
    conn = settings.BIBLEPAY_RPC[network]
    
    url = "http://%s:%s@%s:%s" % (conn['USER'], conn['PASSWORD'], conn['IP'], conn['PORT'])    
    return AuthServiceProxy(url)

class BlockNotFound(Exception):
    pass

class UnknownServerMessage(Exception):
    pass

class BiblePayRpcClient(object):
    """ this is a BiblePay rpc client, used in the PurePool.
        We use it to make it easier and more "python-like" in usage when needed """
    
    def __init__(self, network):
        self.rpc = biblepay_client_factory(network)

    def hexblocktocoinbase(self, block_hex, transaction_hex):
        """ takes the block hex and the transaction hex and returns the the coinbase information.
        Result might looks like this:
        {'txid': 'd92371a21f9e135ba2413db3123fdedec0854d2b5558a25544468613d3556184', 'subsidy': 5492,
        'blockversion': '1.0.8.9', 'biblehash': '0000000523d2e7fbcf914f9703ad19eb3dbaf99637ba69fad4a0707398002614',
        'Command': 'hexblocktocoinbase', 'recipient': 'BA3cgTBNea2jrChntZQz4fJbNFzyGtuttx'}
        """

        return self.rpc.exec('hexblocktocoinbase',block_hex, transaction_hex)

    def pinfo(self):
        """ returns some information about the current mining.
        Result looks like:
        {
          "Command": "pinfo",
          "height": 31369,
          "pinfo": 7424,
          "elapsed": 29
        }
        We want the "pinfo" field, which is the max nounce we accept
        """

        return self.rpc.exec('pinfo')

    def subsidy(self, height):
        data = self.rpc.exec("subsidy", str(height))

        if data.get('error', None) == 'block not found':
            raise BlockNotFound()

        if data.get('error', None) is not None:
            raise UnknownServerMessage()

        return data
    
    def bible_hash(self, block_hash, block_time, prev_block_time, prev_height, nonce):
        """ calculates the biblehash via the biblepay client, as this is a little bit tricks
            to get right, so we won't do it here on our own.
            
            Have a look in the kvj.ccp 
            """
            
        data = self.rpc.exec("biblehash", block_hash, block_time, prev_block_time, prev_height, nonce)
        
        bible_hash = None
        try:
            bible_hash = data['BibleHash']
        except:
            raise UnknownServerMessage()
        
        return bible_hash
    
    def decoderawtransaction(self, txhex):
        return self.rpc.decoderawtransaction(txhex)
    
    def sendtoaddress(self, address, amount, comment="", comment_to="", subtractfeefromamount=True):
        """ sends bbp to another address. Required are only address and amount
            Note: subtractfeefromamount is default TRUE here, as it should not be the pool
            who pays the fee! """

        return self.rpc.sendtoaddress(address, amount, comment, comment_to, subtractfeefromamount)
    
    def getwalletinfo(self):
        return self.rpc.getwalletinfo()
    
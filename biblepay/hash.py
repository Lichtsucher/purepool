
def check_hashtarget(bible_hash, target):
    """ tests if the biblepay hash is valid for the hashtarget, means that is it lower.
        True = is lower and all is fine """

    rs = False
    try:
        rs = int(bible_hash, 16) < int(target, 16)
    except:
        pass

    return rs

def validate_bibleplay_address_format(address):
    """ ensures that the address given looks like a valid biblepay address """
  
    # the addresses are always 34 chars long
    if len(address) != 34:
        return False
    
    # real addresses start with a B, testnet with an y
    if not address[0] in ['B', 'y']:
        return False
    
    # and they only consists of a-z, A-Z and 0-9
    if not address.isalnum():
        return False
    
    return True

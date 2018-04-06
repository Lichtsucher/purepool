from django.core.cache import cache

def GetHashTarget(miner_id, network_id):
    """ The HashTarget we generate here is the highest value of any HashTarget from the client
        we accept as a solution for the given Work.
        We also control bad miners with that when we higher the HashTarget for them
        """

    hash_target = '0000011110000000000000000000000000000000000000000000000000000000000000000000000000000'

    hash_target = hash_target[0:64]

    return hash_target



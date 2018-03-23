from django.core.cache import cache
from purepool.models.miner.models import Miner

def GetHashTarget(miner_id, network_id):
    """ The HashTarget we generate here is the highest value of any HashTarget from the client
        we accept as a solution for the given Work.
        We also control bad miners with that when we higher the HashTarget for them
        """

    hash_target = '0000011110000000000000000000000000000000000000000000000000000000000000000000000000000'

    key = 'miner_id_rating__' + str(miner_id)
    rating = cache.get(key, None)

    if rating is None:
        miner = Miner.objects.get(pk=miner_id)
        rating = miner.rating
        cache.set(key, rating)
    
    if rating < 0:
        positive_rating = rating * -1    #  -2 * -1 = 2
        hash_target = hash_target[positive_rating:]

    if rating > 0:
        hash_target = '0' * rating + hash_target  # '0' * 4 + 'xyz'  > 0000xyz
    
    hash_target = hash_target[0:64]

    return hash_target



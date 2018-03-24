import uuid
import datetime
from django.db import models
from django.db.models import Count, Sum
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.utils import timezone
from biblepay.hash import validate_bibleplay_address_format

class MinerNotFound(Exception):
    pass

class MinerNotEnabled(Exception):
    pass

class InvalidMiner(Exception):
    pass

class InvalidBiblepayAddress(Exception):
    pass

class WorkerNotFound(Exception):
    pass

def get_miner_id_by_address(network, address):
    """ returns the miner database id by the address. Uses the cache to speed up everything """
    
    key = 'miner_id__%s__%s' % (network.replace(' ', '__'), address.replace(' ', '__'))
    miner_id = cache.get(key, None)
    
    if miner_id == 'DISABLED':
        raise MinerNotEnabled
    
    if miner_id is None:
        try:
            miner_data = Miner.objects.filter(address=address, network=network).values('id', 'enabled')[0]
            miner_enabled = miner_data['enabled']
            miner_id = miner_data['id']
        except:
            raise MinerNotFound()

        # a miner that is not enabled is of no use, so we do not allow them.
        # they must be disabled for a good reason
        if not miner_enabled:
            cache.set(key, 'DISABLED')
            raise MinerNotEnabled
        
        cache.set(key, miner_id)
    
    return miner_id

def get_worker_id_by_name(network, address, worker_name):
    """ returns the workers database id by itsname (and its miner address). Uses the cache to speed up everything """
    
    key = 'miner_id__%s__%s__%s' % (network, address.replace(' ', '__'), worker_name.replace(' ', '__'))
    worker_id = cache.get(key, None)
    
    if worker_id is None:
        miner_id = get_miner_id_by_address(network, address) # can raise MinerNotFound!
       
        try:
            worker_id = Worker.objects.filter(miner_id=miner_id, name=worker_name).values('id')[0]['id']            
        except:
            raise WorkerNotFound
        
        cache.set(key, worker_id)
    
    return worker_id

def get_or_create_miner_worker(network, address, worker_name):
    """ tries to find the miner_id and worker_id (db-ids) in the cache or the database.
        If it can not be found, new entries will be created.
        if a miner is disabled, MinerNotEnabled will be raised
        """
        
    if not validate_bibleplay_address_format(address):
        raise InvalidBiblepayAddress()
    
    miner_id = None
    try:
        # this can raise MinerNotEnabled, that will be not catched here
        miner_id = get_miner_id_by_address(network, address)
    except MinerNotFound:
        pass
    
    if miner_id is None:
        miner = Miner(address=address, network=network)
        miner.save(force_insert=True)
        miner_id = miner.id
    
    worker_id = None
    try:
        # this can raise MinerNotEnabled, that will be not catched here
        worker_id = get_worker_id_by_name(network, address, worker_name)
    except WorkerNotFound:
        pass
    
    if worker_id is None:       
        worker = Worker(miner_id=miner_id, name=worker_name)
        worker.save(force_insert=True)
        worker_id = worker.id
    
    return miner_id, worker_id


class Miner(models.Model):
    # we use a uuid for the miner id as this id will be visible in the transactions
    # we do not want any funny attacks by having guessable ids
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # the target bbp address of the miner
    address = models.CharField(max_length=100, unique=True)

    # indeed, we need the network, as we might support test and main at the same time
    network = models.CharField(max_length=20)

    # the rating is used in the Worker Difficutly calculation to ensure that no ineffective
    # miner steals shares
    # Ratings:
    #  -2 = Extremly good miner. Very Easy difficulty
    #  -1 = Very good miner. Easy difficulty
    #   0 = Default. Normal difficutly
    #   1 = Little bit bad miner, littly bit harder diffituly
    #   2 = Bad miner, lot harder
    #   3 = Extremly bad miner. VERY hard diffictuly
    rating = models.IntegerField(default=0)

    # an info-only field. The ratio is the base for the rating and is calculated by
    # comparing the users shares per block with the shares/block of other miners
    ratio = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    # The percent different between the miner ratio and the average int he pool
    percent_ratio = models.DecimalField(max_digits=14, decimal_places=4, default=100)

    # the cached balance for this user
    # Calculated based upon the transactions
    balance = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    # small cache field to identify old accounts
    last_accepted_solution_at = models.DateTimeField(null=True, default=None)
    
    # if we want to disable a miner, we do it here
    enabled = models.BooleanField(default=True)
    
    # when the miner was created
    inserted_at = models.DateTimeField(auto_now_add=True)

    def update_balance(self):
        """ updates the balance cache """
        
        # import here to prevent an import loop
        from puretransaction.models import Transaction

        self.balance = Miner.calculate_miner_balance(self.network, self.id)
    
    @staticmethod
    def calculate_miner_balance(network, miner_id):
        """ calculates the miner balance """
        
        # import here to prevent an import loop
        from puretransaction.models import Transaction

        return Transaction.objects.filter(network=network, miner_id=miner_id).aggregate(Sum('amount'))['amount__sum']
    
    @staticmethod
    def get_active_worker(network, address, days_age=1):
        """ returns a list of workers of a miners that sendet solutions in the last 24h """
        
        # we import it here, to prevent an import loop
        from purepool.models.solution.models import Solution
        
        d = timezone.now() - datetime.timedelta(days=days_age)
        
        worker_solutions = Solution.objects.filter(miner__address=address, miner__network=network, inserted_at__gte=d).values('work__worker_id').annotate(worker_count=Count('work__worker_id'))[0:100]
        workers = Worker.objects.filter(miner__address=address)[0:100] # 100 miner are enough...
        
        result = []
        for ws in worker_solutions:
            for worker in workers:
                if worker.id == ws['work__worker_id']:
                    result.append([worker, ws['worker_count']])
                    
        return result

class Worker(models.Model):
    """ The worker is the biblepayd software itself, identified by a name given in
        the workerid field of biblepay.conf
        Example:
        workerid=BKNSAuBM1JggcaBgecW2PZ1mogKMCeB5pL/MyMiner1
        
        Means:
         Miner/Account -> BKNSAuBM1JggcaBgecW2PZ1mogKMCeB5pL
         Worker -> MyMiner1
        
        """

    miner = models.ForeignKey(Miner, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    # when the worker was created
    inserted_at = models.DateTimeField(auto_now_add=True)

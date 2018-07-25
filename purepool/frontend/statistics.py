import datetime
from cache_memoize import cache_memoize
from django.utils import timezone
from django.db.models import Count, Sum
from purepool.models.miner.models import Miner
from purepool.models.block.models import Block
from purepool.models.solution.models import Solution, RejectedSolution
from puretransaction.models import Transaction

@cache_memoize(timeout=3600)
def get_solution_statistics(network, days=7):
    return _get_solution_statistics(network, days=7)

@cache_memoize(timeout=300)
def get_miner_solution_statistics(network, miner_id=None, days=7):
    return _get_solution_statistics(network, miner_id=miner_id, days=7)

def _get_solution_statistics(network, miner_id=None, days=7):
    """ loads the count of solved solutions for the pool
        or only a single miner id for x-days.
        Should only be used on a cached page """

    result = []

    for i in range(0, days):
        day = timezone.now() - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)

        qs = Solution.objects.filter(network=network, inserted_at__gt=day_start, inserted_at__lt=day_end)
        if miner_id is not None:
            qs = qs.filter(miner_id=miner_id)

        count = qs.count()

        result.append((day.date, count))

    result = reversed(result)

    return result

@cache_memoize(timeout=3600)
def get_block_statistics(network, days=7):

    """ loads the count of found blocks for x-days.
        Should only be used on a cached page """

    result = []

    for i in range(0, days):
        day = timezone.now() - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)

        count = Block.objects.filter(network=network, pool_block=True, inserted_at__gt=day_start, inserted_at__lt=day_end).count()

        result.append((day.date, count))

    result = reversed(result)

    return result

@cache_memoize(timeout=3600)
def get_top_miners(network, days=1):
    """ the list of top miners """
    days24_dt = timezone.now() - datetime.timedelta(days=days)
    return Solution.objects.filter(network=network, miner__enabled=True, inserted_at__gte=days24_dt).values('miner__address').annotate(total=Count('miner_id')).order_by('-total')[0:100]

@cache_memoize(timeout=186400)
def get_miner_count(network, days):
    """ miner count is cached longer, as it is expensice to count by the solutions """

    days_dt = timezone.now() - datetime.timedelta(days=days)
    miners_count = len(Transaction.objects.filter(network=network, inserted_at__gte=days_dt).values('miner_id').annotate(total=Count('miner_id')))

    return miners_count

@cache_memoize(timeout=3600)
def get_basic_statistics(network, days):
    """ some statistics for the statistics page about the pool and the network """

    days_dt = timezone.now() - datetime.timedelta(days=days)

    current_height = 0
    try:
        current_height = Block.objects.filter(network=network).values('height').order_by('-height')[0]['height']
    except IndexError: # db empty
        pass

    all_blocks = Block.objects.filter(network=network, inserted_at__gte=days_dt).count()
    pool_blocks = Block.objects.filter(network=network, pool_block=True, inserted_at__gte=days_dt).count()

    pool_blocks_percent = 0
    try:
        pool_blocks_percent = round((100 / all_blocks) * pool_blocks, 2)
    except ZeroDivisionError: # if no block was found, this can happen
        pass

    bbp_mined = Block.objects.filter(network=network, pool_block=True, inserted_at__gte=days_dt).aggregate(Sum('subsidy'))['subsidy__sum']

    return [current_height, all_blocks, pool_blocks, pool_blocks_percent, bbp_mined]

@cache_memoize(timeout=360)
def miner_error_message_statistic(network, miner_id, days=1):
    days_dt = timezone.now() - datetime.timedelta(days=days)
    
    return RejectedSolution.objects.filter(network=network, miner_id=miner_id, inserted_at__gte=days_dt).exclude(exception_type='').exclude(exception_type='TransactionTampered').values('exception_type', 'work__worker__name').annotate(total=Count('id'))
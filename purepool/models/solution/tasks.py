import datetime
import random
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.db import connection
from celery import shared_task
from bitcoinrpc.authproxy import JSONRPCException
from purepool.interface.formats import SolutionString
from purepool.models.solution.models import Solution, Work, RejectedSolution
from purepool.models.miner.models import Miner
from biblepay.clients import BiblePayRpcClient
from biblepay.hash import check_hashtarget

class HashTargetExceeded(Exception):
    pass

class BibleHashAlreadyKnown(Exception):
    pass

class BibleHashWrong(Exception):
    pass

class InvalidSolution(Exception):
    pass

class UnknownWork(Exception):
    pass

class TransactionInvalid(Exception):
    pass

class TransactionTampered(Exception):
    pass

class Biblepayd_Outdated(Exception):
    pass

class Invalid_CPID(Exception):
    pass

class Illegal_CPID(Exception):
    pass

def validate_solution(network, solution_string):
    """ the validation of a solution is a multi-step part
        done here. We need to:
        - check the target hash
        - calculate the biblehash
        - ensure that the biblehash is unique
        - and check if the transaction really is for OUR pool address! """

    # we load the work, as it contains the hash target
    # the solutions biblehash must be lower then the hash target, or
    # we will not accept it
    # If the Work does not exists, we will fail here (fast)
    try:
        work = Work.objects.get(pk=solution_string.get_work_id(), network=network)
    except Work.DoesNotExist as e:
        raise UnknownWork

    # biblehash must be lower then the hashtarget
    if not check_hashtarget(solution_string.get_bible_hash(), work.hash_target):
        raise HashTargetExceeded()

    # next we calculate the biblehash from the elements given
    # if this is successfull
    client = BiblePayRpcClient(network)
    bible_hash = client.bible_hash(
        solution_string.get_block_hash(),
        solution_string.get_block_time(),
        solution_string.get_prev_block_time(),
        solution_string.get_prev_height(),
        solution_string.get_nonce(),
    )

    if bible_hash != solution_string.get_bible_hash():
        raise BibleHashWrong()

    # Check if the target address of the block is the one from our pool!
    # This is a very important check, without it, people could send in
    # solutions that are not meant for our pool
    addresses = []
    try:
        coinbase = client.hexblocktocoinbase(solution_string.get_block_hex(), solution_string.get_transaction_hex())
        addresses = [coinbase.get('recipient', None)]
    except (JSONRPCException, TypeError):
        raise TransactionInvalid()

    if not settings.POOL_ADDRESS[network] in addresses:
        raise TransactionTampered('Invalid recipient')

    # we only accept solutions from users with a valid CPID.
    # From 1.1.1.1c, the biblepay client returns a info about that in the
    # hexblocktocoinbase request
    if not 'cpid_sig_valid' in coinbase:
        raise Biblepayd_Outdated('cpid_sig_valid missing. Upgrade to 1.1.1.c or later')

    if not coinbase['cpid_sig_valid']:
        raise Invalid_CPID()

    if not coinbase['cpid_legal']:
        raise Illegal_CPID()

    # this is a check on the nonce, it must be smaller then the currently
    # allowed max nonce value. If not, somebody tried something bad
    pinfo = client.pinfo()
    if int(solution_string.get_nonce()) > int(pinfo.get('pinfo', 0)):
        raise TransactionTampered('Nonce height wrong')

    # we also only accept the solution if the given prev_block is really
    # the current height of the blockchain
    if int(solution_string.get_prev_height()) != int(pinfo['height']):
        raise TransactionTampered('Wrong height')

    return True

def calculate_multiply(solution_string):
    """ Some miners are punished for being bad at finding blocks,
        while others are boosted for being good at that. """

    miner_id = str(solution_string.get_miner_id())
    key = 'miner_id__percent_ratio__' + miner_id
    percent_ratio = cache.get(key, None)

    multiply_solution = 1 # default

    if percent_ratio is None:
        miner = Miner.objects.get(pk=miner_id)
        percent_ratio = miner.percent_ratio
        cache.set(key, percent_ratio)

    if percent_ratio > 120:
        # we only allow the solution if the random value
        # is under 101. The higher the percent_ratio, the more unlikely
        # it if that this is true, so more solutions are dropped
        rand_val = random.randrange(0, int(percent_ratio))
        if rand_val > 100:
            multiply_solution = 0

    if percent_ratio < 30:
        multiply_solution = 4
    elif percent_ratio < 40:
        multiply_solution = 3
    elif percent_ratio < 60:
        multiply_solution = 2

    return multiply_solution

@shared_task()
def process_solution(network, solution_s):
    """ called by the celery task queue
        Does the validation and processing of a new solution """
        
    # https://en.bitcoin.it/wiki/Block_hashing_algorithm
    solution_string = SolutionString(solution_s)


    # before we start, we check if we wan't to keep the solution at all,
    # or if the percent ratio is to bad
    multiply_solution = calculate_multiply(solution_string) # very good miners are getting there solutions multiplied to reach 100%
    
    if multiply_solution == 0: # droped because of low percent_ratio? Then we can leave here
        return

    # first, we check if the biblehash already exists. If yes, we ignore the solution
    # This way, we can skip all the later parts of checking the solution and speed up
    # everything
    hashes = Solution.objects.filter(bible_hash=solution_string.get_bible_hash()).values('bible_hash')
    if len(hashes) > 0:
        raise BibleHashAlreadyKnown()

    valid = False
    try:
        valid = validate_solution(network, solution_string)
    except Exception as ex:
        rsol = solution_s
            
        exception_type = type(ex).__name__

        rsolution = RejectedSolution(
            work_id = solution_string.get_work_id(),
            miner_id = solution_string.get_miner_id(),
            network = network,

            bible_hash = solution_string.get_bible_hash(),
            solution = rsol,
            hps=0,
           exception_type = exception_type,
        )
        rsolution.save()        
        
        raise # still raise the error to the level above

    if not valid: 
        raise InvalidSolution()

    # calculated hashes per second. Only for some statitics and leaderboards,
    # but meaningless for all later calculations
    # Same as on the original pool
    runtime = solution_string.get_timer_end() - solution_string.get_timer_start()
    hps = 1000 * solution_string.get_hash_counter() / runtime

    # with everything checked, we insert the solution into the database
    # we also do the multi insert here for good miners
    for r in range(0, multiply_solution):
        bible_hash = solution_string.get_bible_hash()

        if r > 0:
            bible_hash += '#'+str(r)

        solution = Solution(
            work_id = solution_string.get_work_id(),
            miner_id = solution_string.get_miner_id(),
            network = network,

            bible_hash = bible_hash,
            solution = '', # no longer needed

            hps = hps,
        )
        solution.save()
    
    
    
@shared_task()
def cleanup_solutions():
    """ removes old works, solutions and rejected solutions from the database.
        We use raw sql, as djangos delete queries are very slow as bulk queries """
    
    dformat = '%Y-%m-%d %H:%M:%S'

    with connection.cursor() as cursor:

        # rejected solutions are not required for long
        min_date = timezone.now() - datetime.timedelta(days=settings.POOL_CLEANUP_REJECTED_MAXDAYS)
        sql = 'DELETE FROM solution_rejectedsolution WHERE inserted_at < "'+min_date.strftime(dformat)+'"'
        cursor.execute(sql)

        # and remove old entries
        min_date = timezone.now() - datetime.timedelta(days=settings.POOL_CLEANUP_MAXDAYS)
        sql = 'DELETE FROM solution_solution WHERE inserted_at < "'+min_date.strftime(dformat)+'"'
        cursor.execute(sql)

        min_date = timezone.now() - datetime.timedelta(days=settings.POOL_CLEANUP_MAXDAYS+2) # work is used longer, so we need to keep it longer
        sql = 'DELETE FROM solution_work WHERE inserted_at < "'+min_date.strftime(dformat)+'"'
        cursor.execute(sql)

        # remove solution content after x days. Solutions entries itself are stored longer, see above
        min_date_solutions = timezone.now() - datetime.timedelta(days=settings.POOL_SOLUTION_CONTENT_KEEP_DAYS)
        Solution.objects.filter(inserted_at__lt=min_date_solutions).update(solution='')






        
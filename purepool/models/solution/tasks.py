import datetime
from django.utils import timezone
from django.conf import settings
from celery import shared_task
from bitcoinrpc.authproxy import JSONRPCException
from purepool.interface.formats import SolutionString
from purepool.models.solution.models import Solution, Work, RejectedSolution
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

@shared_task()
def process_solution(network, solution_s):
    """ called by the celery task queue
        Does the validation and processing of a new solution """
        
    # https://en.bitcoin.it/wiki/Block_hashing_algorithm

    solution_string = SolutionString(solution_s)

    # first, we check if the biblehash already exists. If yes, we ignore the solution
    # This way, we can skip all the later parts of checking the solution and speed up
    # everything
    hashes = Solution.objects.filter(bible_hash=solution_string.get_bible_hash()).values('bible_hash')
    if len(hashes) > 0:
        raise BibleHashAlreadyKnown()

    valid = False
    try:
        valid = validate_solution(network, solution_string)
    except:
        rsolution = RejectedSolution(
            work_id = solution_string.get_work_id(),
            miner_id = solution_string.get_miner_id(),
            network = network,

            bible_hash = solution_string.get_bible_hash(),
            solution = solution_s,
            hps=0
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
    solution = Solution(
        work_id = solution_string.get_work_id(),
        miner_id = solution_string.get_miner_id(),
        network = network,

        bible_hash = solution_string.get_bible_hash(),
        solution = solution_s,

        hps = hps,
    )
    solution.save()
    
@shared_task()
def cleanup_solutions():
    """ removes old works, solutions and rejected solutions from the database """
    
    min_date = timezone.now() - datetime.timedelta(days=settings.POOL_CLEANUP_MAXDAYS)
    
    Work.objects.filter(inserted_at__lt=min_date).delete()
    Solution.objects.filter(inserted_at__lt=min_date).delete()
    RejectedSolution.objects.filter(inserted_at__lt=min_date).delete()
        
        
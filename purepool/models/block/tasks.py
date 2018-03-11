import datetime
import decimal
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Min, Count
from biblepay.clients import BiblePayRpcClient, BlockNotFound
from purepool.models.block.models import Block
from purepool.models.solution.models import Solution
from purepool.models.miner.models import Miner
from puretransaction.models import Transaction

@shared_task()
def find_new_blocks(network, mark_as_processed=False, max_height=None):
    """ Asks the biblepay client for new blocks and put them into our database.
    
        If mark_as_processed is True, all pool-blocks will be marked as
        "process_status=FI" which is usefull if you setup a second pool version
        with the same addresses and do not want to re-process the old blocks.
        
        For the same purpose, you can set max_height. if max_height is not None,
        no block greater then max_height will be get.
        """

    # first, we ensure that the network is allowed
    if not network in settings.BIBLEPAY_NETWORKS:
        return

    # we find the current highest block
    current_max_height = Block.objects.filter(network=network).aggregate(Max('height'))['height__max']
        
    # is this the first time we run the script? -> no blocks in the db
    # then we want the first (0) block
    if current_max_height is None:
        next_max_height = 1
    else:
        # if not, then we want the NEXT block in the list
        next_max_height = current_max_height +1
    
    client = BiblePayRpcClient(network=network)
    
    # we loop until no new block is found
    while True:
        # have we reached the (optional) max_height?
        if max_height is not None and next_max_height > max_height:
            break

        # now we ask the biblepay client for the block information
        subsidy = None
        try:
            subsidy = client.subsidy(next_max_height)
        except BlockNotFound: # block not in the list (yet)
            break

        # no data found? then we end here
        if subsidy is None:
            break

        # the reward for the block. A MUST HAVE!
        subsidy_amount = None
        try:
            subsidy_amount = subsidy.get('subsidy', None)
        except:
            pass
        if subsidy_amount is None:
            break

        # is this block one of ours?
        pool_block = False
        miner = None
        if subsidy.get('recipient') == settings.POOL_ADDRESS[network]:
            pool_block = True
            
            # we now try to get the miner by ids "minerguid"            
            try:
                miner = Miner.objects.get(pk=subsidy.get('minerguid', None))
            except:
                pass
        
        # are all of our blocks to be marked as "processed"?
        process_status = 'OP'
        if pool_block and mark_as_processed:
            process_status = 'FI'
            
        # and finally, we save the block to the database.
        # in the next step, if processed=False and pool_block=True,
        # the task "process_next_block" will take the block and use it
        block = Block(
            height=next_max_height,
            pool_block=pool_block,
            process_status=process_status,
            network=network,
            miner=miner,
            subsidy=subsidy_amount,
            recipient=subsidy.get('recipient', ''),
            
            # and some statistics
            block_version=subsidy.get('blockversion', ""),
            block_version2=subsidy.get('blockversion2', ""),
        )
        block.save()
        
        # next round with a inceased height
        next_max_height += 1

@shared_task()
def process_next_block(network):
    """ Tries to find the next block to process. Will only process one block and
        then end.
        It simply marks all solutions that are not assigned to any block and older
        then the block and assign them to this block.
        Nothing more is done, as the block needs to mature first
        ( = must be accepted by the network)
    
        The next block is then found in the next call of this function (via cron).
        We do this to prevent problems with overlong running tasks. But it shouldn't
        happen anyway that more then one block is found between runs of this task. """
    
    # find the lowest (oldest) block in the current network that is a pool block and is waiting to
    # be processed
    lowest_pool_waiting_height = Block.objects.filter(network=network, pool_block=True, process_status='OP').aggregate(Min('height'))['height__min']
    if lowest_pool_waiting_height is None: # no unprocessed block found
        return
    
    block = Block.objects.get(network=network, height=lowest_pool_waiting_height)
    
    with transaction.atomic():
        # before the start, we set the block as processed, so that no other job takes it
        block.process_status = 'BP'
        block.save()

        # we now mark all solutions that are older then the block with this block,
        # so that no other script will take them
        Solution.objects.filter(
            network=network,
            processed=False,
            block__isnull=True,
            inserted_at__lt=block.inserted_at
        ).update(block=block)

def calculate_miner_subsidy(subsidy):
    return subsidy - (subsidy / 100 * settings.POOL_FEE_PERCENT)

@shared_task()
def shareout_next_block(network, block_height=None, dry_run=False):
    """ Tries to find the oldest block that had matured and was not yet processed for
        shares. Optional, a specific block can be given.
        This task takes this block, calculates the shares of all users that contributed
        to the block and creates the transactions with there bbps.
        Important: The bbp will not send here, this is an extra step, done when the
        transaction limit is reached for a user

        Dry run will not save anything to the database.
        """


    if settings.TASK_DEBUG:
        print("Debug | ", "Shareout started with network", network, "on block ", block_height, " in dry-run", dry_run)

    # we only start here, if no block is currently processed
    # not important in dry_run
    if not dry_run and Block.objects.filter(network=network, pool_block=True, process_status='PS').count() > 0:
        if settings.TASK_DEBUG:
            print("Debug | ", "Another block is currently processed/has status 'PS'")
        return


    # try to find the oldest block then is OLDER then 1 day
    # (so it had matured -> the network had accepted it) and take it
    age = timezone.now() - datetime.timedelta(hours=settings.POOL_BLOCK_MATURE_HOURS[network])

    if block_height is None:
        lowest_pool_waiting_height = Block.objects.filter(
            network=network,
            pool_block=True,
            process_status='BP',
            inserted_at__lt=age
        ).aggregate(Min('height'))['height__min']
    
        if lowest_pool_waiting_height is None: # no unprocessed block found
            return
    else:
        lowest_pool_waiting_height = block_height

    block = Block.objects.get(network=network, height=lowest_pool_waiting_height)
    
    if settings.TASK_DEBUG:
        print("Debug | ", "Loaded block from database:", block.height, block.network, block.process_status, block.inserted_at)

    # before we start, we mark the block as in-process of the shares
    with transaction.atomic():
        block.process_status = 'PS' # Processing shares
        if not dry_run:
            block.save()
    
    # if we found a block, we ensure that is still ours!
    client = BiblePayRpcClient(network=network)
    subsidy = client.subsidy(lowest_pool_waiting_height)
    
    if settings.TASK_DEBUG:
        print("Debug | ", "Requested subsidy: ", subsidy)
    
    if subsidy.get('recipient') != settings.POOL_ADDRESS[network]:
        block.process_status = 'ST' # stale
        if not dry_run:
            block.save()
        return
    
    # now we count the users solutions for the block
    # Important: Do not remove the ".order_by()", as it is required, or the result
    # will be wrong (seems to be a django problem)
    qs = Solution.objects.filter(network=network, block=block, ignore=False)

    if not dry_run: # in reall live, we only want entries that where not already processed
        qs = qs.filter(processed=False)

    solution_counts = qs.values('miner_id').annotate(total=Count('miner_id')).order_by()

    # with that, we first calculate the total amount of relevant shares
    total_count = 0
    for solution_count in solution_counts:
        total_count += solution_count['total']

    if settings.TASK_DEBUG:
        print("Debug | ", "Solution count is ", total_count)
        print("Debug | ", "Miner/solution count is ", len(solution_counts))
        
    # if there are no shares, then there is nothing todo here anymore
    if total_count == 0:
        block.process_status = 'FI' # finished
        if not dry_run:
            block.save()
        return
    
    # same if the block.subsidy is buggy
    if block.subsidy == 0:
        block.process_status = 'FI' # finished
        if not dry_run:
            block.save()
        return
        
    # before we do the share calculation, we substract the fee from the subsidy
    miner_subsidy = block.subsidy
    if settings.POOL_FEE_PERCENT > 0:
        miner_subsidy = calculate_miner_subsidy(block.subsidy)

    if settings.TASK_DEBUG:
        print("Debug | ", "Miner subsidy is ", miner_subsidy)
    
    # calculcation of the amount of bbp per user based on the solutions of the block
    subsidy_per_solution = miner_subsidy / total_count

    if settings.TASK_DEBUG:
        print("Debug | ", "Subsidy per solution is ", subsidy_per_solution, "with a total of", (subsidy_per_solution * total_count))
    
    added_amount = 0

    # and now we add the transactions that add the coins to the user
    # they are not send to the user here, that will be done by a different script
    with transaction.atomic():
        for solution_count in solution_counts:
            user_subsidy = subsidy_per_solution * solution_count['total']
            
            inote = 'BLOCK:'+str(block.height)+'|SOLUTIONS:'+str(solution_count['total'])
        
            tx = Transaction(
                network = network,
                miner_id = solution_count['miner_id'],
                amount = user_subsidy,
                category = 'MS',
                        
                # some notes for the user and some for us
                note = 'Share for block %s' % block.height,
                internal_note = inote,
            )
            if not dry_run:
                tx.save()

            added_amount += user_subsidy
    
        # last but not least, we mark the block and the solutions as processed
        if not dry_run:
            Solution.objects.filter(network=network, processed=False, block=block).update(processed=True)
        
        # and we mark the block as finished
        block.process_status = 'FI' # finished
        if not dry_run:
            block.save()

    if settings.TASK_DEBUG:
        print("Debug | ", "Created transaction with a total amount of ", added_amount)
        
    # last, we update the user balances. We do this in a new step, as the step before is more important
    # and should be done as fast as possible
    # We do not load the miner from the database, we only update it. This is faster
    if not dry_run:
        update_list = []
        with transaction.atomic():
            for solution_count in solution_counts:
                value = Miner.calculate_miner_balance(network, solution_count['miner_id'])
                Miner.objects.filter(pk=solution_count['miner_id']).update(balance=value)



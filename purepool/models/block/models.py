import datetime
from django.utils import timezone
from django.db import models
from django.utils.translation import gettext as _
from purepool.models.miner.models import Miner

BLOCK_PROCESS_STATUS_CHOICES = (
    ('OP', 'Open'),
    ('BP', 'Basics processed'),
    ('PS', 'Processing shares'),
    ('FI', 'Finished'),
    ('ST', 'Stale')
)

class Block(models.Model):
    """ A list of all blocks in the chains. Mostly used to identify new block for us
        We do not use the "pk"/"id" for the block number, as this would prevent us from
        saving test and main blocks at the same time """

    # the block id/height from the chains
    height = models.IntegerField()

    # usefull if we want to support multiple networks (test, main...)
    network = models.CharField(max_length=20)        
    
    # is this a block of the pool?
    pool_block = models.BooleanField(default=False)
    
    # the miner who found the block
    miner = models.ForeignKey(Miner, null=True, on_delete=models.SET_NULL)
    
    # the reward of the block. Very important for the share calculation
    subsidy = models.IntegerField()
    
    # the target of the block. Doesn't need to be the one who created it,
    # as pool blocks always point to our pool, while someone else had
    # created it
    recipient = models.CharField(max_length=100)
    
    # additional information about the block
    block_version = models.CharField(max_length=100, blank=True)
    block_version2 = models.CharField(max_length=100, blank=True)
    
    # in what step of processing the block is at the moment.
    # Possible:
    #  OP = Open = nothing had been done with it
    #  BP = Processed = the solutions had been assigned to the block. From here on, we will wait 24h
    #  PS = Processing shares = The solutions are counted right now. This step might take longer, so we mark it. Will directly lead to "FI"
    #  FI = Finished = All work is done, the block is finished
    process_status = models.CharField(max_length=2, default="OP", choices=BLOCK_PROCESS_STATUS_CHOICES)
    
    # 24h after the block was first seen, we check if the block is
    # still ours, then we send the shares out, as the block has matured
    sharedout = models.BooleanField(default=False)
    
    # when the block was first seen
    inserted_at = models.DateTimeField(auto_now_add=True)    
            
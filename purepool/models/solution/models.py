import uuid
import datetime
from django.utils import timezone
from django.db import models
from django.utils.translation import gettext as _
from purepool.models.miner.models import Miner, Worker
from purepool.models.block.models import Block


class Work(models.Model):
    """ When a miner does a "readytomine2", it gets a Work as answer.
        Later, when a Solution is send, it will reference the Work here
        
        TODO Every day we will delete the work entries without solutions for
        more then 10 hours
        """

    # we use a uuid for the work to prevent the chance of anybody to guess it
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # when the work was created
    inserted_at = models.DateTimeField(auto_now_add=True)

    # we will only allow the Solution to a work by the same Worker who created it
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    thread_id = models.CharField(max_length=20)

    # we need the hash_target to compare it later
    hash_target = models.CharField(max_length=200)
    
    # indeed, we need the network, as we might support test and main at the same time
    network = models.CharField(max_length=20)
    
    # for statistics or banning
    ip = models.GenericIPAddressField()
    os = models.CharField(max_length=50)
    agent = models.CharField(max_length=50)

class BaseSolution(models.Model):

    # the work is the main reference for the Solution, from there we reference the worker and account
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    
    # we also save the miner here, as it speeds up lookups
    miner = models.ForeignKey(Miner, on_delete=models.CASCADE)

    # network, must be the same as in the work!
    network = models.CharField(max_length=20)

    # the calculated Biblehash. Must be unique
    bible_hash = models.CharField(max_length=100, unique=True)
    
    # holds the whole solution that can be splitted with purepool.interface.formats.SolutionString
    solution = models.TextField()

    # hashes per second. Only for some nices graphics, as it can be faked.
    hps = models.IntegerField(default=0)
    
    # will be set True when the solution was processed to calculate the shares for a found block
    processed = models.BooleanField(default=False, db_index=True)
    
    # when this solution was processed as part of a block, we set the block here
    # as a "note"
    block = models.ForeignKey(Block, null=True, default=None, on_delete=models.CASCADE)

    # the date/time when the solution as send to the pool
    inserted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # sometimes we want to mark already accepted solutions as ignore, this can happen if we
    # found faked solutions, that where only discovered later, but we don't want to alert the
    # faker early
    ignore = models.BooleanField(default=False)

    class Meta:
        abstract = True    
    
class Solution(BaseSolution):
    """ An accepted solution """
    
    pass

class RejectedSolution(BaseSolution):
    """ saves all the rejected solutions, to analyze them later """
    
    exception_type = models.CharField(max_length=200, default='', blank=True)
    
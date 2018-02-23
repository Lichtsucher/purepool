from django.db import models
from django.utils.translation import gettext as _

from purepool.models.miner.models import Miner

TRANSACTION_CATEGORY_CHOICES = (
    ('UD', 'Undefined'),
    ('MS', 'Mining share'),
    ('TX', 'Outgoing'),
)

class TransactionError(models.Model):
    """ Holds transaction errors """

    # time when the Transaction was created
    inserted_at = models.DateTimeField(auto_now_add=True)

    # usefull if we want to support multiple networks (test, main...)
    network = models.CharField(max_length=20)

    # who is the owner / target of this transaction?
    miner = models.ForeignKey(Miner, on_delete=models.CASCADE)

    amount =  models.DecimalField(max_digits=14, decimal_places=4, default=0)

    error_message = models.TextField()


class Transaction(models.Model):
    """ The list of transactions for the Miners. Can be a positive transaction (shares)
        or a payout (negative amount) """

    # time when the Transaction was created
    inserted_at = models.DateTimeField(auto_now_add=True)

    # usefull if we want to support multiple networks (test, main...)
    network = models.CharField(max_length=20)
    
    # who is the owner / target of this transaction?
    miner = models.ForeignKey(Miner, on_delete=models.CASCADE)

    # used to write additional information in the Transaction for the user
    note = models.TextField(blank=True, default="")

    # used to write information about the the transaction for the admin
    internal_note = models.TextField(blank=True, default="")

    # the amount of bbp that is for this transaction. A very important field, indeed
    # Can be a positive value that adds to the local balance (share of a block)
    # Or a negative balance, for an outgoing transaction (like autopayment)
    amount =  models.DecimalField(max_digits=14, decimal_places=4, default=0)

    # shows what was the reason behind the transaction
    category = models.CharField(max_length=2, default='UD', choices=TRANSACTION_CATEGORY_CHOICES)
 
    # the biblepay transaction in which this transaction was part of
    tx = models.CharField(max_length=200, blank=True, default="")
    

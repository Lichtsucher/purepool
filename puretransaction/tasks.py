import time
import traceback
import datetime
from django.utils import timezone
from celery import shared_task
from django.conf import settings
from django.db import transaction
from biblepay.clients import BiblePayRpcClient
from purepool.models.miner.models import Miner
from puretransaction.models import Transaction, TransactionError

@shared_task()
def send_autopayments(network):
    """ Looks into the miner list and finds all miners that
        have a balance greater than settings.POOL_MINIMUM_AUTOSEND """

    # no autosend is done if the miner has a balance below
    # this value
    minimum = settings.POOL_MINIMUM_AUTOSEND[network]

    # miners of the network with more then the minimum balance
    miners = Miner.objects.filter(balance__gt=minimum, network=network).values('id', 'address')
       
    client = BiblePayRpcClient(network=network)

    # the system will only do the transactions for
    # this amount of miners before this task is closed
    # the next task will go on from then on
    max_miners = 10
    
    miner_pos = 0
    for miner in miners:
        # we only send payments for miners who hadn't a payment in the last 12 hours
        last_trans_dt = timezone.now() - datetime.timedelta(hours=12)
        last_trans_count = Transaction.objects.filter(miner_id=miner['id'], network=network, category='TX', inserted_at__gt=last_trans_dt).count()

        if last_trans_count > 0:
            continue

        miner_pos += 1

        with transaction.atomic():
            # for security reasons, we recalculate the balance,
            # as the miner table can be changed by the frontend
            value = Miner.calculate_miner_balance(network, miner['id'])
            
            # if all is fine, we send out the bbp
            if value > minimum:
                tx_id = None
                try:
                    tx_id = client.sendtoaddress(miner['address'], value)
                except Exception as e:
                    error_message = ' # '.join([str(e), str(type(e))])+"\n"
                    error_message += str(traceback.extract_stack()) + "\n"
                    error_message += str(traceback.format_stack())
                    
                    # we should log the error if something goes wrong
                    transerror = TransactionError(
                        network = network,
                        miner_id = miner['id'],
                        amount = (value * -1),
                        error_message = error_message,
                    )
                    transerror.save()
                
                # transaction failed? Then we skip this user this time
                if tx_id is None:
                    continue
               
                internal_note = 'TX_ID:%s' % tx_id

                tx = Transaction(
                    network = network,
                    miner_id = miner['id'],
                    category = 'TX', # outgoing transaction
                    
                    # We substract the amount here, so it must be negative (55 -> -55)
                    amount = (value * -1),

                    # biblepay transaction
                    tx  = tx_id,

                    # some notes for the user and some for us
                    note = 'Autosend',
                    internal_note = internal_note,                    
                )
                tx.save()                
                
                # no value should be on the account anymore
                # but we better calculate it, if something had changed
                value = Miner.calculate_miner_balance(network, miner['id'])

                # added to prevent a problem with to fast and many transactions
                # in a short time
                time.sleep(5)
            
            # we update the miner with the new balance
            # even if no bbp was send (because of wrong values in the db). We
            # at least fix the value then
            Miner.objects.filter(pk=miner['id'], network=network).update(balance=value)
        
        # we end after we reached our max for this task
        if miner_pos == max_miners:
            break
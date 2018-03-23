import decimal
from django.conf import settings
from django.db.models import Count, Sum
from purepool.core.commands import TaskCommand
from biblepay.clients import BiblePayRpcClient, BlockNotFound
from purepool.models.block.tasks import calculate_miner_subsidy
from purepool.models.block.models import Block
from purepool.models.miner.models import Miner

class Command(TaskCommand):
    help = 'Validate that there are enough fundings on the pool wallet. Will print the result'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

        parser.add_argument('network', type=str, help='The network to use',)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        
        network = options['network']
        client = BiblePayRpcClient(network=network)

        # first, we calculate the existing open balance on the miners
        # and add the amount of subsidity of not payed out blocks (minus
        # pool fee, if one was set). This is the funding that must be
        # in the wallet (mature + immature)
        open_subsidy = Block.objects.filter(network=network, pool_block=True, process_status__in=['OP', 'BP']).aggregate(Sum('subsidy'))['subsidy__sum']
        open_subsidy = calculate_miner_subsidy(open_subsidy) # pool fee, if set

        sum_balance = Miner.objects.filter(network=network).aggregate(Sum('balance'))['balance__sum']
        
        required_balance = decimal.Decimal(open_subsidy) + sum_balance

        # and indeed, we need the current funding in the wallet
        walletinfo = client.getwalletinfo()

        existing_balance = decimal.Decimal(walletinfo['balance']) + decimal.Decimal(walletinfo['immature_balance'])

        print('Required:', round(required_balance, 3), 'Existing:', round(existing_balance, 3), 'Diff:', round(existing_balance-required_balance, 3))


        

        
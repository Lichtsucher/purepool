from django.conf import settings
from purepool.core.commands import TaskCommand
from purepool.models.miner.models import Miner

class Command(TaskCommand):
    help = 'Creates tasks that finds new block in the blockchains'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        
        parser.add_argument('miner_id', type=str, help='The miner who needs its balance calculated',)


    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        miner = Miner.objects.get(pk=options['miner_id'])
                
        value = Miner.calculate_miner_balance(miner.network, miner.id)
        
        miner.balance = value
        miner.save()
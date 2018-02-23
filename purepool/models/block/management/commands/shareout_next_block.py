from django.conf import settings
from purepool.core.commands import TaskCommand
from purepool.models.block.tasks import shareout_next_block

class Command(TaskCommand):
    help = 'Checks if a block had matures and is ready for the share out'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        
        parser.add_argument('--network', default=None, type=str, help='Limit the task to one network',)
        parser.add_argument('--block', default=None, type=int, help='process the block given. Usefull for debug runs',)
        parser.add_argument('--dry-run', action='store_true', dest="dry_run", help='Calculate and show the amounts, but do not send any bbp',)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        
        # per default, the script creates tasks for all networks        
        networks = settings.BIBLEPAY_NETWORKS
        
        network = options.get('network')
        if network is not None:
            networks = (network,)
        
        for network in networks:
            shareout_next_block.delay(
                network=network,
                block_height=options['block'],
                dry_run=options['dry_run']
            )
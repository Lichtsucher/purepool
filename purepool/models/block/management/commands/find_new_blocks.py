from django.conf import settings
from purepool.core.commands import TaskCommand
from purepool.models.block.tasks import find_new_blocks

class Command(TaskCommand):
    help = 'Creates tasks that finds new block in the blockchains'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        
        parser.add_argument('--network', default=None, type=str, help='Limit the task to one network',)
        parser.add_argument('--mark_as_processed', action='store_true', dest="mark_as_processed", help='Mark all of our pool blocks found as processed',)
        parser.add_argument('--max-height', default=None, dest="max_height", type=int, help='Only get blocks until max_height is reached',)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        
        # per default, the script creates tasks for all networks        
        networks = settings.BIBLEPAY_NETWORKS
        
        network = options.get('network')
        if network is not None:
            networks = (network,)
        
        for network in networks:
            find_new_blocks.delay(
                network=network,
                mark_as_processed=options.get('mark_as_processed'),
                max_height=options.get('max_height'),
            )
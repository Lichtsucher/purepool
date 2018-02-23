from django.conf import settings
from purepool.core.commands import TaskCommand
from puretransaction.tasks import send_autopayments

class Command(TaskCommand):
    help = 'Send the auto payments'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        
        parser.add_argument('--network', default=None, type=str, help='Limit the task to one network',)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        
        # per default, the script creates tasks for all networks        
        networks = settings.BIBLEPAY_NETWORKS
        
        network = options.get('network')
        if network is not None:
            networks = (network,)
        
        for network in networks:
            send_autopayments.delay(
                network=network
            )
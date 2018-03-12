from django.conf import settings
from purepool.core.commands import TaskCommand
from purepool.frontend.statistics import get_solution_statistics, get_block_statistics, get_top_miners, get_basic_statistics

class Command(TaskCommand):
    help = 'Resets the statistics caches'

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        days = 1
        graph_days = 7

        # recalculate the caches
        for network in settings.BIBLEPAY_NETWORKS:
            get_basic_statistics(network, days, _refresh=True)

        for network in settings.BIBLEPAY_NETWORKS:
            get_solution_statistics(network, days=graph_days, _refresh=True)

        for network in settings.BIBLEPAY_NETWORKS:
            get_block_statistics(network, days=graph_days, _refresh=True)
        
        for network in settings.BIBLEPAY_NETWORKS:
            get_top_miners(network, _refresh=True)
            
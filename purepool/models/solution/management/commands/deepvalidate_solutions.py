from django.conf import settings
from purepool.core.commands import TaskCommand
from purepool.interface.formats import SolutionString
from purepool.models.solution.models import Solution
from biblepay.clients import BiblePayRpcClient


class Command(TaskCommand):
    help = 'Does a deep validation of solutions by block-hex and transaction hex'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        client = BiblePayRpcClient('main')

        for solution in Solution.objects.all():
            ss = SolutionString(solution.solution)
            
            res = client.rpc.exec('hexblocktocoinbase', ss.get_block_hex(),ss.get_transaction_hex())
            
            print(res)
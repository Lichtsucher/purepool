from django.conf import settings
from purepool.core.commands import TaskCommand
from purepool.models.solution.tasks import process_solution

class Command(TaskCommand):
    help = 'Test command to manual submit a solution'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        
        parser.add_argument('network', type=str, help='The network for the solution',)
        parser.add_argument('solution', type=str, help='The solution itself. A very long string...',)

    def handle(self, *args, **options):
        process_solution.delay(options['network'], options['solution'])
        
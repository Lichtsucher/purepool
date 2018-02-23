from django.conf import settings
from purepool.core.commands import TaskCommand
from purepool.models.solution.tasks import cleanup_solutions

class Command(TaskCommand):
    help = 'Removes old Works, Solutions and RejectedSolutions'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        
    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        
        cleanup_solutions.delay()
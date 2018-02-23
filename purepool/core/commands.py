from django.conf import settings
from django.core.management.base import BaseCommand

class TaskCommand(BaseCommand):
    """ adss some generic options to typical "Task" commands used in the script, like bypassing the task queue """

    def add_arguments(self, parser):
        parser.add_argument('--run-local', action='store_true', dest="run_local", help='Runs the task locally instead via a celery task',)
        parser.add_argument('--debug', action='store_true', dest="debug", help='Show debug mesages',)

    def handle(self, *args, **options):
        if options.get('run_local', False):
            # ugly, but it works for tasks
            settings.CELERY_TASK_ALWAYS_EAGER = True
            settings.CELERY_TASK_EAGER_PROPAGATES  = True

        settings.TASK_DEBUG = False
        if options.get('debug', False):
            # ugly, but it works for tasks
            settings.TASK_DEBUG = True        
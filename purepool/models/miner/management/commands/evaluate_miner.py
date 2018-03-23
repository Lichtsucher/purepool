import datetime
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Sum
from purepool.core.commands import TaskCommand
from purepool.models.miner.models import Miner
from purepool.models.block.models import Block
from purepool.models.solution.models import Solution

class Command(TaskCommand):
    help = 'Evaluate the quality of miners (comparing found blocks with shares) and give them a "rating"'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

        parser.add_argument('network', type=str, help='Limit the task to one network',)


    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        network = options['network']

        days24_dt = timezone.now() - datetime.timedelta(days=1)

        # we reset the level of all miners first, to ensure that it is fair for everybody
        # as we will only recalculate the miners that had shares in the last 24 hours
        # 0 is the default
        miners = Solution.objects.filter(network=network, miner__enabled=True, inserted_at__gte=days24_dt).values('miner__address', 'miner_id').annotate(total=Count('miner_id'))
        miners_count = len(miners) # prefetch them, so that the next step will only start after the slow query is done

        Miner.objects.all().update(rating=0)
    
        # We will compare all miners with the effectivity of miners who had found blocks. For that reason
        # we need to load the list of "useful" miners and only look at their shares
        pool_blocks = Block.objects.filter(network=network, pool_block=True, inserted_at__gte=days24_dt).count()
        working_miners = Block.objects.filter(network=network, pool_block=True, inserted_at__gte=days24_dt).values('miner_id').annotate(total=Count('miner_id'))
        miner_ids = []
        for working_miner in working_miners:
            miner_ids.append(working_miner['miner_id'])
        pool_solution_count = Solution.objects.filter(network=network, inserted_at__gte=days24_dt, miner_id__in=miner_ids).count()

        ratio = pool_solution_count / pool_blocks # solutions per block

        if settings.TASK_DEBUG:
            print("Statistics: ", pool_solution_count, pool_blocks, ratio)
            print("\n\n")

        # and now per miner
        for miner in miners:
            miner_blocks = Block.objects.filter(network=network, miner_id=miner['miner_id'], inserted_at__gte=days24_dt).count()
            miner_solutions_count = Solution.objects.filter(network=network, miner_id=miner['miner_id'], inserted_at__gte=days24_dt).count()

            try:
                mine_ratio = miner_solutions_count / miner_blocks
            except ZeroDivisionError:
                mine_ratio = miner_solutions_count

            percent_diff = (100 / ratio) * mine_ratio

            rating = 0

            if percent_diff < 50:
                rating = -1

            if percent_diff < 20:
                rating = -2

            if percent_diff > 120:
                rating = 1

            if percent_diff > 250:
                rating = 2

            if percent_diff > 400:
                rating = 3

            # special for small miners: if they hadn't found a block, but
            # have a very small percent_diff, we set the rating to 0
            if miner_blocks == 0 and percent_diff < 50:
                rating = 0

            if settings.TASK_DEBUG:
                print(" - ", miner['miner__address'], miner_solutions_count, miner_blocks, mine_ratio, percent_diff, ' # ', rating)

            m = Miner.objects.get(pk=miner['miner_id'])
            m.rating = rating
            m.save()


        
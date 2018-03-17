import datetime
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_page
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum
from django.http import HttpResponseRedirect, JsonResponse
from purepool.frontend.forms import MinerForm
from purepool.frontend.statistics import get_solution_statistics, get_block_statistics, get_top_miners, get_basic_statistics, get_miner_solution_statistics
from purepool.models.miner.models import Miner
from purepool.models.solution.models import Solution
from purepool.models.block.models import Block
from puretransaction.models import Transaction


def index_redirect(request):
    """ is called when no network was given, so we redirect to the default network"""
    
    network = request.GET.get('network', settings.BIBLEPAY_DEFAULT_NETWORK)
    
    return HttpResponseRedirect(reverse('index_network', kwargs={'network': network}))

def index(request, network):
    
    if request.method == 'POST':
        form = MinerForm(request.POST)        
        if form.is_valid():        
            return HttpResponseRedirect(reverse('miner', kwargs={'network': network, 'address': form.cleaned_data['address']}))

    else:
        form = MinerForm()    
    
    return render(request, 'purepool/index.html', {
        'network': network,
        'form': form,
        })

@cache_page(60 * 1)
def miner(request, network, address):
    """ the miner share statistics and transaction list """

    miner = get_object_or_404(Miner, address=address, network=network)
    share_statistics = get_miner_solution_statistics(network, miner_id=miner.id)
    transactions = Transaction.objects.filter(network=network, miner=miner).order_by('-id')[0:100]
    workers = Miner.get_active_worker(network, address, 1)

    return render(request, 'purepool/miner.html', {
          'address': address,
          'network': network,
          'miner': miner,
          'workers': workers,
          'share_statistics': share_statistics,
          'transactions': transactions,
        })

@cache_page(60 * 1)
def howtojoin(request, network):
    """ shows the join documentation """
    
    return render(request, 'purepool/howtojoin.html', {
        'network': network,
        'transfer_limits': settings.POOL_MINIMUM_AUTOSEND
    })


def statistics(request, network):
    """ some nice statistics for the whole pool """

    # some basic statistics
    days = 1

    current_height, all_blocks, pool_blocks, pool_blocks_percent, bbp_mined = get_basic_statistics(network, days)

    graph_days = 7

    top_miners = get_top_miners(network)

    # the solution and block statistics
    share_statistics = get_solution_statistics(network, days=graph_days)
    block_statistics = list(get_block_statistics(network, days=graph_days))

    statistics = []
    # now we join the statistics
    for i, share_stat in enumerate(list(share_statistics)):
        statistics.append([share_stat[0], share_stat[1], block_statistics[i][1]])

    # and finally the forecast for the blocks
    blocks_two_days = statistics[-2][2] + statistics[-1][2]
    blocks_per_hour = blocks_two_days / (24 + timezone.now().hour)
    forecast_blocks = int(round(blocks_per_hour * 24))

    last_blocks = Block.objects.filter(network=network, pool_block=True).values('height', 'inserted_at').order_by('-height')[0:50]

    return render(request, 'purepool/statistics.html', {
          'network': network,
          'statistics': statistics,
          'top_miners': top_miners,
          'last_blocks': last_blocks,

          'forecast_blocks': forecast_blocks,

          'days': days,
          'current_height': current_height,
          'all_blocks': all_blocks,
          'pool_blocks': pool_blocks,
          'pool_blocks_percent': pool_blocks_percent,
          'bbp_mined': bbp_mined,
        })



############################################# API

@cache_page(60 * 1)
def api_statistics(request, network):
    """ returns the basic statistics as json string """

    days = 1
    current_height, all_blocks, pool_blocks, pool_blocks_percent, bbp_mined = get_basic_statistics(network, days)

    return JsonResponse({
          'network': network,
          'days': days,
          'current_height': current_height,
          'all_blocks': all_blocks,
          'pool_blocks': pool_blocks,
          'pool_blocks_percent': pool_blocks_percent,
          'bbp_mined': bbp_mined,
        })

@cache_page(60 * 10)
def api_block_subsidysum(request, network, days):
    """ returns a sum of all subsidies of the blocks found in "days". It is used to
        calculate the revenue of the masternodes """

    day = timezone.now() - datetime.timedelta(days=days)
    values = Block.objects.filter(network=network, inserted_at__gte=day).aggregate(total=Sum('subsidy'), count=Count('height'))
    
    return JsonResponse({
        'sum': values['total'],
        'count': values['count'],
    })
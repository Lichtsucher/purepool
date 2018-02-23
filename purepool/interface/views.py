from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from purepool.core.tools import get_client_ip
from purepool.interface.formats import WorkerId, InvalidWorkerdId, SolutionString
from purepool.interface.hash import GetHashTarget
from purepool.models.miner.models import Worker, MinerNotEnabled, get_or_create_miner_worker
from purepool.models.solution.models import Work
from purepool.models.solution.tasks import process_solution


class InvalidNetwork(Exception):
    pass

def create_error_msg(msg):
    return '<RESPONSE>%s</RESPONSE><ERROR>%s</ERROR><EOF>' % (msg, msg)

def get_network(request):
    """ gets and validated the network from the request """
    
    network = get_header_field(request, 'NetworkID', None)
    
    if not network in settings.BIBLEPAY_NETWORKS:
        raise InvalidNetwork()
    
    return network

def get_header_field(request, field, default):
    if request.META.get(field, None) is not None:
        return request.META.get(field, None)

    field = 'HTTP_' + field.upper()
    if request.META.get(field, None) is not None:
        return request.META.get(field, None)
    
    return default

@csrf_exempt
def action(request):
    """ a bridge view that calls the real views based upon the header "Action"
        Important: Django puts all custom HTTP Header in the META dict, with
        a leading "HTTP_" and always uppercase.
        The miner sends "Action", but django will return it as "HTTP_ACTION"
    """
    
    # the original pool used the Header "Action" to route to the right page
    # so we do that here, too    
    action = get_header_field(request, 'Action', 'EMPTY')
        
    if action == 'readytomine2':
        return readytomine2(request)
    elif action == 'solution':
        return solution(request)

    return HttpResponse(create_error_msg('UNKNOWN ACTION %s' % action))

def readytomine2(request):
    """ Readytomine2 is called by the biblepay miner when new work is required """
    
    # we first need the network (like "main" or "test"), as it is required in many steps
    try:
        network = get_network(request)
    except InvalidNetwork:
        return HttpResponse(create_error_msg('Invalid network'))

    # first, we check if this is a valid miner/worker, or it must be created
    # We only allow enabled miners here
    worker_id_str = get_header_field(request, 'Miner', None)

    if worker_id_str is None:
        return HttpResponse(create_error_msg('WorkerID is missing'))

    try:
        full_worker_id = WorkerId(worker_id_str)

        # we try to get or create the miner and worker with this call
        miner_id, worker_id = get_or_create_miner_worker(network, full_worker_id.get_address(), full_worker_id.get_worker())
    except MinerNotEnabled:
        return HttpResponse(create_error_msg('Miner %s is disabled' % full_worker_id.get_address()))
    except InvalidWorkerdId:
        return HttpResponse(create_error_msg('WorkerID %s is invalid' % full_worker_id.get_address()))

    # load some additional information from the headers. These are unrealiable but nice to have

    thread_id = get_header_field(request, 'ThreadID', '1')
    os = get_header_field(request, 'OS', 'UNKNOWN')
    agent = get_header_field(request, 'Agent', 'UNKNOWN')
    ip = get_client_ip(request)

    # and calculate the HashTarget
    hash_target = GetHashTarget(miner_id, network)

    # now create new work for this miner/worker    
    work = Work(worker_id=worker_id, thread_id=thread_id, network=network, hash_target=hash_target, ip=ip, os=os, agent=agent)
    work.save(force_insert=True)

    # build response
    response = "<RESPONSE> <ADDRESS>{0}</ADDRESS><HASHTARGET>{1}</HASHTARGET><MINERGUID>{2}</MINERGUID><WORKID>{3}</WORKID></RESPONSE>".format(
        settings.POOL_ADDRESS[network],
        hash_target,
        miner_id,
        work.id
    )
    
    return HttpResponse(response)

def solution(request):
    """ called by the miner whenever a solution is found. We check the solution in
        a different process to see if it is a valid solution, or some fake """
        
    # we first need the network (like "main" or "test"), as it is required in many steps
    try:
        network = get_network(request)
    except InvalidNetwork:
        return HttpResponse(create_error_msg('Invalid network'))
    
    solution_str = get_header_field(request, 'Solution', None)
    
    # an empty solution is always wrong
    if solution_str is None:
        return HttpResponse(create_error_msg('Solution is missing'))
    
    # we will parse it here for a first test, but the real validation
    # will be done later
    try:
        solution = SolutionString(solution_str)
    except InvalidSolutionString:
        return HttpResponse(create_error_msg('Invalit Solution'))

    response = "<RESPONSE><STATUS>ok</STATUS><WORKID>%s</WORKID></RESPONSE><END></HTML>" % solution.get_work_id()    

    # this is not a direct call to "process_solution", but puts it into
    # the celery/rabbitmq queue until it is processed from there with a
    # background task
    process_solution.delay(network, solution_str)

    return HttpResponse(response)
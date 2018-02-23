from django.core.cache import cache

def GetHashTarget(miner_id, network_id):
    modulus = RequestModulusByMinerGuid(miner_id)

    # TODO why at all?
    shares_solved = 0
    if modulus % 50 == 0:
        shares_solved = 1 ## GetHashDifficulty only need this? 

    return GetHashDifficulty(shares_solved)

def RequestModulusByMinerGuid(miner_id):
    global app_cache

    try:
        key = miner_id + "_modulus"
        mod = cache.get(key, 0)
        mod += 1
        cache.set(key, mod)

        return mod
    except:
        return 0

def GetHashDifficulty(shares_solved):
    if (shares_solved > 0): 
        shares_solved = 30

    target_solve_count_per_pound = 35
    master_prefix = 4444444
    sub_len = len(str(master_prefix))
    prefix = master_prefix

    for y in range(shares_solved+1):
        step = ((master_prefix / 1) / target_solve_count_per_pound) * 1.5;
        if (y > (target_solve_count_per_pound * 0.7)):
            step = step / 4;

        prefix = prefix - step;

    if (prefix < 90):
         prefix = 90;

    str_prefix = "00000000000" + str(int(round(prefix, 0)))

    str_prefix = str_prefix[len(str_prefix) - sub_len:sub_len]
    str_pre_prefix = "00000"

    hash_target = str_pre_prefix + str_prefix + "111100000000000000000000000000000000000000000000000000000000";
    hash_target = hash_target[:64]

    return hash_target
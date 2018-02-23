import json
from purepool.models.miner.models import Miner, Worker, get_miner_id_by_address

class InvalidSolutionString(Exception):
    pass

class InvalidWorkerdId(Exception):
    pass

class WorkerId(object):
    """ Splits the worker id from the mining client and offers the separate parts """
    
    def __init__(self, worker_id):
        self.address = None
        self.worker = None
        self.email = None

        try:
            worker_parts = worker_id.split('/')            
            self.address = worker_parts[0] # a must have!
            
            if self.address == '':
                raise

            if len(worker_parts) > 1:
                self.worker = worker_parts[1]
                if self.worker == '':
                    self.worker = 'Default'
            else:
                self.worker = 'Default'

            if len(worker_parts) > 2:
                self.email = worker_parts[2]  
        except:
            raise InvalidWorkerdId
    
    def get_address(self):
        return self.address
    
    def get_worker(self):
        return self.worker
    
    def get_email(self):
        return self.email

    def get_worker_obj(self, network):
        """ small helper that returns the worker model object from the database.
            Will not miner or worker! """
        
        # important: will raise purepool.models.miner.models.MinerNotFound !
        miner_id = get_miner_id_by_address(network, self.address)

        # will raise Worker.DoesNotExist, a good way to catch it
        return Worker.objects.get(miner_id=miner_id, name=self.worker)
        

class SolutionString(object):
    """ Takes the solution string delivered by the Mining client and splits it into its
        original parts.
        
        The original mining/biblepay client has the oposite side of the code in
        src/miner.ccp -> UpdatePoolProgress()
        """
    
    def __init__(self, solution_string=None):
        """ the solution_string is optional, as we fill the fields
            in some tests directly """
        
        if solution_string is not None:
            self.content = self.parse_solution_string(solution_string)
        
    def parse_solution_string(self, solution_string):
        try:
            solution = solution_string.split(',')
            
            return {
                'block_hash': solution[0],
                'block_time': solution[1],
                'prev_block_time': solution[2],
                'prev_height': solution[3],
                'bible_hash': solution[4],
                'miner_id': solution[5],
                'work_id': solution[6],            
                'thread_id': solution[7],
                'thread_hash_counter': solution[8],            
                'thread_start': solution[9],
                'hash_counter': solution[10],
                'timer_start': solution[11],
                'timer_end': solution[12],
                'nonce': solution[13],
                'block_hex': solution[14],
                'transaction_hex': solution[15],
            }
        except:
            raise InvalidSolutionString()
        
    def as_string(self):
        return ','.join([
            self.content['block_hash'],
            self.content['block_time'],
            self.content['prev_block_time'],
            self.content['prev_height'],
            self.content['bible_hash'],
            str(self.content['miner_id']),
            str(self.content['work_id']),
            self.content['thread_id'],
            self.content['thread_hash_counter'],
            self.content['thread_start'],
            self.content['hash_counter'],
            self.content['timer_start'],
            self.content['timer_end'],
            self.content['nonce'],
            self.content['block_hex'],
            self.content['transaction_hex'],
        ])

    def get_block_hash(self):
        """ The hash of block used in this solution.
            Used in the bible_hash calculation """

        return self.content['block_hash']

    def get_block_time(self):
        """ value of GetBlockTime() from the block on client side.
            Used in the bible_hash calculation """
        return self.content['block_time']
    
    def get_prev_block_time(self):
        """ block time of the previous block.
            Used in the bible_hash calculation """
        
        return self.content['prev_block_time']
    
    def get_prev_height(self):
        """ block height of the previous block.
            Used in the bible_hash calculation """
            
        return self.content['prev_height']
    
    def get_bible_hash(self):
        """ The meat of our solution string, the information we want.
            This must be unique, we will ensure that in the database table.
            A lot of the other information delivered are used to ensure that
            this bible_hash is valid and can be calculated based on the given
            information. """        

        return self.content['bible_hash']
    
    def get_miner_id(self):
        """ the miner uuid that the client used for mining """
        
        return self.content['miner_id']
    
    def get_work_id(self):
        """ every miner requests Work with "readytowork2" from the interface.
            This is the work_id it was given """
        
        return self.content['work_id']

    def get_thread_id(self):
        """ Every thread on the miner has an id, starting from 0 """
        
        return self.content['thread_id']

    def get_thread_hash_counter(self):
        """ the amount of hashes calculated before the solution was send """
        
        try:
            return int(self.content['thread_hash_counter'])
        except:
            pass
        
        return 0    
    
    def get_thread_start(self):
        """ time in millieconds then the current work started in the thread """
    
        try:
            return int(self.content['thread_start'])
        except:
            pass
        
        return 0        
    
    def get_hash_counter(self):
        """ how many hashes the whole client calculated before the solution was commited """
    
        try:
            return int(self.content['hash_counter'])
        except:
            pass
        
        return 0    
    
    def get_timer_start(self):
        """ miner starttime """
        
        try:
            return int(self.content['timer_start'])
        except:
            pass
        
        return 0

    def get_timer_end(self):
        """ the time when the solution was commited from client side"""
        
        try:
            return int(self.content['timer_end'])
        except:
            pass
        
        return 0
    
    def get_nonce(self):
        """ the nonce used in the hash """
        
        return self.content['nonce']
    
    def get_block_hex(self):
        return self.content['block_hex']
    
    def get_transaction_hex(self):
        return self.content['transaction_hex']                    
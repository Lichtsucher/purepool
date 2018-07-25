import datetime
from unittest import mock
from django.utils import timezone
from django.test import TestCase, override_settings
from biblepay.clients import BiblePayRpcClient, BlockNotFound
from purepool.models.miner.models import Miner, Worker
from purepool.models.block.tasks import find_new_blocks, process_next_block, shareout_next_block
from purepool.models.block.models import Block
from purepool.models.solution.models import Solution, Work
from puretransaction.models import Transaction

class find_new_blocksTestCase(TestCase):
    
    def setUp(self):
        self.miner = Miner(network="test", address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx")
        self.miner.save()
        
        self.block_time = datetime.datetime(2017, 9, 9, 11, 12, 13, 15, tzinfo=datetime.timezone.utc)
                
    @override_settings(POOL_ADDRESS={'test': 'POOLADDR'})
    def test_basic(self):
        test_block_time1 = datetime.datetime(2017, 9, 9, 11, 12, 13, 15, tzinfo=datetime.timezone.utc)
        test_block_time2 = datetime.datetime(2018, 9, 9, 11, 12, 13, 15, tzinfo=datetime.timezone.utc)
        test_block_time3 = datetime.datetime(2019, 9, 9, 11, 12, 13, 15, tzinfo=datetime.timezone.utc)
        test_block_time4 = datetime.datetime(2020, 9, 9, 11, 12, 13, 15, tzinfo=datetime.timezone.utc)
        
        with mock.patch('purepool.models.block.tasks.BiblePayRpcClient.subsidy') as mock_subsidy, \
             mock.patch('purepool.models.block.tasks.get_block_time') as mock_get_block_time:
            
            # the mock client will return the result for two block
            mock_subsidy.side_effect = [
                {'subsidy': 100, 'minerguid': 'unknown', 'recipient': 'POOLADDR'},
                {'subsidy': 500, 'minerguid': self.miner.id, 'recipient': 'POOLADDR'},
                {'subsidy': 200, 'minerguid': 'xxx', 'recipient': 'rec'},
                None
            ]
            
            mock_get_block_time.side_effect = [
                test_block_time1,
                test_block_time2,
                test_block_time3,
                test_block_time4,
            ]

            find_new_blocks('test')

            mock_subsidy.assert_has_calls(
                [mock.call(1), mock.call(2), mock.call(3), mock.call(4)],
                any_order=False
            )
            
            block1, block2, block3 = Block.objects.all().order_by("height")
            
            self.assertEqual(block1.height, 1)            
            self.assertTrue(block1.pool_block)
            self.assertEqual(block1.subsidy, 100)
            self.assertEqual(block1.process_status, 'OP')
            self.assertEqual(block1.miner, None)
            self.assertEqual(block1.network, 'test')
            self.assertEqual(block1.recipient, 'POOLADDR')
            self.assertEqual(block1.inserted_at, test_block_time1)            
            
            self.assertEqual(block2.height, 2)
            self.assertTrue(block2.pool_block)
            self.assertEqual(block2.subsidy, 500)
            self.assertEqual(block2.process_status, 'OP')
            self.assertEqual(block2.miner, self.miner)
            self.assertEqual(block2.network, 'test')
            self.assertEqual(block2.recipient, 'POOLADDR')
            self.assertEqual(block2.inserted_at, test_block_time2)
            
            self.assertEqual(block3.height, 3)
            self.assertFalse(block3.pool_block)
            self.assertEqual(block3.subsidy, 200)
            self.assertEqual(block3.process_status, 'OP')
            self.assertEqual(block3.miner, None)
            self.assertEqual(block3.network, 'test')
            self.assertEqual(block3.recipient, 'rec')
            self.assertEqual(block3.inserted_at, test_block_time3)
            
            # execute a second time
            mock_subsidy.side_effect = [
                {'subsidy': 55, 'minerguid': 'unknown', 'recipient': 'xxx'},
                None
            ]
            
            
            find_new_blocks('test')
            
            # multiple times called with "4", as the first call
            # asks for "4" and fails on that!
            mock_subsidy.assert_has_calls(
                [mock.call(1), mock.call(2), mock.call(3), mock.call(4), mock.call(4), mock.call(5)],
                any_order=False
            )
            
            block1, block2, block3, block4 = Block.objects.all().order_by("height")
            
            self.assertEqual(block4.height, 4)
            self.assertFalse(block4.pool_block)
            self.assertEqual(block4.subsidy, 55)
            self.assertEqual(block4.process_status, 'OP')
            self.assertEqual(block4.miner, None)
            self.assertEqual(block4.network, 'test')
            self.assertEqual(block4.recipient, 'xxx')
            self.assertEqual(block4.inserted_at, test_block_time4)
            
    def test_invalid_subsidy(self):
        with mock.patch('purepool.models.block.tasks.BiblePayRpcClient.subsidy') as mock_subsidy, \
             mock.patch('purepool.models.block.tasks.get_block_time', return_value=self.block_time):
            # the mock client will return the result for two block
            mock_subsidy.side_effect = [
                {'something': 'else'}
            ]
            
            find_new_blocks('test')
            
            self.assertEqual(Block.objects.all().count(), 0)
        
    def test_blocknotfound(self):
        with mock.patch('purepool.models.block.tasks.BiblePayRpcClient.subsidy') as mock_subsidy, \
             mock.patch('purepool.models.block.tasks.get_block_time', return_value=self.block_time):
            mock_subsidy.side_effect = BlockNotFound()
            
            find_new_blocks('test')
    
    @override_settings(POOL_ADDRESS={'test': 'POOLADDR'})
    def test_mark_as_processed(self):
        with mock.patch('purepool.models.block.tasks.BiblePayRpcClient.subsidy') as mock_subsidy, \
             mock.patch('purepool.models.block.tasks.get_block_time', return_value=self.block_time):
            # the mock client will return the result for two block
            mock_subsidy.side_effect = [
                {'subsidy': 100, 'minerguid': 'unknown', 'recipient': 'POOLADDR'},
                None
            ]
            
            find_new_blocks('test', mark_as_processed=True)
            
            block1 = Block.objects.all().order_by("height")[0]
            
            self.assertEqual(block1.height, 1)            
            self.assertTrue(block1.pool_block)
            self.assertEqual(block1.subsidy, 100)
            self.assertEqual(block1.process_status, 'FI')
            self.assertEqual(block1.miner, None)
            self.assertEqual(block1.network, 'test')
            self.assertEqual(block1.recipient, 'POOLADDR')
                    
    @override_settings(POOL_ADDRESS={'test': 'POOLADDR'})
    def test_max_height(self):
        with mock.patch('purepool.models.block.tasks.BiblePayRpcClient.subsidy') as mock_subsidy, \
             mock.patch('purepool.models.block.tasks.get_block_time', return_value=self.block_time):
            # the mock client will return the result for two block
            mock_subsidy.side_effect = [
                {'subsidy': 100, 'minerguid': 'unknown', 'recipient': 'POOLADDR'},
                {'subsidy': 100, 'minerguid': 'unknown', 'recipient': 'POOLADDR'},
                {'subsidy': 100, 'minerguid': 'unknown', 'recipient': 'POOLADDR'},
                None
            ]
            
            find_new_blocks('test', max_height=1)
            
            self.assertEqual(Block.objects.all().count(), 1)
            
            block1 = Block.objects.all().order_by("height")[0]
            
            self.assertEqual(block1.height, 1)            
            self.assertTrue(block1.pool_block)
            self.assertEqual(block1.subsidy, 100)
            self.assertEqual(block1.process_status, 'OP')
            self.assertEqual(block1.miner, None)
            self.assertEqual(block1.network, 'test')
            self.assertEqual(block1.recipient, 'POOLADDR')    
        
class process_next_blockTestCase(TestCase):
    
    def setUp(self):
        miner = Miner(address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx")
        miner.save()
        
        worker = Worker(miner=miner)
        worker.save()
        
        work_test = Work(worker=worker, ip="1.1.1.1")
        work_test.save()
        
        work_main = Work(worker=worker, ip="1.1.1.1")
        work_main.save()
                        
        # first, we add some blocks in both networks,
        # with only some being pool bocks
        self.block1_main = Block(height=4, network='main', miner=miner, subsidy=1)
        self.block1_main.save()
        
        self.block2_main = Block(height=4, network='main', pool_block=True, miner=miner, subsidy=1)
        self.block2_main.save()           
        
        self.block1_test = Block(height=5, network='test', pool_block=True, miner=miner, subsidy=1)
        self.block1_test.save()
    
        self.block2_test = Block(height=6, network='test', miner=miner, subsidy=1)
        self.block2_test.save()    

        self.block2_test = Block(height=7, network='test', pool_block=True, miner=miner, subsidy=1)
        self.block2_test.save()
        
        # next we set the inserted_time for two of the blocks
        # to match the solutions
        self.block1_test.inserted_at = timezone.now() - datetime.timedelta(days=4)
        self.block1_test.save()
        
        self.block2_test.inserted_at = timezone.now() - datetime.timedelta(days=1)
        self.block2_test.save()
        
        # and now some solutions to attch to the block
        s1 = Solution(network='test', bible_hash="1", miner=miner, work=work_test)
        s1.save()
        s1.inserted_at = timezone.now() - datetime.timedelta(days=5)
        s1.save()
        
        s2 = Solution(network='test', bible_hash="2",miner=miner, work=work_test)
        s2.save()
        s2.inserted_at = timezone.now() - datetime.timedelta(days=2)
        s2.save()        
        
        s3 = Solution(network='test', bible_hash="3",miner=miner, work=work_test)
        s3.save()
        
        s4 = Solution(network='main', bible_hash="4",miner=miner, work=work_main)
        s4.save()
        s4.inserted_at = timezone.now() - datetime.timedelta(days=10)
        s4.save()        
            
        
    def test_(self):
        self.assertEqual(Solution.objects.filter(block__isnull=True).count(), 4)
        
        # should find the first open block in test network, but let the
        # main netzwork untouched.
        process_next_block('test')
        
        self.block1_test = Block.objects.get(pk=self.block1_test.id)        
        self.assertEqual(Block.objects.filter(process_status='BP').count(), 1)
        self.assertEqual(self.block1_test.process_status, 'BP')
        
        self.assertEqual(Solution.objects.filter(block__isnull=True).count(), 3)
        
        # and now find the second block
        process_next_block('test')
        
        self.assertEqual(Block.objects.filter(process_status='BP').count(), 2)        
        self.assertEqual(Solution.objects.filter(block__isnull=True).count(), 2)
        
        # the next round should find nothing, as all other blocks
        # won't match
        process_next_block('test')

        self.assertEqual(Block.objects.filter(process_status='BP').count(), 2)        
        self.assertEqual(Solution.objects.filter(block__isnull=True).count(), 2)

    
    
class shareout_next_blockTestCase(TestCase):
    
    def setUp(self):
        self.miner1 = Miner(network="test", address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx")
        self.miner1.save()
        
        self.worker1 = Worker(miner=self.miner1)
        self.worker1.save()

        self.miner2 = Miner(network="test", address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxx2")
        self.miner2.save()
        
        self.worker2 = Worker(miner=self.miner2)
        self.worker2.save()

        self.insert_age = timezone.now() - datetime.timedelta(days=3)
        
        Transaction(miner=self.miner2, amount=60, network="test").save()
        
        # test network
        #----------------      
        
        # valid
        block1 = Block(height=1, network='test', process_status='BP', pool_block=True, subsidy=100)
        block1.save()
        
        # not a pool block
        block2 = Block(height=2, network='test', pool_block=False, subsidy=1)
        block2.save()
        
        # wrong status
        block3 = Block(height=3, network='test', process_status='OP', pool_block=True, subsidy=1)
        block3.save()
        
        Block.objects.all().update(inserted_at=self.insert_age)
        
        # not old enough
        block4 = Block(height=4, network='test', process_status='BP', pool_block=True, subsidy=1)
        block4.save()
        
        work_test1 = Work(worker=self.worker1, ip="1.1.1.1")
        work_test1.save()        

        work_test2 = Work(worker=self.worker1, ip="1.1.1.1")
        work_test2.save()        
        
        Solution(network='test', block=block1, bible_hash="1", miner=self.miner1, work=work_test1).save()
        Solution(network='test', block=block1, bible_hash="2", miner=self.miner1, work=work_test1).save()
        Solution(network='test', block=block1, bible_hash="3", miner=self.miner1, work=work_test1).save()
        
        Solution(network='test', block=block1, bible_hash="4", miner=self.miner2, work=work_test1).save()
        Solution(network='test', block=block1, bible_hash="4.5", miner=self.miner2, work=work_test1).save()
            
        Solution(network='test', block=block2, bible_hash="5", miner=self.miner1, work=work_test1).save()
        Solution(network='test', block=block3, bible_hash="6", miner=self.miner1, work=work_test1).save()
        Solution(network='test', block=block4, bible_hash="7",  miner=self.miner1, work=work_test1).save()
            
        # main network
        # -----------------
        block1 = Block(height=1, network='main', process_status='BP', pool_block=True, subsidy=1)
        block1.save()
        
        Block.objects.filter(network="main").update(inserted_at=self.insert_age)

        work_main = Work(worker=self.worker1, ip="1.1.1.1")
        work_main.save()              
                
        Solution(network='main', block=block2, bible_hash="8", miner=self.miner1, work=work_main).save()
        

    @override_settings(POOL_ADDRESS={'POOL_BLOCK_MATURE_HOURS': {'test': 48, 'main': 48}})
    @override_settings(POOL_ADDRESS={'test': 'abc', 'main': 'xyz'})
    @override_settings(POOL_FEE_PERCENT=5)
    @mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.subsidy', return_value={'subsidy': '100', 'recipient': 'abc'})
    def test_process(self, mock_subsidy):
        # sucessfull first block
        shareout_next_block('test')
        
        block1 = Block.objects.get(height=1, network="test")
        self.assertEqual(block1.process_status, 'FI')
        
        self.assertEqual(Transaction.objects.all().count(), 3) # 1 old, 2 new
        self.assertEqual(Solution.objects.filter(block=block1, processed=True).count(), 5)
        
        trans1 = Transaction.objects.get(miner=self.miner1)
        trans2 = Transaction.objects.get(miner=self.miner2, amount=38)
        
        self.assertEqual(trans1.amount, 57)
        self.assertEqual(trans1.network, "test")
        self.assertEqual(trans1.miner, self.miner1)
        self.assertEqual(trans1.category, "MS")

        self.assertEqual(trans2.amount, 38)
        self.assertEqual(trans2.network, "test")
        self.assertEqual(trans2.miner, self.miner2)
        self.assertEqual(trans2.category, "MS")
        
        miner1 = Miner.objects.get(pk=self.miner1.id)
        self.assertEqual(miner1.balance, 57)

        # miner 2 already had an open transaction, so the balance is higher        
        miner2 = Miner.objects.get(pk=self.miner2.id)
        self.assertEqual(miner2.balance, 98)
        
        
        # no more blocks, main untouched
        # all existing blocks not fit our requirements
        shareout_next_block('test')
        shareout_next_block('test')
        shareout_next_block('test')
        shareout_next_block('test')
        
        self.assertEqual(Transaction.objects.all().count(), 3) # old old, 2 new
        
        block2 = Block.objects.get(height=2, network="test")
        self.assertEqual(block2.process_status, 'OP')
        
        block3 = Block.objects.get(height=3, network="test")
        self.assertEqual(block3.process_status, 'OP')
        
        block4 = Block.objects.get(height=4, network="test")
        self.assertEqual(block4.process_status, 'BP')
        
        blockmain = Block.objects.get(height=1, network="main")
        self.assertEqual(blockmain.process_status, 'BP')
        
    @override_settings(POOL_ADDRESS={'POOL_BLOCK_MATURE_HOURS': {'test': 48, 'main': 48}})
    @override_settings(POOL_ADDRESS={'test': 'abc', 'main': 'xyz'})
    def test_stale(self):
        
        # not our block (anymore)?
        with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.subsidy', return_value={"XXX": 'xxx'}):
            # marked as stale
            shareout_next_block('test')
            
        block1 = Block.objects.get(height=1, network="test")
        self.assertEqual(block1.process_status, 'ST')
        
        self.assertEqual(Transaction.objects.all().count(), 1)    # one old
        
    @override_settings(POOL_BLOCK_MATURE_HOURS={'test': 48, 'main': 48})
    @override_settings(POOL_ADDRESS={'test': 'abc', 'main': 'xyz'})
    def test_process_noshares(self):
        # remove all shares and test
        
        Solution.objects.all().delete()
        
        with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.subsidy', return_value={'subsidy': '55', 'recipient': 'abc'}):
            shareout_next_block('test')
            
        block1 = Block.objects.get(height=1, network="test")
        self.assertEqual(block1.process_status, 'FI')
        
        self.assertEqual(Transaction.objects.all().count(), 1) # one old
      
    
    @override_settings(POOL_ADDRESS={'POOL_BLOCK_MATURE_HOURS': {'test': 48, 'main': 48}})
    @override_settings(POOL_ADDRESS={'test': 'abc', 'main': 'xyz'})
    def test_process_nosubsidy(self):
        # set subsidy to of all blocks
        
        Block.objects.all().update(subsidy=0)

        with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.subsidy', return_value={'subsidy': '0', 'recipient': 'abc'}):
            # should be marked as FI
            shareout_next_block('test')
            
        block1 = Block.objects.get(height=1, network="test")
        self.assertEqual(block1.process_status, 'FI')
        
        self.assertEqual(Transaction.objects.all().count(), 1) # one old  
        
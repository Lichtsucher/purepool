from django.test import TestCase
from purepool.models.miner.models import Miner, Worker, MinerNotFound
from purepool.interface.formats import SolutionString, WorkerId, InvalidWorkerdId

class WorkerIdTestCase(TestCase):

    def setUp(self):
        self.miner = Miner(address='123456', network="main")
        self.miner.save()

        self.worker = Worker(miner=self.miner, name="abc")
        self.worker.save()

    def test_parsing(self):
        with self.assertRaises(InvalidWorkerdId) as e:
            worker_id = WorkerId('')

        with self.assertRaises(InvalidWorkerdId) as e:
            worker_id = WorkerId('/')

        with self.assertRaises(InvalidWorkerdId) as e:
            worker_id = WorkerId('//')

        worker_id = WorkerId('123456')
        self.assertEqual(worker_id.get_address(), "123456")
        self.assertEqual(worker_id.get_worker(), 'Default')
        self.assertEqual(worker_id.get_email(), None)        
        
        worker_id = WorkerId('123456/')
        self.assertEqual(worker_id.get_address(), "123456")
        self.assertEqual(worker_id.get_worker(), 'Default')
        self.assertEqual(worker_id.get_email(), None)
        
        worker_id = WorkerId('123456/abc')
        self.assertEqual(worker_id.get_address(), "123456")
        self.assertEqual(worker_id.get_worker(), "abc")
        self.assertEqual(worker_id.get_email(), None)
        
        worker_id = WorkerId('123456/abc/ex@test.test')
        self.assertEqual(worker_id.get_address(), "123456")
        self.assertEqual(worker_id.get_worker(), "abc")
        self.assertEqual(worker_id.get_email(), "ex@test.test")

        self.assertEqual(worker_id.get_worker_obj('main'), self.worker)        
        
        with self.assertRaises(MinerNotFound) as e:
            self.assertEqual(worker_id.get_worker_obj('test'), self.worker)

class SolutionStringTestCase(TestCase):  

    def test_parse_solution_string(self):
        s = "12345,1516741759,1516741614,5,54321,SOMERANDOMMINERID,e5161e2a,4,12763,1516741681340,73728,1516741681759,1516741762590,12762,999999,888888"       
        solutionstr = SolutionString(s)
        
        self.assertEqual(solutionstr.get_block_hash(), "12345")
        self.assertEqual(solutionstr.get_block_time(), "1516741759")
        self.assertEqual(solutionstr.get_prev_block_time(), "1516741614")
        self.assertEqual(solutionstr.get_prev_height(), "5")
        self.assertEqual(solutionstr.get_bible_hash(), "54321")
        
        self.assertEqual(solutionstr.get_miner_id(), "SOMERANDOMMINERID")
        
        self.assertEqual(solutionstr.get_work_id(), "e5161e2a")
        self.assertEqual(solutionstr.get_thread_id(), "4")
        self.assertEqual(solutionstr.get_thread_hash_counter(), 12763)
        self.assertEqual(solutionstr.get_thread_start(), 1516741681340)
        self.assertEqual(solutionstr.get_hash_counter(), 73728)
        self.assertEqual(solutionstr.get_timer_start(), 1516741681759)
        self.assertEqual(solutionstr.get_timer_end(), 1516741762590)
        self.assertEqual(solutionstr.get_nonce(), "12762")
        self.assertEqual(solutionstr.get_block_hex(), "999999")
        self.assertEqual(solutionstr.get_transaction_hex(), "888888")
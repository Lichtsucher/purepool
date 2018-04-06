import datetime
from unittest import mock
from django.conf import settings
from django.utils import timezone
from django.test import TestCase
from purepool.interface.formats import SolutionString
from purepool.models.miner.models import Miner, Worker
from purepool.models.solution.models import Solution, Work, RejectedSolution
from purepool.models.solution.tasks import calculate_multiply, process_solution, validate_solution, cleanup_solutions, UnknownWork, HashTargetExceeded, BibleHashWrong, TransactionInvalid, TransactionTampered, InvalidSolution, Invalid_CPID, Biblepayd_Outdated, Illegal_CPID

class calculate_multiplyTestCase(TestCase):
    
    def setUp(self):
        self.miner = Miner()
        self.miner.save()

        self.solution_string = SolutionString()
        self.solution_string.content = {
            'miner_id': self.miner.id,
        }

    def test_regular(self):
        self.miner.percent_ratio = 100
        self.miner.save()

        self.assertEqual(calculate_multiply(self.solution_string), 1)

    def test_bad(self):
        self.miner.percent_ratio = 400
        self.miner.save()

        with mock.patch('random.randrange', return_value=200):
            self.assertEqual(calculate_multiply(self.solution_string), 0)

        with mock.patch('random.randrange', return_value=50):
            self.assertEqual(calculate_multiply(self.solution_string), 1)

    def test_good(self):
        self.miner.percent_ratio = 9
        self.miner.save()
        self.assertEqual(calculate_multiply(self.solution_string), 4)

        self.miner.percent_ratio = 30
        self.miner.save()
        self.assertEqual(calculate_multiply(self.solution_string), 3)

        self.miner.percent_ratio = 50
        self.miner.save()
        self.assertEqual(calculate_multiply(self.solution_string), 2)

class validate_solutionTestCase(TestCase):
    
    def setUp(self):
        self.miner = Miner()
        self.miner.save()
        
        self.worker = Worker(miner=self.miner)
        self.worker.save()
        
        self.solution_string = SolutionString()
        self.solution_string.content = {
            'transaction_hex': '01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff05026e4b0103ffffffff01ca6940057a0100001976a914e83c22b58de63a91952524084f46415c985d715c88acfdce013c5645523e312e302e382e363c2f5645523e3c4d494e4552475549443e65656635636263622d663637332d343230332d613739312d6637373362313737663164663c2f4d494e4552475549443e3c706f6c6d6573736167653e666531313263363532643964643063663436326135333762636466363561323537663461613331303032396666373432383964396366623665303161396662623c2f706f6c6d6573736167653e3c706f6c7765696768743e35363438302e35313c2f706f6c7765696768743e3c706f6c616d6f756e743e31363437342e30303c2f706f6c616d6f756e743e3c706f6c6176676167653e332e3432393c2f706f6c6176676167653e3c5349475f303e494d3736436d344e57376e554e78614e5050797662373473424d437945586e314d49347339376b4f334d475a6469672f496a59486c48594139637346616b3769756451536c6769596f643366756d4c2f44797075706e593d3c2f5349475f303e3c5349475f313e494e684d7a47487658727a4b654366424e384d4c584671466b45495a36455758694a572f6535334e73384e4c5652755274535877395830337937452b46447a7a68455762744756543868307a42477751484c33305930513d3c2f5349475f313e00000000',
            'thread_hash_counter': '332694',
            'prev_block_time': '1518041437',
            'prev_height': '19309',
            'nonce': '14217',
            'block_hash': '4adfaf0c3ad50afecad53ad1e57340e9735bca7d104b2b3565835a346e1c6c96',
            'miner_id': self.miner.id, 
            'work_id': 'b0181b3a-9868-4139-bef5-8c7e5d4239f4',
            'block_time': '1518041523',
            'thread_id': '0',
            'timer_start': '1518037739857',
            'thread_start': '1518040817888',
            'bible_hash': '0000000e5bced1fccc7110dfd386cf461b82852ce4eec5e124ca8f5e5bcc5a11',
            'hash_counter': '1769512',
            'timer_end': '1518041527556',
            'block_hex': '000000209928ce1b5ba829fde591237d3876df45daa2dd30ec31805b43dd6b972eae9aff3fab6ced6b34254aeb8c7f004cb82178984dbf22ea5c5316ac33ae6ec90ef17db3797b5aa5aa081d893700000201000000010000000000000000000000000000000000000000000000000000000000000000ffffffff05026e4b0103ffffffff01ca6940057a0100001976a914e83c22b58de63a91952524084f46415c985d715c88acfdce013c5645523e312e302e382e363c2f5645523e3c4d494e4552475549443e65656635636263622d663637332d343230332d613739312d6637373362313737663164663c2f4d494e4552475549443e3c706f6c6d6573736167653e666531313263363532643964643063663436326135333762636466363561323537663461613331303032396666373432383964396366623665303161396662623c2f706f6c6d6573736167653e3c706f6c7765696768743e35363438302e35313c2f706f6c7765696768743e3c706f6c616d6f756e743e31363437342e30303c2f706f6c616d6f756e743e3c706f6c6176676167653e332e3432393c2f706f6c6176676167653e3c5349475f303e494d3736436d344e57376e554e78614e5050797662373473424d437945586e314d49347339376b4f334d475a6469672f496a59486c48594139637346616b3769756451536c6769596f643366756d4c2f44797075706e593d3c2f5349475f303e3c5349475f313e494e684d7a47487658727a4b654366424e384d4c584671466b45495a36455758694a572f6535334e73384e4c5652755274535877395830337937452b46447a7a68455762744756543868307a42477751484c33305930513d3c2f5349475f313e00000000010000000223e3f54cbfd562a065218f2f5be70a9d22e6ff7820dd0d1f701a53afb53767170000000049483045022100d612e1ee658823964ebdc3dedcecf2e9c19c7a9891ba264b8ba170cdfed58fbd02201d4de4c922afa8c218aa8fe6b73eadd62f00109cd777b3f7489f50eab83d3da301feffffff3fab86d7035b899793e1264899b1838fd6b988a7adc1866365dbd06250c65f260000000048473044022005004171fbc47a417c5c68e3abfd8a76e375029866b779ae117730d61ff64bab0220268e22a951608a7050747fa9e373d7610b11eb3de663f954affdf394941b777501feffffff0225b74458390000001976a9146ebc0349fad92dbb1b277ea9209609b5a485e4f988ac1f3c706f6c7765696768743e31343031312e30303c2f706f6c7765696768743ed6e9123b46010000232103dbeb934062e53b5deef24a89825b225eeea09c31037693ac7d192c5c581e1fbcac1f3c706f6c7765696768743e31343031312e30303c2f706f6c7765696768743e6d4b0000'
        }

    def test_basic(self):
        
        # work missing
        with self.assertRaises(UnknownWork):
            validate_solution('test', self.solution_string)
        
        # check_hashtarget fails
        work = Work(pk='b0181b3a-9868-4139-bef5-8c7e5d4239f4', hash_target="0000000111100000000000000000000000000000000000000000000000000000", worker=self.worker, ip="1.1.1.1", network="test")
        work.save()

        with self.assertRaises(HashTargetExceeded):        
            validate_solution('test', self.solution_string)
        
        # client.bible_hash returns different bible hash
        work.hash_target = '0000001111000000000000000000000000000000000000000000000000000000'
        work.save()

        with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.bible_hash', return_value="1234"):
            with self.assertRaises(BibleHashWrong):
                validate_solution('test', self.solution_string)

        # from here on, we fake a valid answer for the bible_hash calculation, so that
        # succeed
        with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.bible_hash', return_value="0000000e5bced1fccc7110dfd386cf461b82852ce4eec5e124ca8f5e5bcc5a11"):
            
            # fail if the target address in the transaction is not from the pool
            trans_result = {'recipient': 'yiCwAb9qeaQqzDX5jQZJgBQ9mRy2aqk2Tb'}
            with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result):
                with self.settings(POOL_ADDRESS={'test': 'ABCDEFG', 'cpid_sig_valid': True}):
                    with self.assertRaises(TransactionTampered):                
                        validate_solution('test', self.solution_string)
            
            # fail if this is an invalid TX
            with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result) as mock_hexblocktocoinbase:
                mock_hexblocktocoinbase.side_effect = TypeError()
                with self.assertRaises(TransactionInvalid):
                    validate_solution('test', self.solution_string)

            # the TX is valid here, but the nonce is not right!
            with self.settings(POOL_ADDRESS={'test': 'ABCDEFG'}):
                trans_result = {'recipient': 'ABCDEFG', 'cpid_sig_valid': True, 'cpid_legal': True}
                with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result):
                    with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.pinfo', return_value={'pinfo': 3, 'height': 0}):
                        with self.assertRaises(TransactionTampered):
                            validate_solution('test', self.solution_string)

            # Here the prev_height was faked
            with self.settings(POOL_ADDRESS={'test': 'ABCDEFG'}):
                trans_result = {'recipient': 'ABCDEFG', 'cpid_sig_valid': True, 'cpid_legal': True}
                with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result):
                    with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.pinfo', return_value={'pinfo': 999999, 'height': 19}):
                        with self.assertRaises(TransactionTampered):
                            validate_solution('test', self.solution_string)

            # now cpid_sig_valid is missing -> old biblepay server client
            with self.settings(POOL_ADDRESS={'test': 'ABCDEFG'}):
                trans_result = {'recipient': 'ABCDEFG'}
                with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result):
                    with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.pinfo', return_value={'pinfo': 999999, 'height': 19}):
                        with self.assertRaises(Biblepayd_Outdated):
                            validate_solution('test', self.solution_string)

            # and now cpid_sig_valid is False
            with self.settings(POOL_ADDRESS={'test': 'ABCDEFG'}):
                trans_result = {'recipient': 'ABCDEFG', 'cpid_sig_valid': True, 'cpid_legal': False}
                with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result):
                    with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.pinfo', return_value={'pinfo': 999999, 'height': 19}):
                        with self.assertRaises(Illegal_CPID):
                            validate_solution('test', self.solution_string)

            # cpid_legal indicates if the user was in the last payout for Rosetta, plus it checks if the user had just solved a block
            # and can't solve a new one for the next 3 blocks
            with self.settings(POOL_ADDRESS={'test': 'ABCDEFG'}):
                trans_result = {'recipient': 'ABCDEFG', 'cpid_sig_valid': False, 'cpid_legal': True}
                with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result):
                    with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.pinfo', return_value={'pinfo': 999999, 'height': 19}):
                        with self.assertRaises(Invalid_CPID):
                            validate_solution('test', self.solution_string)
        
            # and now, with everything right, it should succeed
            with self.settings(POOL_ADDRESS={'test': 'ABCDEFG'}):
                trans_result = {'recipient': 'ABCDEFG', 'cpid_sig_valid': True, 'cpid_legal': True}
                with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.hexblocktocoinbase', return_value=trans_result):
                    with mock.patch('purepool.models.solution.tasks.BiblePayRpcClient.pinfo', return_value={'pinfo': 999999, 'height': 19309}):
                        self.assertTrue(validate_solution('test', self.solution_string))
        
        
class process_solutionTestCase(TestCase):
    
    def setUp(self):
        self.miner = Miner()
        self.miner.save()
        
        self.worker = Worker(miner=self.miner)
        self.worker.save()
        
        self.work = Work(hash_target="0000000111100000000000000000000000000000000000000000000000000000", worker=self.worker, ip="1.1.1.1")
        self.work.save()        
        
        self.solution_string = SolutionString()
        self.solution_string.content = {
            'transaction_hex': 'TransHex',
            'thread_hash_counter': '332694',
            'prev_block_time': '1518041437',
            'prev_height': '19309',
            'nonce': '14217',
            'block_hash': 'ABCD',
            'miner_id': self.miner.id, 
            'work_id': self.work.id,
            'block_time': '1518041523',
            'thread_id': '0',
            'timer_start': '1518037739857',
            'thread_start': '1518040817888',
            'bible_hash': '0000000e5bced1fccc7110dfd386cf461b82852ce4eec5e124ca8f5e5bcc5a11',
            'hash_counter': '1769512',
            'timer_end': '1518041527556',
            'block_hex': 'BlockHex'}
        self.solution_s = self.solution_string.as_string()
    
    def test_valid(self):
        
        self.assertEqual(len(Solution.objects.all()), 0)
        self.assertEqual(len(RejectedSolution.objects.all()), 0)
        
        with mock.patch('purepool.models.solution.tasks.validate_solution', return_value=True):
            process_solution('test', self.solution_s)
        
        self.assertEqual(len(RejectedSolution.objects.all()), 0)
        self.assertEqual(len(Solution.objects.all()), 1)
        
        solution = Solution.objects.all()[0]
        self.assertEqual(solution.network, 'test')
        self.assertEqual(solution.miner_id, self.miner.id)
        self.assertEqual(solution.work_id, self.work.id)
        self.assertEqual(solution.bible_hash, self.solution_string.get_bible_hash())
        self.assertEqual(solution.solution, self.solution_s)
        self.assertEqual(solution.hps, 467)

    def test_valid_multiply(self):

        self.assertEqual(len(Solution.objects.all()), 0)
        self.assertEqual(len(RejectedSolution.objects.all()), 0)

        with mock.patch('purepool.models.solution.tasks.validate_solution', return_value=True):
            with mock.patch('purepool.models.solution.tasks.calculate_multiply', return_value=3):
                process_solution('test', self.solution_s)

        self.assertEqual(len(RejectedSolution.objects.all()), 0)
        self.assertEqual(len(Solution.objects.all()), 3)

        solution = Solution.objects.all()[0]
        self.assertEqual(solution.network, 'test')
        self.assertEqual(solution.miner_id, self.miner.id)
        self.assertEqual(solution.work_id, self.work.id)
        self.assertEqual(solution.bible_hash, self.solution_string.get_bible_hash())
        self.assertEqual(solution.solution, self.solution_s)
        self.assertEqual(solution.hps, 467)
        
    def test_invalid(self):
        
        self.assertEqual(len(Solution.objects.all()), 0)
        self.assertEqual(len(RejectedSolution.objects.all()), 0)
        
        with mock.patch('purepool.models.solution.tasks.validate_solution', return_value=False) as mock_validate_solution:
            mock_validate_solution.side_effect = BibleHashWrong
            with self.assertRaises(BibleHashWrong):
                process_solution('test', self.solution_s)
                        
        self.assertEqual(len(RejectedSolution.objects.all()), 1)
        self.assertEqual(len(Solution.objects.all()), 0)
        
        rsolution = RejectedSolution.objects.all()[0]
        self.assertEqual(rsolution.network, 'test')
        self.assertEqual(rsolution.miner_id, self.miner.id)
        self.assertEqual(rsolution.work_id, self.work.id)
        self.assertEqual(rsolution.bible_hash, self.solution_string.get_bible_hash())
        self.assertEqual(rsolution.solution, self.solution_s)
        self.assertEqual(rsolution.hps, 0)

class cleanup_solutionsTestCase(TestCase):
    
    def setUp(self):
        self.miner = Miner()
        self.miner.save()
        
        self.worker = Worker(miner=self.miner)
        self.worker.save()        
    
    def test_cleanup(self):
        older = timezone.now() - datetime.timedelta(days=settings.POOL_CLEANUP_MAXDAYS + 8)
        
        # an older entry
        work = Work(worker=self.worker, ip="1.1.1.1")
        work.save()
        work.inserted_at = older
        work.save()
        
        # and a new work entry
        work2 = Work(worker=self.worker, ip="2.2.2.2")
        work2.save()
        
        self.assertEqual(len(Work.objects.all()), 2)
        
        cleanup_solutions()
        
        self.assertEqual(len(Work.objects.all()), 1)
        self.assertEqual(Work.objects.all()[0].ip, '2.2.2.2')
from django.test import TestCase
from purepool.models.miner.models import Miner
from puretransaction.models import Transaction


class MinerCalculationTestCase(TestCase):
    
    def setUp(self):
        self.miner1 = Miner(network="test", address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx")
        self.miner1.save()
        
        self.miner2 = Miner(network="test", address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxx2")
        self.miner2.save()
        
        Transaction(miner=self.miner1, network="test", amount=10).save()
        Transaction(miner=self.miner1, network="test", amount=5).save()
        Transaction(miner=self.miner1, network="test", amount=-2).save()
        
        # should not happen, but better safe then sorry
        Transaction(miner=self.miner1, network="main", amount=100).save()
        
        Transaction(miner=self.miner2, network="test", amount=99).save()
        Transaction(miner=self.miner2, network="test", amount=-90).save()
        
    def test_basic(self):
        self.miner1.update_balance()
        self.miner2.update_balance()
        
        self.assertEqual(self.miner1.balance, 13)
        self.assertEqual(self.miner2.balance, 9)
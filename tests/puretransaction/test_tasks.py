import datetime
from unittest import mock
from django.utils import timezone
from django.conf import settings
from django.test import TestCase, override_settings
from purepool.models.miner.models import Miner
from puretransaction.models import Transaction, TransactionError
from puretransaction.tasks import send_autopayments

class send_autopaymentsTestCase(TestCase):
    
    def setUp(self):
        # the miner 1 starts with a fake balance
        self.miner1 = Miner(network="test", balance=20, address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx")
        self.miner1.save()
        
        # as the user above, but with not enough balance
        self.miner2 = Miner(network="test", balance=1, address="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxx2")
        self.miner2.save()       
        
        Transaction(miner=self.miner1, amount=4, network="test").save()
        Transaction(miner=self.miner2, amount=1, network="test").save()

        
    @override_settings(POOL_MINIMUM_AUTOSEND = {'main': 10, 'test': 10})
    @mock.patch('puretransaction.tasks.BiblePayRpcClient.sendtoaddress', return_value="TXTEST")
    @mock.patch('time.sleep', return_value="")
    def test_wrongvalue(self, mock_sendtoaddress, mock_sleep):
        # balance in Miner table is higher then the real balance
        send_autopayments("test")
        
        miner1 = Miner.objects.get(pk=self.miner1.id)
        self.assertEqual(miner1.balance, 4)
        
        self.assertEqual(Transaction.objects.filter(category='TX').count(), 0)
    
    @override_settings(POOL_MINIMUM_AUTOSEND = {'main': 10, 'test': 10})
    @mock.patch('puretransaction.tasks.BiblePayRpcClient.sendtoaddress', return_value="TXTEST")
    @mock.patch('time.sleep', return_value="")
    def test_outdated_value(self, mock_sendtoaddress, mock_sleep):
        # balance is high enough, but not right
        
        Transaction(miner=self.miner1, amount=10, network="test").save()
        
        send_autopayments("test")

        miner1 = Miner.objects.get(pk=self.miner1.id)
        self.assertEqual(miner1.balance, 0)
        
        self.assertEqual(Transaction.objects.filter(category='TX').count(), 1)
        
        tx = Transaction.objects.get(category='TX')
        self.assertEqual(tx.amount, -14)
        self.assertEqual(tx.miner.id, miner1.id)
        self.assertEqual(tx.network, "test")
        
    @override_settings(POOL_MINIMUM_AUTOSEND = {'main': 10, 'test': 10})
    @mock.patch('puretransaction.tasks.BiblePayRpcClient.sendtoaddress', return_value="TXTEST")
    def test_error_on_send(self, mock_sendtoaddress):
        mock_sendtoaddress.side_effect = Exception()
        
        Transaction(miner=self.miner1, amount=10, network="test").save()
        
        send_autopayments("test")
    
    @override_settings(POOL_MINIMUM_AUTOSEND = {'main': 10, 'test': 10})
    @mock.patch('puretransaction.tasks.BiblePayRpcClient.sendtoaddress', return_value="TXTEST")
    @mock.patch('time.sleep', return_value="")
    def test_process(self, mock_sendtoaddress, mock_sleep):
        # a successfull run
        
        Transaction(miner=self.miner1, amount=30, network="test").save()
        
        self.miner1.update_balance()
        self.miner1.save()
        
        Transaction(miner=self.miner1, amount=10, network="test").save()
        
        send_autopayments("test")

        miner1 = Miner.objects.get(pk=self.miner1.id)
        self.assertEqual(miner1.balance, 0)
        
        self.assertEqual(Transaction.objects.filter(category='TX').count(), 1)
        
        tx = Transaction.objects.get(category='TX')
        self.assertEqual(tx.amount, -44)
        self.assertEqual(tx.miner.id, miner1.id)
        self.assertEqual(tx.network, "test")


        # even with a new balance, should not pay again, as we do not pay so early again
        Transaction(miner=self.miner1, amount=16, network="test").save()

        self.miner1.update_balance()
        self.miner1.save()

        send_autopayments("test")

        miner1 = Miner.objects.get(pk=self.miner1.id)
        self.assertEqual(miner1.balance, 16)

        self.assertEqual(Transaction.objects.filter(category='TX').count(), 1)
        
        tx = Transaction.objects.get(category='TX')
        self.assertEqual(tx.amount, -44)
        self.assertEqual(tx.miner.id, miner1.id)
        self.assertEqual(tx.network, "test")


        # but if first_trans is older, then the second one should be paid
        tx.inserted_at = timezone.now() - datetime.timedelta(hours=18)
        tx.save()

        send_autopayments("test")

        miner1 = Miner.objects.get(pk=self.miner1.id)
        self.assertEqual(miner1.balance, 0)

        self.assertEqual(Transaction.objects.filter(category='TX').count(), 2)
        
        tx = Transaction.objects.filter(category='TX').order_by('-id')[0]
        self.assertEqual(tx.amount, -16)
        self.assertEqual(tx.miner.id, miner1.id)
        self.assertEqual(tx.network, "test")



    @override_settings(POOL_MINIMUM_AUTOSEND = {'main': 10, 'test': 10})
    @mock.patch('puretransaction.tasks.BiblePayRpcClient.sendtoaddress', return_value="TXTEST")
    def test_process_failed(self, mock_sendtoaddress):
        mock_sendtoaddress.side_effect = Exception()

        # a successfull run

        Transaction(miner=self.miner1, amount=30, network="test").save()

        self.miner1.update_balance()
        self.miner1.save()

        Transaction(miner=self.miner1, amount=10, network="test").save()

        send_autopayments("test")

        miner1 = Miner.objects.get(pk=self.miner1.id)
        self.assertEqual(miner1.balance, 34) # transaction wasn't done

        self.assertEqual(Transaction.objects.filter(category='TX').count(), 0)

        self.assertEqual(TransactionError.objects.all().count(), 1)
    
from django.urls import reverse
from django.test import Client
from django.test import TestCase
from purepool.models.miner.models import Miner, Worker
from purepool.models.solution.models import Work

class ActionViewTestCase(TestCase):

    def setUp(self):
        self.client = Client()

    def test_invalid_action(self):        
        response = self.client.post(reverse('action_aspx'))

        self.assertEqual(response.content, b'<RESPONSE>UNKNOWN ACTION EMPTY</RESPONSE><ERROR>UNKNOWN ACTION EMPTY</ERROR><EOF>')      

    
    def test_readytomine2(self):
        # no network defined
        response = self.client.post(reverse('action_aspx'), Action="readytomine2")        
        self.assertEqual(response.content, b'<RESPONSE>Invalid network</RESPONSE><ERROR>Invalid network</ERROR><EOF>')      
        
        # no worker
        response = self.client.post(reverse('action_aspx'), Action="readytomine2", NetworkID='main')        
        self.assertEqual(response.content, b'<RESPONSE>WorkerID is missing</RESPONSE><ERROR>WorkerID is missing</ERROR><EOF>')
        
        # now everything should be right
        with self.settings(POOL_ADDRESS={'main': 'ABCDEFG'}):
            response = self.client.post(reverse('action_aspx'), Action="readytomine2", NetworkID='main', Miner="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx/123")
        
        # we need to load the miner from the db to get its id
        miner = Miner.objects.all()[0]
        work = Work.objects.all()[0]
        rs = "<RESPONSE> <ADDRESS>ABCDEFG</ADDRESS><HASHTARGET>0001111000000000000000000000000000000000000000000000000000000000</HASHTARGET><MINERGUID>%s</MINERGUID><WORKID>%s</WORKID></RESPONSE>" % (miner.id, work.pk)
        
        self.assertEqual(response.content, rs.encode('ascii'))
        
        # and with more information about the system
        Work.objects.all().delete()
        
        response = self.client.post(reverse('action_aspx'), Action="readytomine2", NetworkID='main', Miner="B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx/123",
                                    ThreadID="40", OS="LIN", Agent="1.0.8.3")
        
        work = Work.objects.all()[0]
        self.assertEqual(work.thread_id, "40")
        self.assertEqual(work.os, "LIN")
        self.assertEqual(work.agent, "1.0.8.3")
        
        # even with multiple requests, there should only one miner and one worker
        self.assertEqual(Miner.objects.all().count(), 1)
        miner = Miner.objects.all()[0]
        self.assertEqual(miner.address, "B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxxxx")
        self.assertEqual(miner.network, "main")
        
        self.assertEqual(Worker.objects.all().count(), 1)
        worker = Worker.objects.all()[0]
        self.assertEqual(worker.name, "123")
        
        
        
        
        
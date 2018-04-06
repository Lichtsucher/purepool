from django.urls import reverse
from django.test import Client
from django.test import TestCase
from purepool.models.miner.models import Miner
from purepool.interface.hash import GetHashTarget

class GetHashTargetTestCase(TestCase):

    def setUp(self):
        self.miner = Miner(rating=0)
        self.miner.save()

    def test_basic(self):
        self.assertEqual(GetHashTarget(self.miner.id, 'main'), '0000011110000000000000000000000000000000000000000000000000000000')

        # NOTE: In previos versions, the rating changed the hash
        # But now, we drop them in the validate_solution task. This test ensures that the new behavior is working
        self.miner.rating = -1
        self.miner.save()
        self.assertEqual(GetHashTarget(self.miner.id, 'main'), '0000011110000000000000000000000000000000000000000000000000000000')

        self.miner.rating = -2
        self.miner.save()
        self.assertEqual(GetHashTarget(self.miner.id, 'main'), '0000011110000000000000000000000000000000000000000000000000000000')

        self.miner.rating = 1
        self.miner.save()
        self.assertEqual(GetHashTarget(self.miner.id, 'main'), '0000011110000000000000000000000000000000000000000000000000000000')
        
        self.miner.rating = 2
        self.miner.save()
        self.assertEqual(GetHashTarget(self.miner.id, 'main'), '0000011110000000000000000000000000000000000000000000000000000000')
        
        self.miner.rating = 3
        self.miner.save()
        self.assertEqual(GetHashTarget(self.miner.id, 'main'), '0000011110000000000000000000000000000000000000000000000000000000')                
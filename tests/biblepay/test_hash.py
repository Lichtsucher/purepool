from django.test import TestCase
from biblepay.hash import check_hashtarget, validate_bibleplay_address_format

class check_hashtargetTestCase(TestCase):

    def test_basic(self):
        bible_hash = '0000000ec75f80a3bc9fc2f6477debcbb0d7199618ac0c0a9592a4c3fe141f8c'
        hash_target = '0000001111000000000000000000000000000000000000000000000000000000'        
        self.assertTrue(check_hashtarget(bible_hash, hash_target))
        
        # bible hash not lower than hash target
        bible_hash = '0000000ec75f80a3bc9fc2f6477debcbb0d7199618ac0c0a9592a4c3fe141f8c'
        hash_target = '0000000111100000000000000000000000000000000000000000000000000000'        
        self.assertFalse(check_hashtarget(bible_hash, hash_target))
        
        # invalid bible hash (not a hex)
        bible_hash = '0t00000ec75f80a3bc9fc2f6477debcbb0d7199618ac0c0a9592a4c3fe141f8c'
        hash_target = '0000001111000000000000000000000000000000000000000000000000000000'          
        self.assertFalse(check_hashtarget(bible_hash, hash_target))
        
        # invalid hash_target (not a hex)
        bible_hash = '0000000ec75f80a3bc9fc2f6477debcbb0d7199618ac0c0a9592a4c3fe141f8c'
        hash_target = '0000t01111000000000000000000000000000000000000000000000000000000'        
        self.assertFalse(check_hashtarget(bible_hash, hash_target))
        
class validate_bibleplay_address_formatTestCase(TestCase):

    def test_basic(self):
        self.assertFalse(validate_bibleplay_address_format(''))
        self.assertFalse(validate_bibleplay_address_format('X'))
        self.assertFalse(validate_bibleplay_address_format('B'))
        self.assertFalse(validate_bibleplay_address_format('y'))
        self.assertFalse(validate_bibleplay_address_format('BN4VQZZiMNzrwcUeyQHJMhqwPXAmw6'))
        self.assertFalse(validate_bibleplay_address_format('B91RjV9UoZa5qLN/WZFXJ42sFWbJCyxUTH'))
        self.assertFalse(validate_bibleplay_address_format('BPqA6pteBR9bsU8eDrg4FdqNT9SiwVWYAK/Fake'))
        self.assertFalse(validate_bibleplay_address_format('BPqA6pteBR9bsU8eDrg4FdqNT9SiwVWYAK\Fake'))
        
        self.assertTrue(validate_bibleplay_address_format('B91RjV9UoZa5qLNbWZFXJ42sFWbJCyxUTH'))
        self.assertTrue(validate_bibleplay_address_format('BLzS3xeaoiXUchbBofi7dzNqwrGyUeUdC6'))
        self.assertTrue(validate_bibleplay_address_format('BN4VQZZiMNzrwcUeyQHJMhqwPXAmw6KZyV'))
        self.assertTrue(validate_bibleplay_address_format('BAjSAKyJzMsPq9g4RUwHdjSo9XPKDqCir9'))
        self.assertTrue(validate_bibleplay_address_format('BMT67Esfji6WhoLz8dpEkTra1wcm2op2mb'))
        self.assertTrue(validate_bibleplay_address_format('BLTnAZj8NgaHYwUJNJ8bGkZGHd7mAabGuw'))
        self.assertTrue(validate_bibleplay_address_format('BPqA6pteBR9bsU8eDrg4FdqNT9SiwVWYAK'))
        self.assertTrue(validate_bibleplay_address_format('B6NAr59Sj2738TbKrq9951aJuzzGuaxWDb'))
        self.assertTrue(validate_bibleplay_address_format('BCPKUNFCz8P8uh76yrTpnYYktuHWEDBydM'))
        self.assertTrue(validate_bibleplay_address_format('BH1V3ue4uUdz5shvJMPKkii8kzMwCk7Gpu'))
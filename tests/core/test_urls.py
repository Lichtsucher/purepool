from django.test import Client
from django.test import TestCase

class UrlsTestCase(TestCase):
    
    def test_action_url(self):
        """ ensures that at least the Action.aspx is available """
        
        response = client.get(reverse('blog_index'))
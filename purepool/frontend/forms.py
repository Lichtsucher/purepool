from django import forms

class MinerForm(forms.Form):
    address = forms.CharField(label='Biblepay Address', max_length=100)
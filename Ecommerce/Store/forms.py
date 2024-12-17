from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'address',
            'city',
            'state',
            'zip_code',
            'country',
        ]
        
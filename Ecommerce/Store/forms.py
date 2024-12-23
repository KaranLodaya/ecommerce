from django import forms
from .models import Address
from .models import Review

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
        
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }
from django import forms
from django.forms import Form, ModelForm, ValidationError, TextInput, NumberInput, PasswordInput, DateInput, EmailInput

from .models import *


class GameForm(ModelForm):

    class Meta:
        model = Game
        fields = ['date_start', 'quota_period_days', 'twilio_phone_num', 'twilio_account_sid', 'twilio_auth_token']
        widgets = {
            'date_start': DateInput(attrs={'class': 'form-control date start', 'placeholder': 'mm/dd/yyyy', 'autofocus': 'autofocus'}),  # TODO: data format? make datepicker automatically pop up when field is focused
            'quota_period_days': NumberInput(attrs={'class': 'form-control'}),
            'twilio_phone_num': TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXXXXXXXX', 'type': 'tel'}),
            'twilio_account_sid': TextInput(attrs={'class': 'form-control', 'placeholder': '34 characters long'}),
            'twilio_auth_token': TextInput(attrs={'class': 'form-control', 'placeholder': '32 characters long'}),
        }

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        game = kwargs.get('instance')
        if game and game.has_started:
            self.fields['date_start'].disabled = True


class UserForm(ModelForm):

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'password', 'email')
        widgets = {
            'first_name': TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name', 'autofocus': 'autofocus'}),
            'last_name': TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'username': TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password': PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'email': EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }

    def clean(self, *args, **kwargs):
        self.cleaned_data['first_name'] = self.data['first_name'].capitalize()
        self.cleaned_data['last_name'] = self.data['last_name'].capitalize()
        super(UserForm, self).clean(*args, **kwargs)


class UserProfileForm(ModelForm):

    class Meta:
        model = UserProfile
        fields = ('phone_num', 'codename')
        widgets = {
            'phone_num': TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXXXXXXXX', 'type': 'tel', 'autofocus': 'autofocus'}),
            'codename': TextInput(attrs={'class': 'form-control', 'placeholder': 'Codename'}),
        }
        help_texts = {
            'phone_num': 'For text notifications (recommended)',
            'codename': "Your anonymous name on the leaderboard. Pick something that can't be used to identify you",
        }

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(UserProfileForm, self).__init__(*args, **kwargs)


class UserUpdateForm(forms.Form):
    email = forms.EmailField(required=False, help_text='For email notifications (optional)', widget=EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email', 'autofocus': 'autofocus'}))
    phone_num = forms.CharField(label='Phone Number', required=False, validators=[phone_validator], help_text='For text notifications (recommended)', widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXXXXXXXX', 'type': 'tel'}))
    codename = forms.CharField(required=True, help_text="Your anonymous name on the leaderboard. Pick something that can't be used to identify you", widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Codename'}))

class LoginForm(forms.Form):
    username = forms.CharField(widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Username', 'autofocus': 'autofocus'}))
    password = forms.CharField(widget=PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()

class UniversityLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your Email or University ID',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your Password'
        })
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Invalid email/ID or password. Please verify credentials.",
                    code='invalid_login',
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

class StudentSignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Create strong password'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm password'})
    )

    class Meta:
        model = User
        fields = ['university_id', 'username', 'first_name', 'last_name', 'email', 'phone', 'gender']
        widgets = {
            'university_id': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 21BCE1045'}),
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'student@university.edu'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if password and confirm and password != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data

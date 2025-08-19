from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import FeedbackForm, FeedbackQuestion, User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, required=True)
    
    class Meta:
        model = get_user_model()
        fields = ("username", "email", "first_name", "last_name", "role", "password1", "password2")
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        UserModel = get_user_model()
        if username and UserModel.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Un utilisateur avec ce nom d'utilisateur existe déjà.")
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user

class FeedbackFormForm(forms.ModelForm):
    class Meta:
        model = FeedbackForm
        fields = ['programme', 'jalon', 'titre', 'description']
        widgets = {
            'programme': forms.Select(attrs={'class': 'form-control'}),
            'jalon': forms.Select(attrs={'class': 'form-control'}),
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FeedbackQuestionForm(forms.ModelForm):
    class Meta:
        model = FeedbackQuestion
        fields = ['texte', 'type', 'choices']
        widgets = {
            'texte': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'choices': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Pour les choix multiples, séparez par des virgules'
            }),
        }

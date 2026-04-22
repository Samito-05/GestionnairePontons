from django import forms
from django.utils import timezone
from .models import Embarcation, Location, Ponton, UserProfile
from django.contrib.auth.models import User


class LocationRapideForm(forms.Form):
    """Formulaire gestionnaire : louer une embarcation en 1 clic."""
    embarcation = forms.ModelChoiceField(
        queryset=Embarcation.objects.filter(actif=True),
        label='Embarcation',
        widget=forms.Select(attrs={'class': 'select is-fullwidth'}),
    )
    notes = forms.CharField(
        max_length=255,
        required=False,
        label='Notes',
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Optionnel…'}),
    )

    def __init__(self, *args, ponton=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ponton:
            self.fields['embarcation'].queryset = Embarcation.objects.filter(actif=True, ponton=ponton)


class PontonForm(forms.ModelForm):
    class Meta:
        model = Ponton
        fields = ['nom', 'description', 'ordre', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'input'}),
            'description': forms.Textarea(attrs={'class': 'textarea', 'rows': 3}),
            'ordre': forms.NumberInput(attrs={'class': 'input'}),
        }


class EmbarcationForm(forms.ModelForm):
    class Meta:
        model = Embarcation
        fields = ['nom', 'type_embarcation', 'ponton', 'couleur', 'actif', 'ordre']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'input'}),
            'type_embarcation': forms.Select(attrs={'class': 'select is-fullwidth'}),
            'ponton': forms.Select(attrs={'class': 'select is-fullwidth'}),
            'couleur': forms.TextInput(attrs={'type': 'color', 'class': 'input'}),
            'ordre': forms.NumberInput(attrs={'class': 'input'}),
        }


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['embarcation', 'heure_debut', 'heure_fin', 'notes']
        widgets = {
            'embarcation': forms.Select(attrs={'class': 'select is-fullwidth'}),
            'heure_debut': forms.DateTimeInput(
                attrs={'class': 'input', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'heure_fin': forms.DateTimeInput(
                attrs={'class': 'input', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'notes': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Notes…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['heure_debut'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['heure_fin'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['heure_fin'].required = False

    def clean(self):
        cleaned = super().clean()
        debut = cleaned.get('heure_debut')
        fin = cleaned.get('heure_fin')
        embarcation = cleaned.get('embarcation')

        if debut and not fin:
            from datetime import timedelta
            cleaned['heure_fin'] = debut + timedelta(hours=1)
            fin = cleaned['heure_fin']

        if debut and fin and fin <= debut:
            raise forms.ValidationError("L'heure de fin doit être après l'heure de début.")

        if embarcation and debut and fin:
            overlap = Location.objects.filter(
                embarcation=embarcation,
                heure_debut__lt=fin,
                heure_fin__gt=debut,
            )
            if self.instance.pk:
                overlap = overlap.exclude(pk=self.instance.pk)
            if overlap.exists():
                raise forms.ValidationError("Cette embarcation est déjà réservée sur ce créneau.")

        return cleaned


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'select is-fullwidth'}),
        }


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input'}),
        label='Mot de passe',
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'select is-fullwidth'}),
        label='Rôle',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input'}),
            'first_name': forms.TextInput(attrs={'class': 'input'}),
            'last_name': forms.TextInput(attrs={'class': 'input'}),
            'email': forms.EmailInput(attrs={'class': 'input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            UserProfile.objects.create(user=user, role=self.cleaned_data['role'])
        return user

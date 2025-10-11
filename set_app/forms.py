# Standard library imports
import random

# Django imports
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

# Local imports
from main_app.models import User, Teacher, Student, Class, Evaluation, Criterion

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Login kiriting'
        }),
        label='Login'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Parol kiriting'
        }),
        label='Parol'
    )

class TeacherCreateForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['class_assigned', 'phone_number', 'image']
        widgets = {
            'class_assigned': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
                'placeholder': 'Biriktirilgan sinf'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
                'placeholder': 'Telefon raqami (ixtiyoriy)'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
            })
        }

    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'placeholder': 'Ism'
        }),
        label='Ism'
    )

    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'placeholder': 'Familiya'
        }),
        label='Familiya'
    )

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'placeholder': 'Login'
        }),
        label='Login'
    )

    password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'placeholder': 'Parol'
        }),
        label='Parol'
    )

    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'placeholder': 'Parolni tasdiqlang'
        }),
        label='Parolni tasdiqlang'
    )

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.user_instance:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise ValidationError("Bu login boshqa foydalanuvchida band!")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password or confirm_password:
            if password != confirm_password:
                raise ValidationError("Parollar mos kelmadi!")
        return cleaned_data
    
class TeacherEditForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Ism'}),
        label='Ism'
    )

    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Familiya'}),
        label='Familiya'
    )

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Login'}),
        label='Login'
    )

    password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'placeholder': "Yangi parol (agar o'zgartirmoqchi bo'lsangiz)"
        }),
        label='Yangi parol'
    )

    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Parolni tasdiqlang'}),
        label='Parolni tasdiqlang'
    )

    class Meta:
        model = Teacher
        fields = ['class_assigned', 'phone_number', 'image']
        widgets = {
            'class_assigned': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Telefon raqami'}),
            'image': forms.ClearableFileInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
        }

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

        # Agar user_instance bo'lsa, form initial datani avtomatik to'ldiramiz
        if self.user_instance:
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            self.fields['username'].initial = self.user_instance.username

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.user_instance:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise ValidationError("Bu login boshqa foydalanuvchida band!")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password or confirm_password:
            if password != confirm_password:
                raise ValidationError("Parollar mos kelmadi!")
        return cleaned_data

class ClassCreateForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'grade_level', 'section']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Sinf nomini kiriting (masalan: 7-A)'
            }),
            'grade_level': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': '',
                'min': '1',
                'max': '11'
            }),
            'section': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Bo\'lim (A, B, C...)'
            }),
        }

class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        exclude = ['student', 'teacher', 'week_number', 'year']  # student forma orqali emas, qoʻlda set qilinadi
        widgets = {
            'homework_score': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '0', 'max': '40', 'placeholder': '0-40', 'oninput': 'calculateTotal()'
            }),
            'discipline_score': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '0', 'max': '40', 'placeholder': '0-40', 'oninput': 'calculateTotal()'
            }),
            'uniform_score': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '0', 'max': '20', 'placeholder': '0-20', 'oninput': 'calculateTotal()'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': '3',
                'placeholder': 'Qo\'shimcha izoh yozing...'
            }),
        }

class StudentCreateForm(forms.ModelForm):
    image = forms.ImageField(
        required=False,
        label="Rasm (ixtiyoriy)",
        widget=forms.ClearableFileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm',
        })
    )

    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'class_assigned', 
                  'date_of_birth', 'parent_phone', 'image']  # ❗ student_id olib tashlandi
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm',
                'placeholder': 'Ism kiriting'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm',
                'placeholder': 'Familiya kiriting'
            }),
            'class_assigned': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm',
                'type': 'date'
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm',
                'placeholder': 'Ota-ona telefon raqami'
            }),
        }

    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.student_id:
            class_name = instance.class_assigned.name.replace(" ", "").replace("-", "").upper()
            # Sinf nomidan 2 ta belgi olish (masalan: "7A" -> "7A", "10B" -> "10")
            class_code = class_name[:2] if len(class_name) >= 2 else class_name
            while True:
                random_number = f"{random.randint(100000, 999999)}"  # 6 xonali random raqam
                new_id = f"{class_code}{random_number}"
                if not Student.objects.filter(student_id=new_id).exists():
                    instance.student_id = new_id
                    break
        if commit:
            instance.save()
        return instance

class CriterionForm(forms.ModelForm):
    class Meta:
        model = Criterion
        fields = ['name', 'max_score', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Kriteriya nomini kiriting'
            }),
            'max_score': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '1',
                'max': '100',
                'placeholder': 'Maksimal ball'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'name': 'Kriteriya nomi',
            'max_score': 'Maksimal ball',
            'is_active': 'Faol kriteriya'
        }

    def clean_max_score(self):
        max_score = self.cleaned_data.get('max_score')
        if max_score and max_score <= 0:
            raise ValidationError("Maksimal ball 0 dan katta bo'lishi kerak")
        return max_score

class DynamicEvaluationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        criteria = kwargs.pop('criteria', None)
        super().__init__(*args, **kwargs)
        
        if criteria:
            for criterion in criteria:
                self.fields[f'criterion_{criterion.id}'] = forms.IntegerField(
                    label=criterion.name,
                    min_value=0,
                    max_value=criterion.max_score,
                    widget=forms.NumberInput(attrs={
                        'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                        'placeholder': f'0-{criterion.max_score}',
                        'oninput': 'calculateTotal()'
                    }),
                    help_text=f'Maksimal: {criterion.max_score} ball'
                )
        
        # Comment field
        self.fields['comment'] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': '3',
                'placeholder': 'Qo\'shimcha izoh yozing...'
            }),
            label='Izoh'
        )

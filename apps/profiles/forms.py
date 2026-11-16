from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "bio", "avatar_url"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "How readers will know you"}),
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "A few lines about you and the stories you weave…"}),
            "avatar_url": forms.URLInput(attrs={"placeholder": "https://…"}),
        }
        labels = {"avatar_url": "Avatar image URL"}

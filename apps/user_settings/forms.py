from django import forms

from .models import UserSettings


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = [
            "reader_font", "reader_font_size", "reveal_map",
            "editor_font_size", "default_mode",
            "reduce_motion", "email_notifications",
        ]
        widgets = {
            "reader_font": forms.RadioSelect, "reader_font_size": forms.RadioSelect,
            "editor_font_size": forms.RadioSelect, "default_mode": forms.RadioSelect,
        }

from django.contrib.auth.models import User
from django.db import models


class UserSettings(models.Model):
    class ReaderSize(models.TextChoices):
        SMALL = "small", "Cozy small"
        MEDIUM = "medium", "Comfortable"
        LARGE = "large", "Large"
        XLARGE = "xlarge", "Extra large"

    class ReaderFont(models.TextChoices):
        SERIF = "serif", "Storybook serif"
        SANS = "sans", "Clean sans"
        CLASSIC = "classic", "Classic Georgia"

    class EditorSize(models.TextChoices):
        SMALL = "small", "Small"
        MEDIUM = "medium", "Medium"
        LARGE = "large", "Large"

    class DefaultMode(models.TextChoices):
        EDIT = "edit", "Editor"
        READ = "read", "Reader"

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Reading
    reader_font_size = models.CharField(max_length=10, choices=ReaderSize.choices, default=ReaderSize.MEDIUM)
    reader_font = models.CharField(max_length=10, choices=ReaderFont.choices, default=ReaderFont.SERIF)
    reveal_map = models.BooleanField(default=False)  # authors see the whole map while reading their own story

    # Writing
    editor_font_size = models.CharField(max_length=10, choices=EditorSize.choices, default=EditorSize.MEDIUM)
    default_mode = models.CharField(max_length=10, choices=DefaultMode.choices, default=DefaultMode.EDIT)

    # Comfort & notifications
    reduce_motion = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"Settings for {self.user.username}"

    READER_SIZES = {"small": "1.1rem", "medium": "1.32rem", "large": "1.55rem", "xlarge": "1.8rem"}
    EDITOR_SIZES = {"small": "1.05rem", "medium": "1.25rem", "large": "1.5rem"}
    FONTS = {
        "serif": "'Cormorant Garamond', serif",
        "sans": "'Work Sans', sans-serif",
        "classic": "Georgia, 'Times New Roman', serif",
    }

    def weave_prefs(self):
        """What the Weave screen needs, already resolved to CSS values."""
        return {
            "readerSize": self.READER_SIZES[self.reader_font_size],
            "readerFont": self.FONTS[self.reader_font],
            "editorSize": self.EDITOR_SIZES[self.editor_font_size],
            "defaultMode": self.default_mode,
            "revealMap": self.reveal_map,
            "reduceMotion": self.reduce_motion,
        }

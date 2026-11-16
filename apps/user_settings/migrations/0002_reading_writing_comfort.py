from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("user_settings", "0001_initial")]

    operations = [
        migrations.RemoveField(model_name="usersettings", name="dark_mode"),
        migrations.AddField(model_name="usersettings", name="reader_font_size",
            field=models.CharField(choices=[("small", "Cozy small"), ("medium", "Comfortable"), ("large", "Large"), ("xlarge", "Extra large")], default="medium", max_length=10)),
        migrations.AddField(model_name="usersettings", name="reader_font",
            field=models.CharField(choices=[("serif", "Storybook serif"), ("sans", "Clean sans"), ("classic", "Classic Georgia")], default="serif", max_length=10)),
        migrations.AddField(model_name="usersettings", name="reveal_map", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="usersettings", name="editor_font_size",
            field=models.CharField(choices=[("small", "Small"), ("medium", "Medium"), ("large", "Large")], default="medium", max_length=10)),
        migrations.AddField(model_name="usersettings", name="default_mode",
            field=models.CharField(choices=[("edit", "Editor"), ("read", "Reader")], default="edit", max_length=10)),
        migrations.AddField(model_name="usersettings", name="reduce_motion", field=models.BooleanField(default=False)),
    ]

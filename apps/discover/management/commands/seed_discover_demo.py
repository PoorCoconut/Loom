from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.editor.models import Node, Path
from apps.engagement.models import StoryLike
from apps.stories.models import Story, Tag


class Command(BaseCommand):
    help = "Create a few published stories by other authors (with tags and stars) to try Discover."

    def handle(self, *args, **opts):
        User = get_user_model()
        demo = [
            ("mira", "The Salt Lighthouse", "cozy fantasy",
             "A lighthouse keeper's apprentice discovers the light only burns when someone tells it a secret.",
             ["cozy", "fantasy", "sea"]),
            ("oswin", "Last Train to Marrow", "mystery",
             "The night train stops at a station that is not on any map. Do you step off?",
             ["mystery", "horror", "train"]),
            ("mira", "Tea with the Moth King", "whimsical",
             "An invitation arrives on a moth's wing. Etiquette will decide the fate of the garden.",
             ["cozy", "whimsical", "fantasy"]),
        ]
        for username, title, _, synopsis, tags in demo:
            user, _ = User.objects.get_or_create(username=username)
            if not user.has_usable_password():
                user.set_password("loom-demo-pass"); user.save()
            if Story.objects.filter(title=title).exists():
                continue
            story = Story.objects.create(author=user, title=title, synopsis=synopsis)
            start = Node.objects.create(story=story, node_title="The beginning", text_content=f"{synopsis}\n\nWhat do you do?")
            a = Node.objects.create(story=story, node_title="Say yes", text_content="You say yes, and everything changes.")
            b = Node.objects.create(story=story, node_title="Walk away", text_content="You walk away. The story ends quietly.")
            Path.objects.create(source_node=start, target_node=a, choice_text="Say yes")
            Path.objects.create(source_node=start, target_node=b, choice_text="Walk away")
            story.starting_node = start
            story.save()
            story.tags.set([Tag.objects.get_or_create(name=t)[0] for t in tags])
            story.publish()
            for fan in User.objects.exclude(pk=user.pk)[:3]:
                StoryLike.objects.get_or_create(user=fan, story=story)
        self.stdout.write(self.style.SUCCESS("Demo stories ready. Open /discover/ (demo passwords: loom-demo-pass)."))

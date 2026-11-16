from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.editor.models import GlobalVariable, Node, Path, PathCondition
from apps.stories.models import Story


class Command(BaseCommand):
    help = "Create a small branching demo story (with variables) to try the Weave screen."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Author of the demo story")

    def handle(self, *args, username, **opts):
        User = get_user_model()
        try:
            author = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            raise CommandError(f"No such user: {username}")

        story = Story.objects.create(
            author=author, title="The Lantern Keeper's Hollow",
            synopsis="A cozy little mystery about a village lantern that stopped glowing.",
        )
        lanterns = GlobalVariable.objects.create(story=story, variable_name="embers", data_type="int", default_value="0")
        key = GlobalVariable.objects.create(story=story, variable_name="has_key", data_type="bool", default_value="false")

        def n(title, text):
            return Node.objects.create(story=story, node_title=title, text_content=text)

        door = n("A knock at dusk", "The lantern above the village well has gone dark.\n\nThe mayor presses a tin of tea into your hands and asks you, very politely, to find out why.")
        woods = n("The Hollow Path", "Pine needles muffle every footstep. Something small and bright flickers between the trunks.")
        mill = n("The Quiet Mill", "The old mill wheel turns without water. A brass key hangs from a nail by the door.")
        fox = n("The ember fox", "A fox made of embers blinks at you. It drops a glowing coal at your feet, then waits.")
        cellar = n("Under the mill", "Stairs spiral down into warm dark. A locked iron hatch hums softly.")
        hatch = n("The hum", "The key turns. Inside the hatch sleeps the lantern's heart: a flame the size of a walnut.")
        bright = n("Ending: The village glows", "You carry the flame home. By midnight, every window on the lane is gold.")
        tea = n("Ending: Tea by the well", "You sit under the dark lantern and share your tea with the fox. Some mysteries are better left warm.")
        story.starting_node = door
        story.save()

        def p(a, b, text):
            return Path.objects.create(source_node=a, target_node=b, choice_text=text)

        p(door, woods, "Follow the glimmer into the woods")
        p(door, mill, "Walk to the old mill")
        p(woods, fox, "Kneel and greet the fox")
        p(woods, mill, "Ignore it and head for the mill")
        p(fox, mill, "Follow the fox")
        gather = p(fox, tea, "Pour it a cup of tea")
        to_cellar = p(mill, cellar, "Slip inside")
        take = p(mill, cellar, "Take the key, then slip inside")
        PathCondition.objects.create(path=take, variable=key, modifier_type="set", value="true")
        PathCondition.objects.create(path=fox.outgoing_paths.first(), variable=lanterns, modifier_type="add", value="1")
        open_ = p(cellar, hatch, "Open the hatch")
        PathCondition.objects.create(path=open_, variable=key, requirement_type="eq", value="true")
        p(cellar, tea, "Climb back out and rest")
        p(hatch, bright, "Carry the flame home")
        self.stdout.write(self.style.SUCCESS(f"Created story #{story.pk}. Open /stories/{story.pk}/weave/"))

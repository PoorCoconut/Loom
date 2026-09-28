from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.editor.models import GlobalVariable, Node, Path, PathCondition
from apps.engagement.models import Review, StoryLike
from apps.profiles.models import Profile
from apps.stories.models import Story, StoryCollaborator, Tag, StoryTag
from apps.user_settings.models import UserSettings

from . import engine


class LoomSchemaTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user("ana", "ana@example.com", "pw12345678")
        self.reader = User.objects.create_user("ben", "ben@example.com", "pw12345678")

        self.story = Story.objects.create(author=self.author, title="The Cave")
        self.start = Node.objects.create(story=self.story, node_title="Entrance", text_content="A dark cave.")
        self.treasure = Node.objects.create(story=self.story, node_title="Treasure")
        self.dead_end = Node.objects.create(story=self.story, node_title="Dead end")
        self.story.starting_node = self.start
        self.story.save()
        self.story.publish()

        self.gold = GlobalVariable.objects.create(story=self.story, variable_name="gold", data_type="int", default_value="0")
        self.torch = GlobalVariable.objects.create(story=self.story, variable_name="has_torch", data_type="bool", default_value="false")

    # --- users -------------------------------------------------------
    def test_new_user_gets_profile_and_settings(self):
        self.assertTrue(Profile.objects.filter(user=self.author).exists())
        self.assertTrue(UserSettings.objects.filter(user=self.author).exists())

    def test_soft_deleting_profile_blocks_login(self):
        self.author.profile.delete()
        self.author.refresh_from_db()
        self.assertFalse(self.author.is_active)
        self.assertFalse(Profile.objects.filter(user=self.author).exists())
        self.assertTrue(Profile.all_objects.filter(user=self.author).exists())

    # --- soft delete -------------------------------------------------
    def test_soft_delete_hides_but_keeps_row(self):
        self.dead_end.delete()
        self.assertFalse(Node.objects.filter(pk=self.dead_end.pk).exists())
        self.assertTrue(Node.all_objects.filter(pk=self.dead_end.pk).exists())
        self.dead_end.restore()
        self.assertTrue(Node.objects.filter(pk=self.dead_end.pk).exists())

    def test_queryset_bulk_delete_is_soft(self):
        Node.objects.filter(story=self.story).delete()
        self.assertEqual(Node.objects.count(), 0)
        self.assertEqual(Node.all_objects.count(), 3)

    # --- constraints -------------------------------------------------
    def test_path_must_stay_inside_one_story(self):
        other = Story.objects.create(author=self.author, title="Other")
        foreign = Node.objects.create(story=other, node_title="Elsewhere")
        with self.assertRaises(ValidationError):
            Path(source_node=self.start, target_node=foreign, choice_text="Leave").full_clean()

    def test_starting_node_must_belong_to_story(self):
        other = Story.objects.create(author=self.author, title="Other")
        foreign = Node.objects.create(story=other, node_title="Elsewhere")
        self.story.starting_node = foreign
        with self.assertRaises(ValidationError):
            self.story.full_clean()

    def test_review_rating_range_and_uniqueness(self):
        Review.objects.create(story=self.story, user=self.reader, rating=5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(story=self.story, user=self.reader, rating=3)
        with self.assertRaises(ValidationError):
            Review(story=self.story, user=self.author, rating=6).full_clean()

    def test_deleted_review_allows_a_new_one(self):
        first = Review.objects.create(story=self.story, user=self.reader, rating=2)
        first.delete()
        Review.objects.create(story=self.story, user=self.reader, rating=4)
        self.assertEqual(Review.objects.filter(story=self.story).count(), 1)

    def test_like_tag_collaborator_are_unique(self):
        StoryLike.objects.create(user=self.reader, story=self.story)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StoryLike.objects.create(user=self.reader, story=self.story)
        tag = Tag.objects.create(name="fantasy")
        StoryTag.objects.create(story=self.story, tag=tag)
        self.assertEqual(list(self.story.tags.all()), [tag])
        StoryCollaborator.objects.create(story=self.story, user=self.reader)
        self.assertEqual(list(self.story.collaborators.all()), [self.reader])

    def test_bad_condition_values_are_rejected(self):
        p = Path.objects.create(source_node=self.start, target_node=self.treasure, choice_text="Go")
        with self.assertRaises(ValidationError):
            PathCondition(path=p, variable=self.gold, requirement_type="gte", value="lots").full_clean()
        with self.assertRaises(ValidationError):
            PathCondition(path=p, variable=self.gold, modifier_type="toggle", value="").full_clean()
        with self.assertRaises(ValidationError):
            PathCondition(path=p, variable=self.gold, value="1").full_clean()  # neither type set

    # --- reading engine ---------------------------------------------
    def _build_branches(self):
        grab = Path.objects.create(source_node=self.start, target_node=self.start, choice_text="Grab a torch")
        PathCondition.objects.create(path=grab, variable=self.torch, modifier_type="set", value="true")
        PathCondition.objects.create(path=grab, variable=self.gold, modifier_type="add", value="5")
        go = Path.objects.create(source_node=self.start, target_node=self.treasure, choice_text="Enter (needs torch)")
        PathCondition.objects.create(path=go, variable=self.torch, requirement_type="eq", value="true")
        PathCondition.objects.create(path=go, variable=self.gold, requirement_type="gte", value="5")
        return grab, go

    def test_defaults_and_gated_choices(self):
        grab, go = self._build_branches()
        session = engine.start_session(self.story, self.reader)
        self.assertEqual(session.variable_state, {"gold": 0, "has_torch": False})
        self.assertEqual([p.pk for p in engine.get_choices(session)], [grab.pk])

        with self.assertRaises(engine.StoryError):
            engine.choose(session, go.pk)

        engine.choose(session, grab.pk)
        session.refresh_from_db()
        self.assertEqual(session.variable_state, {"gold": 5, "has_torch": True})
        self.assertEqual({p.pk for p in engine.get_choices(session)}, {grab.pk, go.pk})

        engine.choose(session, go.pk)
        session.refresh_from_db()
        self.assertEqual(session.current_node, self.treasure)
        self.assertTrue(session.is_completed)

        with self.assertRaises(engine.StoryError):
            engine.choose(session, grab.pk)

    def test_restart_resets_state(self):
        grab, _ = self._build_branches()
        session = engine.start_session(self.story)
        engine.choose(session, grab.pk)
        engine.restart(session)
        session.refresh_from_db()
        self.assertEqual(session.variable_state, {"gold": 0, "has_torch": False})
        self.assertEqual(session.current_node, self.start)
        self.assertIsNone(session.user)

    def test_unpublished_story_cannot_be_played(self):
        self.story.unpublish()
        with self.assertRaises(engine.StoryError):
            engine.start_session(self.story)

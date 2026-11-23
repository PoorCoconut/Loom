<div align="center">

# ✦ Loom

### Weave stories that branch.

*A cozy, deep-purple home for writing and reading choose-your-own-path stories.*

![Django](https://img.shields.io/badge/Django-6.x-0c4b33?style=flat-square&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/Supabase-PostgreSQL-3ecf8e?style=flat-square&logo=supabase&logoColor=white)
![JavaScript](https://img.shields.io/badge/Vanilla-JS-f0db4f?style=flat-square&logo=javascript&logoColor=black)
![Theme](https://img.shields.io/badge/theme-twilight%20purple-8b6fe0?style=flat-square)

</div>

---

## What is Loom?

Loom is a **branching story maker**. Authors draw their story as a **horizontal tree of scenes**. Every scene is a node, every choice is a thread leading to another scene. Readers then walk those threads one choice at a time, and the story can end in many different places.

- A scene with **no** connections is an **ending**.
- A scene with **one** connection is a single path forward.
- A scene with **several** connections is a **fork**, where the reader decides what happens next.

Stories can also remember things: gold collected, a key found, trust earned. These **variables** can unlock or hide choices, so two readers can have very different journeys through the same story.

---

## ✨ Features

### 🧵 Weave: the story canvas
The heart of Loom. One screen with two modes, switched by a single toggle.

| | **Editor mode** | **Reader mode** |
|---|---|---|
| Who | The author and invited editors | Everyone (authors can preview too) |
| What | Edit the graph and write scenes | Read the story as a reader would |

**In the editor**
- Pan and zoom a **horizontal tree graph**, with threads labelled by their choice text.
- **Drag a scene** to move it (positions are saved), or press **Tidy up** to auto-arrange the whole tree.
- Drag the gold **＋** out of a scene to branch: drop on empty space for a **new scene**, or on another scene to **link** them. Loops are allowed.
- A big, distraction-free **writing area** with autosave, word count and a *Wide* toggle.
- Edit each scene's choices, retarget them, or cut a thread.
- **Conditions on choices**: require a variable (`gold ≥ 3`) and/or change one (`add 2`, `set to true`, `toggle`).
- Manage **story variables** (number, yes/no, text) with starting values.
- Set the **opening scene**, add an image or audio URL to any scene, and delete scenes.
- **Story details**: title, synopsis, up to 8 **tags**, and a **Publish to Discover** button.

**In the reader**
- A calm, book-style page with serif text, a drop cap and big choice buttons.
- Real choice logic: requirements and variable changes apply as you go. **Back** and **Read again** are built in.
- The graph glows along the path you've taken. Scenes you haven't reached yet stay **fogged** as `?`.
- Authors can reveal the full map, or click any scene to start reading from there.

### 🔭 Discover
Find stories from other weavers.
- Browse every **published** story.
- A **search bar** matches titles, synopses, author names and tags. Every word has to match.
- **Tag chips** with counts act as filters, and you can combine several.
- **Sort** by Newest, Most starred or A–Z.
- **Star** a story you love and **Save** it for later, right from the card.

### 📚 Collections
Your personal bookshelf, with two tabs: **Saved** and **Starred**. Both have their own search and tag filters.

### 🏠 Home
Your library at a glance. Each of your stories has a card showing its tags, star count and scene count, plus search and tag filters, and a quick **New story** box. Open any story in Weave from here.

### 🔎 Insights
A tool for authors, found under **◎ Insights** in the Weave top bar.
- **Outline**: every choice listed with the scene it comes from and the scene it leads to, so you can proof-read the whole story at a glance.
- **Health check**: finds **unreachable scenes** (nothing leads to them), lists your **endings**, and flags scenes with **no text**.
- Each result has a **Show the generated SQL** panel so you can see exactly what ran.

### 👤 Accounts, profile and settings
- Register, log in and out. Soft-deleted or deactivated accounts can't sign in.
- **Profile**: avatar, display name, bio, and stats such as stories, published and scenes written.
- **Settings** to make Loom comfortable for you:
  - Reading typeface and text size, with a live preview.
  - Editor text size, and which mode Weave opens in.
  - Reveal the full map while reading your own stories.
  - Reduce motion.
  - Deactivate account.

### 👋 Guest mode
Not ready to sign up? **Continue as guest** and browse Discover and read published stories. Guests are strictly **read-only**: they can't weave, edit, star or save. Guest accounts are temporary and are cleaned up when they leave.

### 🎨 Made to feel cozy
Deep purple twilight, warm gold thread, stitched dashed borders, a serif storybook typeface and soft glows. The login page has the Loom logo and a calm field of drifting story nodes that gently follows your cursor.

---

## 🧭 Screens at a glance

| Screen | URL | Notes |
|---|---|---|
| Login / Register | `/login/` · `/register/` | Includes **Continue as guest** |
| Home | `/` | Your library, with search and tags |
| Weave | `/?view=weave&story=<id>` | Embedded in Home. Standalone at `/stories/<id>/weave/` |
| Insights | `/stories/<id>/insights/` | Authors and editors only |
| Discover | `/discover/` | Published stories, with search and tags |
| Collections | `/collections/` | Saved and Starred |
| Profile | `/profiles/` | |
| Settings | `/settings/` | |

---

## 🧱 Tech stack

- **Backend:** Python and Django (apps are split by feature under `apps/`)
- **Database:** PostgreSQL on **Supabase** (SQLite locally when no `DATABASE_URL` is set)
- **Frontend:** plain Django templates, CSS and **vanilla JavaScript**. No build step and no framework. The graph is DOM cards plus an SVG layer.
- **Design:** shared CSS in `static/css/shared/`, with per-screen stylesheets beside it

---

## 🗄️ Database

| Area | Tables |
|---|---|
| Users | `auth_user`, `profiles_profile`, `user_settings_usersettings` |
| Stories | `stories_story`, `stories_tag`, `stories_storytag`, `stories_storycollaborator` |
| Story graph | `editor_node` (scenes), `editor_path` (choices), `editor_globalvariable`, `editor_pathcondition` |
| Engagement | `engagement_storylike` (stars), `engagement_storyfavourite` (saves), `engagement_review` |
| Reading | `reading_readingsession` |

Scenes, choices, stories, profiles and conditions use **soft delete** (`is_deleted`), so nothing important disappears for good by accident.

### SQL JOIN and SUBQUERY in the project

Both power the **Insights** screen (`apps/editor/insights.py`):

- **JOIN** (Outline): `editor_path` is `INNER JOIN`ed to `editor_node` **twice**, once for the scene a choice starts from and once for the scene it leads to. In Django: `Path.objects.select_related('source_node', 'target_node')`.
- **SUBQUERY** (Health check): unreachable scenes are scenes whose id is `NOT IN (SELECT target_node_id FROM editor_path ...)`. Endings are the reverse, using `source_node_id`. In Django: `Node.objects.exclude(pk__in=Subquery(...))`.

---

## 🚀 Getting started

**1. Install the requirements**

```bash
pip install django dj-database-url python-dotenv psycopg2-binary
```

**2. Point Loom at your database** (optional). Create a `.env` file next to `manage.py`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
```

Leave it out to use a local SQLite database.

**3. Create the tables**

```bash
python manage.py migrate
python manage.py createsuperuser
```

**4. Run it**

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and register an account (or continue as guest).

### Try it with demo data

```bash
# A small branching story with variables, owned by an existing user
python manage.py seed_demo_story --username YOURNAME

# Published, tagged, starred stories by two other authors (mira and oswin) for Discover
python manage.py seed_discover_demo
```

Then open `/discover/` and look around. The demo authors use the password `loom-demo-pass`.

---

## 🗂️ Project structure

```
apps/
├── core/          soft-delete base model, guest-account helpers
├── login/         login, guest login, logout
├── register/      sign-up
├── home/          Home screen, shared nav bar and logo
├── profiles/      profile screen
├── user_settings/ settings screen
├── stories/       Story, Tag, StoryTag, StoryCollaborator
├── editor/        Weave screen + JSON API, Insights (JOIN and SUBQUERY)
├── discover/      Discover, Collections, search, star and save
├── engagement/    likes, favourites, reviews
└── reading/       reading sessions and the choice engine
static/
├── css/           shared, home, editor, discover, settings, profiles
└── js/            editor/weave.js, discover/engage.js, login/loom-field.js
```

---

## 🔐 Permissions

| | Guest | Member | Collaborator (editor) | Author |
|---|:-:|:-:|:-:|:-:|
| Read published stories | ✅ | ✅ | ✅ | ✅ |
| Star and save | ❌ | ✅ | ✅ | ✅ |
| Edit scenes, choices, tags | ❌ | ❌ | ✅ | ✅ |
| Open Insights | ❌ | ❌ | ✅ | ✅ |
| Publish or unpublish | ❌ | ❌ | ❌ | ✅ |

Unpublished stories are only visible to their author and collaborators, and every editing endpoint checks this on the server.

---

## 🌱 Ideas for later

- Save reading progress to `ReadingSession` so readers can resume where they stopped.
- Reviews and ratings on story cards (the `Review` table already exists).
- Inviting collaborators from inside the app.
- Email notifications (the setting exists; nothing sends yet).
- Cover images on story cards.

---

<div align="center">

*Every story starts with a first thread.* ✦

</div>

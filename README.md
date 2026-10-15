# Sandcastle

Sandcastle is an AI-assisted creative environment for building,
maintaining, and generating from a coherent story canon.

## Structure

- `backend/` — FastAPI, SQLAlchemy, Alembic
- `frontend/` — React, TypeScript, Vite

# Sandcastle V0 — Story-to-Comic

## 1. Product Goal

Sandcastle V0 should prove the core product idea:

> **Sandcastle is an AI-assisted consistency manager for stories and their media.**

The first implementation should allow a user to:

1. Start from a simple story idea.
2. Turn that idea into a lightweight structured world.
3. Create or refine characters and places.
4. Produce a simple four-panel story sequence.
5. Generate a single four-panel image through IG.
6. Preserve enough structured information that the story can continue afterward with generally consistent characters, appearances, outfits, places, and visual style.

V0 is not intended to provide perfect visual continuity, deep canon reasoning, or sophisticated narrative planning.

The goal is to establish the smallest complete loop that demonstrates why Sandcastle is more than a generic AI chat interface.

---

# 2. Core Product Principle

The conversation is not the source of truth.

The structured story world is.

The Sandcastle agent is the conversational interface through which the user reads, creates, and modifies that structured world.

Conceptually:

```text
User
  ↓
Sandcastle Agent
  ↓
Structured Story World
  ↓
Scene / Panel Planning
  ↓
IG
  ↓
Generated Artifact
```

The agent should translate natural-language user intent into operations on story objects rather than simply accumulating conversation text.

---

# 3. V0 User Experience

## 3.1 Create a Story

The entry experience should be extremely simple.

Example:

```text
Tell me your story idea:

[A shy maintenance robot discovers the last living flower
in an abandoned futuristic city.]

[Create Story]
```

The user should not initially need to configure:

- models
- providers
- schemas
- canon structure
- character attributes
- prompt engineering

Sandcastle handles those internally.

---

## 3.2 Initial World Creation

From the user's premise, Sandcastle creates a minimal structured world.

Example:

```text
Story
"The Last Flower"

Characters
- Unit 7

Places
- Abandoned City
- Ruined Greenhouse

Canon
- Plants are believed to be extinct.
- Unit 7 has never encountered a living flower.
- The city has been abandoned for many years.
```

The user can accept, edit, remove, or add information.

---

## 3.3 Character Definition

V0 characters require only enough structure to support storytelling and visual consistency.

Minimum character fields:

```text
Character
- id
- story_id
- name
- description
- appearance
- outfit
- personality
```

Example:

```text
Name:
Unit 7

Description:
A shy maintenance robot left behind after the city was abandoned.

Appearance:
Small worn service robot with a round head,
scratched metal body, and gentle blue eyes.

Outfit:
Yellow utility sash and a small repair pouch.

Personality:
Shy, curious, gentle.
```

Not every field must be exposed directly to the user.

The agent may derive these from conversation and allow natural-language editing.

---

# 4. Place Definition

V0 places should similarly remain lightweight.

Minimum fields:

```text
Place
- id
- story_id
- name
- description
- appearance
- atmosphere
```

Example:

```text
Name:
Abandoned City

Description:
A once-advanced city that has been empty for decades.

Appearance:
Silent futuristic towers, cracked streets,
faded signs, scattered vegetation.

Atmosphere:
Quiet, lonely, mysterious.
```

---

# 5. Canon

V0 needs a simple explicit canon layer.

Minimum structure:

```text
CanonFact
- id
- story_id
- subject_entity_id (optional)
- statement
- status
- source
```

V0 statuses can initially be:

```text
active
superseded
```

Example:

```text
Unit 7 has never seen a living flower.
```

The canon layer exists so facts survive independently of conversation history.

V0 does not require sophisticated timeline-aware canon or branching.

---

# 6. Story Objects

The minimum object model should be intentionally small.

```text
Story
Entity
Character
Place
CanonFact
Scene
ArtifactReference
```

`Character` and `Place` may eventually become specialized entity types, but V0 does not need an elaborate ontology.

Avoid introducing large hierarchies of:

```text
Lore
Faction
Species
Culture
Religion
Technology
TimelineBranch
NarrativeArc
```

until real product usage demonstrates that they require dedicated models.

---

# 7. Sandcastle Agent

The agent is an intelligent interface to the story model.

It should be able to perform operations conceptually equivalent to:

```text
create_story()
create_character()
update_character()

create_place()
update_place()

add_canon_fact()
supersede_canon_fact()

create_scene()
update_scene()

create_comic_plan()
generate_media()
```

The user should interact through natural language rather than through explicit CRUD interfaces.

Example:

```text
User:
Give Unit 7 a yellow utility sash.

Agent operation:
update_character(
  character=unit_7,
  outfit="yellow utility sash and repair pouch"
)
```

The agent then responds conversationally.

---

# 8. Four-Panel Story Planning

A core V0 capability is converting the current story state into a four-panel narrative.

Example:

```text
Panel 1
Unit 7 walks alone through the abandoned city.

Panel 2
Unit 7 notices a faint green glow near a ruined greenhouse.

Panel 3
Unit 7 discovers a flower growing through cracked concrete.

Panel 4
Unit 7 kneels beside it in wonder.
```

The user should be able to edit any panel before generation.

The panel plan should remain a Sandcastle object rather than being stored only inside the final prompt.

---

# 9. Consistency Management

V0 consistency is intentionally limited but explicit.

Sandcastle should maintain consistency across:

## Characters

- general physical appearance
- identifying visual traits
- outfit
- accessories

## Places

- identifying environment features
- overall visual character
- atmosphere

## Story

- established canon facts
- logical progression between panels

## Visual Style

Where a style has already been selected or established, Sandcastle should consistently reuse it.

V0 should be described as:

> **consistency-guided**

rather than guaranteeing exact visual identity.

---

# 10. Reference Artifacts

Sandcastle may associate IG artifact IDs with story objects.

Examples:

```text
Character:
Unit 7

Primary appearance reference:
artifact_123
```

or:

```text
Place:
Abandoned City

Environment reference:
artifact_456
```

Sandcastle owns the semantic meaning of these associations.

IG owns the underlying artifacts and their storage/execution mechanics.

---

# 11. IG Integration

Sandcastle uses IG as its media-generation backend.

Sandcastle should not contain provider-specific generation logic.

The established endpoint is:

```text
POST /v2/media/generations
```

The existing generation contract includes:

```text
media_type

interface_level
- easy
- medium
- hard

strategy

intent.description

output
- quality
- aspect_ratio
- count
- layout

references[]

advanced
```

`advanced` is only available to hard-level users.

Provider and model selection remain IG responsibilities unless explicitly overridden through authorized hard-mode controls.

---

# 12. Four-Panel IG Request

For V0, Sandcastle should generate one image containing four panels.

The agreed layout structure supports:

```text
layout.type = panel_grid

panel_count = 2–4

arrangement:
- 2x2
- 1x4
- 4x1
```

For V0 the default should be:

```text
panel_count = 4
arrangement = 2x2
aspect_ratio = 4:5
```

Sandcastle should construct a semantic generation request containing the resolved four-panel narrative and consistency instructions.

Conceptually:

```json
{
  "media_type": "image",
  "interface_level": "easy",
  "strategy": "balanced",

  "intent": {
    "description": "Create a four-panel comic showing Unit 7 discovering the last living flower. Preserve Unit 7's established appearance and outfit, preserve the visual identity of the abandoned city, and present the panels as a coherent narrative sequence."
  },

  "output": {
    "quality": "standard",
    "aspect_ratio": "4:5",
    "count": 1,
    "layout": {
      "type": "panel_grid",
      "panel_count": 4,
      "arrangement": "2x2"
    }
  },

  "references": []
}
```

The precise prose passed in `intent.description` is compiled by Sandcastle from the structured world and panel plan.

---

# 13. References in the IG Contract

When Sandcastle has reference artifacts, it sends them using the existing IG reference contract:

```json
{
  "artifact_id": "artifact_123",
  "role": "character",
  "strength": "strong"
}
```

Supported reference roles already include:

```text
character
outfit
style
pose
composition
environment
previous_output
```

Reference strength:

```text
loose
normal
strong
```

IG currently supports up to eight references per generation request.

Sandcastle decides which references are semantically appropriate.

IG resolves the artifacts, provider-compatible input representation, and generation execution.

---

# 14. User-Uploaded References

The user may upload an image to use as a reference.

Flow:

```text
Sandcastle
  ↓
IG Artifact Ingestion API
  ↓
artifact_id
  ↓
Sandcastle associates artifact with story object
  ↓
Future generation request includes artifact reference
```

Example:

```text
User uploads image:
"This is what Unit 7 should look like."

Sandcastle stores:

Character Unit 7
→ primary appearance artifact = artifact_123
```

IG remains the authoritative artifact store.

Sandcastle owns the semantic relationship.

---

# 15. Manual / External Generation

Sandcastle should support a future workflow where the user does not use IG to perform the generation.

Example:

```text
Sandcastle creates resolved generation prompt
       ↓
User copies prompt
       ↓
User generates image externally
       ↓
User uploads finished result
       ↓
IG stores artifact
       ↓
Sandcastle marks generation as externally fulfilled
```

This allows users to use systems such as consumer ChatGPT or other external generation tools without requiring API credits.

The exact V0 UI for this may be deferred, but the data model should not block it.

---

# 16. Easy / Medium / Hard Experience Levels

Sandcastle should support three interface complexity levels.

## Easy

Expose only simple controls.

Examples:

```text
Generate
Quality
Aspect ratio
4-panel mode
```

IG selects provider and model.

## Medium

Expose additional semantic preferences.

Examples:

```text
quality
speed
consistency
cost preference
reference strength
```

Provider/model details remain hidden.

## Hard

Allow advanced controls including:

```text
provider override
model override
provider/model parameters
```

IG still validates capabilities and parameters.

Sandcastle should not expose unsupported raw provider options blindly.

---

# 17. V0 UI

A minimal V0 workspace could contain:

```text
┌─────────────────┬─────────────────────────────┐
│ STORY           │                             │
│                 │        AGENT                │
│ Overview        │                             │
│ Characters      │                             │
│ Places          │                             │
│ Canon           │                             │
│ Scenes          │                             │
│ Media           │                             │
│                 │                             │
└─────────────────┴─────────────────────────────┘
```

A richer inspector panel may come later.

The conversation should be prominent but should not become the sole representation of the story.

---

# 18. V0 Generation Workflow

The primary end-to-end flow is:

```text
Enter story idea
      ↓
Agent interprets premise
      ↓
Create Story
      ↓
Create initial Characters / Places / Canon
      ↓
User reviews or modifies world
      ↓
Generate 4-panel plan
      ↓
User reviews/edits panels
      ↓
Sandcastle resolves:
- characters
- appearances
- outfits
- places
- canon
- visual references
- panel descriptions
      ↓
POST /v2/media/generations
      ↓
IG executes
      ↓
Artifact returned
      ↓
Artifact linked to Story / Scene
```

---

# 19. V0 Acceptance Test

V0 is successful when a first-time user can:

1. Enter a one-sentence story premise.
2. Receive a sensible initial structured world.
3. See at least one character and one place represented as persistent objects.
4. Modify character appearance or outfit conversationally.
5. Generate a coherent four-panel story plan.
6. Edit the panel plan.
7. Generate one four-panel image through IG.
8. Receive a result with generally consistent:
   - character appearance
   - outfit
   - place
   - visual style
9. Leave and return without losing the structured story state.

The entire process should feel substantially simpler than manually prompting an image generator four times.

---

# 20. Explicitly Out of Scope for V0

Do not block V0 on:

- perfect character identity
- advanced automatic consistency checking
- timeline reasoning
- alternate universes
- branching canon
- deep relationship graphs
- sophisticated lore ontology
- per-panel image regeneration
- audio generation
- video generation
- multi-chapter narrative management
- automatic downstream impact analysis
- Axtor policy enforcement

These remain future capabilities.

However, V0 architecture should avoid choices that would make them unnecessarily difficult later.

---

# 21. Immediate Follow-On

The natural next milestone after Story-to-Comic is:

## V0.x — Active Consistency Checking

Instead of Sandcastle merely reusing structured state during generation, it begins actively evaluating proposed changes against existing canon.

Example:

```text
User:
Unit 7 has always lived with humans.

Sandcastle:
This conflicts with the established fact that the city
was abandoned before Unit 7 was activated.

Would you like to:
- keep the existing canon
- replace it
- reconcile both facts
```

This is where Sandcastle begins moving from a consistency-guided generation system toward the full consistency-management product.
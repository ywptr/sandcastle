"""Immutable built-in versions and a single capability contract for backend/UI."""
from copy import deepcopy
from fastapi import HTTPException
from app.workflows.schemas import WorkflowConfiguration, ORDER

LEVELS = ["easy", "normal", "difficult", "impossible"]
CAPABILITIES = {
    "easy": ["default_workflow", "next_scene_suggestions", "audience_controls"],
    "normal": ["template_selection", "profile_details", "guidance_options", "review_preferences", "media_options", "structured_world"],
    "difficult": ["step_configuration", "step_ordering", "adaptation_options"],
    "impossible": ["reference_selection"],
}
STEP_DEFINITIONS = [dict(step_id=s, label=s.replace("_", " ").title(), required=s == "scene_creation",
    available=s != "media_execution", dependencies={"storyboard_planning": ["media_adaptation"], "media_execution": ["storyboard_planning"]}.get(s, [])) for s in ORDER]


def capabilities(difficulty):
    result = []
    for level in LEVELS[:LEVELS.index(difficulty) + 1]:
        result.extend(CAPABILITIES[level])
    return result


def difficulties():
    return [dict(id=level, label=level.title(), capabilities=capabilities(level)) for level in LEVELS]


def _template(identity, name, description, minimum="normal", **changes):
    config = WorkflowConfiguration().model_dump()
    for key, values in changes.items():
        config[key].update(values)
    return dict(workflow_template_id=identity, version=1, name=name, description=description,
                difficulty_minimum=minimum, built_in=True, configuration=WorkflowConfiguration.model_validate(config).model_dump())


TEMPLATES = {
    ("standard-story", 1): _template("standard-story", "Standard Story", "Balanced, user-led writing; media planning is optional.", "easy"),
    ("guided-story", 1): _template("guided-story", "Guided Story", "More recent context for concise next-step alternatives.", guidance={"recent_scene_count": 5}),
    ("canon-strict", 1): _template("canon-strict", "Canon Strict", "Review pending new, conflicting and uncertain facts before media planning.", review={"require_before_media": True, "review_new": True}),
    ("webtoon", 1): _template("webtoon", "Webtoon", "Audience-aware adaptation and four-panel planning with existing references.", media={"output_format": "webtoon", "aspect_ratio": "3:4"}),
}


def get_template(identity, version=1):
    template = TEMPLATES.get((identity, version))
    if template is None:
        raise HTTPException(404, "Workflow template version not found")
    return deepcopy(template)


def list_templates():
    return [deepcopy(value) for _, value in sorted(TEMPLATES.items())]


def validate_access(selection):
    template = get_template(selection.workflow_template_id, selection.template_version)
    caps = capabilities(selection.difficulty)
    if LEVELS.index(selection.difficulty) < LEVELS.index(template["difficulty_minimum"]):
        raise HTTPException(422, "This template requires a higher difficulty")
    if "template_selection" not in caps and (selection.workflow_template_id, selection.template_version) != ("standard-story", 1):
        raise HTTPException(422, "Easy uses the curated Standard v1 workflow")
    base = WorkflowConfiguration.model_validate(template["configuration"])
    config = selection.configuration or base
    permissions = {"steps": "step_configuration", "order": "step_ordering", "guidance": "guidance_options",
                   "review": "review_preferences", "media": "media_options", "adaptation": "adaptation_options", "references": "reference_selection"}
    for field, capability in permissions.items():
        if getattr(config, field) != getattr(base, field) and capability not in caps:
            raise HTTPException(422, f"Changing {field} requires capability {capability}")
    return template, config

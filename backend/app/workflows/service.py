from fastapi import HTTPException
from sqlalchemy import select
from app.db.models import StoryWorkflow, Story
from app.stories.service import get_story
from app.workflows.schemas import StoryWorkflowInput, WorkflowConfiguration
from app.workflows.registry import capabilities, get_template, validate_access, STEP_DEFINITIONS


def require_story(db, story_id, user_id):
    story = get_story(db, story_id, user_id)
    if story is None:
        raise HTTPException(404, "Story not found")
    return story


def read_workflow(db, story_id, user_id):
    require_story(db, story_id, user_id)
    row = db.get(StoryWorkflow, story_id)
    if row is None:
        selection = StoryWorkflowInput()
        template, config = validate_access(selection)
    else:
        selection = StoryWorkflowInput(difficulty=row.difficulty, workflow_template_id=row.workflow_template_id,
            template_version=row.template_version, configuration=row.configuration)
        template = get_template(row.workflow_template_id, row.template_version)
        config = selection.configuration
    return dict(story_id=story_id, difficulty=selection.difficulty, workflow_template_id=selection.workflow_template_id,
        template_version=selection.template_version, template_name=template["name"], configuration=config.model_dump(),
        capabilities=capabilities(selection.difficulty), step_definitions=STEP_DEFINITIONS,
        persisted=row is not None)


def save_workflow(db, story_id, user_id, selection):
    require_story(db, story_id, user_id)
    template, config = validate_access(selection)
    db.execute(select(Story.story_id).where(Story.story_id == story_id).with_for_update())
    row = db.get(StoryWorkflow, story_id)
    if row is None:
        row = StoryWorkflow(story_id=story_id)
        db.add(row)
    row.difficulty = selection.difficulty
    row.workflow_template_id = selection.workflow_template_id
    row.template_version = selection.template_version
    row.configuration = config.model_dump()
    db.commit()
    return read_workflow(db, story_id, user_id)


async def perform_step(db, story_id, user_id, step_id, action, *, generator, extractor, planner):
    workflow = read_workflow(db, story_id, user_id)
    config = WorkflowConfiguration.model_validate(workflow["configuration"])
    if not any(step.step_id == step_id and step.enabled for step in config.steps):
        raise HTTPException(409, "This workflow step is disabled or unavailable")
    # This dispatches one explicit action; order is process intent, not a scheduler.
    if step_id == "narrative_guidance":
        from app.guidance.service import suggest_next_scene
        from app.guidance.schemas import SuggestionOptions
        return await suggest_next_scene(db, story_id, user_id, SuggestionOptions(**config.guidance.model_dump()), generator)
    from app.canon import candidate_service as canon
    if step_id == "canon_review":
        return canon.list_candidates(db, story_id, user_id, status="pending", scene_id=action.scene_id)
    if step_id == "continuity_check":
        return canon.continuity_report(db, story_id=story_id, user_id=user_id, scene_id=action.scene_id)
    if step_id == "scene_creation":
        raise HTTPException(409, "Use the existing Scene editor or explicit Generate action; workflow configuration does not create Scenes")
    if not action.scene_id:
        raise HTTPException(422, "This step requires a saved Scene")
    if step_id == "canon_extraction":
        return await canon.extract_candidates(db, story_id=story_id, scene_id=action.scene_id, user_id=user_id, extractor=extractor)
    if config.review.require_before_media:
        report = canon.continuity_report(db, story_id=story_id, user_id=user_id)
        blocked = [kind for kind in ("new", "conflict", "uncertain") if getattr(config.review, "review_" + ("conflicts" if kind == "conflict" else kind)) and report.counts[kind]]
        if blocked:
            raise HTTPException(409, "Review pending Canon before media planning: " + ", ".join(blocked))
    from app.media.adaptation.schemas import AdaptationOptions
    from app.media.adaptation.service import adapt_scene
    options = AdaptationOptions(**config.media.model_dump(), **config.adaptation.model_dump(), **config.references.model_dump())
    adaptation = adapt_scene(db, story_id=story_id, scene_id=action.scene_id, user_id=user_id, options=options, planner=planner)
    if step_id == "media_adaptation":
        return adaptation
    from app.media.storyboard import create_four_panel_storyboard
    return create_four_panel_storyboard(db, story_id=story_id, scene_id=action.scene_id, user_id=user_id, options=options, adaptation=adaptation)

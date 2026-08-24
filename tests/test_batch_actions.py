from tools.applets.batch_actions import (
    execute_automatic_batch,
    normalize_uids,
    plan_automatic_batch,
)


class FakeWorkflow:
    def __init__(self):
        self.writes = []

    def preview_culture_crop_export(self, uid, **options):
        return {
            "status": "PROPOSED",
            "image_uid": uid,
            "crops": [{"column": 1}],
            **options,
        }

    def accept_culture_crop_export(self, uid, proposal):
        self.writes.append(("culture", uid))
        return {"status": "ACCEPTED", "image_uid": uid, "crops": proposal["crops"]}

    def propose_visibility(self, uid, preset):
        return ({"status": "PROPOSED", "image_uid": uid, "preset": preset}, object())

    def accept_visibility(self, uid, proposal):
        self.writes.append(("visibility", uid))
        return ({"status": "ACCEPTED", "image_uid": uid}, None, None)

    def default_annotation_request(self, uid):
        return {"labels": {"date": uid}}

    def propose_annotation(self, uid, request, preset):
        return (
            {
                "status": "PROPOSED",
                "image_uid": uid,
                "annotation_request": request,
                "preset": preset,
                "preview_image": object(),
            },
            object(),
        )

    def accept_annotation(self, uid, proposal):
        self.writes.append(("annotation", uid))
        return ({"status": "ACCEPTED", "image_uid": uid}, None, None)


def test_batch_plans_all_images_before_writes_and_then_executes():
    workflow = FakeWorkflow()
    plan = plan_automatic_batch(
        workflow, "culture", ["A", "B"], options={"crop_width": 50}
    )
    assert workflow.writes == []
    assert plan["output_count"] == 2
    result = execute_automatic_batch(workflow, plan)
    assert result["status"] == "ACCEPTED"
    assert workflow.writes == [("culture", "A"), ("culture", "B")]


def test_annotation_batch_uses_image_defaults_plus_overrides():
    workflow = FakeWorkflow()
    plan = plan_automatic_batch(
        workflow,
        "annotation",
        ["A", "B"],
        options={
            "label_overrides": {"condition": "drug"},
            "preset": {"header_enabled": True},
        },
    )
    assert plan["items"][0]["proposal"]["annotation_request"]["labels"] == {
        "date": "A",
        "condition": "drug",
    }
    assert "preview_image" not in plan["items"][0]["proposal"]
    execute_automatic_batch(workflow, plan)
    assert workflow.writes == [("annotation", "A"), ("annotation", "B")]


def test_visibility_batch_and_uid_validation():
    workflow = FakeWorkflow()
    plan = plan_automatic_batch(
        workflow, "visibility", ["A"], options={"preset": "gamma_boost"}
    )
    assert plan["items"][0]["proposal"]["preset"] == "gamma_boost"
    execute_automatic_batch(workflow, plan)
    assert workflow.writes == [("visibility", "A")]
    try:
        normalize_uids(["A", "A"])
    except ValueError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("duplicate UIDs should fail")

from app.services.pipeline import PipelineService


def test_visual_overlay_mapping_marks_abnormal_tests():
    service = PipelineService()
    overlays = service._build_visual_overlays(
        layout_pages=[
            {
                "page_number": 1,
                "width": 1000,
                "height": 1400,
                "preview_available": True,
                "words": [
                    {"text": "Hemoglobin", "start": 0, "end": 10, "x": 50, "y": 100, "width": 120, "height": 20},
                    {"text": "13.5", "start": 11, "end": 15, "x": 190, "y": 100, "width": 50, "height": 20},
                ],
            }
        ],
        entities=[
            {"text": "Hemoglobin", "label": "TEST_NAME", "start": 0, "end": 10},
        ],
        abnormal_tests=[
            {"test_name": "Hemoglobin"},
        ],
    )

    assert overlays[0]["highlight_count"] == 1
    assert overlays[0]["highlights"][0]["style"] == "abnormal"

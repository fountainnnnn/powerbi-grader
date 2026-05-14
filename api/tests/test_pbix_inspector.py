from src.services.pbix_inspector import pbix_inspector


def named_individual_inspection() -> dict:
    return {
        "file_name": "synthetic-individual.pbix",
        "pages": [
            {
                "display_name": "Ng Yu Hang_Individual",
                "visuals": [
                    {
                        "visual_type": "areaChart",
                        "fields": [
                            "Transactions.Age",
                            "Transactions.Gender",
                            "Sum(Transactions.Amount Spent/Month)",
                        ],
                        "text_content": [
                            {
                                "text": "Sum of Amount Spent/Month by Age and Gender",
                                "source": "config.singleVisual.vcObjects.title",
                            },
                            {"text": "16D", "source": "formatting.fontSize"},
                        ],
                    },
                    {
                        "visual_type": "stackedBarChart",
                        "fields": [
                            "Building.Year",
                            "Sum(Building.Energy Use Intensity (kWh/m2/year))",
                        ],
                        "text_content": [
                            {
                                "text": (
                                    "Sum of Energy Use Intensity "
                                    "(kWh/m2/year) by Year"
                                ),
                                "source": "config.singleVisual.vcObjects.title",
                            }
                        ],
                    },
                ],
            },
            {
                "display_name": "Individual Insights",
                "visuals": [
                    {
                        "visual_type": "textbox",
                        "fields": [],
                        "text_content": [
                            {"text": "[Ng Yu Hang]:"},
                            {"text": "The two visuals I chose are listed below."},
                            {
                                "text": (
                                    "Sum of Amount Spent/Month by Age and Gender "
                                    "(Area Chart) and Sum of Energy Use "
                                    "Intensity (kWh/m2/year) by Year "
                                    "(Stacked Bar Chart)."
                                )
                            },
                        ],
                    }
                ],
            },
        ],
    }


def test_sample_students_and_owned_visuals_from_structural_labels() -> None:
    inspection = {
        "file_name": "synthetic.pbix",
        "pages": [
            {
                "display_name": "Dashboard",
                "visuals": [
                    {
                        "visual_type": "barChart",
                        "fields": [],
                        "text_content": [
                            {"text": "Highest Qualification Distribution (Student A)"}
                        ],
                    },
                    {
                        "visual_type": "lineChart",
                        "fields": [],
                        "text_content": [
                            {"text": "Teacher to Student Ratio - Student A"}
                        ],
                    },
                    {
                        "visual_type": "stackedBarChart",
                        "fields": [],
                        "text_content": [{"text": "Student B - Gender Gap by Age"}],
                    },
                    {
                        "visual_type": "treemap",
                        "fields": [],
                        "text_content": [{"text": "Attainment Mix [Student B]"}],
                    },
                    {
                        "visual_type": "hundredPercentStackedBarChart",
                        "fields": [],
                        "text_content": [{"text": "Target 4.5 Evidence {Student B}"}],
                    },
                ],
            },
            {
                "display_name": "Individual Insights",
                "visuals": [
                    {
                        "visual_type": "textbox",
                        "fields": [],
                        "text_content": [
                            {"text": "[Student A]:"},
                            {"text": "Insight one for Student A is specific enough."},
                            {"text": "Insight two for Student A is specific enough."},
                            {"text": "[Student B]:"},
                            {"text": "Insight one for Student B is specific enough."},
                            {"text": "Insight two for Student B is specific enough."},
                            {"text": "Insight three for Student B is specific enough."},
                        ],
                    }
                ],
            },
        ],
    }

    assert pbix_inspector.extract_student_names(inspection) == ["Student A", "Student B"]

    student_a = pbix_inspector.extract_student_evidence(inspection, "Student A")
    assert student_a["visual_count"] == 2
    assert len(student_a["insights"]) == 2
    student_a_titles = [
        title
        for visual in student_a["visuals"]
        for title in pbix_inspector._visual_title_texts(visual)
    ]
    assert any("Highest Qualification Distribution" in title for title in student_a_titles)
    assert any("Teacher to Student Ratio" in title for title in student_a_titles)

    student_b = pbix_inspector.extract_student_evidence(inspection, "Student B")
    assert student_b["visual_count"] == 3
    assert len(student_b["insights"]) == 3
    assert all(
        "Student B" in " ".join(pbix_inspector._visual_title_texts(visual))
        for visual in student_b["visuals"]
    )


def test_student_named_individual_page_extracts_declared_visuals_and_insights() -> None:
    inspection = named_individual_inspection()

    assert pbix_inspector.extract_student_names(inspection) == ["Ng Yu Hang"]

    evidence = pbix_inspector.extract_student_evidence(inspection, "Ng Yu Hang")
    declared_titles = [item["title"] for item in evidence["declared_visuals"]]

    assert evidence["visual_count"] == 2
    assert "Sum of Amount Spent/Month by Age and Gender" in declared_titles
    assert "Sum of Energy Use Intensity (kWh/m2/year) by Year" in declared_titles
    assert any("two visuals I chose" in insight for insight in evidence["insights"])
    assert all(
        "16D" not in pbix_inspector._visual_title_texts(visual)
        for visual in evidence["visuals"]
    )


def test_prompt_evidence_names_declared_visuals_as_attribution_signal() -> None:
    inspection = named_individual_inspection()

    prompt = pbix_inspector.format_student_evidence_for_prompt(inspection, "Ng Yu Hang")

    assert "Declared chosen visuals from this student's own insight text:" in prompt
    assert "Sum of Amount Spent/Month by Age and Gender (Area Chart)" in prompt
    assert "Sum of Energy Use Intensity (kWh/m2/year) by Year (Stacked Bar Chart)" in prompt
    assert "Grade ONLY the visuals and insights listed above for Ng Yu Hang" in prompt


def test_powerbi_stacked_and_treemap_visuals_are_gradeable_for_student_2() -> None:
    inspection = {
        "file_name": "student-numbered.pbix",
        "pages": [
            {
                "display_name": "Dashboard",
                "visuals": [
                    {
                        "visual_type": "lineChart",
                        "fields": [],
                        "text_content": [
                            {
                                "text": (
                                    "Education Attainment by Age Group "
                                    "(Student 1)"
                                )
                            }
                        ],
                    },
                    {
                        "visual_type": "stackedColumnChart",
                        "fields": [],
                        "text_content": [
                            {"text": "Qualification Trends - Student 1"}
                        ],
                    },
                    {
                        "visual_type": "hundredPercentStackedBarChart",
                        "fields": [],
                        "text_content": [
                            {
                                "text": (
                                    "Gender Parity in Higher Education by Age "
                                    "(Student 2)"
                                )
                            }
                        ],
                    },
                    {
                        "visual_type": "treemap",
                        "fields": [],
                        "text_content": [
                            {
                                "text": (
                                    "Highest Qualification and Gender "
                                    "(Student 2)"
                                )
                            }
                        ],
                    },
                ],
            },
            {
                "display_name": "Individual Insights",
                "visuals": [
                    {
                        "visual_type": "textbox",
                        "fields": [],
                        "text_content": [
                            {"text": "[Student 1]:"},
                            {"text": "Student 1 insight has enough detail."},
                            {"text": "[Student 2]:"},
                            {"text": "Student 2 insight has enough detail."},
                        ],
                    }
                ],
            },
        ],
    }

    assert pbix_inspector.extract_student_names(inspection) == ["Student 1", "Student 2"]

    student_1 = pbix_inspector.extract_student_evidence(inspection, "Student 1")
    student_2 = pbix_inspector.extract_student_evidence(inspection, "Student 2")

    student_1_titles = [
        title
        for visual in student_1["visuals"]
        for title in pbix_inspector._visual_title_texts(visual)
    ]
    student_2_titles = [
        title
        for visual in student_2["visuals"]
        for title in pbix_inspector._visual_title_texts(visual)
    ]

    assert student_1["visual_count"] == 2
    assert student_2["visual_count"] == 2
    assert any(
        "Education Attainment by Age Group (Student 1)" in title
        for title in student_1_titles
    )
    assert any(
        "Gender Parity in Higher Education by Age (Student 2)" in title
        for title in student_2_titles
    )
    assert any(
        "Highest Qualification and Gender (Student 2)" in title
        for title in student_2_titles
    )


def test_curly_braces_are_supported_for_student_attribution() -> None:
    inspection = {
        "file_name": "synthetic.pbix",
        "pages": [
            {
                "display_name": "Dashboard",
                "visuals": [
                    {
                        "visual_type": "lineChart",
                        "fields": ["Table.Year", "Sum(Table.Value)"],
                        "text_content": [
                            {
                                "text": "Trend in results {Student 2}",
                                "source": "config.singleVisual.vcObjects.title",
                            }
                        ],
                    }
                ],
            },
            {
                "display_name": "Individual Insights",
                "visuals": [
                    {
                        "visual_type": "textbox",
                        "fields": [],
                        "text_content": [
                            {
                                "text": (
                                    "{Student 2}: "
                                    "The line chart shows a clear upward trend over time."
                                ),
                                "source": "config.singleVisual.objects.general",
                            }
                        ],
                    }
                ],
            },
        ],
    }

    assert pbix_inspector.extract_student_names(inspection) == ["Student 2"]

    evidence = pbix_inspector.extract_student_evidence(inspection, "Student 2")

    assert evidence["visual_count"] == 1
    assert evidence["insights"] == ["The line chart shows a clear upward trend over time."]

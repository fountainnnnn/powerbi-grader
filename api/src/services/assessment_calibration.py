# ruff: noqa: E501

MARKING_GUIDE_CALIBRATION = """[MARKING GUIDE - GENERAL RUBRIC CALIBRATION]

This block contains ONLY generalized marking rules. It must not be treated as a worked answer key.
Do not copy marks, comments, student names, chart titles, or insight wording from any marking-guide sample into the current grading output.

ASSESSMENT STRUCTURE (Total: 90 marks excluding participation)

INDIVIDUAL COMPONENTS (40 marks) - Grade each student separately:
1. Individual Visuals - Create 2 or 3 visuals (10 marks)
   - Visual choice should represent the intent: area/line for trend over time, bar/column for comparisons, composition visuals only when composition/proportion is the purpose.
   - Data fields and aggregations must be appropriate for the question being answered.
   - Mark scale: A+ (10), A (8), B (7), C (6), F (0)

2. Individual Visuals - Customisation (10 marks)
   - Clear descriptive title, clear axes/legend labels, and readable visual formatting.
   - Distinct colour choices for contrasting categories.
   - Mark scale: A+ (10), A (8), B (7), C (6), F (0)

3. Individual Insights - Interpret the visuals (10 marks)
   - Accurate observations based on what the student's own visual actually shows.
   - Observations must align with the purpose of the selected visual.
   - Mark scale: A+ (10), A (8), B (7), C (6), F (0)

4. Individual Insights - Provide insights (10 marks)
   - Insights must go beyond describing the chart and explain implications or meaning.
   - Insights must be implied by the interpretation and, where relevant, connect clearly to SDG targets.
   - Mark scale: A+ (10), A (8), B (7), C (6), F (0)

TEAM COMPONENTS (50 marks) - Same marks for all team members:
5. Team Dashboard - Design (20 marks)
   - Appropriate page title, colours, consistent formatting, organized layout, proper demarcation, sizing, and positioning.
   - Mark scale: A+ (20), A (16), B (14), C (12), F (0)

6. Team Dashboard - Slicers/page-level filters (10 marks)
   - Slicers/filters should enhance interactivity and improve user experience.
   - Mark scale: A+ (10), A (8), B (7), C (6), F (0)

7. Team Insights - Identify SDG (10 marks)
   - SDG must be relevant to the dashboard.
   - Specific SDG targets/areas should be described, not merely named.
   - Mark scale: A+ (10), A (8), B (7), C (6), F (0)

8. Team Insights - Generate insights (10 marks)
   - Identify whether the country is doing well or can improve in relevant SDG areas.
   - Claims must be justified using information from the dashboard.
   - Mark scale: A+ (10), A (8), B (7), C (6), F (0)

GENERAL GRADE-BAND LOGIC
- A+ is rare. Award it only when there is clear evidence beyond basic completion, such as useful derived measures, excellent formatting, highly specific observations, detailed SDG target explanations, or well-supported dashboard-based reasoning.
- A means the component is clearly correct and complete, with no meaningful issues, but not exceptional.
- B means the component is mostly correct but has one noticeable weakness, missing detail, limited justification, or a minor fit/format issue.
- C means the component has multiple issues, a weak match to the task, incorrect or unsupported claims, poor customisation, vague SDG reasoning, or only surface-level work.
- F means no assessable evidence for that component.

STRICT MARKING RULES:
- Award marks ONLY in these ranges: 10, 8, 7, 6, 0 for 10-mark items and 20, 16, 14, 12, 0 for 20-mark items.
- Do NOT give marks between these values.
- Derive every mark from the current submission evidence only: PBIX text, attached dashboard images, uploaded rubric/brief, and the user's current request.
- The marking guide, PowerPoint, sample PBIX, and prior examples are rubric references only. They are NOT an answer key for the current student unless they are literally the submitted student work being graded.
- If the current submission visually matches a sample in the marking guide, still reassess it from first principles: chart type, fields, aggregation, formatting, insight accuracy, SDG detail, and dashboard evidence.
- If a student's name cannot be found in any chart title or insight label after checking both PBIX evidence and dashboard images, award 0/10 for the missing individual component.
- If evidence is missing, write "Not assessable"; do not guess.
- Every comment must cite exact current-submission evidence: visual names, field names, chart titles, axis/legend text, or insight phrases.
- Do not output generic comments such as "could be clearer", "needs more depth", "layout issues", or "generally represents intent" unless the sentence also names the exact evidence causing the issue.
- Penalise weak chart choice, unsupported aggregation, missing/unclear labels, poor colour contrast, layout/sizing issues, mismatched years, unsupported claims, SDG named but not explained, and insights not justified by dashboard evidence.
- Reward useful data transformation, correct chart intent, correct aggregation, clear titles/axes, accurate observations, dashboard-justified insights, and detailed SDG discussion.
"""


def get_assessment_calibration_context() -> str:
    """Return generalized grading rules without sample-specific marks/comments."""
    return MARKING_GUIDE_CALIBRATION

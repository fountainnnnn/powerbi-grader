# ruff: noqa: E501, I001
import base64
import glob
import os
import re

import httpx
from PIL import Image

from src.config import settings
from src.utils.errors import AIServiceError

class OpenAIClient:
    def __init__(self):
        self.model = settings.openai_model
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        self.api_key = settings.openai_api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def grade_dashboard(
        self,
        query: str,
        context: str = "",
        image_path: str | None = None,
        rubric_path: str | None = None,
        evidence_summary: str = "",
        student_name: str | None = None,
        all_students: list[str] | None = None,
    ) -> dict:
        """
        Analyze dashboard and/or rubric using OpenAI Vision via HTTP.

        Args:
            query: User's question
            context: Previous chat context (optional)
            image_path: Path to the dashboard image or PDF (optional)
            rubric_path: Path to the rubric image or PDF (optional)

        Returns:
            Raw response from OpenAI API as dict

        Raises:
            AIServiceError: If OpenAI API request fails
        """
        try:
            grading_subjects = all_students if all_students else ([student_name] if student_name else None)
            is_multi = grading_subjects and len(grading_subjects) > 1

            SHARED_CRITERIA = """MARKING STRICTNESS DIRECTIVE
You are a STRICT marker. Do NOT default to A (8) — that grade must be EARNED with clear evidence of quality.
Start each component at B (7) and adjust UP only if there is specific evidence of quality, or DOWN if there are issues.
If unsure between two grades, choose the LOWER one. Actively look for problems in each component.
A+ (10) is RARE — it requires exceptional effort clearly beyond the basics (e.g., extra data transformation, detailed SDG target descriptions with explanations).

MARK SCALE — use ONLY these values:
- 10-mark rows: 10, 8, 7, 6, or 0
- 20-mark row (Team Dashboard Design): 20, 16, 14, 12, or 0

MARKING CRITERIA — STEP-BY-STEP THINKING PROCESS (you MUST follow these steps for each component)

Individual Visuals - Create (10):
  STEP 1 — CHART TYPE vs INTENT: For each visual, ask: does the chart type match the analytical intent?
    Area chart for showing TREND over time = correct. Column/bar chart for COMPARISON across categories = correct. Line chart for TREND = correct.
    Penalty: chart type does not match intent (e.g. column chart used to show trend, especially with a Legend field that makes individual trends hard to see — individual category trends become hard to track across clustered columns).
  STEP 2 — AGGREGATION: Look at the Y-axis label, measure name, or field reference for each visual. Check if the aggregation (Sum, Average, Count) is appropriate.
    Average is ONLY appropriate when averaging makes analytical sense for the specific dimension being aggregated over. ASK: "What is being averaged over?" If the answer is multiple unrelated categories (e.g. averaging across institution, qualification, course, field of study), this is INAPPROPRIATE unless the student provides clear justification. Each inappropriate aggregation counts as a separate issue.
    Example of APPROPRIATE average: "Average student-to-teacher ratio" (averaging a ratio makes sense).
    Example of INAPPROPRIATE average: "Average number of graduates" averaged across institution/qualification/course without justification.
  STEP 3 — EXTRA EFFORT: Did the student create any additional data transformation beyond what was given? (e.g. calculated a new ratio from raw columns, created a derived measure). This is what distinguishes A+ from A.
  GRADE:
    A+(10): correct chart types + correct aggregations + additional useful data transformation (e.g. calculated a derived ratio from raw data). A+ is earned, not given.
    A(8): correct chart types and aggregations but no extra transformation effort.
    B(7): one minor issue with chart choice or aggregation.
    C(6): wrong chart type for intent, OR multiple inappropriate aggregations (2+), OR both. Multiple issues = C.
    F(0): no visuals created.

Individual Visuals - Customise (10):
  CHECK TWO THINGS and count issues:
  1. TITLES AND LABELS: A chart title should DESCRIBE the chart (e.g. "Number of Graduates by Year"). If the title contains a finding, observation, or conclusion (e.g. "Average Years of Schooling GREW between 2018-2023" — note the word "Grew" is an observation), that is an issue. Observations should be in the insights, not the title. Also check that axes are clearly labelled.
  2. COLOUR CHOICES: Look at the dashboard images. For charts with a LEGEND showing contrasting categories (e.g. Male vs Female, different institutions), the colours MUST be visually distinct. If two different categories use similar shades (e.g. two shades of blue for Male vs Female), that is an issue.
  Count total issues found:
    A+(10): exceptional titles, labels, and colour choices enhancing readability.
    A(8): clear titles and axes, acceptable colours. ZERO issues found.
    B(7): one minor issue.
    C(6): TWO or more issues (e.g. observations in title + similar-shade colours for contrasting categories).
    F(0): no customisation.

Individual Insights - Interpret (10):
  This is about OBSERVATIONS — factual statements about what the visual SHOWS.
  CHECK:
  1. Are observations ACCURATE based on the actual data in the visual?
  2. Are observations ALIGNED with the visual's purpose? (If the chart shows a trend, does interpretation discuss the trend? If comparison, does it discuss the comparison?)
  3. Is the claimed pattern actually VISIBLE in the chosen chart type? A trend claimed from a column chart with a legend may not be obviously visible.
    A+(10): accurate observations, perfectly aligned with purpose, additional depth.
    A(8): observations are accurate AND aligned with the purpose of each visual.
    B(7): observations are generally correct, but one observation is weakened (e.g. trend claimed but not easily visible in the chosen chart type).
    C(6): observations are inaccurate or misaligned with visual purpose.
    F(0): no interpretation.

Individual Insights - Provide (10):
  This is about INSIGHTS — deeper meaning and implications derived from the interpretations, often connecting to SDG.
  CHECK CAREFULLY — this component has the widest grade range:
  1. DETAIL: Read the student's insight text. Count the sentences. Is it detailed with specific reasoning, or is it brief/surface-level? Brief insights (a few short sentences without depth) = C. Evaluate each visual's insights separately.
  2. ACCURACY: are insights actually implied by the interpretations, or are they generic claims?
  3. SDG CONNECTION — read the exact SDG-related text carefully: Does the student name SPECIFIC SDG targets (e.g. "SDG 4.c" or "Target 4.1")? Do they DESCRIBE what those targets mean? Or do they make vague claims like "this is very important to ensure..." without specifying what "this" refers to?
  A vague SDG claim example: "this is very important to ensure residents are well-educated, therefore supporting SDG 4.c" — the word "this" is unclear, and the target is named but not described.
  A detailed SDG claim example: "SDG Target 4.c aims to increase the supply of qualified teachers. The data shows that Singapore's student-teacher ratio has improved, indicating progress toward this target."
    A+(10): detailed, accurate insights with SPECIFIC SDG target numbers AND descriptions of what those targets mean. Must show extra effort on elaboration.
    A(8): accurate insights with reasonable detail and clear SDG connection.
    B(7): insights present but lacking depth or SDG connection is surface-level.
    C(6): insights are BRIEF (just a few short sentences per visual), OR contain VAGUE/UNCLEAR claims (e.g. unclear what "this" refers to in an SDG statement, or SDG mentioned without explaining relevance). Brevity + vagueness = C.
    F(0): no insights.

Team Dashboard - Design (20):
  CHECK each of these in the dashboard images:
  1. Appropriate page TITLE for the dashboard theme.
  2. Consistent COLOURS and FORMATTING across all visuals (same font family, style).
  3. Organised LAYOUT with proper demarcation between sections.
  4. SIZING: are visuals sized proportionally? If one chart is squeezed small while another takes excessive space, or if visuals are not sized appropriately for their content, that is an issue.
  5. POSITIONING: are visuals well-placed with proper spacing? Awkward gaps or overlaps = issue.
  6. YEAR CONSISTENCY: look at the X-axes across multiple visuals. Do the years/time periods match where they should be comparable? If one chart shows 2000-2023 and a related chart shows 2018-2023, that inconsistency is a penalty.
  ANY sizing/layout issue or year inconsistency drops to B(14) or below:
    A+(20): excellent in ALL areas — no issues found.
    A(16): good overall with only very minor issues.
    B(14): noticeable sizing/layout issues OR year mismatches across visuals.
    C(12): disorganised layout, poor sizing, inconsistent formatting.
    F(0): no design effort.

Team Dashboard - Slicers (10):
  CHECK: do slicers/page-level filters enhance interactivity and improve user experience?
    A+(10): exceptional slicers that significantly enhance data exploration.
    A(8): slicers are useful and functional but not exceptional.
    B(7): slicers present but limited usefulness.
    C(6): basic slicers with minimal interactivity.
    F(0): no slicers.

Team Insights - Identify SDG (10):
  CHECK:
  1. Is the SDG RELEVANT to the dashboard topic?
  2. Are specific SDG TARGETS named (e.g. "SDG 4.c", "Target 4.1")?
  3. Are those targets DESCRIBED in detail — does the student explain what each target means? Just naming targets without description is NOT enough for A.
  Distinguish clearly: "SDG 4.c" mentioned in passing = B. "SDG Target 4.c aims to substantially increase the supply of qualified teachers in developing countries" = A or A+.
    A+(10): relevant SDG with DETAILED DESCRIPTION explaining what each target means and why it connects to the dashboard.
    A(8): relevant SDG with good description of targets.
    B(7): relevant SDG identified, specific targets NAMED but NOT DESCRIBED in detail — just listed.
    C(6): SDG mentioned but vague, no specific targets.
    F(0): no SDG.

Team Insights - Generate (10):
  CHECK — this is about EVIDENCE-BASED claims:
  1. Does the team identify if the country is doing WELL or can IMPROVE?
  2. For EACH claim, ask: is this justified with SPECIFIC data FROM THE DASHBOARD? "Justified" means citing specific numbers, trends, percentages, or comparisons that are visible in the dashboard visuals. Generic opinions without data = NOT justified.
  Example of justified: "Singapore's average years of schooling increased from 10.2 to 11.5 years (2018-2023), showing progress in SDG 4."
  Example of NOT justified: "Singapore can improve its education system" (no specific data cited).
    A+(10): detailed country performance analysis, every claim justified with specific dashboard data/numbers.
    A(8): good analysis with reasonable dashboard justification for most claims.
    B(7): identifies areas but justification is weak/generic — improvement claims stated without citing specific dashboard evidence.
    C(6): generic statements about country without any dashboard evidence.
    F(0): no insights.

IDENTIFYING STUDENT CHARTS FROM IMAGES
The attached dashboard images are the primary source for visual assessment. Student names appear in chart titles in many formats — look carefully at every chart title in the images:
- Before a dash: "Name - Chart Title" or "Name – Chart Title"
- After a dash: "Chart Title - Name" or "Chart Title – Name"
- In parentheses: "Chart Title (Name)" or "(Name) Chart Title"
- In square brackets: "[Name] Chart Title"
- In curly braces: "Chart Title {Name}" or "{Name} Chart Title"
- Or any combination of the above
The PBIX evidence section lists extracted text but may be incomplete. If the PBIX lists 0 visuals for a student but the dashboard images clearly show charts with that student's name in the title, use the image evidence and grade those charts. Do not award 0 simply because text extraction found nothing — use your vision.
If the PBIX evidence contains "Declared chosen visuals from this student's own insight text", treat those declared visual titles as the student's own selected individual visuals. Match them to extracted chart titles/fields/chart types before grading, and do not accidentally grade unrelated cards, slicers, decorative text, or another student's charts.

INDIVIDUAL INSIGHTS PAGE
The Individual Insights page is one of the attached images. Even if PBIX text extraction found 0 insight paragraphs for a student, look at that page image for paragraphs preceded by their name label — formats like "[Name]:", "(Name):", or "Name:" at the start of a paragraph. Grade the insights you find in the image. Only mark "Not assessable" if the student's name genuinely does not appear on that page in any form.

STRICT RULES
- Every comment must cite the exact chart title, field, aggregation, or verbatim insight phrase from the evidence. No generic phrases.
- If a component has no attributable evidence after checking BOTH the PBIX text AND the dashboard images, write "Not assessable".
- Do not invent visuals, fields, or text not present in the evidence."""

            if is_multi:
                students_list = ", ".join(grading_subjects)
                # Build per-student INDIVIDUAL-only blocks
                per_student_templates = []
                for name in grading_subjects:
                    per_student_templates.append(f"""## Student: {name} — Individual Components (40 marks)
| Component | Marks | Comments |
|---|---:|---|
| Individual Visuals - Create | MARK/10 | Reason citing exact chart title and fields |
| Individual Visuals - Customise | MARK/10 | Reason citing exact title or colour choice |
| Individual Insights - Interpret | MARK/10 | Reason citing exact observation text from [{name}] section |
| Individual Insights - Provide | MARK/10 | Reason citing exact insight phrase from [{name}] section |

**Individual Total for {name}: MARK/40**

### Explanation for {name}'s Individual Marks
- One bullet per penalty or credit, tied to exact evidence phrase""")

                totals_rows = "\n".join(
                    f"| {name} | MARK | MARK | MARK |" for name in grading_subjects
                )
                output_template = "\n\n---\n\n".join(per_student_templates) + """

---

## Team Components (50 marks — same mark for all students)
| Component | Marks | Comments |
|---|---:|---|
| Team Dashboard - Design | MARK/20 | Reason citing visual layout evidence |
| Team Dashboard - Slicers | MARK/10 | Reason citing slicer behaviour |
| Team Insights - Identify SDG | MARK/10 | Reason citing exact SDG text |
| Team Insights - Generate | MARK/10 | Reason citing dashboard evidence used |

**Team Total: MARK/50**

### Team Explanation
- One bullet per penalty or credit, tied to exact evidence phrase

---

## Final Totals
| Student | Individual /40 | Team /50 | Overall /90 |
|---|---:|---:|---:|
""" + totals_rows + """

## Evidence Received
- Rubric images: yes/no
- Dashboard images: yes/no and page count
- PBIX insights: yes/no; note any missing components"""

                system_prompt = f"""You are the Power BI dashboard assessment marker. Grade ALL of the following students from this submission: {students_list}.

Produce a completed marking table with real numerical marks for EACH student — never output placeholder text or refuse to grade.

INDIVIDUAL COMPONENTS (40 marks per student — each student's OWN work only):
- A student's visuals are identified by their name appearing in the chart title in ANY of these formats:
  * Before a dash: "Name - Chart Title"
  * After a dash: "Chart Title - Name"
  * In parentheses: "Chart Title (Name)" or "(Name) Chart Title"
  * In square brackets: "[Name] Chart Title"
  * In curly braces: "{{Name}} Chart Title" or "Chart Title {{Name}}"
  * A combination or variation of the above
- A student's insights are paragraphs labelled with their name in ANY of these formats on the Individual Insights page: "[Name]:", "(Name):", "{{Name}}:", "Name:", or similar.
- Do NOT credit or penalise a student for another student's visuals or insights.

TEAM COMPONENTS (50 marks — identical score for every student in the team):
- Team Dashboard design and slicers: assess from the attached dashboard images.
- Team Insights: assess from the Team Insights & Reflection page in the PBIX context.

{SHARED_CRITERIA}

Now produce the grading output for every student listed above. Use this exact format — one complete block per student:

{output_template}"""

            else:
                name = (grading_subjects[0] if grading_subjects else None)
                student_identifier = f"for {name}" if name else "for this student"
                display_name = name or "Unknown"

                system_prompt = f"""You are the Power BI dashboard assessment marker. Your task is to grade {student_identifier} right now by examining the attached rubric images, dashboard images, and PBIX technical insights in the context.

Produce a completed marking table with real numerical marks — never output placeholder text or refuse to grade.

WHAT TO GRADE
Individual components (40 marks) — assess THIS STUDENT'S OWN work only:
- Their visuals are identified by their name appearing in the chart title in ANY of these formats:
  * Before a dash: "{display_name} - Chart Title"
  * After a dash: "Chart Title - {display_name}"
  * In parentheses: "Chart Title ({display_name})" or "({display_name}) Chart Title"
  * In square brackets: "[{display_name}] Chart Title"
  * In curly braces: "{{{display_name}}} Chart Title" or "Chart Title {{{display_name}}}"
  * A combination or variation of the above
- Their insights are paragraphs labelled with their name in ANY format on the Individual Insights page: "[{display_name}]:", "({display_name}):", "{{{display_name}}}:", "{display_name}:", or similar.
- Do NOT credit or penalise this student for another student's visuals or text.

Team components (50 marks) — same mark for all team members:
- Team Dashboard design and slicers: assess from the attached dashboard images.
- Team Insights: assess from the Team Insights & Reflection page text in the PBIX context.

{SHARED_CRITERIA}

Now produce the grading output for {student_identifier} in this exact format:

## Student: {display_name} — Individual Components (40 marks)
| Component | Marks | Comments |
|---|---:|---|
| Individual Visuals - Create | MARK/10 | Reason citing exact chart title and fields |
| Individual Visuals - Customise | MARK/10 | Reason citing exact title or colour choice |
| Individual Insights - Interpret | MARK/10 | Reason citing exact observation text from [{display_name}] section |
| Individual Insights - Provide | MARK/10 | Reason citing exact insight phrase from [{display_name}] section |

**Individual Total: MARK/40**

### Explanation for Individual Marks
- One bullet per penalty or credit, tied to exact evidence phrase

---

## Team Components (50 marks)
| Component | Marks | Comments |
|---|---:|---|
| Team Dashboard - Design | MARK/20 | Reason citing visual layout evidence |
| Team Dashboard - Slicers | MARK/10 | Reason citing slicer behaviour |
| Team Insights - Identify SDG | MARK/10 | Reason citing exact SDG text |
| Team Insights - Generate | MARK/10 | Reason citing dashboard evidence used |

**Team Total: MARK/50**

### Team Explanation
- One bullet per penalty or credit, tied to exact evidence phrase

---

## Totals
- Individual: MARK/40
- Team: MARK/50
- **Overall: MARK/90**

## Evidence Received
- Rubric images: yes/no
- Dashboard images: yes/no and page count
- PBIX insights: yes/no; note any missing components"""

            # Build user message — evidence FIRST so the AI reads it before the long calibration block
            user_message = f"""{"STUDENT SUBMISSION EVIDENCE:\n" + evidence_summary if evidence_summary else ""}

{"GENERAL RUBRIC RULES (do NOT copy sample wording or infer marks from prior examples):\n" + context if context else ""}

{query}"""

            # Build content array with images
            content = [{"type": "text", "text": user_message}]

            # Add rubric images first (as grading criteria)
            if rubric_path:
                if rubric_path.endswith(".pdf") or rubric_path.endswith(".docx") or rubric_path.endswith(".doc") or rubric_path.endswith(".pbix"):
                    # Extract file_id from path (filename without extension)
                    filename = os.path.basename(rubric_path)
                    file_id = os.path.splitext(filename)[0]
                    upload_dir = os.path.dirname(rubric_path)
                    base_path = os.path.join(upload_dir, file_id)

                    page_images = sorted(
                        glob.glob(f"{base_path}_page_*.png"),
                        key=lambda p: int(re.search(r'_page_(\d+)', p).group(1))
                    )
                    if not page_images:
                        raise AIServiceError(f"No converted pages found for document at {rubric_path}. Make sure it was uploaded as PDF, DOCX, or image.")
                    for page_image_path in page_images:
                        if not os.path.exists(page_image_path):
                            raise AIServiceError(f"Rubric page file not found: {page_image_path}")
                        try:
                            img = Image.open(page_image_path)
                            img_format = img.format.lower() if img.format else "png"
                        except Exception as e:
                            raise AIServiceError(f"Invalid rubric page image: {str(e)}")
                        mime_type = f"image/{img_format}"
                        with open(page_image_path, "rb") as f:
                            image_data = base64.b64encode(f.read()).decode("utf-8")
                        content.append({
                            "type": "text",
                            "text": "[RUBRIC - Grading Criteria]"
                        })
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                                "detail": "high",
                            },
                        })
                else:
                    if not os.path.exists(rubric_path):
                        raise AIServiceError(f"Rubric file not found: {rubric_path}")
                    # Detect actual image format
                    try:
                        img = Image.open(rubric_path)
                        img_format = img.format.lower() if img.format else "png"
                    except Exception as e:
                        raise AIServiceError(f"Invalid rubric image: {str(e)}")

                    mime_type = f"image/{img_format}"
                    with open(rubric_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode("utf-8")
                    content.append({
                        "type": "text",
                        "text": "[RUBRIC - Grading Criteria]"
                    })
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}",
                            "detail": "high",
                        },
                    })

            # Add dashboard/document images
            if image_path:
                if image_path.endswith(".pdf") or image_path.endswith(".docx") or image_path.endswith(".doc") or image_path.endswith(".pbix"):
                    # Extract file_id from path (filename without extension)
                    filename = os.path.basename(image_path)
                    file_id = os.path.splitext(filename)[0]
                    upload_dir = os.path.dirname(image_path)
                    base_path = os.path.join(upload_dir, file_id)

                    page_images = sorted(
                        glob.glob(f"{base_path}_page_*.png"),
                        key=lambda p: int(re.search(r'_page_(\d+)', p).group(1))
                    )
                    if not page_images:
                        raise AIServiceError(f"No converted pages found for document at {image_path}. Make sure it was uploaded as PDF, DOCX, or image.")
                    for page_image_path in page_images:
                        if not os.path.exists(page_image_path):
                            raise AIServiceError(f"Document page file not found: {page_image_path}")
                        try:
                            img = Image.open(page_image_path)
                            img_format = img.format.lower() if img.format else "png"
                        except Exception as e:
                            raise AIServiceError(f"Invalid document page image: {str(e)}")
                        mime_type = f"image/{img_format}"
                        with open(page_image_path, "rb") as f:
                            image_data = base64.b64encode(f.read()).decode("utf-8")
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                                "detail": "high",
                            },
                        })
                else:
                    if not os.path.exists(image_path):
                        raise AIServiceError(f"Document file not found: {image_path}")
                    # Detect actual image format
                    try:
                        img = Image.open(image_path)
                        img_format = img.format.lower() if img.format else "png"
                    except Exception as e:
                        raise AIServiceError(f"Invalid document image: {str(e)}")

                    mime_type = f"image/{img_format}"
                    with open(image_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}",
                            "detail": "high",
                        },
                    })

            # Build request payload
            payload = {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
            }

            # Make HTTP request to OpenAI API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            with httpx.Client() as client:
                response = client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=120.0,
                )

                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", str(error_data))
                    except Exception:
                        error_msg = response.text
                    raise AIServiceError(f"OpenAI API error ({response.status_code}): {error_msg}")

                result = response.json()

            # Extract response
            response_text = result["choices"][0]["message"]["content"]

            return {
                "text": response_text,
                "model": self.model,
                "finish_reason": result["choices"][0]["finish_reason"],
                "usage": {
                    "prompt_tokens": result["usage"]["prompt_tokens"],
                    "completion_tokens": result["usage"]["completion_tokens"],
                    "total_tokens": result["usage"]["total_tokens"],
                },
            }

        except AIServiceError:
            raise
        except Exception as e:
            raise AIServiceError(f"Error analyzing dashboard with OpenAI: {str(e)}")

openai_client = OpenAIClient()

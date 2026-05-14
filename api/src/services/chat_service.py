from sqlalchemy.orm import Session
import glob
import os
from src.db import crud
from src.services.assessment_calibration import get_assessment_calibration_context
from src.services.ai_client import openai_client
from src.services.pbix_inspector import pbix_inspector
from src.utils.errors import ChatServiceError, NotFoundError

def _converted_page_count(file_path: str | None) -> int:
    if not file_path:
        return 0
    filename = os.path.basename(file_path)
    file_id = os.path.splitext(filename)[0]
    upload_dir = os.path.dirname(file_path)
    base_path = os.path.join(upload_dir, file_id)
    page_images = glob.glob(f"{base_path}_page_*.png")
    return len(page_images)

def _visual_type_summary(inspection: dict) -> str:
    counts = inspection.get("visual_type_counts") or {}
    if not counts:
        return "none detected"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))

def _pbix_page_names(inspection: dict) -> list[str]:
    return [
        page.get("display_name") or page.get("name") or "Unnamed"
        for page in inspection.get("pages") or []
    ]

def _extract_student_name_from_pbix(inspection: dict) -> str | None:
    """Try to extract student name from PBIX Individual Insights page text."""
    if not inspection:
        return None

    # Look for "Individual Insights" page
    for page in inspection.get("pages") or []:
        page_name = (page.get("display_name") or page.get("name") or "").lower()
        if "individual insights" in page_name:
            # Extract text from this page
            text_content = page.get("text_content") or []
            for entry in text_content:
                text = entry.get("text", "").strip()
                # Look for patterns like "By: [Name]" or "[Name] - Individual Insights"
                if text and len(text) < 100:  # Likely a name, not full text
                    # Check if it looks like a name (contains letters, no full sentences)
                    if ":" in text or text.count(" ") <= 3:
                        # Extract name after "By: " or similar patterns
                        parts = text.split(":")
                        if len(parts) == 2:
                            name = parts[1].strip()
                            if name and len(name) < 50:
                                return name
                        # Or just return the short text if it looks like a name
                        if len(text) < 50 and any(c.isupper() for c in text):
                            return text

    return None

class ChatService:
    def send_message(
        self,
        db: Session,
        message: str | None = None,
        dashboard_id: str | None = None,
        pbix_id: str | None = None,
        student_name: str | None = None,
    ) -> dict:
        """
        Process user message: send to OpenAI and save to database.

        Args:
            db: Database session
            message: User's question (optional if dashboard_id provided)
            dashboard_id: Optional dashboard ID to analyze
            student_name: Name of the student being graded

        Returns:
            Response dict with message ID and AI response

        Raises:
            ChatServiceError: If OpenAI fails
        """
        try:
            # Validate that either message or dashboard_id is provided
            if not message and not dashboard_id and not pbix_id:
                raise ChatServiceError("Either message or an attachment is required")

            dashboard = None
            image_path = None
            visual_dashboard_id = dashboard_id
            if dashboard_id:
                dashboard = crud.get_dashboard(db, dashboard_id)
                if not dashboard:
                    raise NotFoundError(f"Dashboard {dashboard_id} not found")
                if dashboard.file_path.lower().endswith(".pbix"):
                    if not pbix_id:
                        pbix_id = dashboard_id
                    dashboard = None
                    visual_dashboard_id = None
                else:
                    image_path = dashboard.file_path

            pbix_dashboard = None
            pbix_context = ""
            pbix_inspection = None
            if pbix_id:
                pbix_dashboard = crud.get_dashboard(db, pbix_id)
                if not pbix_dashboard:
                    raise NotFoundError(f"PBIX attachment {pbix_id} not found")
                pbix_inspection = pbix_inspector.inspect(pbix_dashboard.file_path)

                # Determine which student(s) to grade
                all_students: list[str] | None = None
                detected_names = pbix_inspector.extract_student_names(pbix_inspection)

                if student_name:
                    # User explicitly selected a specific student
                    pbix_context = pbix_inspector.format_student_evidence_for_prompt(
                        pbix_inspection, student_name
                    )
                elif detected_names:
                    # No student selected → grade ALL detected students
                    all_students = detected_names
                    pbix_context = pbix_inspector.format_all_students_evidence_for_prompt(
                        pbix_inspection, detected_names
                    )
                else:
                    pbix_context = pbix_inspector.format_for_prompt(pbix_inspection)

            # Load active rubric
            rubric = crud.get_active_rubric(db)
            rubric_path = rubric.file_path if rubric else None

            # Get recent chat history for context
            all_messages = crud.get_all_messages(db)
            history_context = "\n".join(
                [f"Q: {m.user_message}\nA: {m.ai_response.get('text', 'N/A')[:100]}"
                 for m in all_messages[-5:]]  # Last 5 messages for context
            )
            # Calibration context only — PBIX evidence goes into evidence_summary instead
            context_parts = []
            context_parts.append(get_assessment_calibration_context())
            if history_context and not image_path and not pbix_context:
                context_parts.append(history_context)
            context = "\n\n".join(context_parts)
            evidence_lines = []
            if rubric_path:
                rubric_pages = _converted_page_count(rubric_path)
                evidence_lines.append(
                    f"Rubric received: {rubric.filename if rubric else 'active rubric'}; converted pages/images available: {rubric_pages if rubric_pages else 1}."
                )
            else:
                evidence_lines.append("Rubric received: no active rubric was attached.")

            if image_path:
                visual_pages = _converted_page_count(image_path)
                evidence_lines.append(
                    f"Visual dashboard evidence received: {dashboard.filename if dashboard else os.path.basename(image_path)}; converted pages/images available: {visual_pages if visual_pages else 1}."
                )
            else:
                evidence_lines.append("Visual dashboard evidence received: no PDF/image attachment was provided.")

            if pbix_inspection:
                page_names = _pbix_page_names(pbix_inspection)
                all_student_names = pbix_inspector.extract_student_names(pbix_inspection)

                evidence_lines.append(
                    "PBIX technical insights received: "
                    f"{pbix_dashboard.filename if pbix_dashboard else 'PBIX attachment'}; "
                    f"readable={pbix_inspection.get('readable', False)}; "
                    f"pages={pbix_inspection.get('total_pages', 0)}; "
                    f"page names={', '.join(page_names) if page_names else 'none detected'}; "
                    f"all students detected in PBIX={', '.join(all_student_names) if all_student_names else 'none'}."
                )

                grading_targets = [student_name] if student_name else (all_students or [])
                any_missing_insights = False
                for grading_name in grading_targets:
                    student_evidence = pbix_inspector.extract_student_evidence(pbix_inspection, grading_name)
                    evidence_lines.append(
                        f"Student being graded: {grading_name}; "
                        f"visuals on Dashboard page: {student_evidence['visual_count']}."
                    )
                    if student_evidence["visual_count"] == 0:
                        evidence_lines.append(
                            f"NOTE: PBIX text extraction found no visuals attributed to '{grading_name}'. "
                            "Check the dashboard images — if charts with this student's name appear in a title, grade them from the image."
                        )
                    if not student_evidence["insights"]:
                        any_missing_insights = True
                        evidence_lines.append(
                            f"NOTE: Label-based attribution found 0 insight paragraphs for '{grading_name}' — "
                            "the raw Individual Insights page text is included below; locate this student's section by their name label and grade from it."
                        )

                # If any student is missing insights, dump the full Individual Insights page text here
                if any_missing_insights:
                    raw_insights = pbix_inspector.get_insights_page_raw_text(pbix_inspection)
                    if raw_insights:
                        evidence_lines.append("")
                        evidence_lines.append("[INDIVIDUAL INSIGHTS PAGE — FULL RAW TEXT]")
                        evidence_lines.append(
                            "Find each student's section by their name label "
                            "([Name]:, (Name):, or Name: at the start of a paragraph), "
                            "then grade the paragraphs that follow as their insights:"
                        )
                        evidence_lines.extend(raw_insights)
                    else:
                        evidence_lines.append(
                            "Individual Insights page: no text could be extracted from PBIX — "
                            "grade insights from the Individual Insights page image directly."
                        )

                has_team_insights = any("team insights" in name.lower() for name in page_names)
                has_individual_insights = any("individual insights" in name.lower() for name in page_names)
                visual_pages = _converted_page_count(image_path)
                if not has_team_insights and visual_pages < 3:
                    evidence_lines.append(
                        "Component availability: Team Insights evidence was not detected; "
                        "mark Team Insights rows as Not assessable unless attached images "
                        "visibly contain team insight text."
                    )
                if not has_individual_insights:
                    evidence_lines.append(
                        "Component availability: Individual Insights page not found in PBIX; "
                        "mark Individual Insights rows as Not assessable."
                    )
                notes = pbix_inspection.get("notes") or []
                if notes:
                    evidence_lines.append(f"PBIX parser limitations/notes: {'; '.join(notes)}")
            else:
                evidence_lines.append("PBIX technical insights received: no PBIX attachment was provided.")

            # Put PBIX student evidence first in the summary so it's prominent
            if pbix_context:
                evidence_summary = pbix_context + "\n\n" + "\n".join(evidence_lines)
            else:
                evidence_summary = "\n".join(evidence_lines)

            # Default query for AI if only image is provided (backend only)
            ai_query = message or "Please analyze and grade this document based on the rubric."

            # Send to OpenAI
            ai_response = openai_client.grade_dashboard(
                image_path=image_path,
                rubric_path=rubric_path,
                query=ai_query,
                context=context,
                evidence_summary=evidence_summary,
                student_name=student_name,
                all_students=all_students,
            )

            # Save message to database - keep original message (may be empty for image-only)
            db_message = crud.create_message(
                db=db,
                user_message=message or "",  # Save empty string if no message
                ai_response=ai_response,
                dashboard_id=visual_dashboard_id,
                pbix_dashboard_id=pbix_id,
                student_name=student_name,
            )

            return {
                "id": db_message.id,
                "dashboard_id": db_message.dashboard_id,
                "pbix_id": db_message.pbix_dashboard_id,
                "student_name": db_message.student_name,
                "user_message": db_message.user_message,
                "ai_response": db_message.ai_response,
                "created_at": db_message.created_at,
                "dashboard_filename": dashboard.filename if dashboard else None,
                "dashboard_file_path": dashboard.file_path if dashboard else None,
                "pbix_filename": pbix_dashboard.filename if pbix_dashboard else None,
                "pbix_file_path": pbix_dashboard.file_path if pbix_dashboard else None,
            }

        except (NotFoundError, ChatServiceError):
            raise
        except Exception as e:
            raise ChatServiceError(f"Chat service error: {str(e)}")

    def grade_stateless(
        self,
        message: str | None = None,
        image_path: str | None = None,
        image_filename: str | None = None,
        pbix_path: str | None = None,
        pbix_filename: str | None = None,
        rubric_path: str | None = None,
        rubric_filename: str | None = None,
        student_name: str | None = None,
    ) -> dict:
        """Grade a one-shot Vercel/serverless request without DB or persistent uploads."""
        try:
            if not message and not image_path and not pbix_path:
                raise ChatServiceError("Either message or an attachment is required")

            pbix_context = ""
            pbix_inspection = None
            all_students: list[str] | None = None
            if pbix_path:
                pbix_inspection = pbix_inspector.inspect(pbix_path)
                detected_names = pbix_inspector.extract_student_names(pbix_inspection)

                if student_name:
                    pbix_context = pbix_inspector.format_student_evidence_for_prompt(
                        pbix_inspection, student_name
                    )
                elif detected_names:
                    all_students = detected_names
                    pbix_context = pbix_inspector.format_all_students_evidence_for_prompt(
                        pbix_inspection, detected_names
                    )
                else:
                    pbix_context = pbix_inspector.format_for_prompt(pbix_inspection)

            context = get_assessment_calibration_context()
            evidence_lines = []
            if rubric_path:
                rubric_pages = _converted_page_count(rubric_path)
                evidence_lines.append(
                    f"Rubric received: {rubric_filename or 'uploaded rubric'}; "
                    f"converted pages/images available: {rubric_pages if rubric_pages else 1}."
                )
            else:
                evidence_lines.append("Rubric received: no rubric was attached.")

            if image_path:
                visual_pages = _converted_page_count(image_path)
                evidence_lines.append(
                    f"Visual dashboard evidence received: {image_filename or os.path.basename(image_path)}; "
                    f"converted pages/images available: {visual_pages if visual_pages else 1}."
                )
            else:
                evidence_lines.append("Visual dashboard evidence received: no PDF/image attachment was provided.")

            if pbix_inspection:
                page_names = _pbix_page_names(pbix_inspection)
                all_student_names = pbix_inspector.extract_student_names(pbix_inspection)
                evidence_lines.append(
                    "PBIX technical insights received: "
                    f"{pbix_filename or 'PBIX attachment'}; "
                    f"readable={pbix_inspection.get('readable', False)}; "
                    f"pages={pbix_inspection.get('total_pages', 0)}; "
                    f"page names={', '.join(page_names) if page_names else 'none detected'}; "
                    f"all students detected in PBIX={', '.join(all_student_names) if all_student_names else 'none'}."
                )

                grading_targets = [student_name] if student_name else (all_students or [])
                any_missing_insights = False
                for grading_name in grading_targets:
                    student_evidence = pbix_inspector.extract_student_evidence(
                        pbix_inspection, grading_name
                    )
                    evidence_lines.append(
                        f"Student being graded: {grading_name}; "
                        f"visuals on Dashboard page: {student_evidence['visual_count']}."
                    )
                    if student_evidence["visual_count"] == 0:
                        evidence_lines.append(
                            f"NOTE: PBIX text extraction found no visuals attributed to '{grading_name}'. "
                            "Check the dashboard images if available."
                        )
                    if not student_evidence["insights"]:
                        any_missing_insights = True
                        evidence_lines.append(
                            f"NOTE: Label-based attribution found 0 insight paragraphs for '{grading_name}'."
                        )

                if any_missing_insights:
                    raw_insights = pbix_inspector.get_insights_page_raw_text(pbix_inspection)
                    if raw_insights:
                        evidence_lines.append("")
                        evidence_lines.append("[INDIVIDUAL INSIGHTS PAGE - FULL RAW TEXT]")
                        evidence_lines.extend(raw_insights)

                has_team_insights = any("team insights" in name.lower() for name in page_names)
                has_individual_insights = any("individual insights" in name.lower() for name in page_names)
                visual_pages = _converted_page_count(image_path)
                if not has_team_insights and visual_pages < 3:
                    evidence_lines.append(
                        "Component availability: Team Insights evidence was not detected; "
                        "mark Team Insights rows as Not assessable unless attached images visibly contain team insight text."
                    )
                if not has_individual_insights:
                    evidence_lines.append(
                        "Component availability: Individual Insights page not found in PBIX; "
                        "mark Individual Insights rows as Not assessable."
                    )
                notes = pbix_inspection.get("notes") or []
                if notes:
                    evidence_lines.append(f"PBIX parser limitations/notes: {'; '.join(notes)}")
            else:
                evidence_lines.append("PBIX technical insights received: no PBIX attachment was provided.")

            evidence_summary = (
                pbix_context + "\n\n" + "\n".join(evidence_lines)
                if pbix_context
                else "\n".join(evidence_lines)
            )
            ai_query = message or "Please analyze and grade this document based on the rubric."

            ai_response = openai_client.grade_dashboard(
                image_path=image_path,
                rubric_path=rubric_path,
                query=ai_query,
                context=context,
                evidence_summary=evidence_summary,
                student_name=student_name,
                all_students=all_students,
            )

            return {
                "ai_response": ai_response,
                "student_name": student_name,
            }

        except ChatServiceError:
            raise
        except Exception as e:
            raise ChatServiceError(f"Stateless grading error: {str(e)}")

    def get_chat_history(self, db: Session) -> list[dict]:
        """
        Get global chat history.

        Args:
            db: Database session

        Returns:
            List of all messages
        """
        try:
            messages = crud.get_all_messages(db)

            result = []
            for m in messages:
                dashboard = crud.get_dashboard(db, m.dashboard_id) if m.dashboard_id else None
                pbix_dashboard = crud.get_dashboard(db, m.pbix_dashboard_id) if m.pbix_dashboard_id else None
                result.append({
                    "id": m.id,
                    "dashboard_id": m.dashboard_id,
                    "pbix_id": m.pbix_dashboard_id,
                    "student_name": m.student_name,
                    "user_message": m.user_message,
                    "ai_response": m.ai_response,
                    "created_at": m.created_at,
                    "dashboard_filename": dashboard.filename if dashboard else None,
                    "dashboard_file_path": dashboard.file_path if dashboard else None,
                    "pbix_filename": pbix_dashboard.filename if pbix_dashboard else None,
                    "pbix_file_path": pbix_dashboard.file_path if pbix_dashboard else None,
                })
            return result

        except Exception as e:
            raise ChatServiceError(f"Error fetching chat history: {str(e)}")

chat_service = ChatService()

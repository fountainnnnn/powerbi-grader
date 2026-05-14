import json
import os
import re
import zipfile
from html import unescape
from typing import Any


class PBIXInspector:
    GRADEABLE_VISUAL_TYPES = {
        "areaChart",
        "barChart",
        "clusteredBarChart",
        "clusteredColumnChart",
        "columnChart",
        "donutChart",
        "filledMap",
        "funnel",
        "gauge",
        "hundredPercentStackedBarChart",
        "hundredPercentStackedColumnChart",
        "lineChart",
        "lineClusteredColumnComboChart",
        "lineStackedColumnComboChart",
        "map",
        "matrix",
        "pieChart",
        "ribbonChart",
        "scatterChart",
        "shapeMap",
        "stackedAreaChart",
        "stackedBarChart",
        "stackedColumnChart",
        "tableEx",
        "treemap",
        "waterfallChart",
    }

    def inspect(self, file_path: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "readable": False,
            "pages": [],
            "total_pages": 0,
            "total_visuals": 0,
            "visual_type_counts": {},
            "fields_used": [],
            "text_content": [],
            "package_files": [],
            "notes": [],
        }

        if not file_path.lower().endswith(".pbix"):
            result["notes"].append("The uploaded insight file is not a PBIX file.")
            return result

        if not os.path.exists(file_path):
            result["notes"].append("PBIX file was not found on disk.")
            return result

        if not zipfile.is_zipfile(file_path):
            result["notes"].append("PBIX package could not be opened as a readable archive.")
            return result

        with zipfile.ZipFile(file_path) as archive:
            names = archive.namelist()
            result["readable"] = True
            result["package_files"] = names[:80]

            layout = self._read_json_member(archive, names, "Report/Layout")
            if layout:
                self._apply_classic_layout(result, layout)
            else:
                result["notes"].append("Classic Report/Layout JSON was not found or could not be parsed.")

            if not result["pages"]:
                self._apply_json_fallback(result, archive, names)

        result["total_pages"] = len(result["pages"])
        result["total_visuals"] = sum(page.get("visual_count", 0) for page in result["pages"])
        result["fields_used"] = sorted({field for page in result["pages"] for visual in page.get("visuals", []) for field in visual.get("fields", [])})[:120]
        result["text_content"] = self._collect_text_content(result)
        return result

    def _normalise_owner_name(self, value: str) -> str:
        text = value.strip()
        text = re.sub(r"[_\-]+", " ", text)
        text = re.sub(
            r"\b(individual|dashboard|insights|visuals|page|report|pbix)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", " ", text).strip(" :;-_")

    def _name_key(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _page_belongs_to_student(self, page_name: str, student_name: str) -> bool:
        page_key = self._name_key(self._normalise_owner_name(page_name))
        student_key = self._name_key(student_name)
        return bool(student_key and page_key and (student_key == page_key or student_key in page_key))

    def _visual_is_gradeable_chart(self, visual: dict[str, Any]) -> bool:
        return (visual.get("visual_type") or "") in self.GRADEABLE_VISUAL_TYPES

    def _looks_like_formatting_value(self, text: str) -> bool:
        stripped = text.strip()
        if re.fullmatch(r"\d+(?:\.\d+)?[DL]?", stripped):
            return True
        if stripped.lower() in {"scalar", "insideend", "multiline", "basic", "between", "dropdown"}:
            return True
        if "segoe ui" in stripped.lower():
            return True
        return False

    def _visual_title_texts(self, visual: dict[str, Any]) -> list[str]:
        title_entries: list[str] = []
        fallback_entries: list[str] = []
        seen: set[str] = set()
        for entry in visual.get("text_content") or []:
            text = (entry.get("text") or "").strip()
            if not text or text in seen:
                continue
            if self._looks_like_formatting_value(text):
                continue
            seen.add(text)
            source = (entry.get("source") or "").lower()
            if "title" in source:
                title_entries.append(text)
            elif len(text) > 8:
                fallback_entries.append(text)
        return title_entries + fallback_entries

    def _visual_search_text(self, visual: dict[str, Any]) -> str:
        return " ".join(self._visual_title_texts(visual) + (visual.get("fields") or [])).lower()

    def extract_student_names(self, inspection: dict[str, Any]) -> list[str]:
        """
        Return unique student names from the PBIX.

        Detection strategy (in priority order):
        1. Individual Insights page — standalone label entries: [Name], [Name]:, (Name):, Name:
        2. Dashboard visual titles — candidate appears in 2+ chart titles in any position:
           "Name - Title", "Title - Name", "Title (Name)", "(Name) - Title", "[Name] - Title", etc.
        """
        label_names: set[str] = set()
        page_names: set[str] = set()

        # Standalone label patterns (whole text entry must match)
        bracket_standalone = re.compile(r"^\[([^\]]+)\]\s*:?\s*$")
        paren_standalone = re.compile(r"^\(([^)]+)\)\s*:?\s*$")
        brace_standalone = re.compile(r"^\{([^}]+)\}\s*:?\s*$")
        bracket_inline = re.compile(r"^\[([^\]]+)\]\s*:")
        paren_inline = re.compile(r"^\(([^)]+)\)\s*:")
        brace_inline = re.compile(r"^\{([^}]+)\}\s*:")
        plain_label = re.compile(r"^([^:\[\](){}\n]{2,50}):\s*$")

        # All ways a name can appear inside a chart title
        dash_prefix = re.compile(r"^(.+?)\s*[-–]\s*.+")          # "Name - rest"
        dash_suffix = re.compile(r".+\s*[-–]\s*(.+?)$")          # "rest - Name"
        paren_any   = re.compile(r"\(([^)]+)\)")                  # "(Name)" anywhere
        bracket_any = re.compile(r"\[([^\]]+)\]")                 # "[Name]" anywhere
        brace_any = re.compile(r"\{([^}]+)\}")                    # "{Name}" anywhere

        candidate_counts: dict[str, int] = {}

        def _plausible(s: str) -> bool:
            s = s.strip()
            if not s or len(s) < 2 or len(s) > 50:
                return False
            if not re.search(r"[a-zA-Z]", s):
                return False
            if len(s.split()) > 5:
                return False
            if re.search(r"\d{1,2}\s*[-–]\s*\d{1,2}", s):   # "25-34", "18–24"
                return False
            if s.lower().startswith("e.g"):
                return False
            if re.fullmatch(r"[\d\s\W]+", s):
                return False
            return True

        def _count(candidate: str) -> None:
            c = candidate.strip()
            if _plausible(c):
                candidate_counts[c] = candidate_counts.get(c, 0) + 1

        for page in inspection.get("pages") or []:
            raw_page_name = page.get("display_name") or page.get("name") or ""
            page_name = raw_page_name.lower()
            cleaned_page_name = self._normalise_owner_name(raw_page_name)
            if raw_page_name and "individual" in page_name and _plausible(cleaned_page_name):
                page_names.add(cleaned_page_name)

            for visual in page.get("visuals") or []:
                for entry in visual.get("text_content") or []:
                    text = entry.get("text", "").strip()
                    if not text:
                        continue

                    # ── Individual Insights page: standalone labels only ──
                    if "individual insights" in page_name:
                        for pat in (
                            bracket_standalone,
                            paren_standalone,
                            brace_standalone,
                            bracket_inline,
                            paren_inline,
                            brace_inline,
                            plain_label,
                        ):
                            m = pat.match(text)
                            if m and _plausible(m.group(1)):
                                label_names.add(m.group(1).strip())
                                break

                    # ── Dashboard page: extract candidates from all title positions ──
                    if "dashboard" in page_name:
                        m = dash_prefix.match(text)
                        if m:
                            _count(m.group(1))
                        m = dash_suffix.search(text)
                        if m:
                            _count(m.group(1))
                        for m in paren_any.finditer(text):
                            _count(m.group(1))
                        for m in bracket_any.finditer(text):
                            _count(m.group(1))
                        for m in brace_any.finditer(text):
                            _count(m.group(1))

        # Insight-page standalone labels are ground truth
        if label_names:
            return sorted(label_names)

        # A page like "Ng Yu Hang_Individual" is a strong single-student signal.
        if page_names:
            return sorted(page_names)

        # Dashboard fallback: accept any candidate that appears in 2+ chart titles
        return sorted(c for c, n in candidate_counts.items() if n >= 2)

    def _raw_student_insight_texts(
        self, inspection: dict[str, Any], student_name: str
    ) -> list[str]:
        texts: list[str] = []
        name_re = re.escape(student_name.strip())
        label_pat = re.compile(r"^[\[\(\{]?\s*" + name_re + r"\s*[\]\)\}]?\s*:?\s*$", re.I)
        inline_label = re.compile(
            r"^[\[\(\{]?\s*" + name_re + r"\s*[\]\)\}]?\s*:\s*(.+)",
            re.I | re.S,
        )
        any_label = re.compile(r"^[\[\(\{][^\]\)\}]+[\]\)\}]\s*:", re.I)

        def should_keep_insight(text: str) -> bool:
            clean = text.strip()
            if len(clean) <= 10 or not re.search(r"[a-zA-Z]{3,}", clean):
                return False
            if self._looks_like_formatting_value(clean):
                return False
            lowered = clean.lower()
            if lowered in {
                "individual insights",
                "individual insight",
                "team insights",
                "team insight",
            }:
                return False
            if len(clean.split()) <= 3 and not re.search(r"\d+[\).]", clean):
                return False
            return True

        for page in inspection.get("pages") or []:
            page_name = page.get("display_name") or page.get("name") or ""
            page_is_named_for_student = self._page_belongs_to_student(page_name, student_name)
            page_is_individual_insights = "individual insights" in page_name.lower()

            for visual in page.get("visuals") or []:
                if (visual.get("visual_type") or "") != "textbox":
                    continue
                entries = [
                    (entry.get("text") or "").strip()
                    for entry in visual.get("text_content") or []
                    if (entry.get("text") or "").strip()
                ]
                collecting = page_is_named_for_student and not page_is_individual_insights
                for text in entries:
                    inline = inline_label.match(text)
                    if inline:
                        remainder = inline.group(1).strip()
                        if should_keep_insight(remainder):
                            texts.append(remainder)
                        collecting = True
                        continue
                    if label_pat.match(text):
                        collecting = True
                        continue
                    if collecting:
                        if any_label.match(text) and not inline_label.match(text):
                            collecting = False
                            continue
                        if should_keep_insight(text):
                            texts.append(text)
        return texts

    def _declared_visual_refs_for_student(
        self, inspection: dict[str, Any], student_name: str
    ) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        chart_type_pattern = (
            r"(?:area|bar|stacked bar|column|clustered column|line|pie|donut|scatter|card)"
            r"\s+chart|bar graph|graph"
        )

        for text in self._raw_student_insight_texts(inspection, student_name):
            for match in re.finditer(
                rf"([^.\n:;]+?)\s*\(([^)]*?(?:{chart_type_pattern})[^)]*)\)",
                text,
                flags=re.IGNORECASE,
            ):
                title = re.sub(r"^\s*(and|or)\s+", "", match.group(1), flags=re.IGNORECASE)
                title = re.sub(r"^\s*(and|or)(?=[A-Z])", "", title, flags=re.IGNORECASE)
                title = title.strip(" ,.;:-")
                chart_type = match.group(2).strip()
                if len(title) < 6:
                    continue
                key = (self._name_key(title), self._name_key(chart_type))
                if key not in seen:
                    seen.add(key)
                    refs.append({"title": title, "chart_type": chart_type})
        return refs

    def extract_student_evidence(self, inspection: dict[str, Any], student_name: str) -> dict[str, Any]:
        """
        Return only the visuals and insights that belong to this student.

        Visual ownership: chart title starts with "<student_name> -" or "<student_name>-"
        Insight ownership: insight block is immediately preceded by "[<student_name>]:"
        """
        student_visuals: list[dict[str, Any]] = []
        student_insights: list[str] = []
        declared_refs = self._declared_visual_refs_for_student(inspection, student_name)

        name_norm = student_name.strip().lower()

        def title_belongs(text: str) -> bool:
            """True if the student's name appears in a STRUCTURAL position in the title."""
            t = text.strip().lower()
            n = re.escape(name_norm)
            # "Name - rest" or "Name– rest" at the START
            if re.match(r"^" + n + r"\s*[-–]", t):
                return True
            # "rest - Name" at the END (name is after the last dash)
            if re.search(r"[-–]\s*" + n + r"\s*$", t):
                return True
            # "(Name)" as a whole parenthesised segment (not buried mid-sentence)
            if re.search(r"\(\s*" + n + r"\s*\)", t):
                return True
            # "[Name]" as a whole bracketed segment
            if re.search(r"\[\s*" + n + r"\s*\]", t):
                return True
            # "{Name}" as a whole brace-delimited segment
            if re.search(r"\{\s*" + n + r"\s*\}", t):
                return True
            # Title is exactly the name (or name with trailing colon)
            if re.fullmatch(n + r"\s*:?", t):
                return True
            return False

        def visual_matches_declared_ref(visual: dict[str, Any]) -> bool:
            search_text = self._visual_search_text(visual)
            visual_type = (visual.get("visual_type") or "").lower()
            for ref in declared_refs:
                title_tokens = [
                    token
                    for token in re.findall(r"[a-z0-9]+", ref.get("title", "").lower())
                    if len(token) > 2 and token not in {"sum", "avg", "average", "chart", "graph", "the"}
                ]
                token_hits = sum(1 for token in title_tokens if token in search_text)
                if title_tokens and token_hits >= min(3, len(title_tokens)):
                    return True
                chart_type = ref.get("chart_type", "").lower()
                chart_type_matches = (
                    ("bar" in chart_type and "bar" in visual_type)
                    or ("area" in chart_type and "area" in visual_type)
                    or ("line" in chart_type and "line" in visual_type)
                    or ("column" in chart_type and "column" in visual_type)
                    or ("pie" in chart_type and "pie" in visual_type)
                    or ("donut" in chart_type and "donut" in visual_type)
                    or ("tree" in chart_type and "treemap" in visual_type)
                    or ("map" in chart_type and "map" in visual_type)
                    or ("funnel" in chart_type and "funnel" in visual_type)
                )
                if chart_type_matches and token_hits >= 1:
                    return True
            return False

        # Insight ownership: a STANDALONE label entry that is just [Name], (Name), or Name:
        # Must be the whole text entry, not embedded in a sentence
        _esc = re.escape(student_name.strip())
        label_pat = re.compile(
            r"^[\[\(\{]?\s*" + _esc + r"\s*[\]\)\}]?\s*:?\s*$",
            re.IGNORECASE,
        )

        for page in inspection.get("pages") or []:
            page_name = (page.get("display_name") or page.get("name") or "")
            page_name_lower = page_name.lower()
            page_is_named_for_student = self._page_belongs_to_student(page_name, student_name)

            # ── Dashboard page: collect visuals owned by this student ──
            if "dashboard" in page_name_lower or page_is_named_for_student:
                for visual in page.get("visuals") or []:
                    if not self._visual_is_gradeable_chart(visual):
                        continue
                    owned = False
                    for entry in visual.get("text_content") or []:
                        if title_belongs(entry.get("text", "")):
                            owned = True
                            break
                    if not owned and page_is_named_for_student:
                        owned = visual_matches_declared_ref(visual) if declared_refs else True
                    if owned:
                        student_visuals.append(visual)

            # ── Individual Insights page: collect paragraphs owned by this student ──
            if "individual insights" in page_name_lower:
                # Also match inline labels: "[Name]: insight text..." in a single entry
                inline_label = re.compile(
                    r"^[\[\(\{]?\s*" + re.escape(student_name.strip()) + r"\s*[\]\)\}]?\s*:\s*(.+)",
                    re.IGNORECASE | re.DOTALL,
                )
                # Pattern to detect ANY student label (to stop collecting)
                any_label = re.compile(r"^[\[\(\{].+[\]\)\}]\s*:", re.IGNORECASE)

                for visual in page.get("visuals") or []:
                    texts = [
                        e.get("text", "")
                        for e in visual.get("text_content") or []
                        if e.get("text", "").strip()
                    ]
                    collecting = False
                    for text in texts:
                        # Case 1: inline "[Name]: full insight text in one entry"
                        m = inline_label.match(text)
                        if m:
                            collecting = False  # reset; this entry is self-contained
                            remainder = m.group(1).strip()
                            if len(remainder) > 10 and re.search(r"[a-zA-Z]{3,}", remainder):
                                student_insights.append(remainder)
                            continue
                        # Case 2: standalone label "[Name]:" → start collecting next entries
                        if label_pat.search(text):
                            collecting = True
                            continue
                        if collecting:
                            # Stop when another student's label appears
                            if any_label.match(text.strip()):
                                collecting = False
                            else:
                                clean = text.strip()
                                if len(clean) > 10 and re.search(r"[a-zA-Z]{3,}", clean):
                                    student_insights.append(clean)

        if not student_insights:
            student_insights = self._raw_student_insight_texts(inspection, student_name)

        return {
            "student_name": student_name,
            "visuals": student_visuals,
            "visual_count": len(student_visuals),
            "insights": student_insights,
            "declared_visuals": declared_refs,
        }

    def format_student_evidence_for_prompt(
        self, inspection: dict[str, Any], student_name: str
    ) -> str:
        """Format only this student's visuals and insights for the grading prompt."""
        evidence = self.extract_student_evidence(inspection, student_name)
        lines = [
            f"[STUDENT-SPECIFIC PBIX EVIDENCE for: {student_name}]",
            f"File: {inspection.get('file_name', 'Unknown')}",
        ]

        # ── Their visuals ──
        lines.append(f"\n{student_name}'s attributable gradeable visuals ({evidence['visual_count']} found):")
        if evidence.get("declared_visuals"):
            lines.append("Declared chosen visuals from this student's own insight text:")
            for ref in evidence["declared_visuals"]:
                lines.append(f"  - {ref['title']} ({ref['chart_type']})")
        if evidence["visuals"]:
            for v in evidence["visuals"]:
                vtype = v.get("visual_type", "unknown")
                titles = self._visual_title_texts(v)
                fields = v.get("fields") or []
                lines.append(f"  - {vtype}")
                if titles:
                    lines.append(f"    titles/text: {' | '.join(titles[:4])}")
                if fields:
                    lines.append(f"    fields/measures: {', '.join(fields[:8])}")
        else:
            lines.append("  (no gradeable visuals could be attributed to this student from PBIX text)")

        # ── Their insights ──
        lines.append(f"\n{student_name}'s Individual Insight Texts (grade as Interpret and Provide):")
        if evidence["insights"]:
            for i, insight in enumerate(evidence["insights"], 1):
                lines.append(f"  [{student_name}] Insight {i}: {insight}")
        else:
            lines.append("  (none found — check Individual Insights page image)")

        # Always include full raw Individual Insights page text as fallback
        raw_insights = self.get_insights_page_raw_text(inspection)
        if raw_insights:
            lines.append(f"\n[INDIVIDUAL INSIGHTS PAGE — FULL RAW TEXT (use to find {student_name}'s section if attribution above is empty)]")
            lines.append("Look for a label like [Name]:, (Name):, or Name: then read the following paragraphs as their insights.")
            lines.extend(raw_insights)

        lines.append(
            f"\nGrade ONLY the visuals and insights listed above for {student_name}. "
            "If a 'Declared chosen visuals' list is present, treat it as the student's own declared selection "
            "and match it to the extracted gradeable visuals by title/fields/chart type. "
            "When reading the attached dashboard images, identify this student's charts by their name "
            "appearing in the title in ANY position or format: before a dash, after a dash, in parentheses (), "
            "in square brackets [], in curly braces {}, or as a label anywhere in the title. "
            "Do not penalise or credit this student for another student's work."
        )
        return "\n".join(lines)

    def format_all_students_evidence_for_prompt(
        self, inspection: dict[str, Any], student_names: list[str]
    ) -> str:
        """Format evidence for ALL students in a single prompt block."""
        lines = [
            "[PBIX EVIDENCE — ALL STUDENTS]",
            f"File: {inspection.get('file_name', 'Unknown')}",
            f"Students detected: {', '.join(student_names)}",
        ]
        for name in student_names:
            evidence = self.extract_student_evidence(inspection, name)
            lines.append(f"\n{'=' * 50}")
            lines.append(f"STUDENT: {name}")
            lines.append(f"Attributable gradeable visuals ({evidence['visual_count']} found):")
            if evidence.get("declared_visuals"):
                lines.append("Declared chosen visuals from this student's own insight text:")
                for ref in evidence["declared_visuals"]:
                    lines.append(f"  - {ref['title']} ({ref['chart_type']})")
            if evidence["visuals"]:
                for v in evidence["visuals"]:
                    vtype = v.get("visual_type", "unknown")
                    titles = self._visual_title_texts(v)
                    fields = v.get("fields") or []
                    lines.append(f"  - {vtype}")
                    if titles:
                        lines.append(f"    titles/text: {' | '.join(titles[:4])}")
                    if fields:
                        lines.append(f"    fields: {', '.join(fields[:8])}")
            else:
                lines.append("  (none found)")
            lines.append(f"Individual Insight Texts for {name} ({len(evidence['insights'])} found — grade as Interpret and Provide components):")
            if evidence["insights"]:
                for i, insight in enumerate(evidence["insights"], 1):
                    lines.append(f"  [{name}] Insight {i}: {insight}")
            else:
                lines.append("  (none found — check Individual Insights page image)")
        # Always include full raw Individual Insights page text as fallback
        raw_insights = self.get_insights_page_raw_text(inspection)
        if raw_insights:
            lines.append(f"\n{'=' * 50}")
            lines.append("[INDIVIDUAL INSIGHTS PAGE — FULL RAW TEXT]")
            lines.append("If a student's attributed insights above are empty, find their section here by looking for their name label ([Name]:, (Name):, Name:) followed by paragraphs.")
            lines.extend(raw_insights)

        lines.append(f"\n{'=' * 50}")
        lines.append(
            "Grade EACH student's Individual components using only their own listed evidence above. "
            "If a student has a 'Declared chosen visuals' list, use that as the strongest attribution signal "
            "and match those declared titles/fields/chart types to the extracted gradeable visuals. "
            "When reading the attached dashboard images, identify each student's charts by their name "
            "appearing in the title in ANY position or format: before a dash, after a dash, in parentheses (), "
            "in square brackets [], in curly braces {}, or as a label anywhere in the title. "
            "Team components receive the same mark for every student."
        )
        return "\n".join(lines)

    def get_insights_page_raw_text(self, inspection: dict[str, Any]) -> list[str]:
        """Return all meaningful text entries from the Individual Insights page, in document order."""
        texts = []
        for page in inspection.get("pages") or []:
            page_name = (page.get("display_name") or page.get("name") or "").lower()
            if "individual insights" in page_name:
                for visual in page.get("visuals") or []:
                    for entry in visual.get("text_content") or []:
                        text = entry.get("text", "").strip()
                        if text and len(text) > 5:
                            texts.append(text)
        return texts

    def format_for_prompt(self, inspection: dict[str, Any]) -> str:
        lines = [
            "[PBIX TECHNICAL INSIGHTS]",
            f"File: {inspection.get('file_name', 'Unknown')}",
            f"Readable PBIX package: {inspection.get('readable', False)}",
            f"Pages detected: {inspection.get('total_pages', 0)}",
            f"Visuals detected: {inspection.get('total_visuals', 0)}",
        ]

        counts = inspection.get("visual_type_counts") or {}
        if counts:
            visual_counts = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
            lines.append(f"Visual type counts: {visual_counts}")

        fields = inspection.get("fields_used") or []
        if fields:
            lines.append("Fields/measures referenced by visuals:")
            for field in fields[:80]:
                lines.append(f"- {field}")

        text_content = inspection.get("text_content") or []
        if text_content:
            lines.append("Full static/visible text extracted from PBIX:")
            for entry in text_content:
                page = entry.get("page") or "Unknown page"
                visual_type = entry.get("visual_type") or "unknown"
                text = entry.get("text") or ""
                lines.append(f"- [{page} / {visual_type}] {text}")

        pages = inspection.get("pages") or []
        if pages:
            lines.append("Report pages and visuals:")
            for page in pages[:20]:
                lines.append(f"Page: {page.get('display_name') or page.get('name') or 'Unnamed'}")
                page_size = page.get("size") or {}
                if page_size:
                    lines.append(f"Canvas: {page_size.get('width', 'unknown')} x {page_size.get('height', 'unknown')}")
                for visual in page.get("visuals", [])[:30]:
                    position = visual.get("position") or {}
                    position_text = ""
                    if position:
                        position_text = f" at x={position.get('x')}, y={position.get('y')}, w={position.get('width')}, h={position.get('height')}"
                    fields_text = ", ".join(visual.get("fields", [])[:12])
                    if fields_text:
                        lines.append(f"- {visual.get('visual_type', 'unknown visual')}{position_text}; fields: {fields_text}")
                    else:
                        lines.append(f"- {visual.get('visual_type', 'unknown visual')}{position_text}")

        notes = inspection.get("notes") or []
        if notes:
            lines.append("PBIX parser notes:")
            for note in notes:
                lines.append(f"- {note}")

        lines.append("Use these PBIX insights for technical/content evaluation. Use the attached PDF/image pages for visual appearance, layout, readability, and design evaluation.")
        return "\n".join(lines)

    def _apply_classic_layout(self, result: dict[str, Any], layout: dict[str, Any]) -> None:
        sections = layout.get("sections") or []
        visual_type_counts: dict[str, int] = {}
        pages = []

        for section in sections:
            visuals = []
            containers = section.get("visualContainers") or []
            for container in containers:
                visual = self._extract_visual(container)
                if visual:
                    visuals.append(visual)
                    visual_type = visual.get("visual_type") or "unknown"
                    visual_type_counts[visual_type] = visual_type_counts.get(visual_type, 0) + 1

            pages.append({
                "name": section.get("name"),
                "display_name": section.get("displayName") or section.get("name"),
                "size": {
                    "width": section.get("width"),
                    "height": section.get("height"),
                },
                "visual_count": len(visuals),
                "visuals": visuals,
            })

        result["pages"] = pages
        result["visual_type_counts"] = visual_type_counts

    def _extract_visual(self, container: dict[str, Any]) -> dict[str, Any] | None:
        config = self._parse_json_value(container.get("config")) or {}
        query = self._parse_json_value(container.get("query")) or {}
        transforms = self._parse_json_value(container.get("dataTransforms")) or {}
        single_visual = config.get("singleVisual") or {}
        visual_type = single_visual.get("visualType") or config.get("visualType") or "unknown"
        fields = sorted(self._collect_query_refs({"config": config, "query": query, "dataTransforms": transforms}))[:40]
        text_content = self._extract_visible_text_entries({"config": config, "query": query, "dataTransforms": transforms})
        position = self._extract_position(container, config)

        if visual_type == "unknown" and not fields and not text_content and not position:
            return None

        return {
            "visual_type": visual_type,
            "position": position,
            "fields": fields,
            "text_content": text_content,
        }

    def _extract_position(self, container: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        x = container.get("x")
        y = container.get("y")
        width = container.get("width")
        height = container.get("height")

        layouts = config.get("layouts") or []
        if layouts and isinstance(layouts, list):
            position = layouts[0].get("position") if isinstance(layouts[0], dict) else None
            if isinstance(position, dict):
                x = position.get("x", x)
                y = position.get("y", y)
                width = position.get("width", width)
                height = position.get("height", height)

        return {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }

    def _apply_json_fallback(self, result: dict[str, Any], archive: zipfile.ZipFile, names: list[str]) -> None:
        candidates = [name for name in names if name.lower().endswith(".json") and "report" in name.lower()]
        visuals = []
        visual_type_counts: dict[str, int] = {}

        for name in candidates[:80]:
            data = self._read_json_member(archive, names, name)
            if not data:
                continue
            for visual in self._extract_visuals_from_any_json(data):
                visuals.append(visual)
                visual_type = visual.get("visual_type") or "unknown"
                visual_type_counts[visual_type] = visual_type_counts.get(visual_type, 0) + 1

        if visuals:
            result["pages"] = [{
                "name": "Extracted Report JSON",
                "display_name": "Extracted Report JSON",
                "size": {},
                "visual_count": len(visuals),
                "visuals": visuals[:120],
            }]
            result["visual_type_counts"] = visual_type_counts
            result["notes"].append("Used fallback JSON extraction because classic Report/Layout was unavailable.")

    def _extract_visuals_from_any_json(self, value: Any) -> list[dict[str, Any]]:
        visuals = []
        if isinstance(value, dict):
            visual_type = value.get("visualType") or value.get("type")
            fields = sorted(self._collect_query_refs(value))[:40]
            text_content = self._extract_visible_text_entries(value)
            if visual_type or fields or text_content:
                visuals.append({
                    "visual_type": visual_type or "unknown",
                    "position": {},
                    "fields": fields,
                    "text_content": text_content,
                })
            for child in value.values():
                visuals.extend(self._extract_visuals_from_any_json(child))
        elif isinstance(value, list):
            for item in value:
                visuals.extend(self._extract_visuals_from_any_json(item))
        return visuals[:200]

    def _read_json_member(self, archive: zipfile.ZipFile, names: list[str], target: str) -> dict[str, Any] | list[Any] | None:
        member = next((name for name in names if name.replace("\\", "/").lower() == target.lower()), None)
        if not member:
            member = next((name for name in names if name.replace("\\", "/").lower().endswith(target.lower())), None)
        if not member:
            return None

        try:
            raw = archive.read(member)
            text = self._decode_text(raw)
            return json.loads(text)
        except Exception:
            return None

    def _decode_text(self, raw: bytes) -> str:
        sample = raw[:300]
        if sample.count(b"\x00") > max(8, len(sample) // 5):
            return raw.decode("utf-16-le").lstrip("\ufeff").strip()

        for encoding in ("utf-8-sig", "utf-8", "utf-16-le", "latin-1"):
            try:
                return raw.decode(encoding).lstrip("\ufeff").strip()
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore").lstrip("\ufeff").strip()

    def _parse_json_value(self, value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return json.loads(value)
        except Exception:
            return None

    def _collect_query_refs(self, value: Any) -> set[str]:
        refs: set[str] = set()
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "queryRef" and isinstance(child, str):
                    refs.add(child)
                elif key in {"field", "measure", "column"} and isinstance(child, str):
                    refs.add(child)
                elif key in {"expr", "expression"} and isinstance(child, str):
                    for match in re.findall(r"[A-Za-z_][\w ]*\[[^\]]+\]|\[[^\]]+\]", child):
                        refs.add(match)
                else:
                    refs.update(self._collect_query_refs(child))
        elif isinstance(value, list):
            for item in value:
                refs.update(self._collect_query_refs(item))
        return refs

    def _collect_text_content(self, result: dict[str, Any]) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for page in result.get("pages", []):
            page_name = page.get("display_name") or page.get("name") or "Unnamed"
            page_display = self._clean_text_value(page_name)
            if page_display:
                key = (page_name, "page", page_display)
                if key not in seen:
                    seen.add(key)
                    entries.append({
                        "page": page_name,
                        "visual_type": "page",
                        "source": "page display name",
                        "text": page_display,
                    })
            for visual in page.get("visuals", []):
                visual_type = visual.get("visual_type") or "unknown"
                for entry in visual.get("text_content", []):
                    text = entry.get("text") or ""
                    source = entry.get("source") or "unknown source"
                    key = (page_name, visual_type, text)
                    if text and key not in seen:
                        seen.add(key)
                        entries.append({
                            "page": page_name,
                            "visual_type": visual_type,
                            "source": source,
                            "text": text,
                        })
        return entries

    def _extract_visible_text_entries(self, value: Any) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        self._walk_visible_text(value, "root", entries)

        unique_entries = []
        seen: set[tuple[str, str]] = set()
        for entry in entries:
            key = (entry["source"], entry["text"])
            if key not in seen:
                seen.add(key)
                unique_entries.append(entry)
        return unique_entries

    def _walk_visible_text(self, value: Any, source: str, entries: list[dict[str, str]]) -> None:
        if isinstance(value, dict):
            literal_text = self._extract_literal_text(value)
            if literal_text:
                entries.append({"source": source, "text": literal_text})

            text_runs = value.get("textRuns")
            if isinstance(text_runs, list):
                text = "".join(
                    self._clean_text_value(run.get("value"))
                    for run in text_runs
                    if isinstance(run, dict) and self._clean_text_value(run.get("value"))
                )
                text = self._clean_text_value(text)
                if text:
                    entries.append({"source": f"{source}.textRuns", "text": text})

            for key, child in value.items():
                if key == "textRuns":
                    continue
                child_source = f"{source}.{key}"
                if isinstance(child, str) and self._looks_like_visible_text_key(key, source):
                    text = self._clean_text_value(child)
                    if text:
                        entries.append({"source": child_source, "text": text})
                self._walk_visible_text(child, child_source, entries)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self._walk_visible_text(item, f"{source}[{index}]", entries)

    def _extract_literal_text(self, value: dict[str, Any]) -> str | None:
        literal = value.get("Literal")
        if isinstance(literal, dict):
            return self._clean_text_value(literal.get("Value"))
        return None

    def _looks_like_visible_text_key(self, key: str, source: str) -> bool:
        key_lower = key.lower()
        source_lower = source.lower()
        if key_lower in {"displayname", "text", "title", "label", "caption", "alttext", "description", "header", "subtitle"}:
            return True
        if key_lower == "value":
            return any(
                marker in source_lower
                for marker in ("paragraph", "textrun", "title", "text", "label", "caption", "alttext", "literal")
            )
        return False

    def _clean_text_value(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        text = unescape(value).strip()
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
        if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
            text = text[1:-1].replace("''", "'")
        elif len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1].replace('\\"', '"')
        text = re.sub(r"[ \t]+", " ", text).strip()
        if not self._is_meaningful_text(text):
            return None
        return text

    def _is_meaningful_text(self, text: str) -> bool:
        if len(text) < 2:
            return False
        if not re.search(r"[^\W\d_]", text, re.UNICODE):
            return False
        if re.fullmatch(r"#?[0-9a-fA-F]{6,8}", text):
            return False
        if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", text):
            return False
        if re.fullmatch(r"[A-Za-z_][\w ]*\[[^\]]+\]|\[[^\]]+\]", text):
            return False
        if text.lower() in {
            "true",
            "false",
            "none",
            "auto",
            "left",
            "right",
            "center",
            "middle",
            "bold",
            "italic",
            "normal",
            "solid",
            "horizontal",
            "vertical",
            "default",
            "category",
            "measure",
            "column",
        }:
            return False
        return True


pbix_inspector = PBIXInspector()

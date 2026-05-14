import os
import uuid
import glob
import re
import io
from fastapi import UploadFile
from src.config import settings
from src.utils.errors import FileUploadError
from PIL import Image
import fitz  # pymupdf
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class FileHandler:
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.max_size = settings.max_upload_size_mb * 1024 * 1024
        self.allowed_types = {
            "image/png",
            "image/jpeg",
            "image/jpg",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "application/vnd.ms-excel.sheet.macroEnabled.12",  # PBIX
            "application/octet-stream",  # Fallback for PBIX
        }

    async def save_dashboard_image(
        self, file: UploadFile, upload_dir: str | None = None
    ) -> tuple[str, str]:
        """
        Save uploaded dashboard image, PDF, DOCX, or PBIX.

        Args:
            file: Uploaded file from request

        Returns:
            Tuple of (file_id, file_path)

        Raises:
            FileUploadError: If file validation or save fails
        """
        try:
            # Check by content type OR file extension (for PBIX)
            file_ext = os.path.splitext(file.filename)[1].lower()
            is_pbix = file_ext == ".pbix"
            allowed_extensions = {".png", ".jpg", ".jpeg", ".pdf", ".docx", ".doc", ".pbix"}

            if not (file.content_type in self.allowed_types or file_ext in allowed_extensions):
                raise FileUploadError(
                    f"Invalid file type: {file.content_type}. "
                    f"Allowed types: images (PNG/JPG), PDF, DOCX, PBIX"
                )

            # Read file content
            content = await file.read()

            # Validate file size
            if len(content) > self.max_size:
                raise FileUploadError(
                    f"File size exceeds maximum of {settings.max_upload_size_mb}MB"
                )

            # Generate unique filename
            file_id = str(uuid.uuid4())
            filename = f"{file_id}{file_ext}"
            target_dir = upload_dir or self.upload_dir
            file_path = os.path.join(target_dir, filename)

            # Create directory if it doesn't exist
            os.makedirs(target_dir, exist_ok=True)

            # Save file
            with open(file_path, "wb") as f:
                f.write(content)

            # Handle different file types
            if file_ext == ".pdf" or file.content_type == "application/pdf":
                self._convert_pdf_to_images(file_path, file_id, target_dir)
            elif file_ext in {".docx", ".doc"} or file.content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
                # Convert DOCX to PDF first, then to images
                pdf_path = self._convert_docx_to_pdf(file_path, file_id, target_dir)
                self._convert_pdf_to_images(pdf_path, file_id, target_dir)
            elif is_pbix:
                # PBIX files: inform user to export as PDF/PNG
                # For now, we just store it - user should export dashboards as PDF/PNG
                pass
            else:
                # Validate image format
                try:
                    Image.open(file_path)
                except Exception:
                    os.remove(file_path)
                    raise FileUploadError("Invalid image file")

            return file_id, file_path

        except FileUploadError:
            raise
        except Exception as e:
            raise FileUploadError(f"File upload failed: {str(e)}")

    def _convert_docx_to_pdf(
        self, docx_path: str, file_id: str, upload_dir: str | None = None
    ) -> str:
        """
        Convert DOCX to PDF using reportlab.

        Args:
            docx_path: Path to the DOCX file
            file_id: UUID of the file

        Returns:
            Path to the generated PDF file

        Raises:
            FileUploadError: If conversion fails
        """
        try:
            # Read DOCX
            doc = Document(docx_path)

            # Create PDF
            target_dir = upload_dir or self.upload_dir
            pdf_path = os.path.join(target_dir, f"{file_id}.pdf")
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            y = height - 50

            # Write text from DOCX to PDF
            c.setFont("Helvetica", 11)
            for para in doc.paragraphs:
                if para.text.strip():
                    # Simple line wrapping
                    lines = self._wrap_text(para.text, 80)
                    for line in lines:
                        c.drawString(50, y, line)
                        y -= 20
                        if y < 50:
                            c.showPage()
                            y = height - 50

            c.save()
            return pdf_path
        except Exception as e:
            raise FileUploadError(f"DOCX conversion failed: {str(e)}")

    def _wrap_text(self, text: str, width: int) -> list[str]:
        """Simple text wrapping."""
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            if len(" ".join(current_line + [word])) <= width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def _convert_pdf_to_images(
        self, pdf_path: str, file_id: str, upload_dir: str | None = None
    ) -> None:
        """
        Convert PDF pages to PNG images.

        Args:
            pdf_path: Path to the PDF file
            file_id: UUID of the file (for naming page images)

        Raises:
            FileUploadError: If PDF has too many pages or conversion fails
        """
        try:
            doc = fitz.open(pdf_path)

            # Check page count limit
            if len(doc) > settings.max_pdf_pages:
                doc.close()
                os.remove(pdf_path)
                raise FileUploadError(
                    f"PDF has {len(doc)} pages, maximum is {settings.max_pdf_pages}"
                )

            # Convert each page to PNG
            for page_num, page in enumerate(doc):
                # Render page at 2x zoom for better readability
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Save as PNG
                target_dir = upload_dir or self.upload_dir
                page_path = os.path.join(target_dir, f"{file_id}_page_{page_num}.png")
                pix.save(page_path)

            doc.close()
        except FileUploadError:
            raise
        except Exception as e:
            # Clean up PDF if conversion fails
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            raise FileUploadError(f"PDF conversion failed: {str(e)}")

    def delete_file(self, file_path: str) -> bool:
        """Delete uploaded file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def get_file_path(self, file_id: str) -> str:
        """Get file path by ID. Returns absolute path for file serving."""
        return os.path.join(self.upload_dir, f"{file_id}")

file_handler = FileHandler()

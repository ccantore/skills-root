---
name: handwritten-exam-pdf-to-markdown
description: Convert folders of handwritten exam PDFs or scanned student solutions into reviewed Markdown transcripts. Use when Codex needs to process handwritten/scanned exams, render PDF pages to images, test OCR quality, visually transcribe answers with LaTeX math, create one Markdown file per student, and produce an index plus a review checklist for unclear or low-confidence passages.
---

# Handwritten Exam PDF to Markdown

## Overview

Use this image-first workflow for handwritten or scanned exams where plain PDF text extraction is unreliable. Keep source PDFs unchanged, create durable page images, and make uncertainty visible instead of silently guessing.

## Workflow

1. Inventory the PDF folder.
   - Use `find` or `rg --files` to list PDFs.
   - Separate rosters, instructions, or answer keys from student solution PDFs unless the user asks to transcribe them too.
   - Count pages with `mdls -raw -name kMDItemNumberOfPages` on macOS when Poppler is unavailable.

2. Render pages and create a manifest.
   - Prefer the bundled script:

```bash
/Users/cristiano/.venvs/jupyter/bin/python skills/handwritten-exam-pdf-to-markdown/scripts/render_exam_pdfs.py "/path/to/pdf-folder"
```

   - The script creates:
     - `ocr-work/pages/<student>/page-XX.png`
     - `ocr-work/manifest.csv`
     - `markdown/`
   - Use high-resolution page images as the source of truth for transcription.

3. Test OCR, then decide.
   - Try local OCR only as a diagnostic, not as trusted output.
   - If Tesseract or macOS Vision OCR produces noisy, incomplete, or hallucination-prone text, switch to visual transcription from page images.
   - For student exams, do not send page images to external OCR/API services unless the user explicitly approves it.

4. Transcribe one pilot PDF first.
   - Choose a short, readable student PDF.
   - Create one Markdown file in `markdown/<Student Name>.md`.
   - Preserve the student's answer structure by page and exercise.
   - Convert clear math to LaTeX.
   - Mark ambiguous text as `[unclear]`, unfinished work as `[unfinished]`, and omitted crossed-out algebra as a short note.

5. Batch the rest in the same format.
   - Use this header:

```markdown
# Student Name

Source PDF: `../Student Name.pdf`  
Rendered pages: `../ocr-work/pages/Student Name/`  
Transcription status: visual transcription from rendered page images; handwritten OCR was not reliable.
```

   - Add `Student number shown on scan: ...` when visible.
   - Use `## Page N` sections.
   - Preserve page order even when exercises appear out of order.
   - Prefer faithful transcription over correcting the student's economics.
   - Do not transcribe bleed-through from the reverse side unless it is clearly part of the answer.

6. Create navigation and review artifacts.
   - Create `markdown/index.md` with one row per student: student name, page count, Markdown link, PDF link, image folder link.
   - Create `markdown/needs_review.csv` with columns:

```csv
student,file,page_or_section,reason
```

   - Populate it from `[unclear]`, `[unfinished]`, low-contrast pages, crossed-out derivations, and suspected student-number ambiguity.

7. Validate counts.
   - Check:
     - student PDFs count;
     - canonical rendered images count with `find ... -name 'page-*.png'`;
     - student Markdown file count, excluding `index.md`;
     - review-row count.
   - Report any scratch files or intentionally excluded PDFs.

## Transcription Rules

- Treat rendered page images as authoritative.
- Keep the student's terminology and mistakes when they are readable.
- Normalize obvious line wrapping and punctuation for readable Markdown.
- Use LaTeX for equations that are clear enough to read.
- Mark uncertainty inline rather than guessing.
- Summarize crossed-out derivations only when the final readable answer is clear.
- For exam/privacy data, keep processing local unless the user explicitly approves an external service.

## Useful Local Commands

```bash
find "exam-folder" -maxdepth 1 -type f -iname "*.pdf" -print | sort
```

```bash
for f in "exam-folder"/*.pdf; do
  pages=$(mdls -raw -name kMDItemNumberOfPages "$f" 2>/dev/null)
  printf "%s\tpages=%s\n" "$(basename "$f")" "$pages"
done
```

```bash
find "exam-folder/ocr-work/pages" -type f -name "page-*.png" | wc -l
find "exam-folder/markdown" -maxdepth 1 -type f -name "*.md" ! -name "index.md" | wc -l
```

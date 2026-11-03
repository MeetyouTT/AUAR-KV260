# Template contract

The design authority is `sources/技术文档模板.docx` (SHA256 d15a2aa186f600cb9c234bffd9deff0c4e9b05c569643d8a81d536f66f424f0c). The user requested completion from local project materials and existing SolidWorks models, with all editable text in SimSun and all displayed wall-clock times in Beijing time.

## Fixed structure and geometry

- Keep the original five parts, their order and all named fields. Do not include school, student, or author identities.
- A4 portrait, 11906 × 16838 twips. Top/bottom margins 1440 twips; left/right 1800 twips. Preserve the original section settings and original first/default/even header and footer relationships.
- Preserve the original purple competition header image and horizontal rule. Do not substitute the separate 10th-anniversary artwork. Preserve the original page field.
- Use the source paragraph patterns: centered 18 pt title; bold source part labels; 12 pt numbered field headings; 12 pt body with 1.5 line spacing. The title uses the Word Title role with its source appearance retained.
- Preserve the original numbering definitions and numbered field paragraph properties. Added narrative, captions, tables and images must not increment the field sequence.

## Authoring slots and limits

- Work name; abstract ≤800 non-whitespace characters.
- Part 1: function ≤400; applications ≤400; technical features ≤400; performance ≤200 including table text; innovation ≤200; flow ≤200.
- Part 2: overall system; hardware overview; mechanical design; circuit modules; software overview; software module details. Expand these slots with verified diagrams, CAD exports and explanatory prose.
- Part 3: overall result; mechanical/circuit/software results; quantified feature results. Distinguish real software screenshots, native CAD exports and physical photographs explicitly.
- Part 4: expansion ≤300; engineering lessons ≤1000.
- Part 5: ≤20 references. Technical sources should point to public primary documentation where available. Local evidence is supplied in the source index.

## Evidence and permitted deviations

- Replace instructional placeholder text and red instructional runs with project content. Expand the original three pages as required without reducing text size.
- All editable runs, numbering labels and page fields use 宋体; raster screenshots, logo and native CAD views retain their original glyphs. This explicitly requested typography change overrides the source's Latin Times New Roman.
- Native CAD is opened read-only from task-local copies. Do not save CAD originals. Dimensions are exact local-coordinate solid-body spans from IBody2.GetExtremePoint, rounded to 0.01 mm; they are design values rather than physical measurements.
- No fresh board experiment or movement is authorized in this subtask. Use the historical board window and model comparisons with their versions. Use the immutable latest engineering-package receipt for the offline rebuilt candidate, never claiming it was deployed.
- Only existing face-mosaic software screenshot is eligible; do not copy unredacted face images.
- The current local corpus does not yet contain a verified full-device front/45° physical photograph or final measurement drawing. State this evidence gap in the relevant results field without leaving placeholders or fabricating a photograph.

## Rendering and QA

Run the packaged render_docx.py. If LibreOffice is absent, preserve its failure log, use hidden Microsoft Word native PDF export, rasterize the PDF with bundled Poppler, and inspect every page. Keep page images internal. Check limits, numbering, source hashes, active fonts, PDF text geometry and header fidelity. Deliver DOCX and the matching PDF plus source/QA records.

# BCDK2 template contract

## Reference

- Retained source: `D:\HomePage_D\AI_Surveillance_System\docs\NguyenMinhTuan_E11_BCDK1.docx`
- SHA-256: `54EE32A6956CF9EC97C7DB0DA14F8E5E87C0B63231DDA5C636FBAF0AA51806C3`
- Cached page count: 37 pages (`docProps/app.xml`)
- Sections: 1
- Evidence: `reference_text.txt`, `style_evidence.json`, section-audit output
- Canonical LibreOffice rendering was attempted twice but LibreOffice is not
  installed. Microsoft Word PDF export was also attempted and stalled. Visual
  page rendering is therefore unresolved and must be disclosed if no later
  renderer succeeds.

## Page system

- US Letter portrait, 8.5 x 11 inches
- Margins: 1 inch on all sides
- One section, new-page start
- Header and footer distance inherited from the retained source
- Header: `Báo cáo TTTN Đại học`
- Footer: `Nhóm_E11`
- No different-first-page header/footer

## Typography

- Primary family: Times New Roman
- Body roles: source `Normal` and `Normal (Web)` styles
- Heading roles: source Heading 1 (20 pt, blue `2F5496`), Heading 2 (16 pt,
  blue), Heading 3 (14 pt, blue), Heading 4 (blue)
- New body content must be Times New Roman, 13 pt, justified, 1.3 line spacing,
  4 pt after.
- New headings must reuse the source heading styles without introducing a new
  visual system.

## Lists and tables

- Reuse the source numbering definitions.
- Reference assignment table uses `Table Grid`; progress and use-case tables
  use `Normal Table`.
- New comparison/status tables must use `Table Grid`, explicit widths totaling
  6.5 inches, repeated header rows, 0.08 inch cell margins, and no fixed row
  heights.
- New bullet lists must use the real `List Bullet` style.

## Components and content flow

- Preserve cover page, institution block, topic, team identity, gratitude,
  abbreviations, work assignment, and Chapters 1-3.
- Editable slots:
  - Cover report number: update from periodic report 1 to report 2.
  - Gratitude date: update to July 2026.
  - Introduction progress/limitations: replace BCDK1 state with verified BCDK2
    state.
  - Section 1.3.4: update report scope from period 1 to period 2.
  - Progress table: update percentages and add integration/verification rows.
  - Append a scope reconciliation after Chapter 3.
  - Append Chapters 4-6, conclusion, references, and technical appendix.
- Preserve the two source images and their relationships.
- Preserve headers, footers, styles, numbering, theme, and section geometry.

## Package preservation

- Reference package contains 21 parts.
- Preserve-only parts: `word/header1.xml`, `word/footer1.xml`,
  `word/media/image1.png`, `word/media/image2.png`, theme, relationships, and
  numbering.
- Editable parts: main document body, styles only if required for explicit
  table geometry, core/app metadata.
- Final output must be a new file and the retained reference hash must remain
  unchanged.

## Fidelity gates

- BCDK1 must remain byte-for-byte unchanged.
- Cover and recurring page furniture must remain source-derived.
- No claims may state that ROI editing, behavior-rule configuration,
  authentication, FCM push notification, or multi-camera deployment are
  implemented.
- Uploaded-video mode must be described as non-persistent.
- Live mode must be described as the only mode that stores sessions, logs,
  alerts, and snapshots.
- Verification evidence must match the completed checks: 87 backend tests,
  4 Flutter tests, clean Flutter analysis, 26 OpenAPI paths, and 7 successful
  read-only smoke endpoints.

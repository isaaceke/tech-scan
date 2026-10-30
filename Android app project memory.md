# Android app project memory

- **Export Date:** 10/26/2026, 12:12:25 PM
- **Source URL:** https://chatgpt.com/c/6adda963-7b88-83e9-aec0-efe2c06a1a20
- **Total Turns:** 12

---

### User

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### ChatGPT

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### User

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### ChatGPT

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### User

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### ChatGPT

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### User

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### ChatGPT

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### User

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### ChatGPT

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### User

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

### ChatGPT

Yesterday 8:02 AMI need to build an android app. Do you remember my failed techlog scanner project?

Yes. Your failed techlog scanner project was meant to automate the extraction and verification of handwritten aircraft technical-log data. You recently revised the approach into a Python pipeline on your Dell.

Here is what I remember.

## The original project

- Input: Approximately 200 aircraft technical-log PDF files.
- Processing: Extract the first page of each PDF and crop away the top and bottom 30%, leaving the central table region.
- OCR: Run the cropped images through 7 OCR tools — 2 inexpensive options and 5 free options.
- Reconciliation: Compare all seven outputs and determine the most likely value for each handwritten field, rather than blindly trusting one OCR engine.
- Excel output: Populate the corresponding rows in Excel using the dates and techlog numbers already available in the filenames and workbook.
- Validation: Check the extracted results against chronological and arithmetic logic without requiring the AI to visually inspect the original documents.
- Performance target: Less than 30 seconds per document.
- Live monitoring: A localhost dashboard showing progress, OCR disagreements, validation results, and records requiring manual review.

You also challenged my earlier OCR ranking because I appeared to rank myself first, so the new system needs independent comparison of actual OCR outputs, not rankings based on unsupported claims.

## Now, the Android app

I remember the scanner project, but I don't yet know exactly how you want the Android app to relate to it.

Do you want the Android app to replace the failed scanner, or should it be a mobile interface for the Python OCR pipeline running on your Dell?

No. Not the OCR. It was a mobile app

You're right. I mixed up two separate projects.

The techlog project was your DoomNotes Flutter Android app, located at:

`C:\Users\PC\Downloads\doomnotes`

What I can recover from our previous discussions:

- Technology: Flutter / Dart.
- Android build problem: The APK build failed because `isar_flutter_libs-3.1.0+1` lacked an Android namespace compatible with your Gradle setup.
- Configuration: Your project uses Gradle Kotlin DSL (`.gradle.kts`), with the app namespace `com.doomnotes.app`.
- Previous AI troubleshooting: Gemini tried modifying `android/app/build.gradle`, which did not exist in your project.
- Decision: Fix the APK build first before proceeding with the other system components.

I can recover those technical details, but I haven't recovered the actual mobile app's intended techlog-scanning features or exactly what caused the project to fail.

What was the app supposed to do when someone used it on their phone? I want to reconnect to the correct project rather than invent features.

You don't remember

I don't have the details of that mobile app in the context I can currently retrieve. I checked, and the project I found was a separate Windows app called Techlog Issue Resolver.

I confused your projects twice: first with the Python OCR pipeline, then with DoomNotes. Neither was the mobile app you meant.

I don't want to pretend I remember something I can't recover. I need to locate the earlier conversation about the mobile techlog scanner before I can accurately continue from where we stopped.

I think the name was Enugu air scanner or something

I searched the available conversation history for “Enugu Air Scanner”, but I couldn't recover the project details.

I don't currently have enough information to identify what the app did or why it failed. I won't confuse it with the Python OCR project again.

One clue would help: Was Enugu Air Scanner meant to scan aircraft technical-log pages using the phone's camera, or was it meant to do something else with aircraft records?

Essentially, I want to rebuild it right now. So, what I want to rebuild is a non-rotating camera, essentially. Basically allowing to select date and log number. So, with a shutter button. So yeah, at the top we have the aircraft serial number, we have the date, and we have the log number. In the middle we have the viewfinder. At the bottom we have the shutter and tiny thumbnails showing the scan pages that can be easily, you know, that have an X at the top that we can easily use to delete pages. The whole concept is a non-rotating camera. So you know the way a regular camera app works, where the orientation can rotate randomly. This one doesn't rotate. So no gyro involvement, essentially. The camera is locked in one location and essentially snaps in that exact position. So essentially somebody can pick an aircraft from the top, pick a date, pick a log number, and then essentially take pictures, you know, of the logbook, which is a horizontal or landscape image, the pre-flight, post-flight, checklists, which are vertical or portrait, form ones, landscape, horizontal, serviceable, the go, pictures, vertical, and once they are done, they can click the next button at the bottom right, and it essentially saves the images on the person's phone as a PDF with the correct nomenclature, like correct names and everything, right? Like so the name will contain the aircraft serial number, the aircraft, the tech log number, and the date for that particular PDF. So every group of, you know, scans using the shutter goes into a singular PDF per tech log, and then they can press next, next, and change date at the top and all that. So yeah, currently they use CamScanner, which is the problem statement actually. So CamScanner gives this issue of a self-adjusting camera. So, you know, someone can rotate their phone to take a tech log or a Form 1, and in the PDF it is rotated wrongly. Maybe it is minus 90 degrees or 90 degrees, sometimes completely upside down, 180 degrees. We also have the issue of the CamScanner logo at the bottom, and CamScanner doesn't make it very easy for people to delete error pages, right? So these are the issues we need to fix. So that was the problem statement, essentially. And then another problem statement is when they give me a CamScanner document, the name is usually CamScanner with a bunch of numbers at the back. Then I have to rename it, has split and then rename. I want that whole process to be streamlined and singular. So I am essentially getting the split and renamed files immediately with their appropriate pages.

The app should be rebuilt as a dedicated aircraft techlog scanning app, not a general-purpose document scanner.

The central design decision is that the camera interface stays fixed, while the user can photograph both landscape and portrait documents. Every capture belongs to a specific aircraft, date, and techlog number. The app then produces correctly oriented, individually named PDFs directly on the phone.

## 1. The main camera screen

## ENUGU AIR SCANNER

AIRCRAFT SERIAL NUMBER

### 5N-XXX

DATE

25 Oct 2026

LOG NUMBER

001

### FIXED VIEWFINDER

Place landscape or portrait page inside frame

CAMERA ORIENTATION LOCKED

3 pages

Next

Captured pages appear as thumbnails; each has an X to delete it.

Illustrative interface mockup, not a working camera. Aircraft details and sample values are placeholders.

The key behavior is that the interface never rotates when the phone is tilted. The shutter stays in the same location, the metadata remains visible, and the user can capture landscape and portrait documents without the controls jumping around.

## 2. The workflow

1. Select aircraft

Choose the aircraft serial number from a saved list. Avoid retyping it for every log.
2. Set date and log number

Date picker and log-number field remain at the top. New scans inherit the selected metadata.
3. Capture pages

Tap the shutter repeatedly. Each image appears in a thumbnail strip with an X to delete mistakes immediately.
4. Review and finish

Tap Next to review the captured pages, their order, and their orientation.
5. Generate the PDF

Save one PDF per techlog directly to the phone, using the correct filename. Start the next log without restarting the app.

## 3. Automatic naming and file organization

For example, the generated file could be:

`5N-XXX_TECHLOG_001_2026-10-25.pdf`

The PDF contains every page captured for that specific aircraft, log number, and date. It has no CamScanner branding.

If you later scan another techlog, that produces another PDF rather than combining unrelated logs.

## 4. The important technical requirements

| Problem | Required solution |
| --- | --- |
| Camera controls rotate | Lock the camera screen to portrait orientation. |
| Pages appear sideways or upside down | Normalize captured image orientation before building the PDF. Do not rely on EXIF metadata alone. |
| Different page orientations | Support portrait and landscape pages within the same PDF. |
| Mistaken captures | Individual thumbnail deletion and page reordering. |
| CamScanner watermark | Generate PDFs directly from the original captured images. |
| Repeated renaming and splitting | Generate one correctly named PDF per techlog at capture time. |
| Lost work | Preserve the current session and captured pages if the app is interrupted. |
| Duplicate filenames | Detect existing files and prevent accidental overwriting. |

One critical decision: locking the interface alone does not guarantee correct PDF orientation. Since you want no gyro-driven rotation, the app should use a deterministic image-orientation strategy, with an explicit portrait/landscape correction control where necessary.

## 5. Recommended implementation

Use Flutter and Dart for the Android app, with a native Android camera integration if necessary to guarantee predictable orientation behavior. Generate PDFs locally, with no mandatory cloud service or internet connection.

Before building, I need to settle one detail:

When the user turns the phone sideways to photograph a landscape techlog page, should the app:

Keep the interface fixed and let the user choose Portrait or Landscape using a control.Keep the interface fixed and automatically detect the page's orientation from the image, without using the gyroscope.Keep both the interface and captured image orientation fixed, regardless of how the phone is held.

This choice determines how we implement the camera capture pipeline and avoid recreating the rotation problem from CamScanner.

Keep the camera interface and captured image orientation fixed regardless of phone rotation. Continue designing the Android techlog scanner.

The orientation behavior is now defined: the camera interface and captured image orientation remain fixed regardless of how the user rotates the phone.

That means the app must not use the gyroscope or accelerometer to decide image rotation. It must also avoid trusting camera metadata that could cause a landscape page to appear sideways or upside down in the resulting PDF.

## Camera behavior specification

1. The entire camera interface stays in portrait orientation.
2. The shutter, metadata fields, thumbnails, delete controls, and Next button never move.
3. Every capture follows a deterministic orientation rule, independent of phone rotation.
4. Portrait and landscape pages are both supported in the same techlog.
5. A captured page can be corrected manually before PDF generation if its orientation is wrong.

One technical distinction matters: keeping the interface fixed is straightforward, but a camera sensor's physical orientation and the direction in which the document is held are separate issues. The app cannot always infer the intended reading direction from pixels alone. Manual correction is therefore the reliable fallback.

## 6. Remaining screens

![PaperWise - IzzyOnDroid F-Droid Repository](https://images.openai.com/static-rsc-4/hOskbOOrq2I69MIc1Yw2NPhiEPMTxdF6KQUUm5TetAfgeyGv8r_FnxxC3QGfM7zomMkok-6fVVF6qk7IBVVlp7f_-mkufTymInZqC645R7Z_YMx6hV4IZcBJyv6HqcQZ1SgsSnSL-CdnG1g6acxylYYvq78abhNFSi0RrV8mH4k?purpose=inline)

A. Techlog session

- Aircraft selector
- Date and log number
- Captured-page count
- Resume unfinished scans
- Start a new techlog

![Quick PDF Scan - Free Document Scanner on Android](https://images.openai.com/static-rsc-4/rnuxwV9ehiMzbf0xEMnlgAj86cjhqZ7GnKPF08zqviyQLSsLxezxdcN9eN5JYK3nqKt_nGZxT3lpYege8649wcyCYKWa1i10X-rp7FxqG2mDxmIuL3MpVXZGwVoC0n4SVHQ4J6tsK642YmVk_VESvK5RNeffPueE6GB5Id3xdxU?purpose=inline)

B. Page review

- View each captured page
- Delete unwanted pages
- Reorder pages
- Rotate a page manually by 90° or 180°
- Retake a blurred photograph

![Image To PDF Converter: Pro | Fast Offline Photo to PDF | marktandev](https://images.openai.com/static-rsc-4/4i7kI7qtmvn8uI4MxBeNpDTeGnZnoNH0bFGQFmmCjJvYTXzMEdJ5WeF3HrC-XUT20uHgxAQC8LZXDkl1AasC7g08FX5oFANyEqsF7rSnJpQcTja8qRu_tsIu_DqSw_nbdLQDn_xNbF7bUYzmM4n5BANYPJdQ27EiTAASDUiLuDw?purpose=inline)

C. Generated documents

- List saved techlog PDFs
- Search by aircraft, date, or log number
- Preview PDFs
- Share or export PDFs
- Rename files if metadata needs correction

## 7. Technical architecture

| Component | Implementation |
| --- | --- |
| App | Flutter / Dart |
| Camera | Native Android CameraX integration if Flutter camera plugins cannot guarantee the required behavior |
| Orientation | Portrait-locked activity; no sensor-driven UI rotation |
| Image processing | Normalize pixel orientation and provide manual correction |
| PDF generation | Local PDF creation, with no branding |
| Session storage | Local database plus temporary image files |
| Final storage | Android user-accessible Documents folder, using the Storage Access Framework or MediaStore as appropriate |
| Internet | Not required for scanning or PDF generation |

### PDF naming rule

Use a consistent pattern such as:

`{AIRCRAFT_SERIAL}_TECHLOG_{LOG_NUMBER}_{YYYY-MM-DD}.pdf`

For example:

`5N-ABC_TECHLOG_0042_2026-10-25.pdf`

The aircraft serial number, log number, and date must be validated before finalizing the PDF. If a filename already exists, the app must ask whether to replace it or save a distinct copy.

## 8. Acceptance tests

The first build should not be considered complete until these tests pass:

- Rotate the phone during capture. The interface remains fixed.
- Photograph a landscape page while holding the phone sideways.
- Photograph a portrait page without changing the interface layout.
- Mix portrait and landscape pages in one PDF.
- Verify that no pages appear sideways or upside down unexpectedly.
- Delete a middle page without deleting adjacent pages.
- Close and reopen the app with an unfinished session.
- Generate a PDF offline with the correct filename.
- Confirm there is no scanner watermark.
- Export the PDF and open it in a standard PDF reader.

Recommended build order: camera screen and orientation behavior first, page management second, PDF generation third, and session recovery and file management fourth. This isolates the hardest requirement—the camera orientation—before adding the rest of the application.

ChatGPT can make mistakes. Check important info.

---

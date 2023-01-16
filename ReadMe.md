# Slip Comparison Tool (Doc Compare Proto) - Textract Ver
This version uses AWS textract and resolves the document section headers programmatically (instead of using a list to search for.)
This version is slower BUT it is cleaner and could be adapted for different document "types" more successfully.

### Updated 2023-01-16
* Improved speed with futures functions
* Updated margin calcs and geometry slightly

## Instructions / Prereqs
1. Python 3.8
2. AWS Boto creds with an account with Textract permissions (using AWS CLI)s
3. pip install the relevant libraries
4. create the folders as instructed
5. launch "streamlit run Landing_Page.py" from Command Line

### Libraries
I didn't specify any versions for these when I built this, so I don't anticipate any dependency clash.
* boto3
* streamlit
* opencv-python
* PyMuPDF
* spacy (with en_core_web_md)

### Folders
Create in the root of your python project.
* ./working
* ./bold_images
* ./boldbox_working_textract
* ./pdf_images
* ./textbox_working_textract

### Known Issues
* Non Bolded Document Sections / Headers
* Document Sections that are very close to their text values.
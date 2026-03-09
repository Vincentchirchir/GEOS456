from pypdf import PdfWriter, PdfReader

files = [
    r"C:\Users\vince\OneDrive\Documents\SAIT\Winter 2026\GEOS457\Chapter 8 & 14.pdf",
    r"C:\Users\vince\OneDrive\Documents\SAIT\Winter 2026\GEOS457\GEOS_457_ColourBasics.pdf",
    r"C:\Users\vince\OneDrive\Documents\SAIT\Winter 2026\GEOS457\GEOS 457 - Proportional and Graduated Symbols.pdf",
]

writer = PdfWriter()

for path in files:
    reader = PdfReader(path)
    for page in reader.pages:
        writer.add_page(page)

output_path = "C:/Users/vince/OneDrive/Documents/SAIT/Winter 2026/GEOS457/GEOS457_merged_documents.pdf"
with open(output_path, "wb") as f:
    writer.write(f)

output_path

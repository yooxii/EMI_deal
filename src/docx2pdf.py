import os
import sys
import win32com.client as win32

def convert_docx2pdf(docx_dir):
    try:
        word = win32.Dispatch('Word.Application')
        word.Visible = False
    except:
        print("Please install Microsoft Word 2010 or later.")
        return
    for file in os.listdir(docx_dir):
        if file.endswith(".docx"):
            docx_file = os.path.join(docx_dir, file)
            pdf_file = os.path.join(docx_dir, file.replace(".docx", ".pdf"))
            doc = word.Documents.Open(os.path.abspath(docx_file))
            doc.SaveAs(os.path.abspath(pdf_file), FileFormat=17)
            # 不保存退出
            doc.Close(SaveChanges=0)
    word.Quit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python docx2pdf.py <docx_dir>")
        sys.exit(1)
    docx_dir = sys.argv[1]
    if not os.path.exists(docx_dir):
        print("Error: docx_dir not exists.")
        sys.exit(1)
    convert_docx2pdf(docx_dir)
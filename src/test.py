import os
import win32com.client as win32
from docx import Document


def addZipToExcel(self, directory, SaveFile):
    try:
        excel = win32.Dispatch("Excel.Application")
        excel.Visible = True
    except:
        print("Please install Microsoft Word 2010 or later.")
        return
    wb = excel.Workbooks.Open(os.path.abspath(SaveFile))
    ws = wb.Worksheets("Conducted EMI")
    Embed_zip = ws.OLEObjects()
    Embed_zip.Add(
        ClassType=None,
        Filename=os.path.abspath(directory),
        Link=False,
        DisplayAsIcon=True,
        Left=600,
        Top=400,
    )
    Embed_zip = ws.OLEObjects()
    wb.Save()
    # wb.Close()
    # excel.Quit()


def WordM():
    try:
        word = win32.Dispatch("Word.Application")
        # word.Visible = 0
    except:
        print("Please install Microsoft Word 2010 or later.")
        return
    doc = word.Documents.Open(
        os.path.abspath(
            "D:/Desktop_Li/WorkDir/EMC/WorkDir/test/CN58KK005V-110V-25%-L.docx"
            # "D:/Desktop_Li/WorkDir/EMC/WorkDir/test/2.docx"
        )
    )

    if doc.Tables.Count != 0:
        print(doc.Tables.Count)
        for i in range(doc.Tables.Count):
            table = doc.Tables(i + 1)
            print("Table", i + 1, end=": ")
            print("Rows:", table.Rows.Count, end=", ")
            print("Columns:", table.Columns.Count)
        table = doc.Tables(4)
        for row in range(1, table.Rows.Count + 1):
            print("Row", row, end=": ")
            for col in range(1, table.Columns.Count + 1):
                print("Col", col, end=": ")
                cell = table.Cell(row, col)
                text = (
                    cell.Range.Text.replace("\r", "@")
                    .replace("\x07", "#")
                    .replace("\n", "=")
                )
                if "@#@#1" in text:
                    import re

                    count = 1

                    def replace_func(match):
                        nonlocal count
                        replacement = f"@#@#{count}"
                        count += 1
                        return replacement

                    new_text = re.sub(r"@#@#\d+", replace_func, text)
                    print(new_text)

                    text = (
                        new_text.replace("@", "\r")
                        .replace("#", "\x07")
                        .replace("=", "\n")
                    )
                    cell.Range.Text = text
            print()
    doc.SaveAs(os.path.abspath("D:/Desktop_Li/WorkDir/EMC/WorkDir/test/3.docx"))
    doc.Close(SaveChanges=False)
    word.Quit()


# 获取所有表格的文本
def get_all_tables_text(path):
    """
    获取word中所有表格的文本
    :param path: word路径
    :return: list类型的二维数组
        如：[['年龄', '排序'], ['23', '00',], ...]
    """
    document = Document(path)
    all_tables = document.tables
    text_list = []
    print(f"Total tables: {len(all_tables)}")
    for table in all_tables:
        for row in table.rows:
            text = []
            for cell in row.cells:
                text.append(cell.text.replace("\r", " "))
            text_list.append(text)
    return text_list


def main():
    # addZipToExcel(None, "FSC048-4C0G.zip", "2.1 Conducted EMI Measurement.xlsx")
    # WordM()
    path = "D:/Desktop_Li/WorkDir/EMC/WorkDir/test/CN58KK005V-110V-25%-L.docx"
    tables_text = get_all_tables_text(path)
    print(tables_text)


if __name__ == "__main__":
    main()

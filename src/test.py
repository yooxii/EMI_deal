import os
import win32com.client as win32

def addZipToExcel(self, directory, SaveFile):
        try:
            excel = win32.Dispatch('Excel.Application')
            excel.Visible = True
        except:
            print("Please install Microsoft Word 2010 or later.")
            return
        wb = excel.Workbooks.Open(os.path.abspath(SaveFile))
        ws = wb.Worksheets("Conducted EMI")
        Embed_zip = ws.OLEObjects()
        Embed_zip.Add(ClassType=None, Filename=os.path.abspath(directory), Link=False, DisplayAsIcon=True,Left=600, Top=400)
        Embed_zip = ws.OLEObjects()
        wb.Save()
        # wb.Close()
        # excel.Quit()

if __name__ == '__main__':
    addZipToExcel(None, "FSC048-4C0G.zip", "2.1 Conducted EMI Measurement.xlsx")
import openpyxl as xl

wb = xl.load_workbook("template/2.1 Conducted EMI Measurement_3.xlsx")

ws = wb["Setup"]

ws.delete_rows(1, 4)

wb.save("2.1 Conducted EMI Measurement_3.xlsx")

print(wb.sheetnames)
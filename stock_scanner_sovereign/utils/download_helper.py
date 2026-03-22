import io, csv

def get_csv_download(data_list):
    """
    Returns a CSV blob from a list of dicts. Zero-Pandas.
    """
    if not data_list: return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data_list[0].keys())
    writer.writeheader()
    writer.writerows(data_list)
    return output.getvalue().encode('utf-8-sig')

def get_excel_download(data_list):
    """
    Dummy/Place-holder: Excel typically requires Pandas/OpenPyXL. 
    User requested 'no panda', so we provide CSV only for maximum speed.
    """
    return get_csv_download(data_list)

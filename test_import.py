import traceback
try:
    import ui_utils
    print("UI_UTILS IMPORTED SUCCESSFULLY")
except Exception as e:
    print("ERROR IMPORTING UI_UTILS:")
    traceback.print_exc()

try:
    import main
    print("MAIN IMPORTED SUCCESSFULLY")
except Exception as e:
    print("ERROR IMPORTING MAIN:")
    traceback.print_exc()

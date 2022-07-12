DEBUG = True

def info(text, module="NS"):
    print(f"[{module}][Info] {text}")


def warn(text, module="NS"):
    print(f"[{module}][Warn] {text}")


def error(text, module="NS"):
    print(f"[{module}][Error] {text}")


def debug(text, module="NS"):
    if DEBUG:
        print(f"[{module}][Debug] {text}")

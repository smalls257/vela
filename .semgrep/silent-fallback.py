def a():
    # ruleid: except-pass
    try:
        risky()
    except ValueError:
        pass

def b(cache):
    # ok: except-pass
    try:
        return cache.get()
    except KeyError as exc:
        raise LookupError("no cache entry") from exc

def c():
    # ruleid: except-pass
    try:
        risky()
    except:
        pass

def d():
    # ruleid: broad-except-not-reraised
    try:
        risky()
    except Exception as exc:
        log(exc)
        return None

def e():
    # ok: broad-except-not-reraised
    try:
        risky()
    except Exception as exc:
        raise ToolError(str(exc)) from exc

def main():
    # ok: broad-except-not-reraised
    try:
        return run()
    except Exception as exc:
        print(f"internal error: {exc!r}")
        return 2

def g(keys):
    for key in keys:
        # ruleid: except-pass
        try:
            load(key)
        except (OSError, ValueError):
            continue

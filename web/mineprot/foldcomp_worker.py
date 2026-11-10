"""Isolate the native Foldcomp decoder from the Web process."""


def decompress(connection, data: bytes) -> None:
    import foldcomp

    try:
        try:
            _, pdb = foldcomp.decompress(data)
        except foldcomp.error:
            connection.send((False, None))
        else:
            connection.send((bool(pdb), pdb.encode("utf-8")))
    finally:
        connection.close()

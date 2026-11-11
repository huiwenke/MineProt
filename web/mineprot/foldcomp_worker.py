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


def validate_loop(connection):
    import foldcomp
    import hashlib

    try:
        while True:
            try:
                data = connection.recv_bytes()
            except EOFError:
                break
            try:
                _, pdb = foldcomp.decompress(data)
                valid = any(line.startswith('ATOM  ') for line in pdb.splitlines())
            except foldcomp.error:
                valid = False
            connection.send(hashlib.sha256(pdb.encode('utf-8')).hexdigest() if valid else None)
    finally:
        connection.close()


class Validator:
    """Reuse a decoder per batch; recover after a native crash or timeout."""
    def __init__(self):
        self.process = None
        self.connection = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self.process is not None:
            if self.process.is_alive():
                self.process.kill()
            self.process.join()
            self.process.close()
            self.process = None

    def validate(self, data):
        import multiprocessing
        from . import settings

        if len(data) <= 4 or not data.startswith(b'FCMP'):
            raise ValueError('Invalid FCZ file')
        if self.process is None:
            context = multiprocessing.get_context('spawn')
            self.connection, child = context.Pipe()
            self.process = context.Process(target=validate_loop, args=(child,), daemon=True)
            try:
                self.process.start()
            except BaseException:
                self.connection.close()
                self.process.close()
                self.process = self.connection = None
                raise
            finally:
                child.close()
        try:
            self.connection.send_bytes(data)
            if not self.connection.poll(settings.FOLDCOMP_TIMEOUT):
                raise RuntimeError('FCZ validation timed out')
            digest = self.connection.recv()
            if not digest:
                raise ValueError('Invalid FCZ file')
            return digest
        except (EOFError, OSError) as exc:
            self.close()
            raise ValueError('FCZ decoder crashed; invalid FCZ file') from exc
        except RuntimeError:
            self.close()
            raise

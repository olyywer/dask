import io
import os

from toolz import concat

from ..utils import infer_compression, system_encoding
from ..delayed import delayed
from ..bytes.compression import files as cfiles, seekable_files
from ..bytes import open_text_files, read_bytes
from .core import from_delayed

delayed = delayed(pure=True)


def read_text(path, blocksize=None, compression='infer',
              encoding=system_encoding, errors='strict',
              linedelimiter=os.linesep, **kwargs):
    """ Read lines from text files

    Parameters
    ----------
    path: string
        Can include protocol like s3:// or globstrings
    blocksize: None or int
        Size to cut up larger files.  Streams by default
    compression: string
        Compression format like 'gzip' or 'xz'.  Defaults to 'infer'
    encoding: string
    errors: string
    linedelimiter: string
    **kwargs: dict
        Extra parameters to hand to backend storage system.
        Often used for authentication when using remote storage like S3 or HDFS

    Examples
    --------
    >>> b = read_text('myfiles.*.txt')  # doctest: +SKIP
    >>> b = read_text('myfiles.*.txt.gz')  # doctest: +SKIP
    >>> b = read_text('s3://bucket/myfiles.*.txt')  # doctest: +SKIP

    Parallelize a large file by providing the number of uncompressed bytes to
    load into each partition.

    >>> b = read_text('largefile.txt', chunkbytes=1e7)  # doctest: +SKIP

    Returns
    -------
    dask.bag.Bag

    See Also
    --------
    from_sequence: Build bag from Python sequence
    """
    if compression == 'infer':
        compression = infer_compression(filename)

    if blocksize and compression not in seekable_files:
        raise ValueError(
              "Compression %s does not support breaking apart files\n"
              "Use ``blocksize=None`` or decompress file externally"
              % compression)
    if compression not in seekable_files and compression not in cfiles:
        raise NotImplementedError("Compression format %s not installed" %
                                  compression)

    if blocksize is None:
        files = open_text_files(path, encoding=encoding, errors=errors,
                                      compression=compression, **kwargs)
        return from_delayed(files)

    else:
        _, blocks = read_bytes(path, delimiter=linedelimiter.encode(),
                blocksize=blocksize, sample=False, compression=compression,
                **kwargs)
        if isinstance(blocks[0], (tuple, list)):
            blocks = list(concat(blocks))
        blocks = [delayed(decode)(b, encoding, errors)
                  for b in blocks]
        result = from_delayed(blocks)

    return result


def decode(block, encoding, errors):
    text = block.decode(encoding, errors)
    lines = io.StringIO(text)
    return list(lines)

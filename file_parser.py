import re
import config


def get_reference_info_from_file(maya_file_path):
    ref_pattern = re.compile(r'file -rd.+-ns "(?P<namespace>.+)"(.+|.+\n\s.+)-rfn(.+|.+\n\s.+)"(?P<refnode>.+)"(.+|.+\n\s.+)-typ(.+|.+\n\s.+)"(?P<path>{}.+)"'.format(config.REFERENCE_DRIVE))

    file_upper_chunk = open_file(maya_file_path)
    references = []
    for match in ref_pattern.finditer(file_upper_chunk):
        references.append(match.groupdict())

    return references


def open_file(file_path):
    with open(file_path, "r") as fr:
        return fr.read(10000)


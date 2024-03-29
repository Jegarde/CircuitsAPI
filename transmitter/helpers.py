from typing import List
from datetime import datetime
from dateutil.parser import isoparse

def date_to_unix(date: str, new: bool = False) -> int:
    """
    Converts dates from RecNet to an unix timestamp, that can be used to show dates more elegantly.

    @param date: String representation of a date.
    @param new: Use the new date type
    @return: Unix date represented as an integer.
    """
        
    if new:
        timestamp = datetime.strptime(date, '%m/%d/%Y %H:%M:%S %p').timestamp()
    else:
        timestamp = isoparse(date).timestamp()
        
    return int(timestamp)  # Return UNIX timestamp

def supported_characters() -> List[str]:
    """Returns all supported characters by 'Decimal to Character' converter.

    Returns:
        List[str]: Supported characters
    """
    return [
        ' ',
        'a',
        'b',
        'c',
        'd',
        'e',
        'f',
        'g',
        'h',
        'i',
        'j',
        'k',
        'l',
        'm',
        'n',
        'o',
        'p',
        'q',
        'r',
        's',
        't',
        'u',
        'v',
        'x',
        'y',
        'z',
        'A',
        'B',
        'C',
        'D',
        'E',
        'F',
        'G',
        'H',
        'I',
        'J',
        'K',
        'L',
        'M',
        'N',
        'O',
        'P',
        'Q',
        'R',
        'S',
        'T',
        'U',
        'V',
        'X',
        'Y',
        'Z',
        '0',
        '1',
        '2',
        '3',
        '4',
        '5',
        '6',
        '7',
        '8',
        '9',
        '!',
        '"',
        '#',
        '$',
        '%',
        '&',
        '\'',
        '(',
        ')',
        '*',
        '+',
        ',',
        '-',
        '.',
        '/',
        ':',
        ';',
        '<',
        '=',
        '>',
        '?',
        '@',
        '[',
        '\\',
        ']',
        '^',
        '_',
        '`',
        '{',
        '|',
        '}',
        '~',
        "w",
        "W"
    ]